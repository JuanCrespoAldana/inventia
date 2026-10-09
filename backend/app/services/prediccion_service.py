"""Predicción de demanda: solicitud, ejecución en segundo plano y consulta (RF-025 a RF-028).

Reglas de operación:
 * Solo puede haber UNA ejecución activa por empresa (en cola o ejecutando).
 * La ejecución corre fuera de la petición HTTP; el cálculo pesado va en un hilo para no bloquear la API.
 * Una ejecución que quedó «colgada» (el proceso se reinició) se marca como fallida pasado su tiempo máximo.
 * Al terminar con éxito se recalculan las alertas de riesgo de desabastecimiento.
 * Las predicciones son ESTIMACIONES y se guardan aparte de las ventas reales.
"""

import asyncio
import logging
from datetime import date, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.acceso import Contexto
from app.core.config import settings
from app.core.database import fabrica_de_sesiones
from app.core.exceptions import Conflicto, NoEncontrado, SinPermiso
from app.core.sql import bloqueo_asesor
from app.core.tiempo import ahora_utc, asegurar_utc, hoy_local
from app.ml import datos, pipeline
from app.ml.modelos import CANDIDATOS, LINEA_BASE, POR_NOMBRE
from app.models.catalogo import Producto
from app.models.empresa import Empresa
from app.models.enums import EstadoEjecucion
from app.models.inventario import InventarioSede
from app.models.prediccion import EjecucionPrediccion, Prediccion
from app.models.sede import Sede
from app.models.usuario import Usuario
from app.schemas.comunes import ParametrosPagina
from app.schemas.prediccion import EjecucionSalida, PrediccionSalida, SerieDemanda
from app.schemas.catalogo import ProductoResumen
from app.schemas.sede import SedeResumen
from app.services import alertas_service, auditoria_service
from app.services.alcance import obtener_sede_autorizada

logger = logging.getLogger("inventia.prediccion")

ACTIVAS = (EstadoEjecucion.EN_COLA, EstadoEjecucion.EJECUTANDO)
MAX_OMITIDAS_EN_RESUMEN = 1000
_CLAVE_BLOQUEO = 7_100_000  # + empresa_id: serializa la creación de ejecuciones de una empresa


def descripcion_modelo(nombre: str) -> str:
    c = POR_NOMBRE.get(nombre)
    return c.descripcion if c else nombre


# --------------------------------------------------------------------------------- solicitud
def _vencida(e: EjecucionPrediccion) -> bool:
    referencia = e.iniciada_en or e.creada_en
    return (ahora_utc() - asegurar_utc(referencia)).total_seconds() > settings.ml_tiempo_maximo_segundos + 300


async def cerrar_ejecuciones_colgadas(db: AsyncSession, empresa_id: int | None = None) -> int:
    """Marca como fallidas las ejecuciones activas que superaron su tiempo máximo (proceso caído)."""
    consulta = select(EjecucionPrediccion).where(EjecucionPrediccion.estado.in_(ACTIVAS))
    if empresa_id is not None:
        consulta = consulta.where(EjecucionPrediccion.empresa_id == empresa_id)
    cerradas = 0
    for e in (await db.scalars(consulta)).all():
        if _vencida(e):
            e.estado = EstadoEjecucion.FALLIDA
            e.error = "La ejecución se interrumpió antes de terminar (el servicio se reinició o superó el tiempo máximo)."
            e.finalizada_en = ahora_utc()
            cerradas += 1
    if cerradas:
        await db.flush()
    return cerradas


