"""Administración de las llaves de acceso de los agentes de IA (RNF-049)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import requiere
from app.core.acceso import Contexto
from app.core.database import get_db
from app.schemas.prediccion import LlaveCrear, LlaveCreada, LlaveSalida
from app.services import agentes_service as svc

router = APIRouter(prefix="/api/integraciones", tags=["Integraciones"])


@router.get("/alcances", summary="Alcances que se pueden conceder a un agente")
async def alcances(ctx: Contexto = Depends(requiere("agentes.gestionar"))):
    return [{"alcance": k, "descripcion": v} for k, v in svc.ALCANCES.items()]


@router.get("/llaves", response_model=list[LlaveSalida], summary="Listar llaves de agentes")
async def listar(ctx: Contexto = Depends(requiere("agentes.gestionar")), db: AsyncSession = Depends(get_db)):
    return await svc.listar_llaves(db, ctx)


@router.post("/llaves", response_model=LlaveCreada, status_code=status.HTTP_201_CREATED, summary="Crear una llave")
async def crear(datos: LlaveCrear, ctx: Contexto = Depends(requiere("agentes.gestionar")), db: AsyncSession = Depends(get_db)):
    k, llave = await svc.crear_llave(db, ctx, datos)
    return LlaveCreada(**svc._salida(k).model_dump(), llave=llave)


@router.post("/llaves/{llave_id}/revocar", response_model=LlaveSalida, summary="Revocar una llave")
async def revocar(llave_id: int, ctx: Contexto = Depends(requiere("agentes.gestionar")), db: AsyncSession = Depends(get_db)):
    return await svc.revocar_llave(db, ctx, llave_id)
