from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.dto.calidad_dto import (
    EstadoGarantiaT,
    EstadoNcT,
    GarantiaCrear,
    GarantiaDetalle,
    GarantiaGestionar,
    GarantiaResumen,
    NoConformidadCrear,
    NoConformidadDetalle,
    NoConformidadGestionar,
    NoConformidadResumen,
    ObservacionCrear,
    ResumenCalidad,
    TipoNcT,
)
from app.dto.comunes_dto import Pagina, ParametrosPagina
from app.security.acceso import Contexto
from app.security.dependencias import requiere
from app.service import calidad_service as svc

router = APIRouter(prefix="/api/sig/calidad", tags=["SIG · Calidad"])


@router.get("/resumen", response_model=ResumenCalidad, summary="Conteo de no conformidades y garantías por estado")
async def resumen(
    sede_id: int | None = Query(None, gt=0),
    ctx: Contexto = Depends(requiere("calidad.ver")),
    db: AsyncSession = Depends(get_db),
):
    return await svc.resumen(db, ctx, sede_id)


# --------------------------------------------------------------- no conformidades
@router.get("/no-conformidades", response_model=Pagina[NoConformidadResumen], summary="Consultar no conformidades")
async def listar_nc(
    pag: ParametrosPagina = Depends(),
    sede_id: int | None = Query(None, gt=0),
    estado: EstadoNcT | None = Query(None),
    tipo: TipoNcT | None = Query(None),
    producto_id: int | None = Query(None, gt=0),
    entrada_id: int | None = Query(None, gt=0),
    desde: date | None = Query(None, description="Fecha de detección desde"),
    hasta: date | None = Query(None, description="Fecha de detección hasta"),
    q: str | None = Query(None, max_length=100, description="Producto, código, referencia o número"),
    ctx: Contexto = Depends(requiere("calidad.ver")),
    db: AsyncSession = Depends(get_db),
):
    filas, total = await svc.listar_nc(
        db, ctx, pag, sede_id=sede_id, estado=estado, tipo=tipo, producto_id=producto_id, entrada_id=entrada_id,
        desde=desde, hasta=hasta, q=q,
    )
    return Pagina.crear(filas, total, pag.pagina, pag.tamano)


@router.post("/no-conformidades", response_model=NoConformidadDetalle, status_code=status.HTTP_201_CREATED,
             summary="Registrar una no conformidad (no modifica existencias)")
async def crear_nc(datos: NoConformidadCrear, ctx: Contexto = Depends(requiere("calidad.reportar", "calidad.gestionar")),
                   db: AsyncSession = Depends(get_db)):
    return await svc.detalle_nc(db, ctx, await svc.crear_nc(db, ctx, datos))


@router.get("/no-conformidades/{nc_id}", response_model=NoConformidadDetalle, summary="Detalle de una no conformidad")
async def obtener_nc(nc_id: int, ctx: Contexto = Depends(requiere("calidad.ver")), db: AsyncSession = Depends(get_db)):
    return await svc.detalle_nc(db, ctx, await svc.obtener_nc(db, ctx, nc_id))


@router.patch("/no-conformidades/{nc_id}", response_model=NoConformidadDetalle,
              summary="Cambiar estado, responsable o solución de una no conformidad")
async def gestionar_nc(nc_id: int, datos: NoConformidadGestionar, ctx: Contexto = Depends(requiere("calidad.gestionar")),
                       db: AsyncSession = Depends(get_db)):
    return await svc.detalle_nc(db, ctx, await svc.gestionar_nc(db, ctx, nc_id, datos))


@router.post("/no-conformidades/{nc_id}/observaciones", response_model=NoConformidadDetalle,
             status_code=status.HTTP_201_CREATED, summary="Agregar una observación al historial")
async def observar_nc(nc_id: int, datos: ObservacionCrear,
                      ctx: Contexto = Depends(requiere("calidad.reportar", "calidad.gestionar")), db: AsyncSession = Depends(get_db)):
    return await svc.detalle_nc(db, ctx, await svc.observar_nc(db, ctx, nc_id, datos))


# --------------------------------------------------------------- garantías
@router.get("/garantias", response_model=Pagina[GarantiaResumen], summary="Consultar garantías")
async def listar_garantias(
    pag: ParametrosPagina = Depends(),
    sede_id: int | None = Query(None, gt=0),
    estado: EstadoGarantiaT | None = Query(None),
    producto_id: int | None = Query(None, gt=0),
    proveedor: str | None = Query(None, max_length=100),
    desde: date | None = Query(None, description="Fecha de reporte desde"),
    hasta: date | None = Query(None, description="Fecha de reporte hasta"),
    q: str | None = Query(None, max_length=100, description="Producto, código, documento o número"),
    ctx: Contexto = Depends(requiere("calidad.ver")),
    db: AsyncSession = Depends(get_db),
):
    filas, total = await svc.listar_garantias(
        db, ctx, pag, sede_id=sede_id, estado=estado, producto_id=producto_id, proveedor=proveedor, desde=desde,
        hasta=hasta, q=q,
    )
    return Pagina.crear(filas, total, pag.pagina, pag.tamano)


@router.post("/garantias", response_model=GarantiaDetalle, status_code=status.HTTP_201_CREATED,
             summary="Registrar una garantía (no modifica existencias)")
async def crear_garantia(datos: GarantiaCrear, ctx: Contexto = Depends(requiere("calidad.reportar", "calidad.gestionar")),
                         db: AsyncSession = Depends(get_db)):
    return await svc.detalle_garantia(db, ctx, await svc.crear_garantia(db, ctx, datos))


@router.get("/garantias/{garantia_id}", response_model=GarantiaDetalle, summary="Detalle de una garantía")
async def obtener_garantia(garantia_id: int, ctx: Contexto = Depends(requiere("calidad.ver")), db: AsyncSession = Depends(get_db)):
    return await svc.detalle_garantia(db, ctx, await svc.obtener_garantia(db, ctx, garantia_id))


@router.patch("/garantias/{garantia_id}", response_model=GarantiaDetalle,
              summary="Cambiar estado, responsable o registrar la respuesta del proveedor y la solución")
async def gestionar_garantia(garantia_id: int, datos: GarantiaGestionar, ctx: Contexto = Depends(requiere("calidad.gestionar")),
                             db: AsyncSession = Depends(get_db)):
    return await svc.detalle_garantia(db, ctx, await svc.gestionar_garantia(db, ctx, garantia_id, datos))


@router.post("/garantias/{garantia_id}/observaciones", response_model=GarantiaDetalle,
             status_code=status.HTTP_201_CREATED, summary="Agregar una observación al historial")
async def observar_garantia(garantia_id: int, datos: ObservacionCrear,
                            ctx: Contexto = Depends(requiere("calidad.reportar", "calidad.gestionar")),
                            db: AsyncSession = Depends(get_db)):
    return await svc.detalle_garantia(db, ctx, await svc.observar_garantia(db, ctx, garantia_id, datos))
