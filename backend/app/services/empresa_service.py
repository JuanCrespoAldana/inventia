"""Datos y parámetros de la empresa (RF-007, RU-004)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.acceso import Contexto
from app.core.exceptions import Conflicto, NoEncontrado
from app.models.empresa import CONFIGURACION_POR_DEFECTO, Empresa
from app.schemas.empresa import EmpresaActualizar, EmpresaSalida, ParametrosEmpresa
from app.services import auditoria_service


def a_salida(empresa: Empresa) -> EmpresaSalida:
    return EmpresaSalida(
        id=empresa.id, nombre=empresa.nombre, identificacion=empresa.identificacion, direccion=empresa.direccion,
        ciudad=empresa.ciudad, telefono=empresa.telefono, email=empresa.email, activa=empresa.activa,
        parametros=empresa.parametros(), created_at=empresa.created_at, updated_at=empresa.updated_at,
    )


async def obtener(db: AsyncSession, ctx: Contexto) -> Empresa:
    empresa = await db.get(Empresa, ctx.empresa_id)
    if empresa is None:
        raise NoEncontrado("La empresa no existe")
    return empresa


async def actualizar(db: AsyncSession, ctx: Contexto, datos: EmpresaActualizar) -> Empresa:
    empresa = await obtener(db, ctx)
    cambios = datos.model_dump(exclude_unset=True)
    if "identificacion" in cambios and cambios["identificacion"] is not None:
        duplicada = await db.scalar(
            select(Empresa.id).where(Empresa.identificacion == cambios["identificacion"], Empresa.id != empresa.id)
        )
        if duplicada:
            raise Conflicto("Ya existe una empresa con esa identificación", codigo="identificacion_duplicada")
    anterior = {k: getattr(empresa, k) for k in cambios}
    for campo, valor in cambios.items():
        if campo in ("nombre", "identificacion") and valor is None:
            continue  # obligatorios: no se pueden vaciar
        setattr(empresa, campo, valor)
    await auditoria_service.registrar(
        db, modulo="empresa", accion="actualizar", ctx=ctx, entidad="empresa", entidad_id=empresa.id,
        detalle={"antes": anterior, "despues": cambios},
    )
    await db.commit()
    await db.refresh(empresa)
    return empresa


async def actualizar_parametros(db: AsyncSession, ctx: Contexto, datos: ParametrosEmpresa) -> Empresa:
    empresa = await obtener(db, ctx)
    anterior = empresa.parametros()
    nuevos = {**anterior, **datos.model_dump(exclude_none=True)}
    assert set(nuevos) == set(CONFIGURACION_POR_DEFECTO)
    empresa.configuracion = nuevos
    await auditoria_service.registrar(
        db, modulo="empresa", accion="actualizar_parametros", ctx=ctx, entidad="empresa", entidad_id=empresa.id,
        detalle={"antes": anterior, "despues": nuevos},
    )
    await db.commit()
    await db.refresh(empresa)
    return empresa
