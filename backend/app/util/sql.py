"""Pequeñas utilidades que dependen del dialecto (PostgreSQL en producción, SQLite en pruebas)."""

from sqlalchemy import select, text
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.inventario import Secuencia


def es_postgres(db: AsyncSession) -> bool:
    return db.bind.dialect.name == "postgresql"  # type: ignore[union-attr]


def insertar(db: AsyncSession, modelo):
    """``INSERT`` con soporte de ``ON CONFLICT`` en ambos dialectos."""
    return (postgresql.insert if es_postgres(db) else sqlite.insert)(modelo)


async def bloqueo_asesor(db: AsyncSession, clave: int) -> None:
    """Serializa una sección crítica entre transacciones concurrentes (solo PostgreSQL)."""
    if es_postgres(db):
        await db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": clave})


async def siguiente_secuencia(db: AsyncSession, empresa_id: int, nombre: str) -> int:
    """Siguiente consecutivo de la empresa. Atómico: dos ventas simultáneas nunca obtienen el mismo número."""
    stmt = insertar(db, Secuencia).values(empresa_id=empresa_id, nombre=nombre, valor=1)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Secuencia.empresa_id, Secuencia.nombre], set_={"valor": Secuencia.valor + 1}
    ).returning(Secuencia.valor)
    return int(await db.scalar(stmt))


async def contar(db: AsyncSession, consulta) -> int:
    from sqlalchemy import func

    return int(await db.scalar(select(func.count()).select_from(consulta.subquery())) or 0)
