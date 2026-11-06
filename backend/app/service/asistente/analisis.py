"""Ayudas compartidas por las respuestas ampliadas del asistente (nombres, notas de listados, periodos por defecto y tiempos locales)."""

import re
from datetime import date, datetime, timedelta

from app.service.asistente import bloques as B
from app.service.asistente.peticion import Peticion
from app.util import lenguaje as L
from app.util.tiempo import ZONA, asegurar_utc


def nombre_producto(codigo: str, nombre: str) -> str:
    return f"{nombre} ({codigo})"


def nota_listado(mostrados: int, total: int, cosa: str = "resultados") -> str | None:
    return f"Mostrando {mostrados} de {total} {cosa}." if total > mostrados else None


def ultimos(p: Peticion, dias: int) -> L.Periodo:
    """El periodo pedido o, si no pidieron ninguno, los últimos ``dias`` días hasta hoy."""
    return p.periodo or L.Periodo(p.hoy - timedelta(days=dias - 1), p.hoy, f"los últimos {dias} días")


def hora_local(momento: datetime) -> int:
    return asegurar_utc(momento).astimezone(ZONA).hour


def dia_local(momento: datetime) -> date:
    return asegurar_utc(momento).astimezone(ZONA).date()


def primer_numero(patron: re.Pattern, frase: str) -> int | None:
    m = patron.search(frase)
    return int(m.group(1)) if m else None


def porcentaje_de(parte: float, total: float) -> float:
    return parte / total * 100 if total else 0.0


def plural(n: int, singular: str, plural_: str | None = None) -> str:
    return B.n_de(n, singular, plural_)


def pide_lo_menor(frase: str) -> bool:
    """Verdadero si la frase pide lo MENOR (menos, peor, más bajo, más barato…)."""
    return bool(re.search(r"\b(menos|menor|menores|peor|peores|poco|pocos|baj[oa]s?|pequen[oa]s?|barat\w+|minim[oa]s?)\b", frase))
