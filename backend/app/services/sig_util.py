"""Utilidades compartidas por los módulos del Sistema Integrado de Gestión."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usuario import Usuario


async def nombres_usuarios(db: AsyncSession, ids: set[int | None]) -> dict[int, str]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    return {i: n for i, n in (await db.execute(select(Usuario.id, Usuario.nombre).where(Usuario.id.in_(ids)))).all()}
