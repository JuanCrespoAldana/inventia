"""Datos de la petición en curso (IP, identificador) disponibles para auditoría y registros,
y middleware ASGI que los establece y añade cabeceras de seguridad."""

import uuid
from contextvars import ContextVar

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import settings

_ip: ContextVar[str | None] = ContextVar("ip_cliente", default=None)
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def ip_actual() -> str | None:
    return _ip.get()


def request_id_actual() -> str | None:
    return _request_id.get()


def ip_de_scope(scope: Scope) -> str | None:
    if settings.trust_proxy_headers:
        for nombre, valor in scope.get("headers", []):
            if nombre == b"x-forwarded-for":
                return valor.decode("latin-1").split(",")[0].strip() or None
    cliente = scope.get("client")
    return cliente[0] if cliente else None


CABECERAS_SEGURIDAD = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"cache-control", b"no-store"),
    (b"permissions-policy", b"geolocation=(), microphone=(), camera=()"),
]


class ContextoPeticionMiddleware:
    """Middleware ASGI puro (no BaseHTTPMiddleware) para que los contextvars lleguen al endpoint
    y a las tareas en segundo plano."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        rid = uuid.uuid4().hex[:16]
        token_ip = _ip.set(ip_de_scope(scope))
        token_rid = _request_id.set(rid)

        async def enviar(mensaje: Message) -> None:
            if mensaje["type"] == "http.response.start":
                cabeceras = list(mensaje.get("headers", []))
                presentes = {c[0] for c in cabeceras}
                cabeceras.append((b"x-request-id", rid.encode()))
                for nombre, valor in CABECERAS_SEGURIDAD:
                    if nombre not in presentes:
                        cabeceras.append((nombre, valor))
                mensaje["headers"] = cabeceras
            await send(mensaje)

        try:
            await self.app(scope, receive, enviar)
        finally:
            _ip.reset(token_ip)
            _request_id.reset(token_rid)
