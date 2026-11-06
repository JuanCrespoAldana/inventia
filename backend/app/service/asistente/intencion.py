"""Definición de una intención del asistente y su constructor (separado para que el catálogo se pueda repartir en varios módulos)."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Intencion:
    clave: str
    categoria: str
    titulo: str
    permisos: tuple[str, ...]  # basta uno; vacío = cualquier persona autenticada
    ejemplos: tuple[str, ...]
    senales: tuple[tuple[re.Pattern, float], ...]
    ruta: str | None = None
    requiere: str | None = None  # "producto" | "sede" | "categoria": suma si aparece y resta si falta
    prefiere: str | None = None  # suma si aparece (no resta si falta)
    contras: tuple[tuple[re.Pattern, float], ...] = ()


@dataclass(frozen=True)
class SenalesEntidades:
    """Qué entidades se reconocieron en la frase (la clasificación solo necesita saber si están)."""

    producto: bool = False
    sede: bool = False
    categoria: bool = False
    periodo: bool = False
    horizonte: bool = False


def _compilar(pares: list[tuple[str, float]]) -> tuple[tuple[re.Pattern, float], ...]:
    return tuple((re.compile(p), w) for p, w in pares)


def _i(
    clave: str, categoria: str, titulo: str, permisos: tuple[str, ...], ejemplos: tuple[str, ...], senales: list[tuple[str, float]],
    *, ruta: str | None = None, requiere: str | None = None, prefiere: str | None = None, contras: list[tuple[str, float]] | None = None,
) -> Intencion:
    return Intencion(clave, categoria, titulo, permisos, ejemplos, _compilar(senales), ruta, requiere, prefiere, _compilar(contras or []))


INV = ("inventario.ver", "inventario.consolidado")
