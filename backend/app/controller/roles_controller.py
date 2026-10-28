from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.dto.comunes_dto import Mensaje
from app.dto.rol_dto import PermisoSalida, RolActualizar, RolCrear, RolPermisosEntrada, RolSalida
from app.security.acceso import Contexto
from app.security.dependencias import requiere
from app.service import rol_service

router = APIRouter(prefix="/api", tags=["Roles y permisos"])


@router.get("/permisos", response_model=list[PermisoSalida], summary="Catálogo de permisos")
async def catalogo(ctx: Contexto = Depends(requiere("roles.ver")), db: AsyncSession = Depends(get_db)):
    return await rol_service.listar_permisos(db)


@router.get("/roles", response_model=list[RolSalida], summary="Consultar roles y sus permisos")
async def listar(ctx: Contexto = Depends(requiere("roles.ver", "usuarios.ver")), db: AsyncSession = Depends(get_db)):
    return await rol_service.salidas(db, await rol_service.listar(db, ctx))


@router.post("/roles", response_model=RolSalida, status_code=status.HTTP_201_CREATED, summary="Crear un rol")
async def crear(datos: RolCrear, ctx: Contexto = Depends(requiere("roles.crear")), db: AsyncSession = Depends(get_db)):
    rol = await rol_service.crear(db, ctx, datos)
    return (await rol_service.salidas(db, [rol]))[0]


@router.get("/roles/{rol_id}", response_model=RolSalida, summary="Consultar un rol")
async def obtener(rol_id: int, ctx: Contexto = Depends(requiere("roles.ver")), db: AsyncSession = Depends(get_db)):
    rol = await rol_service.obtener(db, ctx, rol_id)
    return (await rol_service.salidas(db, [rol]))[0]


@router.put("/roles/{rol_id}", response_model=RolSalida, summary="Modificar un rol")
async def actualizar(
    rol_id: int, datos: RolActualizar, ctx: Contexto = Depends(requiere("roles.editar")),
    db: AsyncSession = Depends(get_db),
):
    rol = await rol_service.actualizar(db, ctx, rol_id, datos)
    return (await rol_service.salidas(db, [rol]))[0]


@router.put("/roles/{rol_id}/permisos", response_model=RolSalida, summary="Asignar permisos a un rol")
async def asignar_permisos(
    rol_id: int, datos: RolPermisosEntrada, ctx: Contexto = Depends(requiere("roles.asignar_permisos")),
    db: AsyncSession = Depends(get_db),
):
    rol = await rol_service.asignar_permisos(db, ctx, rol_id, datos.permisos)
    return (await rol_service.salidas(db, [rol]))[0]


@router.delete("/roles/{rol_id}", response_model=Mensaje, summary="Eliminar un rol personalizado sin usuarios")
async def eliminar(rol_id: int, ctx: Contexto = Depends(requiere("roles.editar")), db: AsyncSession = Depends(get_db)):
    await rol_service.eliminar(db, ctx, rol_id)
    return Mensaje(mensaje="Rol eliminado")
