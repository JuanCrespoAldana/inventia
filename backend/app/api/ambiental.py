from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import requiere
from app.core.acceso import Contexto
from app.core.database import get_db
from app.schemas.ambiental import (
    CategoriaAmbientalActualizar,
    ConfiguracionAmbiental,
    FactorRedActualizar,
    RegistroAmbiental,
    ResultadoSincronizacion,
    ResumenAmbiental,
    TipoVehiculoT,
)
from app.schemas.comunes import Pagina, ParametrosPagina
from app.services import ambiental_service as svc

router = APIRouter(prefix="/api/sig/ambiental", tags=["SIG · Gestión ambiental"])


@router.get("/resumen", response_model=ResumenAmbiental, summary="Indicadores ambientales (vehículos vendidos y CO₂ estimado)")
async def resumen(
    anio: int | None = Query(None, ge=2000, le=2100),
    sede_id: int | None = Query(None, gt=0),
    ctx: Contexto = Depends(requiere("ambiental.ver")),
    db: AsyncSession = Depends(get_db),
):
    return await svc.resumen(db, ctx, anio, sede_id)


@router.get("/registros", response_model=Pagina[RegistroAmbiental], summary="Historial de ventas contabilizadas")
async def registros(
    pag: ParametrosPagina = Depends(),
    sede_id: int | None = Query(None, gt=0),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    tipo_vehiculo: TipoVehiculoT | None = Query(None),
    estado: str | None = Query(None, pattern="^(activo|anulado)$"),
    pendientes: bool | None = Query(None, description="true = solo los que aún no tienen CO₂ estimado"),
    ctx: Contexto = Depends(requiere("ambiental.ver")),
    db: AsyncSession = Depends(get_db),
):
    filas, total = await svc.listar_registros(
        db, ctx, pag, sede_id=sede_id, desde=desde, hasta=hasta, tipo_vehiculo=tipo_vehiculo, estado=estado, pendientes=pendientes
    )
    return Pagina.crear(filas, total, pag.pagina, pag.tamano)


@router.get("/configuracion", response_model=ConfiguracionAmbiental, summary="Parámetros de cálculo")
async def configuracion(ctx: Contexto = Depends(requiere("ambiental.ver")), db: AsyncSession = Depends(get_db)):
    return await svc.obtener_configuracion(db, ctx)


@router.put("/factor-red", response_model=ResultadoSincronizacion, summary="Definir el factor de emisión de la red eléctrica")
async def factor_red(datos: FactorRedActualizar, ctx: Contexto = Depends(requiere("ambiental.configurar")), db: AsyncSession = Depends(get_db)):
    return await svc.guardar_factor_red(db, ctx, datos)


@router.put("/categorias/{categoria_id}", response_model=ResultadoSincronizacion,
            summary="Marcar una categoría como vehículo y definir sus parámetros")
async def categoria(
    categoria_id: int, datos: CategoriaAmbientalActualizar,
    ctx: Contexto = Depends(requiere("ambiental.configurar")), db: AsyncSession = Depends(get_db),
):
    return await svc.guardar_categoria(db, ctx, categoria_id, datos)


@router.post("/sincronizar", response_model=ResultadoSincronizacion,
             summary="Incorporar ventas anteriores y calcular los registros pendientes")
async def sincronizar(ctx: Contexto = Depends(requiere("ambiental.configurar")), db: AsyncSession = Depends(get_db)):
    return await svc.ejecutar_sincronizacion(db, ctx)
