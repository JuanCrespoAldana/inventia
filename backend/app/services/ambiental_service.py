"""Gestión ambiental: contribución estimada de los vehículos eléctricos vendidos.

Principios (ver docs/DECISIONES.md):
 * Se distingue lo REAL (unidades vendidas en ventas confirmadas y no anuladas) de lo ESTIMADO (CO₂ evitado).
 * No hay cifras inventadas: la estimación solo existe si la administración configura el factor de emisión de
   la red, y por categoría de vehículo: recorrido anual, consumo eléctrico y emisión del escenario de referencia.
   Sin parámetros, las unidades se cuentan igual y el CO₂ queda «pendiente de parametrización».
 * Solo cuentan las categorías marcadas como «vehículo» por la administración.
 * Cada línea de venta se cuenta UNA sola vez (índice único). Al anular una venta, sus registros pasan a
   «anulado» y dejan de sumar. Los parámetros usados se guardan en cada registro: cambiar la configuración
   después no altera lo ya calculado.

Fórmula (por unidad vendida)::

    CO₂ evitado (kg) = distancia_anual_km × horizonte_años × ( emisión_ref (g/km) / 1000 − consumo (kWh/100 km) / 100 × FE_red (kg/kWh) )
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import extract, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.acceso import Contexto
from app.core.exceptions import NoEncontrado, ReglaNegocio
from app.core.sql import insertar
from app.core.tiempo import ahora_utc, hoy_local
from app.models.ambiental import AmbCategoria, AmbConfiguracion, AmbRegistro
from app.models.catalogo import Categoria, Producto
from app.models.operaciones import Venta, VentaItem
from app.models.sede import Sede
from app.schemas.ambiental import (
    CategoriaAmbientalActualizar,
    CategoriaAmbientalSalida,
    Cifras,
    CifrasAnio,
    CifrasMes,
    CifrasTipo,
    ConfiguracionAmbiental,
    FactorRedActualizar,
    FactorRedSalida,
    Parametrizacion,
    RegistroAmbiental,
    ResultadoSincronizacion,
    ResumenAmbiental,
)
from app.schemas.catalogo import ProductoResumen
from app.schemas.comunes import ParametrosPagina
from app.schemas.sede import SedeResumen
from app.services import auditoria_service
from app.services.alcance import resolver_filtro_sede

MILESIMA = Decimal("0.001")
CERO = Decimal("0")


# --------------------------------------------------------------------------- fórmula


def co2_por_unidad(
    cfg: AmbCategoria | None, factor_red: Decimal | None
) -> tuple[Decimal | None, dict | None]:
    """CO₂ evitado por unidad (kg) y la copia de los parámetros usados; ``(None, None)`` si faltan datos."""
    if cfg is None or factor_red is None or None in (cfg.distancia_anual_km, cfg.consumo_kwh_100km, cfg.emision_referencia_gco2_km):
        return None, None
    referencia_kg_km = Decimal(cfg.emision_referencia_gco2_km) / 1000
    electrico_kg_km = Decimal(cfg.consumo_kwh_100km) / 100 * Decimal(factor_red)
    valor = (Decimal(cfg.distancia_anual_km) * cfg.horizonte_anios * (referencia_kg_km - electrico_kg_km)).quantize(
        MILESIMA, rounding=ROUND_HALF_UP
    )
    parametros = {
        "distancia_anual_km": str(cfg.distancia_anual_km), "horizonte_anios": cfg.horizonte_anios,
        "consumo_kwh_100km": str(cfg.consumo_kwh_100km), "emision_referencia_gco2_km": str(cfg.emision_referencia_gco2_km),
        "factor_red_kgco2_kwh": str(factor_red), "co2_por_unidad_kg": str(valor),
        "vehiculo_referencia": cfg.vehiculo_referencia, "fuente": cfg.fuente,
    }
    return valor, parametros


async def _factor_red(db: AsyncSession, empresa_id: int) -> Decimal | None:
    valor = await db.scalar(select(AmbConfiguracion.factor_red_kgco2_kwh).where(AmbConfiguracion.empresa_id == empresa_id))
    return Decimal(valor) if valor is not None else None


# --------------------------------------------------------------------------- integración con ventas


async def contabilizar_venta(db: AsyncSession, venta: Venta, productos: dict[int, Producto]) -> int:
    """Registra las líneas de la venta que sean vehículos. Se llama DENTRO de la transacción de la venta."""
    categorias = {p.categoria_id for p in productos.values()}
    configs = {
        c.categoria_id: c
        for c in (
            await db.scalars(select(AmbCategoria).where(AmbCategoria.categoria_id.in_(categorias), AmbCategoria.activa.is_(True)))
        ).all()
    }
    if not configs:
        return 0
    factor = await _factor_red(db, venta.empresa_id)
    filas = []
    for item in venta.items:
        producto = productos[item.producto_id]
        cfg = configs.get(producto.categoria_id)
        if cfg is None:
            continue
        por_unidad, parametros = co2_por_unidad(cfg, factor)
        filas.append(
            {
                "empresa_id": venta.empresa_id, "venta_id": venta.id, "venta_item_id": item.id, "sede_id": venta.sede_id,
                "producto_id": item.producto_id, "categoria_id": producto.categoria_id, "fecha": venta.fecha_dia,
                "unidades": item.cantidad, "tipo_vehiculo": cfg.tipo_vehiculo, "propulsion": cfg.propulsion,
                "estado": "activo",
                "co2_evitado_kg": por_unidad * item.cantidad if por_unidad is not None else None,
                "parametros": parametros, "calculado_en": ahora_utc() if por_unidad is not None else None,
            }
        )
    if filas:
        await db.execute(insertar(db, AmbRegistro).values(filas).on_conflict_do_nothing(index_elements=["venta_item_id"]))
    return len(filas)


async def anular_venta(db: AsyncSession, venta_id: int) -> None:
    """Las líneas de una venta anulada dejan de contarse (se conservan marcadas como anuladas)."""
    await db.execute(
        update(AmbRegistro).where(AmbRegistro.venta_id == venta_id, AmbRegistro.estado == "activo")
        .values(estado="anulado", anulado_en=ahora_utc())
    )


async def sincronizar(db: AsyncSession, empresa_id: int) -> ResultadoSincronizacion:
    """Pone al día el registro: (1) incorpora ventas anteriores de categorías de vehículo que aún no se cuentan y
    (2) calcula el CO₂ de los registros que estaban pendientes si ya hay parámetros. Es idempotente."""
    configs = {
        c.categoria_id: c
        for c in (await db.scalars(select(AmbCategoria).where(AmbCategoria.empresa_id == empresa_id, AmbCategoria.activa.is_(True)))).all()
    }
    if not configs:
        return ResultadoSincronizacion(incorporados=0, calculados=0)
    factor = await _factor_red(db, empresa_id)

    faltantes = (
        await db.execute(
            select(
                VentaItem.id, VentaItem.venta_id, VentaItem.producto_id, VentaItem.cantidad, Venta.sede_id, Venta.fecha_dia,
                Producto.categoria_id,
            )
            .join(Venta, Venta.id == VentaItem.venta_id)
            .join(Producto, Producto.id == VentaItem.producto_id)
            .where(
                Venta.empresa_id == empresa_id, Venta.estado == "registrada", Producto.categoria_id.in_(list(configs)),
                ~select(AmbRegistro.id).where(AmbRegistro.venta_item_id == VentaItem.id).exists(),
            )
        )
    ).all()
    filas = []
    for item_id, venta_id, producto_id, cantidad, sede_id, fecha_dia, categoria_id in faltantes:
        cfg = configs[categoria_id]
        por_unidad, parametros = co2_por_unidad(cfg, factor)
        filas.append(
            {
                "empresa_id": empresa_id, "venta_id": venta_id, "venta_item_id": item_id, "sede_id": sede_id,
                "producto_id": producto_id, "categoria_id": categoria_id, "fecha": fecha_dia, "unidades": cantidad,
                "tipo_vehiculo": cfg.tipo_vehiculo, "propulsion": cfg.propulsion, "estado": "activo",
                "co2_evitado_kg": por_unidad * cantidad if por_unidad is not None else None,
                "parametros": parametros, "calculado_en": ahora_utc() if por_unidad is not None else None,
            }
        )
    for i in range(0, len(filas), 500):
        await db.execute(insertar(db, AmbRegistro).values(filas[i : i + 500]).on_conflict_do_nothing(index_elements=["venta_item_id"]))

    calculados = 0
    for categoria_id, cfg in configs.items():
        por_unidad, parametros = co2_por_unidad(cfg, factor)
        if por_unidad is None:
            continue
        res = await db.execute(
            update(AmbRegistro)
            .where(AmbRegistro.empresa_id == empresa_id, AmbRegistro.categoria_id == categoria_id,
                   AmbRegistro.estado == "activo", AmbRegistro.co2_evitado_kg.is_(None))
            .values(co2_evitado_kg=AmbRegistro.unidades * por_unidad, parametros=parametros, calculado_en=ahora_utc())
        )
        calculados += res.rowcount or 0
    return ResultadoSincronizacion(incorporados=len(filas), calculados=calculados)


# --------------------------------------------------------------------------- configuración


def _factor_salida(cfg: AmbConfiguracion | None) -> FactorRedSalida:
    if cfg is None:
        return FactorRedSalida(valor=None, anio=None, fuente=None)
    return FactorRedSalida(valor=cfg.factor_red_kgco2_kwh, anio=cfg.factor_red_anio, fuente=cfg.factor_red_fuente)


async def obtener_configuracion(db: AsyncSession, ctx: Contexto) -> ConfiguracionAmbiental:
    cfg_red = await db.get(AmbConfiguracion, ctx.empresa_id)
    factor = Decimal(cfg_red.factor_red_kgco2_kwh) if cfg_red and cfg_red.factor_red_kgco2_kwh is not None else None
    categorias = (await db.execute(
        select(Categoria, AmbCategoria).outerjoin(AmbCategoria, AmbCategoria.categoria_id == Categoria.id)
        .where(Categoria.empresa_id == ctx.empresa_id).order_by(func.lower(Categoria.nombre))
    )).all()
    vendidas = {
        (c, p): int(u)
        for c, p, u in (await db.execute(
            select(AmbRegistro.categoria_id, AmbRegistro.co2_evitado_kg.is_(None), func.sum(AmbRegistro.unidades))
            .where(AmbRegistro.empresa_id == ctx.empresa_id, AmbRegistro.estado == "activo")
            .group_by(AmbRegistro.categoria_id, AmbRegistro.co2_evitado_kg.is_(None))
        )).all()
    }
    salida = []
    for categoria, cfg in categorias:
        por_unidad, _ = co2_por_unidad(cfg, factor)
        base = dict(categoria_id=categoria.id, categoria_nombre=categoria.nombre, es_vehiculo=cfg is not None)
        if cfg is not None:
            base.update(
                activa=cfg.activa, tipo_vehiculo=cfg.tipo_vehiculo, propulsion=cfg.propulsion,
                distancia_anual_km=cfg.distancia_anual_km, consumo_kwh_100km=cfg.consumo_kwh_100km,
                vehiculo_referencia=cfg.vehiculo_referencia, emision_referencia_gco2_km=cfg.emision_referencia_gco2_km,
                horizonte_anios=cfg.horizonte_anios, fuente=cfg.fuente, parametros_completos=por_unidad is not None,
                co2_por_unidad_kg=por_unidad,
            )
        sin = vendidas.get((categoria.id, True), 0)
        base.update(unidades_vendidas=vendidas.get((categoria.id, False), 0) + sin, unidades_sin_parametrizar=sin)
        salida.append(CategoriaAmbientalSalida(**base))
    return ConfiguracionAmbiental(factor_red=_factor_salida(cfg_red), categorias=salida, puede_configurar=ctx.tiene("ambiental.configurar"))


async def guardar_factor_red(db: AsyncSession, ctx: Contexto, datos: FactorRedActualizar) -> ResultadoSincronizacion:
    ctx.exigir("ambiental.configurar")
    cfg = await db.get(AmbConfiguracion, ctx.empresa_id)
    antes = _factor_salida(cfg).model_dump()
    if cfg is None:
        cfg = AmbConfiguracion(empresa_id=ctx.empresa_id)
        db.add(cfg)
    cfg.factor_red_kgco2_kwh, cfg.factor_red_anio, cfg.factor_red_fuente = datos.valor, datos.anio, datos.fuente
    cfg.actualizado_por = ctx.usuario_id
    await db.flush()
    resultado = await sincronizar(db, ctx.empresa_id)
    await auditoria_service.registrar(
        db, modulo="ambiental", accion="factor_red", ctx=ctx, entidad="amb_configuracion", entidad_id=ctx.empresa_id,
        detalle={"antes": antes, "despues": {"valor": datos.valor, "anio": datos.anio, "fuente": datos.fuente},
                 "calculados": resultado.calculados},
    )
    await db.commit()
    return resultado


async def guardar_categoria(
    db: AsyncSession, ctx: Contexto, categoria_id: int, datos: CategoriaAmbientalActualizar
) -> ResultadoSincronizacion:
    ctx.exigir("ambiental.configurar")
    categoria = await db.scalar(select(Categoria).where(Categoria.id == categoria_id, Categoria.empresa_id == ctx.empresa_id))
    if categoria is None:
        raise NoEncontrado("La categoría no existe")
    cfg = await db.scalar(select(AmbCategoria).where(AmbCategoria.categoria_id == categoria_id))
    nueva = cfg is None
    if nueva:
        cfg = AmbCategoria(empresa_id=ctx.empresa_id, categoria_id=categoria_id)
        db.add(cfg)
    for campo, valor in datos.model_dump().items():
        setattr(cfg, campo, valor)
    cfg.actualizado_por = ctx.usuario_id
    await db.flush()
    resultado = await sincronizar(db, ctx.empresa_id)
    await auditoria_service.registrar(
        db, modulo="ambiental", accion="configurar_categoria", ctx=ctx, entidad="categoria", entidad_id=categoria_id,
        detalle={"categoria": categoria.nombre, "nueva": nueva, **datos.model_dump(), "incorporados": resultado.incorporados,
                 "calculados": resultado.calculados},
    )
    await db.commit()
    return resultado


async def ejecutar_sincronizacion(db: AsyncSession, ctx: Contexto) -> ResultadoSincronizacion:
    ctx.exigir("ambiental.configurar")
    resultado = await sincronizar(db, ctx.empresa_id)
    await auditoria_service.registrar(
        db, modulo="ambiental", accion="sincronizar", ctx=ctx, entidad="empresa", entidad_id=ctx.empresa_id,
        detalle=resultado.model_dump(),
    )
    await db.commit()
    return resultado


# --------------------------------------------------------------------------- panel


async def _parametrizacion(db: AsyncSession, empresa_id: int) -> Parametrizacion:
    factor = await _factor_red(db, empresa_id)
    configs = (await db.scalars(select(AmbCategoria).where(AmbCategoria.empresa_id == empresa_id, AmbCategoria.activa.is_(True)))).all()
    completas = sum(1 for c in configs if co2_por_unidad(c, factor)[0] is not None)
    if not configs:
        estado, mensaje = "sin_categorias", "Aún no hay categorías marcadas como vehículo: no se cuentan ventas. Configúralas en la pestaña Configuración."
    elif completas == 0:
        estado, mensaje = "pendiente", "Pendiente de parametrización: se cuentan los vehículos vendidos, pero el CO₂ evitado no se puede estimar hasta configurar el factor de la red y los parámetros de cada vehículo."
    elif completas < len(configs):
        estado, mensaje = "parcial", "Parametrización parcial: el CO₂ estimado solo incluye las categorías con parámetros completos."
    else:
        estado, mensaje = "completa", "Parametrización completa: el CO₂ evitado es una estimación calculada con los parámetros configurados."
    return Parametrizacion(
        estado=estado, mensaje=mensaje, categorias_vehiculo=len(configs), categorias_parametrizadas=completas,
        factor_red_definido=factor is not None,
    )


def _cifras(unidades, co2, sin) -> dict:
    return dict(unidades=int(unidades or 0), co2_estimado_kg=co2 if co2 is not None else CERO, unidades_sin_parametrizar=int(sin or 0))


async def resumen(db: AsyncSession, ctx: Contexto, anio: int | None, sede_id: int | None) -> ResumenAmbiental:
    sede_ids = resolver_filtro_sede(ctx, sede_id)
    condiciones = [AmbRegistro.empresa_id == ctx.empresa_id, AmbRegistro.estado == "activo"]
    if sede_ids is not None:
        condiciones.append(AmbRegistro.sede_id.in_(sede_ids))
    hoy = hoy_local()
    anio = anio or hoy.year
    sin_param = func.coalesce(func.sum(AmbRegistro.unidades).filter(AmbRegistro.co2_evitado_kg.is_(None)), 0)
    columnas = (func.coalesce(func.sum(AmbRegistro.unidades), 0), func.coalesce(func.sum(AmbRegistro.co2_evitado_kg), 0), sin_param)

    year_expr = extract("year", AmbRegistro.fecha)
    month_expr = extract("month", AmbRegistro.fecha)

    por_anio = {int(a): _cifras(*vals) for a, *vals in (await db.execute(select(year_expr, *columnas).where(*condiciones).group_by(year_expr))).all()}
    por_mes = {
        int(m): _cifras(*vals)
        for m, *vals in (await db.execute(select(month_expr, *columnas).where(*condiciones, year_expr == anio).group_by(month_expr))).all()
    }
    por_tipo = (await db.execute(
        select(AmbRegistro.tipo_vehiculo, *columnas).where(*condiciones, year_expr == anio).group_by(AmbRegistro.tipo_vehiculo)
        .order_by(func.sum(AmbRegistro.unidades).desc())
    )).all()
    mes_actual = (await db.execute(
        select(*columnas).where(*condiciones, year_expr == hoy.year, month_expr == hoy.month)
    )).one()
    total = (await db.execute(select(*columnas).where(*condiciones))).one()

    vacio = _cifras(0, None, 0)
    return ResumenAmbiental(
        anio=anio, parametrizacion=await _parametrizacion(db, ctx.empresa_id),
        mes_actual=Cifras(**_cifras(*mes_actual)),
        anio_seleccionado=Cifras(**por_anio.get(anio, vacio)),
        acumulado=Cifras(**_cifras(*total)),
        meses=[CifrasMes(mes=m, **por_mes.get(m, vacio)) for m in range(1, 13)],
        anios=[CifrasAnio(anio=a, **por_anio[a]) for a in sorted(por_anio)],
        por_tipo=[CifrasTipo(tipo_vehiculo=t, **_cifras(u, c, s)) for t, u, c, s in por_tipo],
        anios_disponibles=sorted(set(por_anio) | {hoy.year}, reverse=True),
    )


async def listar_registros(
    db: AsyncSession, ctx: Contexto, pag: ParametrosPagina, *, sede_id: int | None, desde: date | None, hasta: date | None,
    tipo_vehiculo: str | None, estado: str | None, pendientes: bool | None,
) -> tuple[list[RegistroAmbiental], int]:
    condiciones = [AmbRegistro.empresa_id == ctx.empresa_id]
    sede_ids = resolver_filtro_sede(ctx, sede_id)
    if sede_ids is not None:
        condiciones.append(AmbRegistro.sede_id.in_(sede_ids))
    if desde:
        condiciones.append(AmbRegistro.fecha >= desde)
    if hasta:
        condiciones.append(AmbRegistro.fecha <= hasta)
    if tipo_vehiculo:
        condiciones.append(AmbRegistro.tipo_vehiculo == tipo_vehiculo)
    if estado:
        condiciones.append(AmbRegistro.estado == estado)
    if pendientes is not None:
        condiciones.append(AmbRegistro.co2_evitado_kg.is_(None) if pendientes else AmbRegistro.co2_evitado_kg.is_not(None))
    total = await db.scalar(select(func.count()).select_from(AmbRegistro).where(*condiciones)) or 0
    filas = (await db.scalars(
        select(AmbRegistro).where(*condiciones).order_by(AmbRegistro.fecha.desc(), AmbRegistro.id.desc())
        .offset(pag.offset).limit(pag.tamano)
    )).all()
    if not filas:
        return [], total
    sedes = {s.id: s for s in (await db.scalars(select(Sede).where(Sede.id.in_({f.sede_id for f in filas})))).all()}
    productos = {p.id: p for p in (await db.scalars(select(Producto).where(Producto.id.in_({f.producto_id for f in filas})))).all()}
    categorias = {c.id: c.nombre for c in (await db.scalars(select(Categoria).where(Categoria.id.in_({f.categoria_id for f in filas})))).all()}
    ventas = {i: n for i, n in (await db.execute(select(Venta.id, Venta.numero).where(Venta.id.in_({f.venta_id for f in filas})))).all()}
    return [
        RegistroAmbiental(
            id=f.id, fecha=f.fecha, venta_id=f.venta_id, venta_numero=ventas.get(f.venta_id),
            sede=SedeResumen.model_validate(sedes[f.sede_id]), producto=ProductoResumen.model_validate(productos[f.producto_id]),
            categoria=categorias.get(f.categoria_id), tipo_vehiculo=f.tipo_vehiculo, propulsion=f.propulsion, unidades=f.unidades,
            estado=f.estado, parametrizado=f.co2_evitado_kg is not None, co2_estimado_kg=f.co2_evitado_kg, anulado_en=f.anulado_en,
        )
        for f in filas
    ], total
