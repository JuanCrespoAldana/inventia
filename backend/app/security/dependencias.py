"""Dependencias de FastAPI: autenticación, contexto del usuario y control de permisos (RF-038)."""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.exception.excepciones import NoAutenticado, SinPermiso
from app.model.empresa import Empresa
from app.model.usuario import Usuario
from app.security.acceso import Contexto
from app.security.autenticacion import decode_access_token

esquema_bearer = HTTPBearer(auto_error=False, description="Token JWT obtenido en /api/auth/login")


def contexto_de_usuario(usuario: Usuario) -> Contexto:
    return Contexto(usuario=usuario, permisos=frozenset(usuario.rol.codigos_permisos))


async def _cargar_contexto(
    credenciales: HTTPAuthorizationCredentials | None, db: AsyncSession
) -> Contexto:
    sin_sesion = NoAutenticado("No se pudo validar la sesión", codigo="sesion_invalida")
    if credenciales is None:
        raise sin_sesion
    payload = decode_access_token(credenciales.credentials)
    if payload is None:
        raise sin_sesion
    try:
        usuario_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise sin_sesion from None

    usuario = await db.scalar(select(Usuario).where(Usuario.id == usuario_id))
    if usuario is None or not usuario.activo or payload.get("pv") != usuario.password_version:
        raise sin_sesion  # cuenta inhabilitada o contraseña cambiada después de emitir el token
    empresa = await db.get(Empresa, usuario.empresa_id)
    if empresa is None or not empresa.activa:
        raise sin_sesion
    return contexto_de_usuario(usuario)


async def contexto_sesion(
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
    db: AsyncSession = Depends(get_db),
) -> Contexto:
    """Usuario autenticado, SIN exigir que haya cambiado una contraseña temporal."""
    return await _cargar_contexto(credenciales, db)


async def contexto_actual(ctx: Contexto = Depends(contexto_sesion)) -> Contexto:
    """Usuario autenticado y habilitado para operar (ya cambió su contraseña temporal)."""
    if ctx.usuario.debe_cambiar_password:
        raise SinPermiso("Debes cambiar tu contraseña temporal antes de continuar", codigo="debe_cambiar_password")
    return ctx


def requiere(*permisos: str):
    """Exige al menos uno de los permisos indicados. Se valida en el servidor en cada llamada,
    aunque el frontend oculte los botones."""

    async def _dependencia(ctx: Contexto = Depends(contexto_actual)) -> Contexto:
        ctx.exigir(*permisos)
        return ctx

    return _dependencia
