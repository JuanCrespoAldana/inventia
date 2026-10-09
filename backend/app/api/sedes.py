from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import requiere
from app.core.acceso import Contexto
from app.core.database import get_db
from app.schemas.comunes import Pagina, ParametrosPagina
from app.schemas.sede import SedeActualizar, SedeCrear, SedeDetalle, SedeEstado, SedeResumen
from app.services import sede_service

router = APIRouter(prefix="/api/sedes", tags=["Sedes"])


async def _con_estadisticas(db: AsyncSession, ctx: Contexto, sedes) -> list[SedeDetalle]:
    stats = await sede_service.estadisticas(db, ctx.empresa_id, [s.id for s in sedes])
    return [
        SedeDetalle.model_validate(s).model_copy(
            update={
                "total_usuarios": stats[s.id]["usuarios"],
                "unidades_en_existencia": stats[s.id]["unidades"],
            }
        )
        for s in sedes
    ]


@router.get("", response_model=Pagina[SedeDetalle], summary="Listar y buscar sedes")
async def listar(
    pag: ParametrosPagina = Depends(),
    q: str | None = Query(None, max_length=100, description="Busca en nombre, ciudad y dirección"),
    ciudad: str | None = Query(None, max_length=100),
    activa: bool | None = Query(None, description="true = activas, false = inhabilitadas"),
    ctx: Contexto = Depends(requiere("sedes.ver")),
    db: AsyncSession = Depends(get_db),
):
    sedes, total = await sede_service.listar(db, ctx, pag, q=q, ciudad=ciudad, activa=activa)
    return Pagina.crear(await _con_estadisticas(db, ctx, sedes), total, pag.pagina, pag.tamano)


@router.get(
    "/directorio",
    response_model=list[SedeResumen],
    summary="Sedes activas de la empresa (nombre y ciudad), para elegir la contraparte de un traslado",
)
async def directorio(ctx: Contexto = Depends(requiere("traslados.solicitar", "traslados.ver", "sedes.ver")), db: AsyncSession = Depends(get_db)):
    """Un usuario limitado a su sede no puede listar las demás sedes, pero para solicitar un traslado necesita
    conocer su nombre. Solo se exponen datos mínimos: id, nombre y ciudad."""
    return await sede_service.directorio(db, ctx)


@router.post("", response_model=SedeDetalle, status_code=status.HTTP_201_CREATED, summary="Registrar una sede")
async def crear(datos: SedeCrear, ctx: Contexto = Depends(requiere("sedes.crear")), db: AsyncSession = Depends(get_db)):
    sede = await sede_service.crear(db, ctx, datos)
    return (await _con_estadisticas(db, ctx, [sede]))[0]


@router.get("/{sede_id}", response_model=SedeDetalle, summary="Consultar una sede")
async def obtener(sede_id: int, ctx: Contexto = Depends(requiere("sedes.ver")), db: AsyncSession = Depends(get_db)):
    return (await _con_estadisticas(db, ctx, [await sede_service.obtener(db, ctx, sede_id)]))[0]


@router.put("/{sede_id}", response_model=SedeDetalle, summary="Modificar una sede")
async def actualizar(
    sede_id: int, datos: SedeActualizar, ctx: Contexto = Depends(requiere("sedes.editar")),
    db: AsyncSession = Depends(get_db),
):
    sede = await sede_service.actualizar(db, ctx, sede_id, datos)
    return (await _con_estadisticas(db, ctx, [sede]))[0]


@router.patch("/{sede_id}/estado", response_model=SedeDetalle, summary="Inhabilitar o reactivar una sede")
async def cambiar_estado(
    sede_id: int, datos: SedeEstado, ctx: Contexto = Depends(requiere("sedes.inhabilitar")),
    db: AsyncSession = Depends(get_db),
):
    sede = await sede_service.cambiar_estado(db, ctx, sede_id, datos.activa)
    return (await _con_estadisticas(db, ctx, [sede]))[0]
