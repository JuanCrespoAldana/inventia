"""Recomendaciones de reabastecimiento y de traslado (RF-029, RF-030, RNF-034).

Una recomendación es una SUGERENCIA calculada con reglas explícitas sobre la última predicción vigente
y las existencias actuales. Nunca mueve inventario ni emite compras: una persona debe aprobarla.

Reglas (los parámetros salen de la configuración de cada empresa y se documentan en docs/PREDICCION.md):
    d                  demanda diaria prevista = demanda del horizonte / días del horizonte
    punto_reposicion   max( d · (plazo_entrega + días_seguridad) , stock_mínimo )
    nivel_objetivo     d · (plazo_entrega + días_seguridad + días_cobertura_objetivo), sin pasar del stock máximo
    Se recomienda reabastecer cuando  existencias + en camino  ≤  punto_reposicion,
    por la cantidad  nivel_objetivo − (existencias + en camino).
    Antes de pedir, si otra sede tiene excedente (existencias por encima de lo que necesita para cubrir
    su propio nivel objetivo, o por encima de su stock máximo), se sugiere un TRASLADO; solo lo que
    no se pueda cubrir así se sugiere como reabastecimiento.
Estados: pendiente → aprobada → ejecutada, o pendiente → rechazada. Al regenerar, las pendientes
anteriores pasan a «reemplazada» (se conserva el historial).
"""

import math
from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.acceso import Contexto
from app.core.exceptions import Conflicto, NoEncontrado, ReglaNegocio, SinPermiso
from app.core.tiempo import ahora_utc
from app.models.catalogo import Producto
from app.models.empresa import Empresa
from app.models.enums import EstadoRecomendacion, EstadoTraslado, TipoRecomendacion
from app.models.inventario import InventarioSede
from app.models.operaciones import Traslado, TrasladoItem
from app.models.prediccion import Prediccion, Recomendacion
from app.models.sede import Sede
from app.models.usuario import Usuario
from app.schemas.catalogo import ProductoResumen
from app.schemas.comunes import ParametrosPagina
from app.schemas.inventario import ItemCantidad
from app.schemas.prediccion import RecomendacionSalida
from app.schemas.sede import SedeResumen
from app.schemas.traslados import TrasladoCrear
from app.services import alertas_service, auditoria_service, traslados_service

ABIERTOS = (EstadoTraslado.SOLICITADO, EstadoTraslado.APROBADO)
PRIORIDAD_ORDEN = {"critica": 0, "alta": 1, "media": 2, "baja": 3}


@dataclass
class _Serie:
    sede_id: int
    producto_id: int
    cantidad: int
    minimo: int
    maximo: int | None
    demanda: float  # unidades por día
    confianza: str
    modelo: str
    demanda_horizonte: float
    horizonte: int
    en_camino: int = 0
    saliendo: int = 0
    punto_reposicion: int = 0
    objetivo: int = 0
    nivel_a_conservar: int = 0
    necesidad: int = 0
    excedente: int = 0
    prioridad: str = "media"
    cobertura: float | None = None
    traslados_asignados: list = field(default_factory=list)


def _u(n: int, unidad: str) -> str:
    return f"{n} {unidad}" if unidad != "unidad" else f"{n} unidad" + ("" if n == 1 else "es")


def _decimal(valor: float, decimales: int = 1) -> str:
    """Número con coma decimal, como se escribe en español."""
    return f"{valor:.{decimales}f}".replace(".", ",")


MODELO_LEGIBLE = {
    "media_28": "promedio de 28 días",
    "media_7": "promedio de 7 días",
    "estacional_7": "perfil semanal",
    "croston_sba": "demanda intermitente",
    "ets_semanal": "suavizado exponencial estacional",
    "gbr_rezagos": "gradient boosting",
}


def _recortar(texto: str, maximo: int = 600) -> str:
    return texto if len(texto) <= maximo else texto[: maximo - 1].rstrip() + "…"


