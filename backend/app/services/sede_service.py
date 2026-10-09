"""Gestión de sedes (RF-008, RF-009, RF-010). Toda consulta se filtra por la empresa del usuario."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.acceso import Contexto
from app.core.exceptions import Conflicto, NoEncontrado
from app.models.inventario import InventarioSede
from app.models.operaciones import Traslado
from app.models.sede import Sede
from app.models.usuario import Usuario
from app.schemas.comunes import ParametrosPagina
from app.schemas.sede import SedeActualizar, SedeCrear, SedeResumen
from app.services import auditoria_service
from app.services.alcance import obtener_sede_autorizada


async def _validar_nombre_unico(db: AsyncSession, empresa_id: int, nombre: str, excluir_id: int | None = None) -> None:
    consulta = select(Sede.id).where(Sede.empresa_id == empresa_id, func.lower(Sede.nombre) == nombre.lower())
    if excluir_id is not None:
        consulta = consulta.where(Sede.id != excluir_id)
    if await db.scalar(consulta):
        raise Conflicto(f"Ya existe una sede llamada «{nombre}» en tu empresa", codigo="sede_duplicada")


async def crear(db: AsyncSession, ctx: Contexto, datos: SedeCrear) -> Sede:
    await _validar_nombre_unico(db, ctx.empresa_id, datos.nombre)
    sede = Sede(empresa_id=ctx.empresa_id, nombre=datos.nombre, direccion=datos.direccion, ciudad=datos.ciudad)
    db.add(sede)
    try:
        await db.flush()
    except IntegrityError as exc:  # carrera entre dos altas simultáneas con el mismo nombre
        await db.rollback()
        raise Conflicto(f"Ya existe una sede llamada «{datos.nombre}» en tu empresa", codigo="sede_duplicada") from exc
    await auditoria_service.registrar(
        db, modulo="sedes", accion="crear", ctx=ctx, entidad="sede", entidad_id=sede.id, sede_id=sede.id,
        detalle={"nombre": sede.nombre, "ciudad": sede.ciudad},
    )
    await db.commit()
    await db.refresh(sede)
    return sede


async def listar(
    db: AsyncSession,
    ctx: Contexto,
    pag: ParametrosPagina,
    *,
    q: str | None = None,
    ciudad: str | None = None,
    activa: bool | None = None,
) -> tuple[list[Sede], int]:
    condiciones = [Sede.empresa_id == ctx.empresa_id]
    autorizadas = ctx.sedes_autorizadas()
    if autorizadas is not None:
        condiciones.append(Sede.id.in_(autorizadas))
    if q:
        patron = f"%{q.strip().lower()}%"
        condiciones.append(
            func.lower(Sede.nombre).like(patron)
            | func.lower(func.coalesce(Sede.ciudad, "")).like(patron)
            | func.lower(func.coalesce(Sede.direccion, "")).like(patron)
        )
    if ciudad:
        condiciones.append(func.lower(Sede.ciudad) == ciudad.strip().lower())
    if activa is not None:
        condiciones.append(Sede.activa.is_(activa))
    total = await db.scalar(select(func.count()).select_from(Sede).where(*condiciones)) or 0
    filas = (
        await db.scalars(
            select(Sede).where(*condiciones).order_by(Sede.activa.desc(), func.lower(Sede.nombre))
            .offset(pag.offset).limit(pag.tamano)
        )
    ).all()
    return list(filas), total


async def obtener(db: AsyncSession, ctx: Contexto, sede_id: int) -> Sede:
    return await obtener_sede_autorizada(db, ctx, sede_id)


async def actualizar(db: AsyncSession, ctx: Contexto, sede_id: int, datos: SedeActualizar) -> Sede:
    sede = await obtener_sede_autorizada(db, ctx, sede_id)
    cambios = datos.model_dump(exclude_unset=True)
    if cambios.get("nombre") and cambios["nombre"].lower() != sede.nombre.lower():
        await _validar_nombre_unico(db, ctx.empresa_id, cambios["nombre"], sede.id)
    anterior = {k: getattr(sede, k) for k in cambios}
    for campo, valor in cambios.items():
        if campo in ("nombre", "ciudad") and valor is None:
            continue
        setattr(sede, campo, valor)
    await auditoria_service.registrar(
        db, modulo="sedes", accion="actualizar", ctx=ctx, entidad="sede", entidad_id=sede.id, sede_id=sede.id,
        detalle={"antes": anterior, "despues": cambios},
    )
    await db.commit()
    await db.refresh(sede)
    return sede


async def cambiar_estado(db: AsyncSession, ctx: Contexto, sede_id: int, activa: bool) -> Sede:
    sede = await obtener_sede_autorizada(db, ctx, sede_id)
    if sede.activa == activa:
        return sede
    if not activa:
        pendientes = await db.scalar(
            select(func.count()).select_from(Traslado).where(
                Traslado.empresa_id == ctx.empresa_id,
                Traslado.estado.in_(["solicitado", "aprobado"]),
                (Traslado.sede_origen_id == sede.id) | (Traslado.sede_destino_id == sede.id),
            )
        )
        if pendientes:
            raise Conflicto(
                f"No se puede inhabilitar la sede: tiene {pendientes} traslado(s) pendiente(s). "
                "Confírmalos, recházalos o cancélalos primero.",
                codigo="sede_con_traslados_pendientes",
            )
    sede.activa = activa
    await auditoria_service.registrar(
        db, modulo="sedes", accion="reactivar" if activa else "inhabilitar", ctx=ctx, entidad="sede",
        entidad_id=sede.id, sede_id=sede.id, detalle={"nombre": sede.nombre},
    )
    await db.commit()
    await db.refresh(sede)
    return sede


async def estadisticas(db: AsyncSession, empresa_id: int, sede_ids: list[int]) -> dict[int, dict[str, int]]:
    """Usuarios y unidades en existencia por sede, para mostrar en el listado."""
    if not sede_ids:
        return {}
    usuarios = dict(
        (
            await db.execute(
                select(Usuario.sede_id, func.count()).where(
                    Usuario.empresa_id == empresa_id, Usuario.sede_id.in_(sede_ids), Usuario.activo.is_(True)
                ).group_by(Usuario.sede_id)
            )
        ).all()
    )
    existencias = dict(
        (
            await db.execute(
                select(InventarioSede.sede_id, func.coalesce(func.sum(InventarioSede.cantidad), 0)).where(
                    InventarioSede.empresa_id == empresa_id, InventarioSede.sede_id.in_(sede_ids)
                ).group_by(InventarioSede.sede_id)
            )
        ).all()
    )
    return {s: {"usuarios": int(usuarios.get(s, 0)), "unidades": int(existencias.get(s, 0))} for s in sede_ids}


__all__ = ["crear", "listar", "obtener", "actualizar", "cambiar_estado", "estadisticas", "NoEncontrado"]


async def directorio(db: AsyncSession, ctx: Contexto) -> list[SedeResumen]:
    """Todas las sedes activas de la empresa con datos mínimos (sin estadísticas ni direcciones)."""
    filas = await db.scalars(select(Sede).where(Sede.empresa_id == ctx.empresa_id, Sede.activa.is_(True)).order_by(Sede.nombre))
    return [SedeResumen.model_validate(s) for s in filas]
