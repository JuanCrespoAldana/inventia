"""Excepciones de negocio y su traducción centralizada a respuestas HTTP.

Los servicios lanzan estas excepciones y aquí se convierten UNA sola vez en JSON, de modo que
ningún endpoint repite bloques try/except (y ningún error técnico llega al usuario — RNF-010).
Formato de error: ``{"detail": "mensaje en español", "codigo": "identificador_estable", ...}``.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.contexto import request_id_actual

logger = logging.getLogger("inventia.errores")


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


def _respuesta(status_code: int, detalle: str, codigo: str, **extra: Any) -> JSONResponse:
    cuerpo: dict[str, Any] = {"detail": detalle, "codigo": codigo, **extra}
    rid = request_id_actual()
    if rid:
        cuerpo["request_id"] = rid
    return JSONResponse(status_code=status_code, content=cuerpo)


# ---- Traducción de los mensajes de validación de Pydantic ----
_TRADUCCIONES = {
    "missing": "Este campo es obligatorio",
    "string_too_short": "Debe tener al menos {min_length} caracteres",
    "string_too_long": "No puede superar los {max_length} caracteres",
    "string_type": "Debe ser un texto",
    "int_type": "Debe ser un número entero",
    "int_parsing": "Debe ser un número entero",
    "float_type": "Debe ser un número",
    "float_parsing": "Debe ser un número",
    "decimal_parsing": "Debe ser un número válido",
    "decimal_type": "Debe ser un número válido",
    "greater_than": "Debe ser mayor que {gt}",
    "greater_than_equal": "Debe ser mayor o igual que {ge}",
    "less_than": "Debe ser menor que {lt}",
    "less_than_equal": "Debe ser menor o igual que {le}",
    "bool_parsing": "Debe ser verdadero o falso",
    "date_parsing": "Debe ser una fecha válida (AAAA-MM-DD)",
    "date_from_datetime_parsing": "Debe ser una fecha válida (AAAA-MM-DD)",
    "datetime_parsing": "Debe ser una fecha y hora válidas",
    "datetime_from_date_parsing": "Debe ser una fecha y hora válidas",
    "too_short": "Debe contener al menos {min_length} elementos",
    "too_long": "No puede contener más de {max_length} elementos",
    "list_type": "Debe ser una lista",
    "literal_error": "Valor no permitido",
    "enum": "Valor no permitido",
    "string_pattern_mismatch": "El formato no es válido",
    "json_invalid": "El cuerpo de la petición no es un JSON válido",
    "extra_forbidden": "Campo no permitido",
}


def _traducir_error(err: dict[str, Any]) -> str:
    tipo = err.get("type", "")
    contexto = err.get("ctx") or {}
    if tipo == "value_error":
        mensaje = str(err.get("msg", ""))
        return mensaje.removeprefix("Value error, ")
    if tipo.startswith("value_error.email") or "email" in str(err.get("msg", "")).lower():
        return "Escribe un correo electrónico válido"
    plantilla = _TRADUCCIONES.get(tipo)
    if plantilla:
        try:
            return plantilla.format(**contexto)
        except (KeyError, IndexError):
            return plantilla.split("{")[0].strip()
    return "El valor no es válido"


def registrar_manejadores_excepciones(app: FastAPI) -> None:
    @app.exception_handler(ErrorNegocio)
    async def _error_negocio(request: Request, exc: ErrorNegocio) -> JSONResponse:
        return _respuesta(exc.status_code, exc.mensaje, exc.codigo, **exc.extra)

    @app.exception_handler(RequestValidationError)
    async def _validacion(request: Request, exc: RequestValidationError) -> JSONResponse:
        errores = []
        for e in exc.errors():
            ruta = [str(p) for p in e.get("loc", ()) if p not in ("body", "query", "path")]
            errores.append({"campo": ".".join(ruta), "mensaje": _traducir_error(e)})
        resumen = errores[0]["mensaje"] if len(errores) == 1 and not errores[0]["campo"] else "Hay datos que no son válidos"
        return _respuesta(422, resumen, "validacion", errores=errores)

    @app.exception_handler(RateLimitExceeded)
    async def _limite(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        respuesta = _respuesta(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Demasiados intentos en poco tiempo. Espera un momento e inténtalo de nuevo.",
            "demasiadas_peticiones",
        )
        respuesta.headers["Retry-After"] = "60"
        return respuesta

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        mensajes = {
            401: "No se pudo validar la sesión",
            403: "No tienes permiso para realizar esta acción",
            404: "El recurso solicitado no existe",
            405: "Método no permitido",
        }
        detalle = mensajes.get(exc.status_code) or (exc.detail if isinstance(exc.detail, str) else "Error de solicitud")
        respuesta = _respuesta(exc.status_code, detalle, "http_error")
        if exc.headers:
            respuesta.headers.update(exc.headers)
        return respuesta

    @app.exception_handler(Exception)
    async def _inesperado(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Error no controlado en %s %s", request.method, request.url.path)
        return _respuesta(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Ocurrió un error interno. Inténtalo de nuevo; si persiste, informa al administrador.",
            "error_interno",
        )