def _calcular(s: _Serie, plazo: int, seguridad: int, cobertura_objetivo: int) -> None:
    d = s.demanda
    s.punto_reposicion = max(math.ceil(d * (plazo + seguridad)), s.minimo)
    objetivo = math.ceil(d * (plazo + seguridad + cobertura_objetivo))
    if s.maximo is not None:
        objetivo = min(objetivo, s.maximo)
    s.objetivo = max(objetivo, s.punto_reposicion if s.maximo is None else min(s.punto_reposicion, s.maximo))
    s.cobertura = s.cantidad / d if d > 0 else None
    disponible = s.cantidad + s.en_camino
    if d > 0 and disponible <= s.punto_reposicion:
        s.necesidad = max(s.objetivo - disponible, 0)
    # Lo que una sede puede ceder: lo que supera su propio nivel objetivo (nunca por debajo de su mínimo).
    s.nivel_a_conservar = max(s.objetivo if d > 0 else s.minimo, s.minimo)
    if s.confianza != "baja":
        s.excedente = max(s.cantidad - s.saliendo - s.nivel_a_conservar, 0)
    if s.maximo is not None and s.cantidad > s.maximo:
        # Lo que excede el máximo configurado sobra aunque la estimación sea poco fiable.
        s.nivel_a_conservar = max(s.maximo, s.minimo) if s.confianza == "baja" else s.nivel_a_conservar
        s.excedente = max(s.excedente, s.cantidad - s.saliendo - max(s.maximo, s.minimo))
    if s.necesidad:
        if s.cobertura is not None and s.cobertura < plazo:
            s.prioridad = "critica"
        elif s.cobertura is not None and s.cobertura < plazo + seguridad:
            s.prioridad = "alta"
        else:
            s.prioridad = "media"
        if s.confianza == "baja" and s.prioridad in ("critica", "alta"):
            s.prioridad = "media"  # una estimación poco fiable no genera urgencia máxima


