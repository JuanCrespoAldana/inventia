from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.dto.asistente_dto import AyudaAsistente, PreguntaAsistente, RespuestaAsistente
from app.security.acceso import Contexto
from app.security.dependencias import contexto_actual
from app.security.limiter import limiter
from app.service import asistente_service as svc

router = APIRouter(prefix="/api/asistente", tags=["Asistente"])


@router.post(
    "/preguntar", response_model=RespuestaAsistente,
    summary="Hacerle una pregunta al asistente (solo consulta; respeta el rol y la sede de quien pregunta)",
)
@limiter.limit("60/minute")
async def preguntar(request: Request, datos: PreguntaAsistente, ctx: Contexto = Depends(contexto_actual), db: AsyncSession = Depends(get_db)):
    return await svc.preguntar(db, ctx, datos)


@router.get("/ayuda", response_model=AyudaAsistente, summary="Ejemplos de preguntas según los permisos de quien consulta")
async def ayuda(ctx: Contexto = Depends(contexto_actual)):
    return svc.ayuda(ctx)
