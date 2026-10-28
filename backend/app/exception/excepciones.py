"""Excepciones de negocio de Inventia.

Los servicios lanzan estas excepciones; la traducción a respuestas HTTP vive en ``manejadores.py`` y se hace UNA sola
vez, de modo que ningún endpoint repite bloques try/except (RNF-010).
"""

from typing import Any

from fastapi import status


class ErrorNegocio(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    codigo = "error_negocio"

    def __init__(self, mensaje: str, *, codigo: str | None = None, extra: dict[str, Any] | None = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        if codigo:
            self.codigo = codigo
        self.extra = extra or {}


class NoAutenticado(ErrorNegocio):
    status_code = status.HTTP_401_UNAUTHORIZED
    codigo = "no_autenticado"


class SinPermiso(ErrorNegocio):
    status_code = status.HTTP_403_FORBIDDEN
    codigo = "sin_permiso"


class NoEncontrado(ErrorNegocio):
    status_code = status.HTTP_404_NOT_FOUND
    codigo = "no_encontrado"


class Conflicto(ErrorNegocio):
    status_code = status.HTTP_409_CONFLICT
    codigo = "conflicto"


class ReglaNegocio(ErrorNegocio):
    status_code = status.HTTP_400_BAD_REQUEST
    codigo = "regla_negocio"


class ExistenciasInsuficientes(Conflicto):
    codigo = "existencias_insuficientes"


class CredencialesInvalidas(NoAutenticado):
    codigo = "credenciales_invalidas"


class CuentaBloqueada(ErrorNegocio):
    status_code = status.HTTP_423_LOCKED
    codigo = "cuenta_bloqueada"


class CodigoInvalido(ErrorNegocio):
    codigo = "codigo_invalido"

    def __init__(self, intentos_restantes: int = 0):
        if intentos_restantes > 0:
            mensaje = f"Código incorrecto. Te quedan {intentos_restantes} intentos."
        else:
            mensaje = "El código no es válido o ya venció. Solicita uno nuevo."
        super().__init__(mensaje, extra={"intentos_restantes": intentos_restantes})


class TokenRecuperacionInvalido(ErrorNegocio):
    codigo = "token_invalido"

    def __init__(self) -> None:
        super().__init__("La sesión de recuperación venció. Solicita un código nuevo.")