async def solicitar(db: AsyncSession, ctx: Contexto, horizonte_dias: int | None) -> EjecucionPrediccion:
    if ctx.limitado_a_sede:
        raise SinPermiso(
            "La predicción se calcula para toda la empresa: solicítala con un rol que no esté limitado a una sede",
            codigo="requiere_alcance_empresa",
        )
    await bloqueo_asesor(db, _CLAVE_BLOQUEO + ctx.empresa_id)
    await cerrar_ejecuciones_colgadas(db, ctx.empresa_id)
    activa = await db.scalar(
        select(EjecucionPrediccion.id).where(
            EjecucionPrediccion.empresa_id == ctx.empresa_id, EjecucionPrediccion.estado.in_(ACTIVAS)
        )
    )
    if activa is not None:
        await db.commit()  # conserva el cierre de ejecuciones colgadas, si hubo
        raise Conflicto(
            "Ya hay una predicción en curso. Espera a que termine para solicitar otra.", codigo="ejecucion_en_curso",
            extra={"ejecucion_id": activa},
        )
    empresa = await db.get(Empresa, ctx.empresa_id)
    cfg = empresa.parametros()
    horizonte = horizonte_dias or int(cfg["horizonte_dias"])
    corte = hoy_local() - timedelta(days=1)  # último día completo
    ejecucion = EjecucionPrediccion(
        empresa_id=ctx.empresa_id, usuario_id=ctx.usuario_id, estado=EstadoEjecucion.EN_COLA, horizonte_dias=horizonte,
        fecha_corte=corte,
        parametros={
            "horizonte_dias": horizonte,
            "historia_maxima_dias": settings.ml_historia_maxima_dias,
            "minimo_dias_historia": pipeline.MIN_DIAS_HISTORIA,
            "minimo_dias_con_ventas": pipeline.MIN_DIAS_CON_VENTAS,
            "modelos": [{"nombre": c.nombre, "avanzado": c.avanzado, "descripcion": c.descripcion} for c in CANDIDATOS],
            "linea_base": LINEA_BASE,
            "mejora_minima_modelo_avanzado_pct": pipeline.MEJORA_MINIMA_AVANZADO * 100,
            "intervalo": "80 %",
            "demanda": "unidades vendidas por día local (ventas registradas; las anuladas no cuentan)",
        },
        resumen={},
    )
    db.add(ejecucion)
    await db.flush()
    await auditoria_service.registrar(
        db, modulo="prediccion", accion="ejecutar", ctx=ctx, entidad="ejecucion_prediccion", entidad_id=ejecucion.id,
        detalle={"horizonte_dias": horizonte, "fecha_corte": corte},
    )
    await db.commit()
    await db.refresh(ejecucion)
    return ejecucion


# ------------------------------------------------------------------------------ ejecución
async def ejecutar_en_segundo_plano(ejecucion_id: int) -> None:
    """Corre la ejecución con su propia sesión. Nunca lanza: cualquier fallo queda registrado en la ejecución."""
    fabrica = fabrica_de_sesiones()
    try:
        async with fabrica() as db:
            tomada = await db.execute(
                update(EjecucionPrediccion)
                .where(EjecucionPrediccion.id == ejecucion_id, EjecucionPrediccion.estado == EstadoEjecucion.EN_COLA)
                .values(estado=EstadoEjecucion.EJECUTANDO, iniciada_en=ahora_utc())
                .returning(EjecucionPrediccion.id)
            )
            if tomada.scalar_one_or_none() is None:
                return  # otra instancia ya la tomó
            await db.commit()
            ejecucion = await db.get(EjecucionPrediccion, ejecucion_id)
            try:
                await _calcular_y_guardar(db, ejecucion)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Falló la ejecución de predicción %s", ejecucion_id)
                await db.rollback()
                ejecucion = await db.get(EjecucionPrediccion, ejecucion_id)
                ejecucion.estado = EstadoEjecucion.FALLIDA
                ejecucion.error = f"No se pudo completar el cálculo ({type(exc).__name__}). Revisa el registro del servidor."
                ejecucion.finalizada_en = ahora_utc()
                await _auditar(db, ejecucion, "fallar", {"error": type(exc).__name__}, resultado="fallido")
                await db.commit()
    except Exception:  # noqa: BLE001 - la tarea en segundo plano jamás debe propagar excepciones
        logger.exception("Error inesperado en la tarea de predicción %s", ejecucion_id)