async def generar(db: AsyncSession, ctx: Contexto) -> dict:
    if ctx.limitado_a_sede:
        raise SinPermiso(
            "Las recomendaciones se calculan para toda la empresa: genera con un rol que no esté limitado a una sede",
            codigo="requiere_alcance_empresa",
        )
    ejecucion = await alertas_service.ultima_ejecucion_vigente(db, ctx.empresa_id)
    if ejecucion is None:
        raise ReglaNegocio(
            "No hay una predicción vigente. Genera primero la predicción de demanda (los datos no deben tener más de "
            f"{alertas_service.VIGENCIA_PREDICCION_DIAS} días).",
            codigo="sin_prediccion_vigente",
        )
    empresa = await db.get(Empresa, ctx.empresa_id)
    cfg = empresa.parametros()
    plazo, seguridad, cobertura_obj = int(cfg["plazo_entrega_dias"]), int(cfg["dias_seguridad"]), int(cfg["dias_cobertura_objetivo"])

    filas = (
        await db.execute(
            select(Prediccion, InventarioSede, Producto, Sede)
            .join(InventarioSede, (InventarioSede.sede_id == Prediccion.sede_id) & (InventarioSede.producto_id == Prediccion.producto_id))
            .join(Producto, Producto.id == Prediccion.producto_id)
            .join(Sede, Sede.id == Prediccion.sede_id)
            .where(Prediccion.ejecucion_id == ejecucion.id, Producto.activo.is_(True), Sede.activa.is_(True))
            .execution_options(populate_existing=True)
        )
    ).all()
    productos = {p.id: p for _, _, p, _ in filas}
    sedes = {s.id: s for _, _, _, s in filas}

    # Mercancía ya en camino por traslados abiertos (se resta de la necesidad y del excedente).
    en_camino: dict[tuple[int, int], int] = defaultdict(int)
    saliendo: dict[tuple[int, int], int] = defaultdict(int)
    abiertos = await db.execute(
        select(Traslado.sede_origen_id, Traslado.sede_destino_id, TrasladoItem.producto_id, TrasladoItem.cantidad)
        .join(TrasladoItem, TrasladoItem.traslado_id == Traslado.id)
        .where(Traslado.empresa_id == ctx.empresa_id, Traslado.estado.in_(ABIERTOS))
    )
    for origen, destino, producto, cantidad in abiertos.all():
        en_camino[(destino, producto)] += cantidad
        saliendo[(origen, producto)] += cantidad

    series: dict[tuple[int, int], _Serie] = {}
    for p, inv, _prod, _sede in filas:
        dias = max((p.fecha_fin - p.fecha_inicio).days + 1, 1)
        s = _Serie(
            sede_id=p.sede_id, producto_id=p.producto_id, cantidad=inv.cantidad, minimo=inv.stock_minimo,
            maximo=inv.stock_maximo, demanda=float(p.demanda_estimada) / dias, confianza=p.confianza, modelo=p.modelo,
            demanda_horizonte=float(p.demanda_estimada), horizonte=dias,
            en_camino=en_camino.get((p.sede_id, p.producto_id), 0), saliendo=saliendo.get((p.sede_id, p.producto_id), 0),
        )
        _calcular(s, plazo, seguridad, cobertura_obj)
        series[(s.sede_id, s.producto_id)] = s

    # Sedes con exceso sobre su máximo configurado aunque no tengan predicción (series omitidas).
    sin_prediccion = (
        await db.execute(
            select(InventarioSede, Producto, Sede)
            .join(Producto, Producto.id == InventarioSede.producto_id)
            .join(Sede, Sede.id == InventarioSede.sede_id)
            .where(
                InventarioSede.empresa_id == ctx.empresa_id, InventarioSede.stock_maximo.is_not(None),
                InventarioSede.cantidad > InventarioSede.stock_maximo, Producto.activo.is_(True), Sede.activa.is_(True),
            )
            .execution_options(populate_existing=True)
        )
    ).all()
    extra: dict[tuple[int, int], int] = {}
    for inv, prod, sede in sin_prediccion:
        clave = (inv.sede_id, inv.producto_id)
        if clave in series:
            continue
        productos[prod.id], sedes[sede.id] = prod, sede
        extra[clave] = max(inv.cantidad - saliendo.get(clave, 0) - inv.stock_maximo, 0)

    # Recomendaciones aprobadas aún sin ejecutar: no se duplican.
    aprobadas = {
        (r.tipo, r.sede_id, r.producto_id)
        for r in (
            await db.scalars(
                select(Recomendacion).where(
                    Recomendacion.empresa_id == ctx.empresa_id, Recomendacion.estado == EstadoRecomendacion.APROBADA
                )
            )
        ).all()
    }

    reemplazadas = (
        await db.execute(
            update(Recomendacion)
            .where(Recomendacion.empresa_id == ctx.empresa_id, Recomendacion.estado == EstadoRecomendacion.PENDIENTE)
            .values(estado=EstadoRecomendacion.REEMPLAZADA)
        )
    ).rowcount or 0

    nuevas: list[Recomendacion] = []
    necesitan = sorted(
        (s for s in series.values() if s.necesidad),
        key=lambda s: (PRIORIDAD_ORDEN[s.prioridad], s.cobertura if s.cobertura is not None else 1e9, s.sede_id),
    )
    for s in necesitan:
        producto, destino = productos[s.producto_id], sedes[s.sede_id]
        restante = s.necesidad
        donantes = [
            (clave[0], serie.excedente) for clave, serie in series.items()
            if clave[1] == s.producto_id and clave[0] != s.sede_id and serie.excedente > 0
        ] + [(clave[0], n) for clave, n in extra.items() if clave[1] == s.producto_id and clave[0] != s.sede_id and n > 0]
        donantes.sort(key=lambda x: (-x[1], x[0]))
        base_justificacion = {
            "ejecucion_id": ejecucion.id, "modelo": s.modelo, "confianza": s.confianza,
            "demanda_diaria": round(s.demanda, 2), "demanda_horizonte": round(s.demanda_horizonte, 1),
            "horizonte_dias": s.horizonte, "existencias": s.cantidad, "en_camino": s.en_camino,
            "stock_minimo": s.minimo, "stock_maximo": s.maximo, "plazo_entrega_dias": plazo, "dias_seguridad": seguridad,
            "dias_cobertura_objetivo": cobertura_obj, "punto_reposicion": s.punto_reposicion,
            "nivel_objetivo": s.objetivo, "cobertura_dias": round(s.cobertura, 1) if s.cobertura is not None else None,
            "necesidad": s.necesidad,
        }
        camino = f" (+{s.en_camino} en camino)" if s.en_camino else ""
        existencias = "sin existencias" if s.cantidad == 0 else _u(s.cantidad, producto.unidad_medida)
        # Sin existencias no tiene sentido hablar de «días que alcanzan»: la cobertura es cero.
        cobertura = "" if s.cantidad == 0 else f" y alcanzan para {_decimal(s.cobertura)} días"
        situacion = (
            f"«{producto.nombre}» en {destino.nombre}: {existencias}{camino}; se venden ≈{_decimal(s.demanda)}/día "
            f"(modelo: {MODELO_LEGIBLE.get(s.modelo, s.modelo)}; confianza {s.confianza}){cobertura}"
            f"{', pero' if s.cantidad else ' y'} reponer tarda {plazo} días + {seguridad} de seguridad."
        )
        for sede_origen_id, excedente in donantes:
            if restante <= 0:
                break
            cantidad = min(restante, excedente)
            if cantidad < 1:
                continue
            clave_traslado = (TipoRecomendacion.TRASLADO, s.sede_id, s.producto_id)
            if clave_traslado in aprobadas:
                restante = 0
                break
            origen = sedes[sede_origen_id]
            donante = series.get((sede_origen_id, s.producto_id))
            if donante:
                donante.excedente -= cantidad
                existencias_origen, conservar = donante.cantidad, donante.nivel_a_conservar
                motivo = f"le sobran {cantidad} sobre los {conservar} que necesita para cubrir su propia demanda"
            else:
                extra[(sede_origen_id, s.producto_id)] -= cantidad
                existencias_origen, conservar = (
                    next(i.cantidad for i, _, sed in sin_prediccion if sed.id == sede_origen_id and i.producto_id == s.producto_id),
                    None,
                )
                motivo = f"supera su stock máximo y puede ceder {cantidad}"
            restante -= cantidad
            nuevas.append(Recomendacion(
                empresa_id=ctx.empresa_id, ejecucion_id=ejecucion.id, tipo=TipoRecomendacion.TRASLADO,
                producto_id=s.producto_id, sede_id=s.sede_id, sede_origen_id=sede_origen_id, cantidad_sugerida=cantidad,
                prioridad=s.prioridad, estado=EstadoRecomendacion.PENDIENTE,
                resumen=_recortar(f"{situacion} {origen.nombre} tiene {_u(existencias_origen, producto.unidad_medida)} y {motivo}. "
                                  f"Se sugiere trasladar {cantidad} de {origen.nombre} a {destino.nombre}."),
                justificacion={**base_justificacion, "origen": {
                    "sede": origen.nombre, "existencias": existencias_origen, "nivel_a_conservar": conservar,
                    "excedente_cedido": cantidad}},
            ))
        if restante > 0 and (TipoRecomendacion.REABASTECIMIENTO, s.sede_id, s.producto_id) not in aprobadas:
            cubierto = s.necesidad - restante
            nota = f" Se cubren {cubierto} con traslados desde otras sedes." if cubierto else ""
            tope = " (limitado por el stock máximo)" if s.maximo is not None and s.objetivo == s.maximo else ""
            nuevas.append(Recomendacion(
                empresa_id=ctx.empresa_id, ejecucion_id=ejecucion.id, tipo=TipoRecomendacion.REABASTECIMIENTO,
                producto_id=s.producto_id, sede_id=s.sede_id, cantidad_sugerida=restante, prioridad=s.prioridad,
                estado=EstadoRecomendacion.PENDIENTE,
                resumen=_recortar(f"{situacion}{nota} Se sugiere pedir {restante} para reponer hasta {s.objetivo} unidades{tope}: "
                                  f"cubre el plazo de entrega, el colchón de seguridad y {cobertura_obj} días de ventas."),
                justificacion={**base_justificacion, "cubierto_con_traslados": cubierto},
            ))

    db.add_all(nuevas)
    await db.flush()
    resumen = {
        "ejecucion_id": ejecucion.id, "generadas": len(nuevas),
        "reabastecimientos": sum(1 for r in nuevas if r.tipo == TipoRecomendacion.REABASTECIMIENTO),
        "traslados": sum(1 for r in nuevas if r.tipo == TipoRecomendacion.TRASLADO),
        "reemplazadas": int(reemplazadas), "series_evaluadas": len(series),
    }
    await auditoria_service.registrar(db, modulo="recomendaciones", accion="generar", ctx=ctx, detalle=resumen)
    await db.commit()
    return resumen


