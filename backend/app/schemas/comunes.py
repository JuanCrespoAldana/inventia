"""Tipos y validadores compartidos por los esquemas de entrada y salida."""

import math
import re
from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from fastapi import Query
from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, PlainSerializer, StringConstraints

T = TypeVar("T")

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_ESPACIOS = re.compile(r"[ \t]{2,}")


def _limpiar_texto(valor: str) -> str:
    if _CONTROL.search(valor):
        raise ValueError("Contiene caracteres no permitidos")
    return _ESPACIOS.sub(" ", valor.strip())


def _texto_opcional(valor: str | None) -> str | None:
    if valor is None:
        return None
    limpio = _limpiar_texto(valor)
    return limpio or None


def _correo_minuscula(valor: str) -> str:
    return valor.strip().lower()


Correo = Annotated[EmailStr, AfterValidator(_correo_minuscula), Field(max_length=255)]


def Texto(minimo: int = 1, maximo: int = 150):  # noqa: N802 - fábrica de tipos
    """Texto obligatorio, sin espacios sobrantes ni caracteres de control. Los límites de longitud
    se validan DESPUÉS de limpiar (un texto de solo espacios no cumple el mínimo)."""

    def _validar(valor: str) -> str:
        limpio = _limpiar_texto(valor)
        if len(limpio) < minimo:
            raise ValueError(
                "Este campo es obligatorio" if minimo <= 1 else f"Debe tener al menos {minimo} caracteres"
            )
        if len(limpio) > maximo:
            raise ValueError(f"No puede superar los {maximo} caracteres")
        return limpio

    return Annotated[str, StringConstraints(max_length=maximo * 3), AfterValidator(_validar)]


def TextoOpcional(maximo: int = 300):  # noqa: N802
    """Texto opcional: la cadena vacía se convierte en ``None``."""

    def _validar(valor: str | None) -> str | None:
        limpio = _texto_opcional(valor)
        if limpio is not None and len(limpio) > maximo:
            raise ValueError(f"No puede superar los {maximo} caracteres")
        return limpio

    return Annotated[
        Annotated[str, StringConstraints(max_length=maximo * 3)] | None, AfterValidator(_validar), Field(default=None)
    ]


def validar_password_segura(v: str) -> str:
    if len(v) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres")
    if len(v) > 128:
        raise ValueError("La contraseña no puede superar los 128 caracteres")
    if not re.search(r"[A-Z]", v):
        raise ValueError("La contraseña debe tener al menos una letra mayúscula")
    if not re.search(r"[a-z]", v):
        raise ValueError("La contraseña debe tener al menos una letra minúscula")
    if not re.search(r"\d", v):
        raise ValueError("La contraseña debe tener al menos un número")
    if not re.search(r"[^\w\s]|_", v):
        raise ValueError("La contraseña debe tener al menos un carácter especial")
    return v


Password = Annotated[str, AfterValidator(validar_password_segura)]


def validar_telefono(v: str | None) -> str | None:
    v = _texto_opcional(v)
    if v is None:
        return None
    if not re.fullmatch(r"[0-9+()\-\s]{7,20}", v):
        raise ValueError("Escribe un teléfono válido (solo números, +, - y paréntesis)")
    return v


Telefono = Annotated[str | None, AfterValidator(validar_telefono), Field(default=None)]


def validar_identificacion(v: str) -> str:
    """Normaliza el NIT / identificación empresarial: sin espacios ni puntos, en mayúsculas."""
    v = re.sub(r"[\s.]", "", v).upper()
    if not re.fullmatch(r"[0-9A-Z\-]{5,20}", v):
        raise ValueError("La identificación debe tener entre 5 y 20 caracteres (números, letras o guion)")
    return v


Identificacion = Annotated[str, AfterValidator(validar_identificacion)]


# Dinero: se recibe como decimal exacto (2 decimales) y se entrega al navegador como número.
Dinero = Annotated[
    Decimal,
    Field(ge=0, max_digits=14, decimal_places=2),
    PlainSerializer(lambda v: float(v), return_type=float, when_used="json"),
]
# Cantidad calculada (promedios, previsiones): sin restricciones de entrada, se entrega como número.
Numero = Annotated[Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")]


class EsquemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", str_strip_whitespace=False)


class Pagina(BaseModel, Generic[T]):
    items: list[T]
    total: int
    pagina: int
    tamano: int
    paginas: int

    @classmethod
    def crear(cls, items: list[T], total: int, pagina: int, tamano: int) -> "Pagina[T]":
        return cls(items=items, total=total, pagina=pagina, tamano=tamano, paginas=max(1, math.ceil(total / tamano)))


class ParametrosPagina:
    """Dependencia estándar de paginación: ``?pagina=1&tamano=20`` (máximo 100 por página)."""

    def __init__(
        self,
        pagina: int = Query(1, ge=1, description="Número de página (desde 1)"),
        tamano: int = Query(20, ge=1, le=100, description="Registros por página (máx. 100)"),
    ):
        self.pagina = pagina
        self.tamano = tamano

    @property
    def offset(self) -> int:
        return (self.pagina - 1) * self.tamano


class Mensaje(BaseModel):
    mensaje: str
