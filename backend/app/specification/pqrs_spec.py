"""Especificación de filtros de PQRS: arma las condiciones SQL según el ámbito y los parámetros de consulta."""

from datetime import date

from sqlalchemy import func, or_

from app.model.pqrs import Pqrs
from app.security.acceso import Contexto
from app.util.tiempo import fin_de_dia_utc, inicio_de_dia_utc


def condiciones_pqrs(
    ctx: Contexto, *, ambito: str, tipo: str | None, estado: str | None, usuario_id: int | None,
    desde: date | None, hasta: date | None, q: str | None,
) -> list:
    condiciones = [Pqrs.empresa_id == ctx.empresa_id]
    if ambito == "todas":
        ctx.exigir("pqrs.gestionar")
        if usuario_id:
            condiciones.append(Pqrs.usuario_id == usuario_id)
    else:
        condiciones.append(Pqrs.usuario_id == ctx.usuario_id)
    if tipo:
        condiciones.append(Pqrs.tipo == tipo)
    if estado:
        condiciones.append(Pqrs.estado == estado)
    if desde:
        condiciones.append(Pqrs.created_at >= inicio_de_dia_utc(desde))
    if hasta:
        condiciones.append(Pqrs.created_at < fin_de_dia_utc(hasta))
    if q:
        patron = f"%{q.strip().lower()}%"
        filtro = func.lower(Pqrs.asunto).like(patron)
        if q.strip().isdigit():
            filtro = or_(filtro, Pqrs.numero == int(q.strip()))
        condiciones.append(filtro)
    return condiciones
