from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.dto.comunes_dto import Pagina, ParametrosPagina
from app.dto.sst_dto import (
    ActividadActualizar,
    ActividadCrear,
    ActividadSalida,
    ConfiguracionSst,
    ConfiguracionSstActualizar,
    EstadoPausaT,
    PausaCerrar,
    PausaEstado,
    PausaIniciada,
    PausaRegistro,
    ResumenSst,
)
from app.security.acceso import Contexto
from app.security.dependencias import contexto_actual, requiere
from app.service import sst_service as svc

router = APIRouter(prefix="/api/sig/sst", tags=["SIG · SST"])


# ------------------------------------------------------------ pausas automáticas (cualquier persona autenticada)
@router.get("/pausa/estado", response_model=PausaEstado, summary="Estado de las pausas activas de la persona")
async def estado(ctx: Contexto = Depends(contexto_actual), db: AsyncSession = Depends(get_db)):
    return await svc.estado_pausas(db, ctx)


@router.post("/pausa/iniciar", response_model=PausaIniciada, summary="Solicitar la pausa activa que corresponde mostrar")
async def iniciar(ctx: Contexto = Depends(contexto_actual), db: AsyncSession = Depends(get_db)):
    return await svc.iniciar_pausa(db, ctx)


@router.post("/pausa/{pausa_id}/cerrar", response_model=PausaRegistro, summary="Marcar la pausa como realizada u omitida")
async def cerrar(pausa_id: int, datos: PausaCerrar, ctx: Contexto = Depends(contexto_actual), db: AsyncSession = Depends(get_db)):
    return await svc.cerrar_pausa(db, ctx, pausa_id, datos)


@router.get("/pausas", response_model=Pagina[PausaRegistro], summary="Registro de pausas (las propias o, con permiso, todas)")
async def pausas(
    pag: ParametrosPagina = Depends(),
    ambito: str = Query("mias", pattern="^(mias|todas)$"),
    usuario_id: int | None = Query(None, gt=0),
    estado: EstadoPausaT | None = Query(None),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    ctx: Contexto = Depends(requiere("sst.ver", "sst.gestionar")),
    db: AsyncSession = Depends(get_db),
):
    filas, total = await svc.listar_pausas(
        db, ctx, pag, ambito=ambito, usuario_id=usuario_id, estado=estado, desde=desde, hasta=hasta
    )
    return Pagina.crear(filas, total, pag.pagina, pag.tamano)


@router.get("/resumen", response_model=ResumenSst, summary="Cumplimiento de las pausas activas")
async def resumen(
    dias: int = Query(30, ge=1, le=365), ctx: Contexto = Depends(requiere("sst.gestionar")), db: AsyncSession = Depends(get_db)
):
    return await svc.resumen(db, ctx, dias)


# ------------------------------------------------------------ contenido y configuración
@router.get("/actividades", response_model=list[ActividadSalida], summary="Ejercicios y recomendaciones de pausas activas")
async def actividades(
    todas: bool = Query(False, description="Incluye las inactivas (solo administración)"),
    ctx: Contexto = Depends(requiere("sst.ver", "sst.gestionar")),
    db: AsyncSession = Depends(get_db),
):
    return await svc.listar_actividades(db, ctx, incluir_inactivas=todas)


@router.post("/actividades", response_model=ActividadSalida, status_code=status.HTTP_201_CREATED, summary="Crear una actividad")
async def crear_actividad(datos: ActividadCrear, ctx: Contexto = Depends(requiere("sst.gestionar")), db: AsyncSession = Depends(get_db)):
    return await svc.crear_actividad(db, ctx, datos)


@router.patch("/actividades/{actividad_id}", response_model=ActividadSalida, summary="Editar una actividad")
async def actualizar_actividad(
    actividad_id: int, datos: ActividadActualizar, ctx: Contexto = Depends(requiere("sst.gestionar")), db: AsyncSession = Depends(get_db)
):
    return await svc.actualizar_actividad(db, ctx, actividad_id, datos)


@router.delete("/actividades/{actividad_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar una actividad")
async def eliminar_actividad(actividad_id: int, ctx: Contexto = Depends(requiere("sst.gestionar")), db: AsyncSession = Depends(get_db)):
    await svc.eliminar_actividad(db, ctx, actividad_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/configuracion", response_model=ConfiguracionSst, summary="Frecuencia de las pausas activas")
async def configuracion(ctx: Contexto = Depends(requiere("sst.ver", "sst.gestionar")), db: AsyncSession = Depends(get_db)):
    return await svc.obtener_configuracion(db, ctx)


@router.put("/configuracion", response_model=ConfiguracionSst, summary="Cambiar la frecuencia o activar/desactivar las pausas")
async def actualizar_configuracion(
    datos: ConfiguracionSstActualizar, ctx: Contexto = Depends(requiere("sst.gestionar")), db: AsyncSession = Depends(get_db)
):
    return await svc.actualizar_configuracion(db, ctx, datos)
