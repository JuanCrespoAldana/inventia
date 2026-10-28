from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.dto.comunes_dto import Pagina, ParametrosPagina
from app.model.auditoria import Auditoria
from app.security.acceso import Contexto
from app.security.dependencias import requiere
from app.service import auditoria_service

router = APIRouter(prefix="/api/auditoria", tags=["Auditoría"])


class RegistroAuditoria(BaseModel):
    id: int
    fecha: datetime
    usuario_email: str | None
    modulo: str
    accion: str
    entidad: str | None
    entidad_id: str | None
    resultado: str
    detalle: dict
    ip: str | None
    sede_id: int | None

    model_config = {"from_attributes": True}


@router.get("", response_model=Pagina[RegistroAuditoria], summary="Consultar la auditoría")
async def consultar(
    pag: ParametrosPagina = Depends(),
    usuario_id: int | None = Query(None, gt=0),
    modulo: str | None = Query(None, max_length=40),
    accion: str | None = Query(None, max_length=60),
    resultado: str | None = Query(None, pattern="^(exitoso|fallido)$"),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    q: str | None = Query(None, max_length=100, description="Busca en usuario, acción y entidad"),
    ctx: Contexto = Depends(requiere("auditoria.ver", "auditoria.operaciones")),
    db: AsyncSession = Depends(get_db),
):
    filas, total = await auditoria_service.consultar(
        db, ctx, usuario_id=usuario_id, modulo=modulo, accion=accion, resultado=resultado, desde=desde, hasta=hasta,
        q=q, pagina=pag.pagina, tamano=pag.tamano,
    )
    return Pagina.crear([RegistroAuditoria.model_validate(f) for f in filas], total, pag.pagina, pag.tamano)


class OpcionesAuditoria(BaseModel):
    modulos: list[str]
    acciones: list[str]


@router.get("/opciones", response_model=OpcionesAuditoria, summary="Módulos y acciones disponibles para filtrar")
async def opciones(ctx: Contexto = Depends(requiere("auditoria.ver", "auditoria.operaciones")), db: AsyncSession = Depends(get_db)):
    consulta = select(Auditoria.modulo, Auditoria.accion).where(Auditoria.empresa_id == ctx.empresa_id).distinct()
    if not ctx.tiene("auditoria.ver"):
        consulta = consulta.where(Auditoria.modulo != "auth")
    filas = (await db.execute(consulta)).all()
    return OpcionesAuditoria(modulos=sorted({m for m, _ in filas}), acciones=sorted({a for _, a in filas}))
