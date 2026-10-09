"""Motor de base de datos asíncrono y sesión por petición."""

from collections.abc import AsyncIterator
from ipaddress import ip_address

from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.base import Base  # noqa: F401  (se reexporta: ``from app.core.database import Base``)


def _requiere_ssl(url_texto: str) -> bool:
    """asyncpg no entiende ``sslmode`` en la URL; el SSL se activa con connect_args.

    Modo ``auto``: se exige SSL para servidores remotos (p. ej. Neon) y se
    desactiva para localhost / IPs privadas / nombres de servicio de Docker.
    """
    if settings.database_ssl != "auto":
        return settings.database_ssl == "true"
    host = make_url(url_texto).host or ""
    if host in {"localhost", ""} or "." not in host:
        return False
    try:
        ip = ip_address(host)
        return not (ip.is_loopback or ip.is_private)
    except ValueError:
        return True


def crear_engine(url: str | None = None, **extra) -> AsyncEngine:
    """Crea el motor. ``extra`` permite, p. ej., ``poolclass=NullPool`` en las migraciones."""
    url = url or settings.database_url
    parsed = make_url(url)
    kwargs: dict = {"echo": False}
    if parsed.drivername.startswith("postgresql+asyncpg"):
        if _requiere_ssl(url):
            kwargs["connect_args"] = {"ssl": "require"}
        if "poolclass" not in extra:
            kwargs.update(
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow,
                pool_pre_ping=True,  # Neon cierra conexiones inactivas
                pool_recycle=1800,
            )
    kwargs.update(extra)
    return create_async_engine(url, **kwargs)


engine: AsyncEngine = crear_engine()
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


def fabrica_de_sesiones() -> async_sessionmaker[AsyncSession]:
    """Punto único para obtener sesiones fuera de una petición (tareas en segundo plano, CLI).

    Se resuelve en cada llamada para que las pruebas puedan sustituir ``AsyncSessionLocal``.
    """
    return AsyncSessionLocal


async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session