async def _auditar(db: AsyncSession, ejecucion: EjecucionPrediccion, accion: str, detalle: dict, resultado: str = "exitoso") -> None:
    usuario = await db.get(Usuario, ejecucion.usuario_id)
    await auditoria_service.registrar(
        db, modulo="prediccion", accion=accion, usuario=usuario, empresa_id=ejecucion.empresa_id,
        entidad="ejecucion_prediccion", entidad_id=ejecucion.id, resultado=resultado, detalle=detalle,
    )


async def _calcular_y_guardar(db: AsyncSession, ejecucion: EjecucionPrediccion) -> None:
    series, truncado = await datos.cargar_series(
        db, ejecucion.empresa_id, ejecucion.fecha_corte,
        historia_max_dias=int(ejecucion.parametros.get("historia_maxima_dias", settings.ml_historia_maxima_dias)),
        limite_series=settings.ml_max_series_por_ejecucion,
    )
    horizonte = ejecucion.horizonte_dias
    resultados = await asyncio.to_thread(
        pipeline.pronosticar_lote, series, horizonte, tiempo_maximo_s=settings.ml_tiempo_maximo_segundos
    )
    resumen = pipeline.resumir(resultados)
    resumen["truncado"] = truncado
    resumen["omitidas"] = [
        {"sede_id": r.sede_id, "producto_id": r.producto_id, "motivo": r.omitida, "dias_historia": r.dias_historia,
         "dias_con_ventas": r.dias_con_ventas}
        for r in resultados if r.omitida
    ][:MAX_OMITIDAS_EN_RESUMEN]
    resumen["advertencia_global"] = (
        None if resumen["series_con_prediccion"] else
        "Ninguna serie tiene datos suficientes: registra más ventas (al menos 28 días de historial) para pronosticar."
    )

    for r in resultados:
        if r.omitida:
            continue
        db.add(Prediccion(
            empresa_id=ejecucion.empresa_id, ejecucion_id=ejecucion.id, sede_id=r.sede_id, producto_id=r.producto_id,
            fecha_inicio=r.fecha_inicio, fecha_fin=r.fecha_fin, demanda_estimada=r.demanda_total,
            limite_inferior=r.limite_inferior, limite_superior=r.limite_superior, modelo=r.modelo,
            es_linea_base=r.es_linea_base, confianza=r.confianza, metricas=r.metricas,
            serie_diaria=[[(r.fecha_inicio + timedelta(days=i)).isoformat(), v] for i, v in enumerate(r.pronostico)],
            advertencias=r.advertencias,
        ))
    ejecucion.resumen = resumen
    ejecucion.estado = EstadoEjecucion.COMPLETADA
    ejecucion.finalizada_en = ahora_utc()
    await db.flush()
    # Las alertas de riesgo dependen de la última ejecución completada: se recalculan con ella.
    pares = [(s.sede_id, s.producto_id) for s in series]
    resumen_alertas = await alertas_service.sincronizar(db, ejecucion.empresa_id, pares)
    await _auditar(
        db, ejecucion, "completar",
        {k: v for k, v in resumen.items() if k not in ("omitidas",)} | {"alertas": resumen_alertas},
    )
    await db.commit()


# -------------------------------------------------------------------------------- consulta
async def obtener_ejecucion(db: AsyncSession, ctx: Contexto, ejecucion_id: int) -> EjecucionPrediccion:
    e = await db.scalar(
        select(EjecucionPrediccion).where(EjecucionPrediccion.id == ejecucion_id, EjecucionPrediccion.empresa_id == ctx.empresa_id)
    )
    if e is None:
        raise NoEncontrado("La ejecución no existe")
    return e


async def ultima_completada(db: AsyncSession, empresa_id: int) -> EjecucionPrediccion | None:
    return await db.scalar(
        select(EjecucionPrediccion)
        .where(EjecucionPrediccion.empresa_id == empresa_id, EjecucionPrediccion.estado == EstadoEjecucion.COMPLETADA)
        .order_by(EjecucionPrediccion.finalizada_en.desc(), EjecucionPrediccion.id.desc())
        .limit(1)
    )


