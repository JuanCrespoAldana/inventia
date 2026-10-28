"""Manejadores de excepciones: traducen cada error a una respuesta JSON uniforme (RNF-010).

Ningún error técnico llega al usuario. Formato de error: ``{"detail": "mensaje en español", "codigo": "identificador_estable", ...}``.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import DataError as DatoInvalidoBD
from sqlalchemy.exc import DBAPIError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exception.excepciones import ErrorNegocio
from app.security.contexto import request_id_actual

logger = logging.getLogger("inventia.errores")


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


def es_dato_numerico_invalido(exc: DBAPIError) -> bool:
    """¿La base rechazó un VALOR enviado por quien llama (p. ej. un id de 30 dígitos) y no una falla del servidor?

    Con PostgreSQL ocurre de varias maneras: el servidor devuelve un error de clase 22 (texto demasiado largo, formato
    inválido, byte nulo en un texto…) o el controlador asyncpg se niega a codificar el argumento porque no cabe en
    ``INTEGER``/``BIGINT``. Todos son entradas inválidas: se responden con 422, no con 500.
    """
    if isinstance(exc, DatoInvalidoBD):
        return True
    causa = getattr(exc.orig, "__cause__", None)
    # asyncpg agrupa en ``DataError`` tanto el argumento que no cabe como los errores de clase 22 del servidor
    # (p. ej. ``CharacterNotInRepertoireError`` cuando el texto trae un byte nulo, que PostgreSQL no admite).
    return any(c.__name__ == "DataError" and c.__module__.startswith("asyncpg") for c in type(causa).__mro__)


def _documentar_error_de_validacion(app: FastAPI) -> None:
    """Hace que el contrato OpenAPI describa el cuerpo REAL de los errores 422.

    FastAPI documenta por defecto ``{"detail": [{"loc", "msg", "type"}]}``, pero esta API responde con el mismo formato
    que el resto de sus errores (``detail`` en texto, ``codigo`` y la lista ``errores`` por campo). Sin este ajuste, el
    contrato y el comportamiento no coincidían (lo detectó la prueba de contrato con Schemathesis).
    """
    original = app.openapi

    def con_errores_reales() -> dict[str, Any]:
        esquema = original()
        esquemas = esquema.get("components", {}).get("schemas", {})
        if "HTTPValidationError" in esquemas:
            esquemas["ErrorDeCampo"] = {
                "type": "object", "title": "ErrorDeCampo", "required": ["campo", "mensaje"],
                "properties": {"campo": {"type": "string", "title": "Campo"}, "mensaje": {"type": "string", "title": "Mensaje"}},
            }
            esquemas["HTTPValidationError"] = {
                "type": "object", "title": "HTTPValidationError", "required": ["detail", "codigo"],
                "properties": {
                    "detail": {"type": "string", "title": "Detail"},
                    "codigo": {"type": "string", "title": "Codigo"},
                    "request_id": {"type": "string", "title": "Request Id"},
                    "errores": {"type": "array", "title": "Errores", "items": {"$ref": "#/components/schemas/ErrorDeCampo"}},
                },
            }
            esquemas.pop("ValidationError", None)
        return esquema

    app.openapi = con_errores_reales  # type: ignore[method-assign]


def registrar_manejadores_excepciones(app: FastAPI) -> None:
    _documentar_error_de_validacion(app)

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

    @app.exception_handler(DBAPIError)
    async def _base_de_datos(request: Request, exc: DBAPIError) -> JSONResponse:
        if es_dato_numerico_invalido(exc):
            logger.warning("Valor rechazado por la base en %s %s: %s", request.method, request.url.path, type(exc.orig).__name__)
            return _respuesta(422, "Hay un valor fuera del rango permitido", "validacion", errores=[])
        logger.error("Error de base de datos en %s %s", request.method, request.url.path, exc_info=exc)
        return _respuesta(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Ocurrió un error interno. Inténtalo de nuevo; si persiste, informa al administrador.",
            "error_interno",
        )

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
