from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import requiere
from app.core.acceso import Contexto
from app.core.database import get_db
from app.schemas.catalogo import ProductoActualizar, ProductoCrear, ProductoEstado, ProductoSalida
from app.schemas.comunes import Pagina, ParametrosPagina
from app.services import catalogo_service as svc

router = APIRouter(prefix="/api/productos", tags=["Productos"])


async def _uno(db: AsyncSession, ctx: Contexto, producto) -> ProductoSalida:
    return (await svc.salidas_productos(db, ctx, [producto]))[0]


@router.get("", response_model=Pagina[ProductoSalida], summary="Listar y buscar productos")
async def listar(
    pag: ParametrosPagina = Depends(),
    q: str | None = Query(None, max_length=100, description="Busca en código y nombre"),
    categoria_id: int | None = Query(None, gt=0),
    activo: bool | None = Query(None),
    ctx: Contexto = Depends(requiere("productos.ver")),
    db: AsyncSession = Depends(get_db),
):
    filas, total = await svc.listar_productos(db, ctx, pag, q=q, categoria_id=categoria_id, activo=activo)
    return Pagina.crear(await svc.salidas_productos(db, ctx, filas), total, pag.pagina, pag.tamano)


@router.post("", response_model=ProductoSalida, status_code=status.HTTP_201_CREATED, summary="Registrar un producto")
async def crear(datos: ProductoCrear, ctx: Contexto = Depends(requiere("productos.crear")), db: AsyncSession = Depends(get_db)):
    return await _uno(db, ctx, await svc.crear_producto(db, ctx, datos))


@router.get("/{producto_id}", response_model=ProductoSalida, summary="Consultar un producto")
async def obtener(producto_id: int, ctx: Contexto = Depends(requiere("productos.ver")), db: AsyncSession = Depends(get_db)):
    return await _uno(db, ctx, await svc.obtener_producto(db, ctx, producto_id))


@router.put("/{producto_id}", response_model=ProductoSalida, summary="Modificar un producto (el código no cambia)")
async def actualizar(
    producto_id: int, datos: ProductoActualizar,
    ctx: Contexto = Depends(requiere("productos.editar")), db: AsyncSession = Depends(get_db),
):
    return await _uno(db, ctx, await svc.actualizar_producto(db, ctx, producto_id, datos))


@router.patch("/{producto_id}/estado", response_model=ProductoSalida, summary="Inhabilitar o reactivar un producto")
async def estado(
    producto_id: int, datos: ProductoEstado,
    ctx: Contexto = Depends(requiere("productos.inhabilitar")), db: AsyncSession = Depends(get_db),
):
    return await _uno(db, ctx, await svc.cambiar_estado_producto(db, ctx, producto_id, datos.activo))
