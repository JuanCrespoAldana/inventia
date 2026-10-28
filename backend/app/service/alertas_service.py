"""Alertas de inventario persistentes (RF-024).

Tipos: inventario_bajo, inventario_excesivo, riesgo_desabastecimiento (usa la última predicción
vigente) y requiere_revision (existencias sin rotación). Una alerta se abre cuando la condición
aparece y se RESUELVE sola cuando desaparece; nunca hay dos activas iguales para la misma
sede-producto-tipo (índice único parcial). Se re-evalúan dentro de la misma transacción de cada
movimiento de inventario y en un recálculo completo bajo demanda.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import case, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.dto.comunes_dto import ParametrosPagina
from app.model.catalogo import Producto
from app.model.empresa import Empresa
from app.model.enums import EstadoAlerta, EstadoEjecucion, PrioridadAlerta, TipoAlerta, TipoMovimiento
from app.model.inventario import Alerta, InventarioSede, Movimiento
from app.model.prediccion import EjecucionPrediccion, Prediccion
from app.model.sede import Sede
from app.security.acceso import Contexto
from app.service import auditoria_service
from app.specification.alertas_spec import condiciones_alertas
from app.util.niveles import BAJO, EXCESIVO, clasificar_stock
from app.util.sql import insertar
from app.util.tiempo import ahora_utc, hoy_local

ORDEN_PRIORIDAD = {"critica": 0, "alta": 1, "media": 2, "baja": 3}
VIGENCIA_PREDICCION_DIAS = 14  # una predicción más vieja no se usa para alertar


@dataclass
class _Deseada:
    tipo: str
    prioridad: str
    mensaje: str
    detalle: dict = field(default_factory=dict)


def _u(n: int, unidad: str) -> str:
    return f"{n} {unidad}" if unidad != "unidad" else f"{n} unidad" + ("" if n == 1 else "es")


async def ultima_ejecucion_vigente(db: AsyncSession, empresa_id: int) -> EjecucionPrediccion | None:
    ejecucion = await db.scalar(
        select(EjecucionPrediccion)
        .where(EjecucionPrediccion.empresa_id == empresa_id, EjecucionPrediccion.estado == EstadoEjecucion.COMPLETADA)
        .order_by(EjecucionPrediccion.finalizada_en.desc(), EjecucionPrediccion.id.desc())
        .limit(1)
    )
    if ejecucion is None or ejecucion.fecha_corte is None:
        return None
    if (hoy_local() - ejecucion.fecha_corte).days > VIGENCIA_PREDICCION_DIAS:
        return None
    return ejecucion


def _evaluar(
    *,
    nombre: str,
    sede: str,
    unidad: str,
    cantidad: int,
    minimo: int,
    maximo: int | None,
    demanda_diaria: float | None,
    confianza: str | None,
    plazo: int,
    seguridad: int,
    umbral: int,
    sin_rotacion_dias: int | None,
) -> list[_Deseada]:
    deseadas: list[_Deseada] = []
    estado = clasificar_stock(cantidad, minimo, maximo)
    base = {"cantidad": cantidad, "stock_minimo": minimo, "stock_maximo": maximo}

    if estado in ("agotado", BAJO) and (minimo > 0 or cantidad <= 0 and demanda_diaria):
        if cantidad <= 0:
            prioridad = PrioridadAlerta.CRITICA
            mensaje = f"«{nombre}» está agotado en {sede}"
        elif cantidad <= minimo / 2:
            prioridad = PrioridadAlerta.ALTA
            mensaje = f"«{nombre}» tiene solo {_u(cantidad, unidad)} en {sede} (mínimo {minimo})"
        else:
            prioridad = PrioridadAlerta.MEDIA
            mensaje = f"«{nombre}» está en el nivel mínimo en {sede}: {_u(cantidad, unidad)} (mínimo {minimo})"
        deseadas.append(_Deseada(TipoAlerta.INVENTARIO_BAJO, prioridad, mensaje, dict(base)))

    if estado == EXCESIVO and maximo is not None:
        exceso = cantidad - maximo
        prioridad = PrioridadAlerta.MEDIA if cantidad > maximo * 1.5 else PrioridadAlerta.BAJA
        deseadas.append(
            _Deseada(
                TipoAlerta.INVENTARIO_EXCESIVO, prioridad,
                f"«{nombre}» supera el máximo en {sede}: {_u(cantidad, unidad)} (máximo {maximo}, exceso {exceso})",
                {**base, "exceso": exceso},
            )
        )

    if demanda_diaria and demanda_diaria > 0 and cantidad >= 0:
        cobertura = cantidad / demanda_diaria
        if cobertura < max(umbral, plazo + seguridad):
            if cobertura < plazo:
                prioridad = PrioridadAlerta.CRITICA
            elif cobertura < plazo + seguridad:
                prioridad = PrioridadAlerta.ALTA
            else:
                prioridad = PrioridadAlerta.MEDIA
            if confianza == "baja" and prioridad in (PrioridadAlerta.CRITICA, PrioridadAlerta.ALTA):
                prioridad = PrioridadAlerta.MEDIA  # una estimación poco fiable no genera urgencia máxima
            nota = " (estimación de baja confianza)" if confianza == "baja" else ""
            demanda_txt = f"{demanda_diaria:.1f}".replace(".", ",")
            if cantidad == 0:
                mensaje = (
                    f"«{nombre}» no tiene existencias en {sede} y se venden ≈{demanda_txt}/día; "
                    f"el reabastecimiento tarda {plazo} días{nota}"
                )
            else:
                mensaje = (
                    f"«{nombre}» alcanzaría para {f'{cobertura:.1f}'.replace('.', ',')} días en {sede} con la demanda prevista "
                    f"({demanda_txt}/día); el reabastecimiento tarda {plazo} días{nota}"
                )
            deseadas.append(
                _Deseada(
                    TipoAlerta.RIESGO_DESABASTECIMIENTO, prioridad, mensaje,
                    {**base, "cobertura_dias": round(cobertura, 1), "demanda_diaria": round(demanda_diaria, 2),
                     "plazo_entrega_dias": plazo, "confianza": confianza},
                )
            )

    if sin_rotacion_dias is not None and cantidad > 0:
        deseadas.append(
            _Deseada(
                TipoAlerta.REQUIERE_REVISION, PrioridadAlerta.BAJA,
                f"«{nombre}» no tiene salidas ni ventas en {sede} hace más de {sin_rotacion_dias} días "
                f"y conserva {_u(cantidad, unidad)}: revisa si sigue vigente",
                {**base, "dias_sin_rotacion": sin_rotacion_dias},
            )
        )
    return deseadas


async def sincronizar(db: AsyncSession, empresa_id: int, pares: Iterable[tuple[int, int]]) -> dict[str, int]:
    """Deja las alertas de los pares (sede_id, producto_id) acordes con la realidad actual.

    Devuelve cuántas alertas se abrieron y cuántas se resolvieron."""
    pares = list(dict.fromkeys(pares))
    contadores = {"abiertas": 0, "resueltas": 0, "actualizadas": 0}
    if not pares:
        return contadores

    empresa = await db.get(Empresa, empresa_id)
    cfg = empresa.parametros() if empresa else {}
    plazo, seguridad = int(cfg.get("plazo_entrega_dias", 7)), int(cfg.get("dias_seguridad", 3))
    umbral, dias_rot = int(cfg.get("umbral_cobertura_alerta_dias", 5)), int(cfg.get("dias_sin_rotacion", 60))
    ejecucion = await ultima_ejecucion_vigente(db, empresa_id)

    for lote in (pares[i : i + 400] for i in range(0, len(pares), 400)):
        filas = {
            (i.sede_id, i.producto_id): i
            for i in (
                await db.scalars(
                    select(InventarioSede)
                    .where(
                        InventarioSede.empresa_id == empresa_id,
                        tuple_(InventarioSede.sede_id, InventarioSede.producto_id).in_(lote),
                    )
                    .execution_options(populate_existing=True)  # las existencias se actualizan con SQL directo
                )
            ).all()
        }
        productos = {
            p.id: p for p in (await db.scalars(select(Producto).where(Producto.id.in_({p for _, p in lote})))).all()
        }
        sedes = {s.id: s for s in (await db.scalars(select(Sede).where(Sede.id.in_({s for s, _ in lote})))).all()}

        pred: dict[tuple[int, int], Prediccion] = {}
        if ejecucion:
            for p in (
                await db.scalars(
                    select(Prediccion).where(
                        Prediccion.ejecucion_id == ejecucion.id,
                        tuple_(Prediccion.sede_id, Prediccion.producto_id).in_(lote),
                    )
                )
            ).all():
                pred[(p.sede_id, p.producto_id)] = p

        corte = ahora_utc() - timedelta(days=dias_rot)
        ultima_salida = {
            (s, p): f
            for s, p, f in (
                await db.execute(
                    select(Movimiento.sede_id, Movimiento.producto_id, func.max(Movimiento.fecha))
                    .where(
                        Movimiento.empresa_id == empresa_id,
                        tuple_(Movimiento.sede_id, Movimiento.producto_id).in_(lote),
                        Movimiento.tipo.in_((TipoMovimiento.VENTA, TipoMovimiento.SALIDA, TipoMovimiento.TRASLADO_SALIDA)),
                    )
                    .group_by(Movimiento.sede_id, Movimiento.producto_id)
                )
            ).all()
        }

        activas: dict[tuple[int, int, str], Alerta] = {
            (a.sede_id, a.producto_id, a.tipo): a
            for a in (
                await db.scalars(
                    select(Alerta).where(
                        Alerta.empresa_id == empresa_id,
                        Alerta.estado == EstadoAlerta.ACTIVA,
                        tuple_(Alerta.sede_id, Alerta.producto_id).in_(lote),
                    )
                )
            ).all()
        }

        for par in lote:
            fila, producto, sede = filas.get(par), productos.get(par[1]), sedes.get(par[0])
            deseadas: list[_Deseada] = []
            if fila and producto and sede and producto.activo and sede.activa:
                p = pred.get(par)
                demanda = None
                confianza = None
                if p is not None:
                    dias = (p.fecha_fin - p.fecha_inicio).days + 1
                    demanda = float(p.demanda_estimada) / max(dias, 1)
                    confianza = p.confianza
                u_sal = ultima_salida.get(par)
                if u_sal is not None and u_sal.tzinfo is None:
                    u_sal = u_sal.replace(tzinfo=corte.tzinfo)
                antigua = fila.created_at.replace(tzinfo=corte.tzinfo) if fila.created_at.tzinfo is None else fila.created_at
                sin_rot = dias_rot if (antigua < corte and (u_sal is None or u_sal < corte)) else None
                deseadas = _evaluar(
                    nombre=producto.nombre, sede=sede.nombre, unidad=producto.unidad_medida, cantidad=fila.cantidad,
                    minimo=fila.stock_minimo, maximo=fila.stock_maximo, demanda_diaria=demanda, confianza=confianza,
                    plazo=plazo, seguridad=seguridad, umbral=umbral, sin_rotacion_dias=sin_rot,
                )
            por_tipo = {d.tipo: d for d in deseadas}

            for tipo in TipoAlerta:
                existente = activas.get((par[0], par[1], tipo.value))
                deseada = por_tipo.get(tipo.value)
                if deseada and existente is None:
                    resultado = await db.execute(
                        insertar(db, Alerta)
                        .values(
                            empresa_id=empresa_id, sede_id=par[0], producto_id=par[1], tipo=tipo.value,
                            prioridad=deseada.prioridad, estado=EstadoAlerta.ACTIVA, mensaje=deseada.mensaje,
                            detalle=deseada.detalle, abierta_en=ahora_utc(),
                        )
                        .on_conflict_do_nothing()
                    )
                    contadores["abiertas"] += resultado.rowcount or 0
                elif deseada and existente is not None:
                    if (existente.prioridad, existente.mensaje) != (deseada.prioridad, deseada.mensaje):
                        existente.prioridad, existente.mensaje, existente.detalle = (
                            deseada.prioridad, deseada.mensaje, deseada.detalle,
                        )
                        contadores["actualizadas"] += 1
                elif existente is not None and not deseada:
                    existente.estado = EstadoAlerta.RESUELTA
                    existente.resuelta_en = ahora_utc()
                    contadores["resueltas"] += 1
    await db.flush()
    return contadores


async def recalcular_empresa(db: AsyncSession, ctx: Contexto) -> dict[str, int]:
    """Re-evalúa TODAS las existencias de la empresa (o de la sede del usuario si está limitado a una)."""
    consulta = select(InventarioSede.sede_id, InventarioSede.producto_id).where(InventarioSede.empresa_id == ctx.empresa_id)
    autorizadas = ctx.sedes_autorizadas()
    if autorizadas is not None:
        consulta = consulta.where(InventarioSede.sede_id.in_(autorizadas))
    pares = [(s, p) for s, p in (await db.execute(consulta)).all()]
    # Alertas activas de pares que ya no tienen fila de inventario también se revisan.
    huerfanas = select(Alerta.sede_id, Alerta.producto_id).where(
        Alerta.empresa_id == ctx.empresa_id, Alerta.estado == EstadoAlerta.ACTIVA
    )
    if autorizadas is not None:
        huerfanas = huerfanas.where(Alerta.sede_id.in_(autorizadas))
    pares += [(s, p) for s, p in (await db.execute(huerfanas)).all()]
    resultado = await sincronizar(db, ctx.empresa_id, pares)
    activas = await db.scalar(
        select(func.count()).select_from(Alerta).where(Alerta.empresa_id == ctx.empresa_id, Alerta.estado == EstadoAlerta.ACTIVA)
    )
    resultado["activas"] = int(activas or 0)
    resultado["series_evaluadas"] = len(set(pares))
    await auditoria_service.registrar(
        db, modulo="alertas", accion="recalcular", ctx=ctx, detalle=dict(resultado),
        sede_id=ctx.sede_id if ctx.limitado_a_sede else None,
    )
    await db.commit()
    return resultado


async def listar(
    db: AsyncSession,
    ctx: Contexto,
    pag: ParametrosPagina,
    *,
    sede_ids: list[int] | None,
    estado: str | None,
    tipo: str | None,
    prioridad: str | None,
    q: str | None,
):
    condiciones = condiciones_alertas(ctx, sede_ids, estado, tipo, prioridad)
    base = (
        select(Alerta, Producto, Sede)
        .join(Producto, Producto.id == Alerta.producto_id)
        .join(Sede, Sede.id == Alerta.sede_id)
        .where(*condiciones)
    )
    if q:
        patron = f"%{q.strip().lower()}%"
        base = base.where(func.lower(Producto.nombre).like(patron) | func.lower(Producto.codigo).like(patron))
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    orden_prioridad = (
        (Alerta.prioridad == "critica", 0), (Alerta.prioridad == "alta", 1), (Alerta.prioridad == "media", 2)
    )
    filas = (
        await db.execute(
            base.order_by(
                case(*orden_prioridad, else_=3), Alerta.abierta_en.desc(), Alerta.id.desc()
            ).offset(pag.offset).limit(pag.tamano)
        )
    ).all()
    return filas, total


async def resumen(db: AsyncSession, ctx: Contexto, sede_ids: list[int] | None) -> dict:
    condiciones = condiciones_alertas(ctx, sede_ids, EstadoAlerta.ACTIVA, None, None)
    filas = (
        await db.execute(select(Alerta.tipo, Alerta.prioridad, func.count()).where(*condiciones).group_by(Alerta.tipo, Alerta.prioridad))
    ).all()
    por_tipo: dict[str, int] = defaultdict(int)
    por_prioridad: dict[str, int] = defaultdict(int)
    for tipo, prioridad, n in filas:
        por_tipo[tipo] += n
        por_prioridad[prioridad] += n
    return {"total": sum(por_tipo.values()), "por_tipo": dict(por_tipo), "por_prioridad": dict(por_prioridad)}
