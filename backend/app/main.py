"""Punto de entrada de la API de Inventia."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from app.api import (
    agentes, alertas, auditoria, auth, categorias, dashboard, empresa, integraciones, inventario, predicciones, productos, recomendaciones,
    reportes, roles, sedes, setup, traslados, usuarios, ventas,
)
from app.core.config import settings
from app.core.contexto import ContextoPeticionMiddleware
from app.core.database import engine, fabrica_de_sesiones
from app.core.exceptions import registrar_manejadores_excepciones
from app.core.limiter import limiter
from app.core.logging import configurar_logging
from app.services.bootstrap import sincronizar_permisos
from app.services.prediccion_service import cerrar_ejecuciones_colgadas

configurar_logging()
logger = logging.getLogger("inventia")


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    # Mantiene el catálogo de permisos al día con el código (idempotente).
    try:
        async with fabrica_de_sesiones()() as db:
            await sincronizar_permisos(db)
            await db.commit()
            if await cerrar_ejecuciones_colgadas(db):
                await db.commit()
    except Exception:  # noqa: BLE001 - p. ej. migraciones aún sin aplicar: la API debe poder arrancar y avisar
        logger.exception("No se pudo sincronizar el catálogo de permisos (¿migraciones pendientes?)")
    yield
    await engine.dispose()


app = FastAPI(
    title=f"{settings.app_nombre} · API",
    description=(
        "Sistema web de gestión inteligente de inventarios multisede para PyMEs. "
        "Todas las rutas (salvo configuración inicial y recuperación de contraseña) exigen "
        "`Authorization: Bearer <token>` y validan permisos y sede en el servidor."
    ),
    version="1.0.0",
    lifespan=ciclo_de_vida,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

app.state.limiter = limiter
registrar_manejadores_excepciones(app)

app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origenes_permitidos,
    allow_credentials=False,  # el token viaja en la cabecera Authorization, no en cookies
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    expose_headers=["X-Request-ID", "Content-Disposition"],
)
app.add_middleware(ContextoPeticionMiddleware)

ROUTERS = (
    setup, auth, empresa, sedes, usuarios, roles, categorias, productos, inventario, alertas, ventas, traslados,
    predicciones, recomendaciones, auditoria, dashboard, reportes,
    integraciones, agentes,
)
for modulo in ROUTERS:
    app.include_router(modulo.router)


@app.get("/api/health", tags=["Sistema"], summary="Estado del servicio")
async def health():
    return {"status": "ok"}


@app.get("/api/health/ready", tags=["Sistema"], summary="Estado de la base de datos")
async def ready():
    try:
        async with fabrica_de_sesiones()() as db:
            await db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=503, content={"status": "error", "database": "no disponible"})
    return {"status": "ok", "database": "ok"}
