from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import contexto_actual
from app.core.acceso import Contexto
from app.core.database import get_db
from app.services import dashboard_service

router = APIRouter(prefix="/api/dashboard", tags=["Panel de control"])


@router.get("", summary="Indicadores del panel (solo las secciones que el usuario puede ver)")
async def dashboard(
    sede_id: int | None = Query(None, gt=0, description="Limita todas las cifras a una sede"),
    dias: int = Query(30, ge=7, le=365, description="Periodo de ventas en días"),
    ctx: Contexto = Depends(contexto_actual),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await dashboard_service.construir(db, ctx, sede_id=sede_id, dias=dias)
