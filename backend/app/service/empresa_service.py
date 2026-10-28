"""Datos y parámetros de la empresa (RF-007, RU-004)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dto.empresa_dto import EmpresaActualizar, ParametrosEmpresa
from app.exception.excepciones import Conflicto, NoEncontrado
from app.model.empresa import CONFIGURACION_POR_DEFECTO, Empresa
from app.security.acceso import Contexto
from app.service import auditoria_service


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
    if set(nuevos) != set(CONFIGURACION_POR_DEFECTO):  # no es un assert: python -O los elimina
        raise RuntimeError("Los parámetros de la empresa no coinciden con la configuración por defecto")
    empresa.configuracion = nuevos
    await auditoria_service.registrar(
        db, modulo="empresa", accion="actualizar_parametros", ctx=ctx, entidad="empresa", entidad_id=empresa.id,
        detalle={"antes": anterior, "despues": nuevos},
    )
    await db.commit()
    await db.refresh(empresa)
    return empresa
