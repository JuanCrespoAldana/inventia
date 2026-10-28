from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.config.settings import settings
from app.dto.auth_dto import TokenSalida
from app.dto.setup_dto import ConfiguracionInicial, EstadoInstalacion
from app.security.autenticacion import create_access_token
from app.security.dependencias import contexto_de_usuario
from app.security.limiter import limiter
from app.service import setup_service
from app.service.sesion import construir_sesion

router = APIRouter(prefix="/api/setup", tags=["Configuración inicial"])


@router.get("/estado", response_model=EstadoInstalacion, summary="¿Ya se configuró la empresa?")
async def estado(db: AsyncSession = Depends(get_db)):
    return EstadoInstalacion(
        configurado=await setup_service.hay_empresa(db),
        requiere_token=bool(settings.setup_token),
        nombre_aplicacion=settings.app_nombre,
    )


@router.post(
    "",
    response_model=TokenSalida,
    status_code=status.HTTP_201_CREATED,
    summary="Crear la empresa y su primer administrador (solo una vez)",
)
@limiter.limit("5/minute")
async def configurar(request: Request, datos: ConfiguracionInicial, db: AsyncSession = Depends(get_db)):
    _, admin = await setup_service.configurar(db, datos)
    ctx = contexto_de_usuario(admin)
    return TokenSalida(
        access_token=create_access_token(admin.id, admin.password_version),
        expira_en_minutos=settings.access_token_expire_minutes,
        usuario=await construir_sesion(db, ctx),
    )