async def listar_ejecuciones(db: AsyncSession, ctx: Contexto, pag: ParametrosPagina):
    base = select(EjecucionPrediccion).where(EjecucionPrediccion.empresa_id == ctx.empresa_id)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    filas = (
        await db.scalars(base.order_by(EjecucionPrediccion.id.desc()).offset(pag.offset).limit(pag.tamano))
    ).all()
    return list(filas), int(total)


async def a_salida(db: AsyncSession, ejecuciones: list[EjecucionPrediccion], *, detallada: bool) -> list[EjecucionSalida]:
    ids = {e.usuario_id for e in ejecuciones}
    nombres = {}
    if ids:
        nombres = {u.id: u.nombre for u in (await db.scalars(select(Usuario).where(Usuario.id.in_(ids)))).all()}
    salidas = []
    for e in ejecuciones:
        resumen = dict(e.resumen or {})
        if detallada and resumen.get("omitidas"):
            resumen["omitidas"] = await _nombrar_omitidas(db, e.empresa_id, resumen["omitidas"])
        elif not detallada:
            resumen.pop("omitidas", None)
        salidas.append(EjecucionSalida(
            id=e.id, estado=e.estado, horizonte_dias=e.horizonte_dias, fecha_corte=e.fecha_corte, parametros=e.parametros or {},
            resumen=resumen, error=e.error, creada_en=e.creada_en, iniciada_en=e.iniciada_en, finalizada_en=e.finalizada_en,
            solicitada_por=nombres.get(e.usuario_id),
        ))
    return salidas


async def _nombrar_omitidas(db: AsyncSession, empresa_id: int, omitidas: list[dict]) -> list[dict]:
    productos = {
        p.id: p for p in (await db.scalars(select(Producto).where(Producto.empresa_id == empresa_id, Producto.id.in_({o["producto_id"] for o in omitidas})))).all()
    }
    sedes = {s.id: s for s in (await db.scalars(select(Sede).where(Sede.empresa_id == empresa_id, Sede.id.in_({o["sede_id"] for o in omitidas})))).all()}
    return [
        {**o, "producto": productos[o["producto_id"]].nombre if o["producto_id"] in productos else None,
         "codigo": productos[o["producto_id"]].codigo if o["producto_id"] in productos else None,
         "sede": sedes[o["sede_id"]].nombre if o["sede_id"] in sedes else None}
        for o in omitidas
    ]


def _salida_prediccion(p: Prediccion, producto: Producto, sede: Sede, existencias: int | None) -> PrediccionSalida:
    dias = max((p.fecha_fin - p.fecha_inicio).days + 1, 1)
    diaria = float(p.demanda_estimada) / dias
    return PrediccionSalida(
        id=p.id, ejecucion_id=p.ejecucion_id, producto=ProductoResumen.model_validate(producto),
        sede=SedeResumen.model_validate(sede), fecha_inicio=p.fecha_inicio, fecha_fin=p.fecha_fin,
        demanda_estimada=float(p.demanda_estimada), demanda_diaria=round(diaria, 3),
        limite_inferior=None if p.limite_inferior is None else float(p.limite_inferior),
        limite_superior=None if p.limite_superior is None else float(p.limite_superior),
        modelo=p.modelo, modelo_descripcion=descripcion_modelo(p.modelo), es_linea_base=p.es_linea_base,
        confianza=p.confianza, metricas=p.metricas or {}, advertencias=list(p.advertencias or []),
        existencias_actuales=existencias,
        cobertura_dias=round(existencias / diaria, 1) if existencias is not None and diaria > 0 else None,
        generada_en=p.generada_en,
    )


