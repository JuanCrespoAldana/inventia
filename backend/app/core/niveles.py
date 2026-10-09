"""Reglas puras (sin base de datos) para clasificar las existencias de un producto en una sede."""

from sqlalchemy import case, literal
from sqlalchemy.sql.elements import ColumnElement

AGOTADO = "agotado"
BAJO = "bajo"
EXCESIVO = "excesivo"
NORMAL = "normal"
ESTADOS_STOCK = (AGOTADO, BAJO, NORMAL, EXCESIVO)


def clasificar_stock(cantidad: int, minimo: int, maximo: int | None) -> str:
    """agotado: sin unidades · bajo: en o por debajo del mínimo (si hay mínimo) · excesivo: sobre el máximo."""
    if cantidad <= 0:
        return AGOTADO
    if minimo > 0 and cantidad <= minimo:
        return BAJO
    if maximo is not None and cantidad > maximo:
        return EXCESIVO
    return NORMAL


def sql_estado_stock(cantidad: ColumnElement, minimo: ColumnElement, maximo: ColumnElement) -> ColumnElement:
    """Misma regla que ``clasificar_stock`` expresada en SQL (para filtrar y ordenar en la base)."""
    return case(
        (cantidad <= 0, literal(AGOTADO)),
        ((minimo > 0) & (cantidad <= minimo), literal(BAJO)),
        (maximo.is_not(None) & (cantidad > maximo), literal(EXCESIVO)),
        else_=literal(NORMAL),
    )
