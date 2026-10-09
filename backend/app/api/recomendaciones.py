from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import requiere
from app.core.acceso import Contexto
from app.core.database import get_db
from app.schemas.comunes import Pagina, ParametrosPagina
from app.schemas.prediccion import RecomendacionSalida, RevisionRecomendacion
from app.services import recomendaciones_service as svc
from app.services.alcance import resolver_filtro_sede

router = APIRouter(prefix="/api/recomendaciones", tags=["Recomendaciones"])


class ResultadoGeneracion(BaseModel):
    ejecucion_id: int
    generadas: int
    reabastecimientos: int
    traslados: int
    reemplazadas: int
    series_evaluadas: int


@router.get("", response_model=Pagina[RecomendacionSalida], summary="Consultar recomendaciones")
async def listar(
    pag: ParametrosPagina = Depends(),
    estado: str | None = Query(None, pattern="^(pendiente|aprobada|rechazada|ejecutada|reemplazada)$"),
    tipo: str | None = Query(None, pattern="^(reabastecimiento|traslado)$"),
    prioridad: str | None = Query(None, pattern="^(critica|alta|media|baja)$"),
    sede_id: int | None = Query(None, gt=0),
    q: str | None = Query(None, max_length=100),
    ctx: Contexto = Depends(requiere("recomendaciones.ver")),
    db: AsyncSession = Depends(get_db),
):
    filas, total = await svc.listar(
        db, ctx, pag, sede_ids=resolver_filtro_sede(ctx, sede_id), estado=estado, tipo=tipo, prioridad=prioridad, q=q
    )
    return Pagina.crear(await svc.salidas(db, ctx, filas), total, pag.pagina, pag.tamano)


@router.post(
    "/generar", response_model=ResultadoGeneracion, status_code=status.HTTP_201_CREATED,
    summary="Generar recomendaciones a partir de la última predicción",
)
async def generar(ctx: Contexto = Depends(requiere("recomendaciones.generar")), db: AsyncSession = Depends(get_db)):
    return ResultadoGeneracion(**await svc.generar(db, ctx))


@router.get("/{recomendacion_id}", response_model=RecomendacionSalida, summary="Consultar una recomendación")
async def obtener(recomendacion_id: int, ctx: Contexto = Depends(requiere("recomendaciones.ver")), db: AsyncSession = Depends(get_db)):
    r = await svc.obtener(db, ctx, recomendacion_id)
    return (await svc.salidas(db, ctx, [r]))[0]


@router.post("/{recomendacion_id}/aprobar", response_model=RecomendacionSalida, summary="Aprobar una recomendación")
async def aprobar(
    recomendacion_id: int, datos: RevisionRecomendacion, ctx: Contexto = Depends(requiere("recomendaciones.aprobar")),
    db: AsyncSession = Depends(get_db),
):
    r = await svc.aprobar(db, ctx, recomendacion_id, datos.comentario)
    return (await svc.salidas(db, ctx, [r]))[0]


@router.post("/{recomendacion_id}/rechazar", response_model=RecomendacionSalida, summary="Rechazar una recomendación")
async def rechazar(
    recomendacion_id: int, datos: RevisionRecomendacion, ctx: Contexto = Depends(requiere("recomendaciones.aprobar")),
    db: AsyncSession = Depends(get_db),
):
    r = await svc.rechazar(db, ctx, recomendacion_id, datos.comentario)
    return (await svc.salidas(db, ctx, [r]))[0]


@router.post("/{recomendacion_id}/ejecutar", response_model=RecomendacionSalida, summary="Marcar un reabastecimiento aprobado como realizado")
async def ejecutar(
    recomendacion_id: int, datos: RevisionRecomendacion, ctx: Contexto = Depends(requiere("recomendaciones.aprobar")),
    db: AsyncSession = Depends(get_db),
):
    r = await svc.ejecutar(db, ctx, recomendacion_id, datos.comentario)
    return (await svc.salidas(db, ctx, [r]))[0]
