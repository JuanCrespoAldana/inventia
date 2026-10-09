"""Verificación de que una sede (o cualquier recurso) pertenece a la empresa del usuario y de
que el usuario puede operar sobre ella."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.acceso import Contexto
from app.core.exceptions import NoEncontrado, ReglaNegocio, SinPermiso
from app.models.sede import Sede


async def obtener_sede_autorizada(
    db: AsyncSession, ctx: Contexto, sede_id: int, *, requerir_activa: bool = False
) -> Sede:
    """Devuelve la sede si es de la empresa del usuario y está dentro de su alcance.

    - Sede de otra empresa o inexistente -> 404 (no se revela que existe).
    - Sede de la empresa pero fuera del alcance del usuario -> 403.
    """
    sede = await db.scalar(select(Sede).where(Sede.id == sede_id, Sede.empresa_id == ctx.empresa_id))
    if sede is None:
        raise NoEncontrado("La sede no existe")
    if ctx.limitado_a_sede and sede.id != ctx.sede_id:
        raise SinPermiso("No tienes acceso a esta sede")
    if requerir_activa and not sede.activa:
        raise ReglaNegocio(f"La sede «{sede.nombre}» está inhabilitada", codigo="sede_inactiva")
    return sede


async def obtener_sede_de_empresa(
    db: AsyncSession, empresa_id: int, sede_id: int, *, requerir_activa: bool = False
) -> Sede:
    """Igual que la anterior pero sin restricción de alcance del usuario (p. ej. sede de destino)."""
    sede = await db.scalar(select(Sede).where(Sede.id == sede_id, Sede.empresa_id == empresa_id))
    if sede is None:
        raise NoEncontrado("La sede no existe")
    if requerir_activa and not sede.activa:
        raise ReglaNegocio(f"La sede «{sede.nombre}» está inhabilitada", codigo="sede_inactiva")
    return sede


def resolver_filtro_sede(ctx: Contexto, sede_id: int | None) -> list[int] | None:
    """Traduce el parámetro opcional ``sede_id`` de una consulta al conjunto de sedes que el
    usuario puede ver. ``None`` = sin restricción de sede (toda la empresa)."""
    autorizadas = ctx.sedes_autorizadas()
    if autorizadas is None:
        return [sede_id] if sede_id is not None else None
    if sede_id is not None and sede_id not in autorizadas:
        raise SinPermiso("No tienes acceso a esta sede")
    return autorizadas
