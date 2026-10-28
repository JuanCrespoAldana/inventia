from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.config.settings import settings
from app.dto.auth_dto import (
    CambiarPasswordEntrada,
    LoginEntrada,
    RestablecerPasswordEntrada,
    SolicitudRecuperacion,
    TokenSalida,
    VerificarCodigoEntrada,
    VerificarCodigoSalida,
)
from app.dto.comunes_dto import Mensaje
from app.dto.usuario_dto import UsuarioSesion
from app.security.acceso import Contexto
from app.security.dependencias import contexto_de_usuario, contexto_sesion
from app.security.limiter import limiter
from app.service import auth_service
from app.service.sesion import construir_sesion

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenSalida, summary="Iniciar sesión")
@limiter.limit("10/minute")
async def iniciar_sesion(request: Request, datos: LoginEntrada, db: AsyncSession = Depends(get_db)):
    token, usuario = await auth_service.iniciar_sesion(db, datos.email, datos.password)
    return TokenSalida(
        access_token=token,
        expira_en_minutos=settings.access_token_expire_minutes,
        usuario=await construir_sesion(db, contexto_de_usuario(usuario)),
    )


@router.post("/logout", response_model=Mensaje, summary="Cerrar sesión (queda en la auditoría)")
async def cerrar_sesion(ctx: Contexto = Depends(contexto_sesion), db: AsyncSession = Depends(get_db)):
    await auth_service.cerrar_sesion(db, ctx)
    return Mensaje(mensaje="Sesión cerrada")


@router.get("/me", response_model=UsuarioSesion, summary="Datos y permisos del usuario autenticado")
async def usuario_actual(ctx: Contexto = Depends(contexto_sesion), db: AsyncSession = Depends(get_db)):
    return await construir_sesion(db, ctx)


@router.post("/cambiar-password", response_model=TokenSalida, summary="Cambiar la contraseña propia")
@limiter.limit("5/minute")
async def cambiar_password(
    request: Request,
    datos: CambiarPasswordEntrada,
    ctx: Contexto = Depends(contexto_sesion),
    db: AsyncSession = Depends(get_db),
):
    token = await auth_service.cambiar_password(db, ctx, datos.password_actual, datos.nueva_password)
    await db.refresh(ctx.usuario)
    return TokenSalida(
        access_token=token,
        expira_en_minutos=settings.access_token_expire_minutes,
        usuario=await construir_sesion(db, contexto_de_usuario(ctx.usuario)),
    )


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED, response_model=Mensaje,
             summary="Solicitar código de recuperación")
@limiter.limit("3/minute")
async def olvide_password(request: Request, datos: SolicitudRecuperacion, db: AsyncSession = Depends(get_db)):
    await auth_service.solicitar_recuperacion(db, datos.email)
    # Misma respuesta exista o no el correo (evita enumerar usuarios).
    return Mensaje(mensaje="Si el correo está registrado, recibirás un código para restablecer tu contraseña")


@router.post("/verify-reset-code", response_model=VerificarCodigoSalida, summary="Validar el código recibido")
@limiter.limit("10/minute")
async def verificar_codigo(request: Request, datos: VerificarCodigoEntrada, db: AsyncSession = Depends(get_db)):
    return VerificarCodigoSalida(session_token=await auth_service.verificar_codigo(db, datos.email, datos.codigo))


@router.post("/reset-password", response_model=Mensaje, summary="Crear la nueva contraseña")
@limiter.limit("5/minute")
async def restablecer(request: Request, datos: RestablecerPasswordEntrada, db: AsyncSession = Depends(get_db)):
    await auth_service.restablecer_password(db, datos.session_token, datos.nueva_password)
    return Mensaje(mensaje="Contraseña actualizada correctamente")
