"""Consulta de solo lectura para agentes de IA. Se autentica con la cabecera ``X-API-Key``."""

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import SinPermiso
from app.core.limiter import limiter
from app.schemas.comunes import Pagina, ParametrosPagina
from app.services import agentes_service as svc
from app.services.agentes_service import ContextoAgente

router = APIRouter(prefix="/api/agentes", tags=["Agentes de IA"])


async def agente_autenticado(x_api_key: str | None = Header(None, alias="X-API-Key"), db: AsyncSession = Depends(get_db)) -> ContextoAgente:
    return await svc.autenticar(db, x_api_key)


async def _con_alcance(agente: ContextoAgente, alcance: str, recurso: str) -> None:
    try:
        agente.exigir(alcance)
    except SinPermiso:
        await svc.registrar_denegacion(agente, recurso, f"falta el alcance {alcance}")
        raise


@router.get("/yo", summary="Qué puede consultar esta llave")
@limiter.limit("60/minute")
async def yo(request: Request, agente: ContextoAgente = Depends(agente_autenticado)):
    return {"nombre": agente.nombre, "sede_id": agente.sede_id, "alcances": sorted(agente.alcances), "solo_lectura": True}


@router.get("/inventario", summary="Existencias por sede")
@limiter.limit("60/minute")
async def inventario(
    request: Request, pag: ParametrosPagina = Depends(), sede_id: int | None = Query(None, gt=0),
    q: str | None = Query(None, max_length=100), agente: ContextoAgente = Depends(agente_autenticado),
    db: AsyncSession = Depends(get_db),
):
    await _con_alcance(agente, "inventario:leer", "inventario")
    items, total = await svc.inventario(db, agente, pag, sede_id, q)
    return Pagina.crear(items, total, pag.pagina, pag.tamano)


@router.get("/alertas", summary="Alertas de inventario activas")
@limiter.limit("60/minute")
async def alertas(
    request: Request, pag: ParametrosPagina = Depends(), sede_id: int | None = Query(None, gt=0),
    tipo: str | None = Query(None, max_length=30), agente: ContextoAgente = Depends(agente_autenticado),
    db: AsyncSession = Depends(get_db),
):
    await _con_alcance(agente, "alertas:leer", "alertas")
    items, total = await svc.alertas(db, agente, pag, sede_id, tipo)
    return Pagina.crear(items, total, pag.pagina, pag.tamano)


@router.get("/predicciones", summary="Última predicción de demanda (son estimaciones, no ventas)")
@limiter.limit("60/minute")
async def predicciones(
    request: Request, pag: ParametrosPagina = Depends(), sede_id: int | None = Query(None, gt=0),
    q: str | None = Query(None, max_length=100), agente: ContextoAgente = Depends(agente_autenticado),
    db: AsyncSession = Depends(get_db),
):
    await _con_alcance(agente, "predicciones:leer", "predicciones")
    items, total, ejecucion = await svc.predicciones(db, agente, pag, sede_id, q)
    return {**Pagina.crear(items, total, pag.pagina, pag.tamano).model_dump(),
            "ejecucion_id": ejecucion.id if ejecucion else None,
            "fecha_corte": ejecucion.fecha_corte.isoformat() if ejecucion and ejecucion.fecha_corte else None}


@router.get("/recomendaciones", summary="Recomendaciones pendientes de aprobación humana")
@limiter.limit("60/minute")
async def recomendaciones(
    request: Request, pag: ParametrosPagina = Depends(), sede_id: int | None = Query(None, gt=0),
    agente: ContextoAgente = Depends(agente_autenticado), db: AsyncSession = Depends(get_db),
):
    await _con_alcance(agente, "recomendaciones:leer", "recomendaciones")
    items, total = await svc.recomendaciones(db, agente, pag, sede_id)
    return Pagina.crear(items, total, pag.pagina, pag.tamano)
