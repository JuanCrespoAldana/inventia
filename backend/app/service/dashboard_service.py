"""Panel de control (RF-031..RF-033): TODAS las cifras salen de consultas reales a la base de datos.

* El valor del inventario se calcula solo con productos que tienen costo registrado; si algún producto con
  existencias no tiene costo se indica (``valor_completo = false``) en lugar de inventar un valor.
* Las ventas anuladas no suman a ningún total.
* Cada sección solo se entrega si el usuario tiene el permiso correspondiente.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dto.comunes_dto import ParametrosPagina
from app.model.catalogo import Producto
from app.model.enums import EstadoAlerta, EstadoEjecucion, EstadoTraslado
from app.model.inventario import Alerta, InventarioSede
from app.model.operaciones import Traslado, Venta, VentaItem
from app.model.prediccion import EjecucionPrediccion, Recomendacion
from app.model.sede import Sede
from app.security.acceso import Contexto
from app.service import alertas_service, inventario_service
from app.service.alcance import resolver_filtro_sede
from app.util.niveles import AGOTADO, BAJO, EXCESIVO, sql_estado_stock
from app.util.tiempo import ahora_utc, hoy_local


def _f(v) -> float:
    return float(v or 0)


async def _inventario(db: AsyncSession, ctx: Contexto, sede_ids: list[int] | None) -> dict:
    cant, minimo = InventarioSede.cantidad, InventarioSede.stock_minimo
    estado = sql_estado_stock(cant, minimo, InventarioSede.stock_maximo)
    filtro = [InventarioSede.empresa_id == ctx.empresa_id]
    if sede_ids is not None:
        filtro.append(InventarioSede.sede_id.in_(sede_ids))

    # Una sola consulta: totales, conteo por estado y productos activos de la empresa.
    activos = (
        select(func.count()).select_from(Producto)
        .where(Producto.empresa_id == ctx.empresa_id, Producto.activo.is_(True)).scalar_subquery()
    )

    def con_estado(nombre: str):
        return func.count().filter(Producto.activo.is_(True), estado == nombre)

    t = (
        await db.execute(
            select(
                func.coalesce(func.sum(cant), 0),
                func.count(func.distinct(case((cant > 0, InventarioSede.producto_id)))),
                func.coalesce(func.sum(case((Producto.costo.is_not(None), cant * Producto.costo), else_=0)), 0),
                func.count(func.distinct(case(((cant > 0) & Producto.costo.is_(None), InventarioSede.producto_id)))),
                con_estado(AGOTADO), con_estado(BAJO), con_estado(EXCESIVO), activos,
            )
            .join(Producto, Producto.id == InventarioSede.producto_id)
            .where(*filtro)
        )
    ).one()
    return {
        "productos_activos": int(t[7]),
        "referencias_con_existencias": int(t[1]),
        "unidades_totales": int(t[0]),
        "valor_inventario": _f(t[2]),
        "productos_sin_costo": int(t[3]),
        "valor_completo": int(t[3]) == 0,
        "agotados": int(t[4]),
        "bajos": int(t[5]),
        "excesivos": int(t[6]),
    }


async def _ventas(db: AsyncSession, ctx: Contexto, sede_ids: list[int] | None, desde: date, hasta: date) -> dict:
    dias = (hasta - desde).days + 1
    inicio_anterior = desde - timedelta(days=dias)

    def filtro(d1: date, d2: date):
        c = [Venta.empresa_id == ctx.empresa_id, Venta.fecha_dia >= d1, Venta.fecha_dia <= d2]
        if sede_ids is not None:
            c.append(Venta.sede_id.in_(sede_ids))
        return c

    # Consulta 1: ventas por día y estado del período actual y del anterior (se agrupan en Python).
    total, n, anuladas, anterior_total = Decimal(0), 0, 0, Decimal(0)
    totales_dia: dict[date, tuple[float, int]] = {}
    por_dia_estado = await db.execute(
        select(Venta.fecha_dia, Venta.estado, func.sum(Venta.total), func.count())
        .where(*filtro(inicio_anterior, hasta)).group_by(Venta.fecha_dia, Venta.estado)
    )
    for dia, estado, suma, cuantas in por_dia_estado.all():
        if estado == "registrada" and dia < desde:
            anterior_total += suma
        elif estado == "registrada":
            total += suma
            n += cuantas
            totales_dia[dia] = (_f(suma), int(cuantas))
        elif estado == "anulada" and dia >= desde:
            anuladas += cuantas

    # Consulta 2: unidades vendidas por día; su suma es el total de unidades del período.
    unidades_dia = {
        d: int(u)
        for d, u in (
            await db.execute(
                select(Venta.fecha_dia, func.sum(VentaItem.cantidad)).join(VentaItem, VentaItem.venta_id == Venta.id)
                .where(*filtro(desde, hasta), Venta.estado == "registrada").group_by(Venta.fecha_dia)
            )
        ).all()
    }
    unidades = sum(unidades_dia.values())
    serie = []
    for i in range(dias):
        d = desde + timedelta(days=i)
        t, c = totales_dia.get(d, (0.0, 0))
        serie.append({"fecha": d.isoformat(), "total": t, "unidades": unidades_dia.get(d, 0), "ventas": c})

    # Consulta 3: los cinco productos más vendidos.
    top = (
        await db.execute(
            select(Producto.id, Producto.codigo, Producto.nombre, func.sum(VentaItem.cantidad).label("u"), func.sum(VentaItem.subtotal))
            .join(VentaItem, VentaItem.producto_id == Producto.id).join(Venta, Venta.id == VentaItem.venta_id)
            .where(*filtro(desde, hasta), Venta.estado == "registrada")
            .group_by(Producto.id, Producto.codigo, Producto.nombre).order_by(func.sum(VentaItem.cantidad).desc()).limit(5)
        )
    ).all()
    variacion = None
    if anterior_total > 0:
        variacion = round(float((total - anterior_total) / anterior_total * 100), 1)
    return {
        "total": _f(total), "numero_ventas": n, "unidades": unidades,
        "ticket_promedio": _f(total / n) if n else 0.0, "anuladas": anuladas,
        "total_periodo_anterior": _f(anterior_total), "variacion_pct": variacion,
        "serie_diaria": serie,
        "top_productos": [{"producto_id": i, "codigo": c, "nombre": nom, "unidades": int(u), "total": _f(t)} for i, c, nom, u, t in top],
    }


async def _por_sede(db: AsyncSession, ctx: Contexto, sede_ids: list[int] | None) -> list[dict]:
    alertas_activas = (
        select(func.count()).select_from(Alerta)
        .where(Alerta.empresa_id == ctx.empresa_id, Alerta.sede_id == Sede.id, Alerta.estado == EstadoAlerta.ACTIVA)
        .correlate(Sede).scalar_subquery()
    )
    consulta = (
        select(
            Sede.id, Sede.nombre,
            func.coalesce(func.sum(InventarioSede.cantidad), 0),
            func.coalesce(func.sum(case((Producto.costo.is_not(None), InventarioSede.cantidad * Producto.costo), else_=0)), 0),
            alertas_activas,
        )
        .outerjoin(InventarioSede, InventarioSede.sede_id == Sede.id)
        .outerjoin(Producto, Producto.id == InventarioSede.producto_id)
        .where(Sede.empresa_id == ctx.empresa_id, Sede.activa.is_(True))
        .group_by(Sede.id, Sede.nombre).order_by(Sede.nombre)
    )
    if sede_ids is not None:
        consulta = consulta.where(Sede.id.in_(sede_ids))
    return [
        {"sede_id": i, "sede": n, "unidades": int(u), "valor": _f(v), "alertas": int(al)}
        for i, n, u, v, al in (await db.execute(consulta)).all()
    ]


async def construir(db: AsyncSession, ctx: Contexto, *, sede_id: int | None, dias: int) -> dict:
    sede_ids = resolver_filtro_sede(ctx, sede_id)
    hasta = hoy_local()
    desde = hasta - timedelta(days=dias - 1)
    salida: dict = {
        "generado_en": ahora_utc().isoformat(), "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat(), "dias": dias},
        "sede_id": sede_id, "inventario": None, "ventas": None, "por_sede": None, "alertas": None,
        "traslados_pendientes": None, "recomendaciones_pendientes": None, "prediccion": None, "movimientos_recientes": None,
    }
    if ctx.tiene_alguno("inventario.ver", "inventario.consolidado"):
        salida["inventario"] = await _inventario(db, ctx, sede_ids)
        salida["por_sede"] = await _por_sede(db, ctx, sede_ids)
    if ctx.tiene("ventas.ver"):
        salida["ventas"] = await _ventas(db, ctx, sede_ids, desde, hasta)
    if ctx.tiene("alertas.ver"):
        resumen = await alertas_service.resumen(db, ctx, sede_ids)
        criticas, _ = await alertas_service.listar(
            db, ctx, ParametrosPagina(1, 5), sede_ids=sede_ids, estado="activa", tipo=None, prioridad=None, q=None, contar=False
        )
        resumen["principales"] = [
            {"id": a.id, "tipo": a.tipo, "prioridad": a.prioridad, "mensaje": a.mensaje, "sede": s.nombre, "producto": p.nombre}
            for a, p, s in criticas
        ]
        salida["alertas"] = resumen
    if ctx.tiene("traslados.ver"):
        c = [Traslado.empresa_id == ctx.empresa_id, Traslado.estado.in_((EstadoTraslado.SOLICITADO, EstadoTraslado.APROBADO))]
        if sede_ids is not None:
            c.append(Traslado.sede_origen_id.in_(sede_ids) | Traslado.sede_destino_id.in_(sede_ids))
        salida["traslados_pendientes"] = int(await db.scalar(select(func.count()).select_from(Traslado).where(*c)) or 0)
    if ctx.tiene("recomendaciones.ver"):
        c = [Recomendacion.empresa_id == ctx.empresa_id, Recomendacion.estado == "pendiente"]
        if sede_ids is not None:
            c.append(Recomendacion.sede_id.in_(sede_ids))
        salida["recomendaciones_pendientes"] = int(await db.scalar(select(func.count()).select_from(Recomendacion).where(*c)) or 0)
    if ctx.tiene("prediccion.ver"):
        ej = await db.scalar(
            select(EjecucionPrediccion).where(EjecucionPrediccion.empresa_id == ctx.empresa_id, EjecucionPrediccion.estado == EstadoEjecucion.COMPLETADA)
            .order_by(EjecucionPrediccion.finalizada_en.desc()).limit(1)
        )
        if ej:
            r = ej.resumen or {}
            salida["prediccion"] = {
                "ejecucion_id": ej.id, "finalizada_en": ej.finalizada_en.isoformat() if ej.finalizada_en else None,
                "fecha_corte": ej.fecha_corte.isoformat() if ej.fecha_corte else None, "horizonte_dias": ej.horizonte_dias,
                "series_con_prediccion": r.get("series_con_prediccion"), "series_omitidas": r.get("series_omitidas"),
                "wape_global": r.get("wape_global"), "mejora_vs_linea_base_pct": r.get("mejora_vs_linea_base_pct"),
            }
    if ctx.tiene("movimientos.ver"):
        filas, _ = await inventario_service.listar_movimientos(
            db, ctx, ParametrosPagina(1, 8), sede_id=sede_id, producto_id=None, tipo=None, desde=None, hasta=None, usuario_id=None, contar=False
        )
        salida["movimientos_recientes"] = [f.model_dump(mode="json") for f in filas]
    return salida
