"""Dependencias de FastAPI: autenticación, contexto del usuario y control de permisos (RF-038)."""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.config.database import get_db
from app.exception.excepciones import NoAutenticado, SinPermiso
from app.model.acceso import Rol
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

    # Una sola consulta con usuario, rol, permisos y empresa. Antes eran tres viajes a la base en
    # cada petición; con una base remota (Neon) cada viaje cuesta decenas de milisegundos. La
    # empresa queda en el mapa de identidad de la sesión, así que los servicios que luego la
    # piden con ``db.get(Empresa, ...)`` ya no vuelven a consultarla.
    consulta = (
        select(Usuario, Empresa)
        .join(Empresa, Empresa.id == Usuario.empresa_id)
        .options(joinedload(Usuario.rol).joinedload(Rol.permisos))
        .where(Usuario.id == usuario_id)
    )
    fila = (await db.execute(consulta)).unique().first()
    if fila is None:
        raise sin_sesion
    usuario, empresa = fila
    if not usuario.activo or not empresa.activa or payload.get("pv") != usuario.password_version:
        raise sin_sesion  # cuenta o empresa inhabilitadas, o contraseña cambiada tras emitir el token
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