# ------------------------------------------------------------------------------- consulta
def _alcanza(ctx: Contexto, *sedes: int | None) -> bool:
    autorizadas = ctx.sedes_autorizadas()
    return autorizadas is None or any(s in autorizadas for s in sedes if s is not None)


async def obtener(db: AsyncSession, ctx: Contexto, recomendacion_id: int) -> Recomendacion:
    r = await db.scalar(
        select(Recomendacion).where(Recomendacion.id == recomendacion_id, Recomendacion.empresa_id == ctx.empresa_id)
    )
    if r is None or not _alcanza(ctx, r.sede_id, r.sede_origen_id):
        raise NoEncontrado("La recomendación no existe")
    return r


async def listar(
    db: AsyncSession, ctx: Contexto, pag: ParametrosPagina, *, sede_ids: list[int] | None, estado: str | None,
    tipo: str | None, prioridad: str | None, q: str | None,
) -> tuple[list[Recomendacion], int]:
    base = select(Recomendacion).join(Producto, Producto.id == Recomendacion.producto_id).where(
        Recomendacion.empresa_id == ctx.empresa_id
    )
    if sede_ids is not None:
        base = base.where(or_(Recomendacion.sede_id.in_(sede_ids), Recomendacion.sede_origen_id.in_(sede_ids)))
    if estado:
        base = base.where(Recomendacion.estado == estado)
    if tipo:
        base = base.where(Recomendacion.tipo == tipo)
    if prioridad:
        base = base.where(Recomendacion.prioridad == prioridad)
    if q:
        patron = f"%{q.strip().lower()}%"
        base = base.where(func.lower(Producto.nombre).like(patron) | func.lower(Producto.codigo).like(patron))
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    orden = case(
        (Recomendacion.prioridad == "critica", 0), (Recomendacion.prioridad == "alta", 1),
        (Recomendacion.prioridad == "media", 2), else_=3,
    )
    filas = (
        await db.scalars(base.order_by(orden, Recomendacion.generada_en.desc(), Recomendacion.id).offset(pag.offset).limit(pag.tamano))
    ).all()
    return list(filas), int(total)


