"""Especificación de filtros de ventas: arma las condiciones SQL a partir de los parámetros de consulta."""

from datetime import date

from app.model.operaciones import Venta
from app.security.acceso import Contexto
from app.service.alcance import resolver_filtro_sede


def condiciones_ventas(ctx: Contexto, *, sede_id, estado, desde: date | None, hasta: date | None, numero: int | None, usuario_id=None):
    sede_ids = resolver_filtro_sede(ctx, sede_id)
    condiciones = [Venta.empresa_id == ctx.empresa_id]
    if sede_ids is not None:
        condiciones.append(Venta.sede_id.in_(sede_ids))
    if estado:
        condiciones.append(Venta.estado == estado)
    if desde:
        condiciones.append(Venta.fecha_dia >= desde)
    if hasta:
        condiciones.append(Venta.fecha_dia <= hasta)
    if numero:
        condiciones.append(Venta.numero == numero)
    if usuario_id:
        condiciones.append(Venta.usuario_id == usuario_id)
    return condiciones
