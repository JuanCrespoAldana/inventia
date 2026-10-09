from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import contexto_de_usuario
from app.core.config import settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import create_access_token
from app.schemas.auth import TokenSalida
from app.schemas.setup import ConfiguracionInicial, EstadoInstalacion
from app.services import setup_service
from app.services.sesion import construir_sesion

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
