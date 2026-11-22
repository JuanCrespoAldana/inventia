"""Motor de base de datos asíncrono y sesión por petición."""

import time
from collections.abc import AsyncIterator
from ipaddress import ip_address

from sqlalchemy import event, exc, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import settings
from app.model.base import Base  # noqa: F401  (se reexporta: ``from app.config.database import Base``)


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


# Una conexión que se usó hace menos de estos segundos se entrega sin comprobarla; una que estuvo
# inactiva más tiempo se comprueba antes (Neon cierra las conexiones inactivas). Con ``pool_pre_ping``
# se comprobaba en CADA petición, lo que añade un viaje completo a la base remota por petición.
SEGUNDOS_INACTIVA_PARA_COMPROBAR = 20


def _comprobar_conexiones_inactivas(motor: AsyncEngine) -> None:
    sync_engine = motor.sync_engine

    @event.listens_for(sync_engine, "checkin")
    def _al_devolver(dbapi_connection, registro) -> None:
        registro.info["ultimo_uso"] = time.monotonic()

    @event.listens_for(sync_engine, "checkout")
    def _al_entregar(dbapi_connection, registro, _proxy) -> None:
        ultimo_uso = registro.info.get("ultimo_uso")
        if ultimo_uso is not None and time.monotonic() - ultimo_uso < SEGUNDOS_INACTIVA_PARA_COMPROBAR:
            return
        try:
            sync_engine.dialect.do_ping(dbapi_connection)
        except Exception as error:  # noqa: BLE001 - cualquier fallo significa conexión inservible
            raise exc.DisconnectionError("Conexión inactiva descartada") from error


def crear_engine(url: str | None = None, **extra) -> AsyncEngine:
    """Crea el motor. ``extra`` permite, p. ej., ``poolclass=NullPool`` en las migraciones."""
    url = url or settings.database_url
    parsed = make_url(url)
    kwargs: dict = {"echo": False}
    con_pool = False
    if parsed.drivername.startswith("postgresql+asyncpg"):
        if _requiere_ssl(url):
            kwargs["connect_args"] = {"ssl": "require"}
        if "poolclass" not in extra:
            con_pool = True
            kwargs.update(pool_size=settings.db_pool_size, max_overflow=settings.db_max_overflow, pool_recycle=1800)
    kwargs.update(extra)
    motor = create_async_engine(url, **kwargs)
    if con_pool:
        _comprobar_conexiones_inactivas(motor)
    return motor


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
