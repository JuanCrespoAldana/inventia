"""Especificación de filtros del kardex de movimientos de inventario."""

from datetime import date

from app.model.inventario import Movimiento
from app.security.acceso import Contexto
from app.service.alcance import resolver_filtro_sede
from app.util.tiempo import fin_de_dia_utc, inicio_de_dia_utc


def condiciones_movimientos(
    ctx: Contexto,
    *,
    sede_id: int | None,
    producto_id: int | None,
    tipo: str | None,
    desde: date | None,
    hasta: date | None,
    usuario_id: int | None,
) -> list:
    sede_ids = resolver_filtro_sede(ctx, sede_id)
    condiciones = [Movimiento.empresa_id == ctx.empresa_id]
    if sede_ids is not None:
        condiciones.append(Movimiento.sede_id.in_(sede_ids))
    if producto_id:
        condiciones.append(Movimiento.producto_id == producto_id)
    if tipo:
        condiciones.append(Movimiento.tipo == tipo)
    if usuario_id:
        condiciones.append(Movimiento.usuario_id == usuario_id)
    if desde:
        condiciones.append(Movimiento.fecha >= inicio_de_dia_utc(desde))
    if hasta:
        condiciones.append(Movimiento.fecha < fin_de_dia_utc(hasta))
    return condiciones