async def salidas(db: AsyncSession, ctx: Contexto, recomendaciones: list[Recomendacion]) -> list[RecomendacionSalida]:
    if not recomendaciones:
        return []
    productos = {p.id: p for p in (await db.scalars(select(Producto).where(Producto.id.in_({r.producto_id for r in recomendaciones})))).all()}
    ids_sede = {r.sede_id for r in recomendaciones} | {r.sede_origen_id for r in recomendaciones if r.sede_origen_id}
    sedes = {s.id: s for s in (await db.scalars(select(Sede).where(Sede.id.in_(ids_sede)))).all()}
    revisores = {r.revisada_por for r in recomendaciones if r.revisada_por}
    nombres = {u.id: u.nombre for u in (await db.scalars(select(Usuario).where(Usuario.id.in_(revisores)))).all()} if revisores else {}
    traslados = {
        t.recomendacion_id: t
        for t in (await db.scalars(select(Traslado).where(Traslado.recomendacion_id.in_([r.id for r in recomendaciones])))).all()
    }
    puede_revisar = ctx.tiene("recomendaciones.aprobar")
    resultado = []
    for r in recomendaciones:
        acciones: list[str] = []
        if puede_revisar and _alcanza(ctx, r.sede_id, r.sede_origen_id):
            if r.estado == EstadoRecomendacion.PENDIENTE:
                acciones = ["aprobar", "rechazar"]
            elif r.estado == EstadoRecomendacion.APROBADA:
                acciones = ["ejecutar"]
        t = traslados.get(r.id)
        resultado.append(RecomendacionSalida(
            id=r.id, tipo=r.tipo, prioridad=r.prioridad, estado=r.estado,
            producto=ProductoResumen.model_validate(productos[r.producto_id]), sede=SedeResumen.model_validate(sedes[r.sede_id]),
            sede_origen=SedeResumen.model_validate(sedes[r.sede_origen_id]) if r.sede_origen_id else None,
            cantidad_sugerida=r.cantidad_sugerida, resumen=r.resumen, justificacion=r.justificacion or {},
            ejecucion_id=r.ejecucion_id, generada_en=r.generada_en, revisada_por_nombre=nombres.get(r.revisada_por),
            revisada_en=r.revisada_en, comentario_revision=r.comentario_revision,
            traslado_id=t.id if t else None, traslado_numero=t.numero if t else None, acciones=acciones,
        ))
    return resultado


