from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import requiere
from app.core.acceso import Contexto
from app.core.database import get_db
from app.schemas.comunes import Pagina, ParametrosPagina
from app.schemas.usuario import (
    UsuarioActualizar,
    UsuarioCrear,
    UsuarioEstado,
    UsuarioRestablecerPassword,
    UsuarioSalida,
)
from app.services import usuario_service

router = APIRouter(prefix="/api/usuarios", tags=["Usuarios"])


@router.get("", response_model=Pagina[UsuarioSalida], summary="Consultar usuarios")
async def listar(
    pag: ParametrosPagina = Depends(),
    q: str | None = Query(None, max_length=100, description="Busca en nombre y correo"),
    rol_id: int | None = Query(None, gt=0),
    sede_id: int | None = Query(None, gt=0),
    activo: bool | None = Query(None),
    ctx: Contexto = Depends(requiere("usuarios.ver")),
    db: AsyncSession = Depends(get_db),
):
    usuarios, total = await usuario_service.listar(db, ctx, pag, q=q, rol_id=rol_id, sede_id=sede_id, activo=activo)
    return Pagina.crear(await usuario_service.salidas(db, usuarios), total, pag.pagina, pag.tamano)


@router.post("", response_model=UsuarioSalida, status_code=status.HTTP_201_CREATED, summary="Registrar un usuario")
async def crear(datos: UsuarioCrear, ctx: Contexto = Depends(requiere("usuarios.crear")), db: AsyncSession = Depends(get_db)):
    usuario = await usuario_service.crear(db, ctx, datos)
    return (await usuario_service.salidas(db, [usuario]))[0]


@router.get("/{usuario_id}", response_model=UsuarioSalida, summary="Consultar un usuario")
async def obtener(usuario_id: int, ctx: Contexto = Depends(requiere("usuarios.ver")), db: AsyncSession = Depends(get_db)):
    usuario = await usuario_service.obtener(db, ctx, usuario_id)
    return (await usuario_service.salidas(db, [usuario]))[0]


@router.put("/{usuario_id}", response_model=UsuarioSalida, summary="Modificar datos, rol o sede de un usuario")
async def actualizar(
    usuario_id: int, datos: UsuarioActualizar, ctx: Contexto = Depends(requiere("usuarios.editar")),
    db: AsyncSession = Depends(get_db),
):
    usuario = await usuario_service.actualizar(db, ctx, usuario_id, datos)
    return (await usuario_service.salidas(db, [usuario]))[0]


@router.patch("/{usuario_id}/estado", response_model=UsuarioSalida, summary="Activar o inhabilitar una cuenta")
async def cambiar_estado(
    usuario_id: int, datos: UsuarioEstado, ctx: Contexto = Depends(requiere("usuarios.inhabilitar")),
    db: AsyncSession = Depends(get_db),
):
    usuario = await usuario_service.cambiar_estado(db, ctx, usuario_id, datos.activo)
    return (await usuario_service.salidas(db, [usuario]))[0]


@router.post("/{usuario_id}/restablecer-password", response_model=UsuarioSalida,
             summary="Asignar una contraseña temporal")
async def restablecer_password(
    usuario_id: int, datos: UsuarioRestablecerPassword, ctx: Contexto = Depends(requiere("usuarios.editar")),
    db: AsyncSession = Depends(get_db),
):
    usuario = await usuario_service.restablecer_password(db, ctx, usuario_id, datos.nueva_password)
    return (await usuario_service.salidas(db, [usuario]))[0]


@router.post("/{usuario_id}/desbloquear", response_model=UsuarioSalida, summary="Quitar el bloqueo por intentos fallidos")
async def desbloquear(
    usuario_id: int, ctx: Contexto = Depends(requiere("usuarios.editar")), db: AsyncSession = Depends(get_db)
):
    usuario = await usuario_service.desbloquear(db, ctx, usuario_id)
    return (await usuario_service.salidas(db, [usuario]))[0]
