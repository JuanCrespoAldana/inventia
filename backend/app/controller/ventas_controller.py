from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.dto.comunes_dto import Pagina, ParametrosPagina
from app.dto.ventas_dto import VentaAnular, VentaCrear, VentaDetalle, VentaResumen
from app.security.acceso import Contexto
from app.security.dependencias import requiere
from app.service import ventas_service as svc

router = APIRouter(prefix="/api/ventas", tags=["Ventas"])


@router.get("", response_model=Pagina[VentaResumen], summary="Consultar ventas")
async def listar(
    pag: ParametrosPagina = Depends(),
    sede_id: int | None = Query(None, gt=0),
    estado: str | None = Query(None, pattern="^(registrada|anulada)$"),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    numero: int | None = Query(None, gt=0, description="Número de venta"),
    ctx: Contexto = Depends(requiere("ventas.ver")),
    db: AsyncSession = Depends(get_db),
):
    filas, total = await svc.listar_ventas(db, ctx, pag, sede_id=sede_id, estado=estado, desde=desde, hasta=hasta, numero=numero)
    return Pagina.crear(filas, total, pag.pagina, pag.tamano)


@router.post("", response_model=VentaDetalle, status_code=status.HTTP_201_CREATED, summary="Registrar una venta")
async def registrar(datos: VentaCrear, ctx: Contexto = Depends(requiere("ventas.registrar")), db: AsyncSession = Depends(get_db)):
    venta = await svc.registrar_venta(db, ctx, datos)
    return await svc.detalle(db, ctx, venta)


@router.get("/{venta_id}", response_model=VentaDetalle, summary="Consultar una venta con su detalle")
async def obtener(venta_id: int, ctx: Contexto = Depends(requiere("ventas.ver")), db: AsyncSession = Depends(get_db)):
    return await svc.detalle(db, ctx, await svc.obtener_venta(db, ctx, venta_id))


@router.post("/{venta_id}/anular", response_model=VentaDetalle, summary="Anular una venta y reintegrar existencias")
async def anular(
    venta_id: int, datos: VentaAnular,
    ctx: Contexto = Depends(requiere("ventas.anular")), db: AsyncSession = Depends(get_db),
):
    venta = await svc.anular_venta(db, ctx, venta_id, datos.motivo)
    return await svc.detalle(db, ctx, venta)
