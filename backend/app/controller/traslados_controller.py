from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.dto.comunes_dto import Pagina, ParametrosPagina
from app.dto.traslados_dto import TrasladoCrear, TrasladoDetalle, TrasladoMotivo, TrasladoResumen
from app.security.acceso import Contexto
from app.security.dependencias import requiere
from app.service import traslados_service as svc

router = APIRouter(prefix="/api/traslados", tags=["Traslados"])


@router.get("", response_model=Pagina[TrasladoResumen], summary="Consultar traslados")
async def listar(
    pag: ParametrosPagina = Depends(),
    sede_id: int | None = Query(None, gt=0, description="Traslados que salen de o llegan a esta sede"),
    estado: str | None = Query(None, pattern="^(solicitado|aprobado|confirmado|rechazado|cancelado)$"),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    numero: int | None = Query(None, gt=0),
    ctx: Contexto = Depends(requiere("traslados.ver")),
    db: AsyncSession = Depends(get_db),
):
    filas, total = await svc.listar_traslados(db, ctx, pag, sede_id=sede_id, estado=estado, desde=desde, hasta=hasta, numero=numero)
    return Pagina.crear(filas, total, pag.pagina, pag.tamano)


@router.post("", response_model=TrasladoDetalle, status_code=status.HTTP_201_CREATED, summary="Solicitar un traslado entre sedes")
async def solicitar(datos: TrasladoCrear, ctx: Contexto = Depends(requiere("traslados.solicitar")), db: AsyncSession = Depends(get_db)):
    return await svc.detalle(db, ctx, await svc.crear_traslado(db, ctx, datos))


@router.get("/{traslado_id}", response_model=TrasladoDetalle, summary="Consultar un traslado")
async def obtener(traslado_id: int, ctx: Contexto = Depends(requiere("traslados.ver")), db: AsyncSession = Depends(get_db)):
    return await svc.detalle(db, ctx, await svc.obtener_traslado(db, ctx, traslado_id))


@router.post("/{traslado_id}/aprobar", response_model=TrasladoDetalle, summary="Aprobar un traslado solicitado")
async def aprobar(traslado_id: int, ctx: Contexto = Depends(requiere("traslados.aprobar")), db: AsyncSession = Depends(get_db)):
    return await svc.detalle(db, ctx, await svc.aprobar(db, ctx, traslado_id))


@router.post("/{traslado_id}/rechazar", response_model=TrasladoDetalle, summary="Rechazar un traslado solicitado")
async def rechazar(traslado_id: int, datos: TrasladoMotivo, ctx: Contexto = Depends(requiere("traslados.aprobar")), db: AsyncSession = Depends(get_db)):
    return await svc.detalle(db, ctx, await svc.rechazar(db, ctx, traslado_id, datos.motivo))


@router.post("/{traslado_id}/confirmar", response_model=TrasladoDetalle, summary="Confirmar la recepción y mover las existencias")
async def confirmar(traslado_id: int, ctx: Contexto = Depends(requiere("traslados.confirmar")), db: AsyncSession = Depends(get_db)):
    return await svc.detalle(db, ctx, await svc.confirmar(db, ctx, traslado_id))


@router.post("/{traslado_id}/cancelar", response_model=TrasladoDetalle, summary="Cancelar un traslado pendiente")
async def cancelar(
    traslado_id: int, datos: TrasladoMotivo,
    ctx: Contexto = Depends(requiere("traslados.solicitar", "traslados.aprobar")), db: AsyncSession = Depends(get_db),
):
    return await svc.detalle(db, ctx, await svc.cancelar(db, ctx, traslado_id, datos.motivo))