# ------------------------------------------------------------------------------- revisión
async def _cambiar_estado(
    db: AsyncSession, ctx: Contexto, r: Recomendacion, desde: str, hacia: str, comentario: str | None
) -> None:
    res = await db.execute(
        update(Recomendacion)
        .where(Recomendacion.id == r.id, Recomendacion.estado == desde)
        .values(estado=hacia, revisada_por=ctx.usuario_id, revisada_en=ahora_utc(), comentario_revision=comentario)
        .returning(Recomendacion.id)
    )
    if res.scalar_one_or_none() is None:
        raise Conflicto(
            f"La recomendación ya no está «{desde}». Actualiza la pantalla.", codigo="estado_cambiado"
        )


async def aprobar(db: AsyncSession, ctx: Contexto, recomendacion_id: int, comentario: str | None) -> Recomendacion:
    """Aprueba la sugerencia. Un traslado aprobado genera la SOLICITUD de traslado (que sigue su propio
    flujo de aprobación y confirmación en las sedes); un reabastecimiento queda aprobado a la espera de su
    compra, que se registra con «ejecutar»."""
    r = await obtener(db, ctx, recomendacion_id)
    if r.estado != EstadoRecomendacion.PENDIENTE:
        raise Conflicto("Solo se pueden aprobar recomendaciones pendientes", codigo="estado_invalido")
    detalle = {"tipo": r.tipo, "producto_id": r.producto_id, "sede_id": r.sede_id, "cantidad": r.cantidad_sugerida}
    if r.tipo == TipoRecomendacion.TRASLADO:
        traslado = await traslados_service.crear_traslado(
            db, ctx,
            TrasladoCrear(
                sede_origen_id=r.sede_origen_id, sede_destino_id=r.sede_id,
                observacion=f"Generado desde la recomendación #{r.id}",
                items=[ItemCantidad(producto_id=r.producto_id, cantidad=r.cantidad_sugerida)],
            ),
            recomendacion_id=r.id, confirmar=False,
        )
        await _cambiar_estado(db, ctx, r, EstadoRecomendacion.PENDIENTE, EstadoRecomendacion.EJECUTADA, comentario)
        detalle["traslado_numero"] = traslado.numero
    else:
        await _cambiar_estado(db, ctx, r, EstadoRecomendacion.PENDIENTE, EstadoRecomendacion.APROBADA, comentario)
    await auditoria_service.registrar(
        db, modulo="recomendaciones", accion="aprobar", ctx=ctx, entidad="recomendacion", entidad_id=r.id,
        sede_id=r.sede_id, detalle=detalle | {"comentario": comentario},
    )
    await db.commit()
    await db.refresh(r)
    return r


async def rechazar(db: AsyncSession, ctx: Contexto, recomendacion_id: int, comentario: str | None) -> Recomendacion:
    r = await obtener(db, ctx, recomendacion_id)
    await _cambiar_estado(db, ctx, r, EstadoRecomendacion.PENDIENTE, EstadoRecomendacion.RECHAZADA, comentario)
    await auditoria_service.registrar(
        db, modulo="recomendaciones", accion="rechazar", ctx=ctx, entidad="recomendacion", entidad_id=r.id,
        sede_id=r.sede_id, detalle={"tipo": r.tipo, "comentario": comentario},
    )
    await db.commit()
    await db.refresh(r)
    return r


async def ejecutar(db: AsyncSession, ctx: Contexto, recomendacion_id: int, comentario: str | None) -> Recomendacion:
    """Marca como realizado el reabastecimiento aprobado (la compra se gestiona fuera del sistema)."""
    r = await obtener(db, ctx, recomendacion_id)
    if r.tipo != TipoRecomendacion.REABASTECIMIENTO:
        raise ReglaNegocio("Los traslados se ejecutan desde el módulo de traslados", codigo="tipo_invalido")
    res = await db.execute(
        update(Recomendacion)
        .where(Recomendacion.id == r.id, Recomendacion.estado == EstadoRecomendacion.APROBADA)
        .values(estado=EstadoRecomendacion.EJECUTADA, comentario_revision=comentario or Recomendacion.comentario_revision)
        .returning(Recomendacion.id)
    )
    if res.scalar_one_or_none() is None:
        raise Conflicto("Solo se pueden ejecutar recomendaciones aprobadas", codigo="estado_invalido")
    await auditoria_service.registrar(
        db, modulo="recomendaciones", accion="ejecutar", ctx=ctx, entidad="recomendacion", entidad_id=r.id,
        sede_id=r.sede_id, detalle={"cantidad": r.cantidad_sugerida, "comentario": comentario},
    )
    await db.commit()
    await db.refresh(r)
    return r