async def listar_predicciones(
    db: AsyncSession, ctx: Contexto, pag: ParametrosPagina, *, ejecucion_id: int | None, sede_ids: list[int] | None,
    producto_id: int | None, confianza: str | None, q: str | None, orden: str,
) -> tuple[list[PrediccionSalida], int, EjecucionPrediccion | None]:
    if ejecucion_id is not None:
        ejecucion = await obtener_ejecucion(db, ctx, ejecucion_id)
    else:
        ejecucion = await ultima_completada(db, ctx.empresa_id)
    if ejecucion is None:
        return [], 0, None
    base = (
        select(Prediccion, Producto, Sede, InventarioSede.cantidad)
        .join(Producto, Producto.id == Prediccion.producto_id)
        .join(Sede, Sede.id == Prediccion.sede_id)
        .outerjoin(
            InventarioSede,
            (InventarioSede.sede_id == Prediccion.sede_id) & (InventarioSede.producto_id == Prediccion.producto_id),
        )
        .where(Prediccion.empresa_id == ctx.empresa_id, Prediccion.ejecucion_id == ejecucion.id)
    )
    if sede_ids is not None:
        base = base.where(Prediccion.sede_id.in_(sede_ids))
    if producto_id is not None:
        base = base.where(Prediccion.producto_id == producto_id)
    if confianza:
        base = base.where(Prediccion.confianza == confianza)
    if q:
        patron = f"%{q.strip().lower()}%"
        base = base.where(func.lower(Producto.nombre).like(patron) | func.lower(Producto.codigo).like(patron))
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    criterio = {
        "demanda": Prediccion.demanda_estimada.desc(),
        "producto": Producto.nombre.asc(),
    }.get(orden, Prediccion.demanda_estimada.desc())
    filas = (await db.execute(base.order_by(criterio, Prediccion.id).offset(pag.offset).limit(pag.tamano))).all()
    return [_salida_prediccion(p, prod, sed, ex) for p, prod, sed, ex in filas], int(total), ejecucion


async def serie_de_demanda(
    db: AsyncSession, ctx: Contexto, sede_id: int, producto_id: int, dias_historial: int
) -> SerieDemanda:
    sede = await obtener_sede_autorizada(db, ctx, sede_id)
    producto = await db.scalar(select(Producto).where(Producto.id == producto_id, Producto.empresa_id == ctx.empresa_id))
    if producto is None:
        raise NoEncontrado("El producto no existe")
    ejecucion = await ultima_completada(db, ctx.empresa_id)
    corte = ejecucion.fecha_corte if ejecucion and ejecucion.fecha_corte else hoy_local() - timedelta(days=1)
    series, _ = await datos.cargar_series(
        db, ctx.empresa_id, corte, historia_max_dias=settings.ml_historia_maxima_dias, limite_series=1,
        sede_id=sede.id, producto_id=producto.id,
    )
    historial: list[tuple[date, float]] = []
    if series and len(series[0].unidades):
        s = series[0]
        desde = max(0, len(s.unidades) - dias_historial)
        historial = [(s.inicio + timedelta(days=i), float(s.unidades[i])) for i in range(desde, len(s.unidades))]
    pred = None
    motivo = None
    if ejecucion is not None:
        pred = await db.scalar(
            select(Prediccion).where(
                Prediccion.ejecucion_id == ejecucion.id, Prediccion.sede_id == sede.id, Prediccion.producto_id == producto.id
            )
        )
        if pred is None:
            for o in (ejecucion.resumen or {}).get("omitidas", []):
                if o["sede_id"] == sede.id and o["producto_id"] == producto.id:
                    motivo = o["motivo"]
            motivo = motivo or "Esta combinación de sede y producto no estaba activa cuando se generó la predicción"
    else:
        motivo = "Aún no se ha generado ninguna predicción"
    return SerieDemanda(
        producto=ProductoResumen.model_validate(producto), sede=SedeResumen.model_validate(sede),
        ejecucion_id=ejecucion.id if ejecucion else None, historial=historial,
        pronostico=[(date.fromisoformat(f), float(v)) for f, v in (pred.serie_diaria if pred else [])],
        modelo=pred.modelo if pred else None, confianza=pred.confianza if pred else None,
        demanda_estimada=float(pred.demanda_estimada) if pred else None,
        limite_inferior=float(pred.limite_inferior) if pred and pred.limite_inferior is not None else None,
        limite_superior=float(pred.limite_superior) if pred and pred.limite_superior is not None else None,
        metricas=pred.metricas if pred else {}, advertencias=list(pred.advertencias) if pred else [],
        motivo_sin_prediccion=motivo,
    )
