"""Registro de auditoría (RF-036) y consulta (RF-037).

``registrar`` añade la fila a la MISMA transacción de la operación auditada: si la operación se
revierte, su registro también; si se confirma, ambos quedan. Para eventos que deben sobrevivir
a una reversión (intentos fallidos) se usa ``registrar_independiente``.
"""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import fabrica_de_sesiones
from app.model.auditoria import Auditoria
from app.model.usuario import Usuario
from app.security.acceso import Contexto
from app.security.contexto import ip_actual, request_id_actual
from app.util.tiempo import fin_de_dia_utc, inicio_de_dia_utc

_CLAVES_SENSIBLES = re.compile(r"(pass|contrase|token|codigo|code|secret|clave|hash|authorization|api_?key)", re.I)


def _seguro(valor: Any, profundidad: int = 0) -> Any:
    if profundidad > 4:
        return "…"
    if isinstance(valor, dict):
        return {
            str(k): ("[oculto]" if _CLAVES_SENSIBLES.search(str(k)) else _seguro(v, profundidad + 1))
            for k, v in list(valor.items())[:60]
        }
    if isinstance(valor, (list, tuple, set)):
        return [_seguro(v, profundidad + 1) for v in list(valor)[:60]]
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if isinstance(valor, str):
        return valor[:500]
    if valor is None or isinstance(valor, (int, float, bool)):
        return valor
    return str(valor)[:200]


def _fila(
    *,
    modulo: str,
    accion: str,
    ctx: Contexto | None,
    usuario: Usuario | None,
    empresa_id: int | None,
    entidad: str | None,
    entidad_id: Any,
    sede_id: int | None,
    resultado: str,
    detalle: dict | None,
) -> Auditoria:
    u = ctx.usuario if ctx else usuario
    return Auditoria(
        empresa_id=ctx.empresa_id if ctx else (u.empresa_id if u else empresa_id),
        usuario_id=u.id if u else None,
        usuario_email=u.email if u else None,
        sede_id=sede_id,
        modulo=modulo,
        accion=accion,
        entidad=entidad,
        entidad_id=str(entidad_id) if entidad_id is not None else None,
        resultado=resultado,
        detalle=_seguro(detalle or {}),
        ip=ip_actual(),
        request_id=request_id_actual(),
    )


async def registrar(
    db: AsyncSession,
    *,
    modulo: str,
    accion: str,
    ctx: Contexto | None = None,
    usuario: Usuario | None = None,
    empresa_id: int | None = None,
    entidad: str | None = None,
    entidad_id: Any = None,
    sede_id: int | None = None,
    resultado: str = "exitoso",
    detalle: dict | None = None,
) -> None:
    db.add(
        _fila(
            modulo=modulo, accion=accion, ctx=ctx, usuario=usuario, empresa_id=empresa_id, entidad=entidad,
            entidad_id=entidad_id, sede_id=sede_id, resultado=resultado, detalle=detalle,
        )
    )


async def registrar_independiente(
    *,
    modulo: str,
    accion: str,
    usuario: Usuario | None = None,
    empresa_id: int | None = None,
    entidad: str | None = None,
    entidad_id: Any = None,
    resultado: str = "fallido",
    detalle: dict | None = None,
) -> None:
    """Escribe en una transacción propia (sobrevive a la reversión de la operación original)."""
    async with fabrica_de_sesiones()() as sesion:
        sesion.add(
            _fila(
                modulo=modulo, accion=accion, ctx=None, usuario=usuario, empresa_id=empresa_id, entidad=entidad,
                entidad_id=entidad_id, sede_id=None, resultado=resultado, detalle=detalle,
            )
        )
        await sesion.commit()


async def consultar(
    db: AsyncSession,
    ctx: Contexto,
    *,
    usuario_id: int | None = None,
    modulo: str | None = None,
    accion: str | None = None,
    resultado: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    q: str | None = None,
    pagina: int = 1,
    tamano: int = 20,
):
    """Consulta con filtros. ``auditoria.ver`` ve todo; ``auditoria.operaciones`` ve solo
    operaciones de negocio (no accesos) y, si está limitado a una sede, solo las de su sede."""
    ctx.exigir("auditoria.ver", "auditoria.operaciones")
    condiciones = [Auditoria.empresa_id == ctx.empresa_id]
    if not ctx.tiene("auditoria.ver"):
        condiciones.append(Auditoria.modulo != "auth")
        if ctx.limitado_a_sede:
            condiciones.append(Auditoria.sede_id == ctx.sede_id)
    if usuario_id:
        condiciones.append(Auditoria.usuario_id == usuario_id)
    if modulo:
        condiciones.append(Auditoria.modulo == modulo)
    if accion:
        condiciones.append(Auditoria.accion == accion)
    if resultado:
        condiciones.append(Auditoria.resultado == resultado)
    if desde:
        condiciones.append(Auditoria.fecha >= inicio_de_dia_utc(desde))
    if hasta:
        condiciones.append(Auditoria.fecha < fin_de_dia_utc(hasta))
    if q:
        patron = f"%{q.strip().lower()}%"
        condiciones.append(
            func.lower(func.coalesce(Auditoria.usuario_email, "")).like(patron)
            | func.lower(Auditoria.accion).like(patron)
            | func.lower(func.coalesce(Auditoria.entidad, "")).like(patron)
        )
    total = await db.scalar(select(func.count()).select_from(Auditoria).where(*condiciones)) or 0
    filas = (
        await db.scalars(
            select(Auditoria)
            .where(*condiciones)
            .order_by(Auditoria.fecha.desc(), Auditoria.id.desc())
            .offset((pagina - 1) * tamano)
            .limit(tamano)
        )
    ).all()
    return filas, total
