from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import requiere
from app.core.acceso import Contexto
from app.core.database import get_db
from app.schemas.comunes import Pagina, ParametrosPagina
from app.schemas.pqrs import (
    AmbitoPqrsT,
    EstadoPqrsT,
    PqrsConteo,
    PqrsCrear,
    PqrsDetalle,
    PqrsGestionar,
    PqrsResumen,
    TipoPqrsT,
)
from app.services import pqrs_service as svc

router = APIRouter(prefix="/api/sig/pqrs", tags=["SIG · PQRS"])


@router.get("", response_model=Pagina[PqrsResumen], summary="Consultar PQRS (las propias o, con permiso, todas)")
async def listar(
    pag: ParametrosPagina = Depends(),
    ambito: AmbitoPqrsT = Query("mias", description="«todas» exige el permiso de gestión"),
    tipo: TipoPqrsT | None = Query(None),
    estado: EstadoPqrsT | None = Query(None),
    usuario_id: int | None = Query(None, gt=0),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    q: str | None = Query(None, max_length=100, description="Texto del asunto o número de radicado"),
    ctx: Contexto = Depends(requiere("pqrs.crear", "pqrs.gestionar")),
    db: AsyncSession = Depends(get_db),
):
    filas, total = await svc.listar(
        db, ctx, pag, ambito=ambito, tipo=tipo, estado=estado, usuario_id=usuario_id, desde=desde, hasta=hasta, q=q
    )
    return Pagina.crear(filas, total, pag.pagina, pag.tamano)


@router.post("", response_model=PqrsDetalle, status_code=status.HTTP_201_CREATED, summary="Enviar una PQRS")
async def crear(datos: PqrsCrear, ctx: Contexto = Depends(requiere("pqrs.crear")), db: AsyncSession = Depends(get_db)):
    return await svc.detalle(db, ctx, await svc.crear(db, ctx, datos))


@router.get("/conteo", response_model=PqrsConteo, summary="Cantidad de PQRS por estado")
async def conteo(ctx: Contexto = Depends(requiere("pqrs.gestionar")), db: AsyncSession = Depends(get_db)):
    return await svc.conteo(db, ctx)


@router.get("/{pqrs_id}", response_model=PqrsDetalle, summary="Detalle de una PQRS con su historial")
async def obtener(
    pqrs_id: int, ctx: Contexto = Depends(requiere("pqrs.crear", "pqrs.gestionar")), db: AsyncSession = Depends(get_db)
):
    return await svc.detalle(db, ctx, await svc.obtener(db, ctx, pqrs_id))


@router.patch("/{pqrs_id}", response_model=PqrsDetalle, summary="Cambiar el estado o responder una PQRS")
async def gestionar(
    pqrs_id: int, datos: PqrsGestionar, ctx: Contexto = Depends(requiere("pqrs.gestionar")), db: AsyncSession = Depends(get_db)
):
    return await svc.detalle(db, ctx, await svc.gestionar(db, ctx, pqrs_id, datos))
