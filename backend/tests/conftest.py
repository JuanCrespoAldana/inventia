"""Fixtures compartidas.

Por defecto las pruebas usan SQLite en un archivo temporal (no requiere nada instalado). Las pruebas marcadas
con ``@pytest.mark.postgres`` (concurrencia real, índices parciales, triggers y migraciones) se ejecutan solo
cuando se define ``TEST_DATABASE_URL`` apuntando a una base PostgreSQL **vacía y descartable**, p. ej.::

    TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/inventia_test pytest
"""

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="inventia-test-"))
URL_PRUEBA = os.environ.get("TEST_DATABASE_URL") or f"sqlite+aiosqlite:///{(_TMP / 'prueba.db').as_posix()}"
HAY_POSTGRES = URL_PRUEBA.startswith("postgresql")

# Debe fijarse ANTES de importar la aplicación: Settings se lee al importar.
os.environ.update(
    DATABASE_URL=URL_PRUEBA,
    DATABASE_SSL="false",
    SECRET_KEY="clave-de-pruebas-que-no-sirve-para-nada-0123456789",
    ENVIRONMENT="test",
    SETUP_TOKEN="",
    SMTP_USER="",
    SMTP_PASSWORD="",
    EMAIL_FROM="",
    LOG_LEVEL="WARNING",
)

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import event, text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402

import app.config.database as bd  # noqa: E402
import app.model  # noqa: E402,F401  (registra todas las tablas)
from app.main import app  # noqa: E402
from app.model.base import Base  # noqa: E402
from app.security.limiter import limiter  # noqa: E402


def pytest_collection_modifyitems(config, items):
    if HAY_POSTGRES:
        return
    omitir = pytest.mark.skip(reason="requiere PostgreSQL: defina TEST_DATABASE_URL")
    for item in items:
        if "postgres" in item.keywords:
            item.add_marker(omitir)


@pytest_asyncio.fixture(scope="session")
async def motor():
    motor = bd.crear_engine(URL_PRUEBA)
    if motor.dialect.name == "sqlite":

        @event.listens_for(motor.sync_engine, "connect")
        def _fk(conexion, _):  # SQLite no valida claves foráneas salvo que se pida
            cursor = conexion.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    async with motor.begin() as conexion:
        if motor.dialect.name == "postgresql":
            await conexion.execute(text("DROP SCHEMA public CASCADE"))
            await conexion.execute(text("CREATE SCHEMA public"))
        await conexion.run_sync(Base.metadata.create_all)
    yield motor
    await motor.dispose()


@pytest_asyncio.fixture(scope="session")
async def fabrica(motor):
    return async_sessionmaker(motor, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def base_limpia(motor, fabrica, monkeypatch):
    """Cada prueba parte de una base vacía y usa el motor de pruebas en toda la aplicación."""
    monkeypatch.setattr(bd, "AsyncSessionLocal", fabrica)
    limiter.reset()
    yield
    async with motor.begin() as conexion:
        if motor.dialect.name == "postgresql":
            tablas = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
            await conexion.execute(text(f"TRUNCATE {tablas} RESTART IDENTITY CASCADE"))
        else:
            for tabla in reversed(Base.metadata.sorted_tables):
                await conexion.execute(tabla.delete())


@pytest_asyncio.fixture
async def db(fabrica):
    async with fabrica() as sesion:
        yield sesion


@pytest_asyncio.fixture
async def cliente():
    transporte = ASGITransport(app=app, client=("203.0.113.9", 4000))
    async with AsyncClient(transport=transporte, base_url="http://prueba") as c:
        yield c
