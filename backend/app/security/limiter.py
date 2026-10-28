from slowapi import Limiter
from starlette.requests import Request

from app.security.contexto import ip_de_scope


def _clave_ip(request: Request) -> str:
    return ip_de_scope(request.scope) or "desconocida"


# Límite por IP (RNF-026). El bloqueo por cuenta se aplica además en auth_service.
limiter = Limiter(key_func=_clave_ip)
