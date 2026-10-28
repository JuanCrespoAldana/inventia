from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.dto.catalogo_dto import ProductoResumen
from app.dto.comunes_dto import Pagina, ParametrosPagina
from app.dto.sede_dto import SedeResumen
from app.security.acceso import Contexto
from app.security.dependencias import requiere
from app.service import alertas_service as svc
from app.service.alcance import resolver_filtro_sede

router = APIRouter(prefix="/api/alertas", tags=["Alertas"])


class AlertaSalida(BaseModel):
    id: int
    tipo: str
    prioridad: str
    estado: str
    mensaje: str
    detalle: dict
    abierta_en: datetime
    resuelta_en: datetime | None
    producto: ProductoResumen
    sede: SedeResumen


class ResumenAlertas(BaseModel):
    total: int
    por_tipo: dict[str, int]
    por_prioridad: dict[str, int]


@router.get("", response_model=Pagina[AlertaSalida], summary="Consultar alertas de inventario")
async def listar(
    pag: ParametrosPagina = Depends(),
    estado: str | None = Query("activa", pattern="^(activa|resuelta)$", description="Vacío = todas"),
    tipo: str | None = Query(None, max_length=30),
    prioridad: str | None = Query(None, pattern="^(critica|alta|media|baja)$"),
    sede_id: int | None = Query(None, gt=0),
    q: str | None = Query(None, max_length=100),
    ctx: Contexto = Depends(requiere("alertas.ver")),
    db: AsyncSession = Depends(get_db),
):
    filas, total = await svc.listar(
        db, ctx, pag, sede_ids=resolver_filtro_sede(ctx, sede_id), estado=estado, tipo=tipo, prioridad=prioridad, q=q
    )
    items = [
        AlertaSalida(
            id=a.id, tipo=a.tipo, prioridad=a.prioridad, estado=a.estado, mensaje=a.mensaje, detalle=a.detalle,
            abierta_en=a.abierta_en, resuelta_en=a.resuelta_en, producto=ProductoResumen.model_validate(p),
            sede=SedeResumen.model_validate(s),
        )
        for a, p, s in filas
    ]
    return Pagina.crear(items, total, pag.pagina, pag.tamano)


@router.get("/resumen", response_model=ResumenAlertas, summary="Conteo de alertas activas")
async def resumen(
    sede_id: int | None = Query(None, gt=0),
    ctx: Contexto = Depends(requiere("alertas.ver")),
    db: AsyncSession = Depends(get_db),
):
    return ResumenAlertas(**await svc.resumen(db, ctx, resolver_filtro_sede(ctx, sede_id)))


class ResultadoRecalculo(BaseModel):
    abiertas: int
    resueltas: int
    actualizadas: int
    activas: int
    series_evaluadas: int


@router.post("/recalcular", response_model=ResultadoRecalculo, summary="Re-evaluar todas las alertas")
async def recalcular(ctx: Contexto = Depends(requiere("alertas.recalcular")), db: AsyncSession = Depends(get_db)):
    return ResultadoRecalculo(**await svc.recalcular_empresa(db, ctx))
