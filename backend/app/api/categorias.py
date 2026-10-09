from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import requiere
from app.core.acceso import Contexto
from app.core.database import get_db
from app.schemas.catalogo import CategoriaActualizar, CategoriaCrear, CategoriaEstado, CategoriaSalida
from app.schemas.comunes import Pagina, ParametrosPagina
from app.services import catalogo_service as svc

router = APIRouter(prefix="/api/categorias", tags=["Categorías"])


async def _una(db: AsyncSession, categoria) -> CategoriaSalida:
    return (await svc.salidas_categorias(db, [categoria]))[0]


@router.get("", response_model=Pagina[CategoriaSalida], summary="Listar y buscar categorías")
async def listar(
    pag: ParametrosPagina = Depends(),
    q: str | None = Query(None, max_length=100),
    activa: bool | None = Query(None),
    ctx: Contexto = Depends(requiere("categorias.ver")),
    db: AsyncSession = Depends(get_db),
):
    filas, total = await svc.listar_categorias(db, ctx, pag, q=q, activa=activa)
    return Pagina.crear(await svc.salidas_categorias(db, filas), total, pag.pagina, pag.tamano)


@router.post("", response_model=CategoriaSalida, status_code=status.HTTP_201_CREATED, summary="Crear una categoría")
async def crear(datos: CategoriaCrear, ctx: Contexto = Depends(requiere("categorias.crear")), db: AsyncSession = Depends(get_db)):
    return await _una(db, await svc.crear_categoria(db, ctx, datos))


@router.get("/{categoria_id}", response_model=CategoriaSalida, summary="Consultar una categoría")
async def obtener(categoria_id: int, ctx: Contexto = Depends(requiere("categorias.ver")), db: AsyncSession = Depends(get_db)):
    return await _una(db, await svc.obtener_categoria(db, ctx, categoria_id))


@router.put("/{categoria_id}", response_model=CategoriaSalida, summary="Modificar una categoría")
async def actualizar(
    categoria_id: int, datos: CategoriaActualizar,
    ctx: Contexto = Depends(requiere("categorias.editar")), db: AsyncSession = Depends(get_db),
):
    return await _una(db, await svc.actualizar_categoria(db, ctx, categoria_id, datos))


@router.patch("/{categoria_id}/estado", response_model=CategoriaSalida, summary="Inhabilitar o reactivar una categoría")
async def estado(
    categoria_id: int, datos: CategoriaEstado,
    ctx: Contexto = Depends(requiere("categorias.editar")), db: AsyncSession = Depends(get_db),
):
    return await _una(db, await svc.cambiar_estado_categoria(db, ctx, categoria_id, datos.activa))
