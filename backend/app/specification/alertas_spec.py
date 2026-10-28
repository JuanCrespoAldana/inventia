"""Especificación de filtros de alertas: arma la lista de condiciones SQL a partir de los parámetros de consulta."""

from app.model.inventario import Alerta
from app.security.acceso import Contexto


def condiciones_alertas(ctx: Contexto, sede_ids: list[int] | None, estado: str | None, tipo: str | None, prioridad: str | None):
    condiciones = [Alerta.empresa_id == ctx.empresa_id]
    if sede_ids is not None:
        condiciones.append(Alerta.sede_id.in_(sede_ids))
    if estado:
        condiciones.append(Alerta.estado == estado)
    if tipo:
        condiciones.append(Alerta.tipo == tipo)
    if prioridad:
        condiciones.append(Alerta.prioridad == prioridad)
    return condiciones
