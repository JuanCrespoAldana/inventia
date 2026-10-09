from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import requiere
from app.core.acceso import Contexto
from app.core.database import get_db
from app.ml import pipeline
from app.ml.modelos import CANDIDATOS, LINEA_BASE
from app.schemas.comunes import Pagina, ParametrosPagina
from app.schemas.prediccion import EjecucionSalida, EjecutarPrediccion, PrediccionSalida, SerieDemanda
from app.services import prediccion_service as svc
from app.services.alcance import resolver_filtro_sede

router = APIRouter(prefix="/api/predicciones", tags=["Predicciones"])


def _acotar_a_sedes(ctx: Contexto, salida: EjecucionSalida) -> EjecucionSalida:
    """Un usuario limitado a una sede no ve en el detalle series de otras sedes."""
    autorizadas = ctx.sedes_autorizadas()
    if autorizadas is not None and salida.resumen.get("omitidas"):
        salida.resumen["omitidas"] = [o for o in salida.resumen["omitidas"] if o["sede_id"] in autorizadas]
    return salida


@router.post(
    "/ejecutar", response_model=EjecucionSalida, status_code=status.HTTP_202_ACCEPTED,
    summary="Generar predicciones de demanda (se calculan en segundo plano)",
)
async def ejecutar(
    datos: EjecutarPrediccion, segundo_plano: BackgroundTasks, ctx: Contexto = Depends(requiere("prediccion.ejecutar")),
    db: AsyncSession = Depends(get_db),
):
    ejecucion = await svc.solicitar(db, ctx, datos.horizonte_dias)
    segundo_plano.add_task(svc.ejecutar_en_segundo_plano, ejecucion.id)
    return (await svc.a_salida(db, [ejecucion], detallada=False))[0]


@router.get("/ejecuciones", response_model=Pagina[EjecucionSalida], summary="Historial de ejecuciones")
async def listar_ejecuciones(
    pag: ParametrosPagina = Depends(), ctx: Contexto = Depends(requiere("prediccion.ver")), db: AsyncSession = Depends(get_db)
):
    filas, total = await svc.listar_ejecuciones(db, ctx, pag)
    return Pagina.crear(await svc.a_salida(db, filas, detallada=False), total, pag.pagina, pag.tamano)


@router.get("/ejecuciones/{ejecucion_id}", response_model=EjecucionSalida, summary="Detalle de una ejecución")
async def obtener_ejecucion(
    ejecucion_id: int, ctx: Contexto = Depends(requiere("prediccion.ver")), db: AsyncSession = Depends(get_db)
):
    e = await svc.obtener_ejecucion(db, ctx, ejecucion_id)
    return _acotar_a_sedes(ctx, (await svc.a_salida(db, [e], detallada=True))[0])


@router.get("", response_model=Pagina[PrediccionSalida], summary="Consultar predicciones de demanda")
async def listar(
    pag: ParametrosPagina = Depends(),
    ejecucion_id: int | None = Query(None, gt=0, description="Vacío = la última ejecución completada"),
    sede_id: int | None = Query(None, gt=0),
    producto_id: int | None = Query(None, gt=0),
    confianza: str | None = Query(None, pattern="^(alta|media|baja)$"),
    q: str | None = Query(None, max_length=100),
    orden: str = Query("demanda", pattern="^(demanda|producto)$"),
    ctx: Contexto = Depends(requiere("prediccion.ver")),
    db: AsyncSession = Depends(get_db),
):
    items, total, _ = await svc.listar_predicciones(
        db, ctx, pag, ejecucion_id=ejecucion_id, sede_ids=resolver_filtro_sede(ctx, sede_id), producto_id=producto_id,
        confianza=confianza, q=q, orden=orden,
    )
    return Pagina.crear(items, total, pag.pagina, pag.tamano)


@router.get("/serie", response_model=SerieDemanda, summary="Historial de ventas y pronóstico de un producto en una sede")
async def serie(
    sede_id: int = Query(gt=0), producto_id: int = Query(gt=0), dias: int = Query(60, ge=14, le=365),
    ctx: Contexto = Depends(requiere("prediccion.ver")), db: AsyncSession = Depends(get_db),
):
    return await svc.serie_de_demanda(db, ctx, sede_id, producto_id, dias)


class ModeloInfo(BaseModel):
    nombre: str
    descripcion: str
    avanzado: bool
    es_linea_base: bool


class CatalogoModelos(BaseModel):
    modelos: list[ModeloInfo]
    minimo_dias_historia: int
    minimo_dias_con_ventas: int
    mejora_minima_modelo_avanzado_pct: float


@router.get("/modelos", response_model=CatalogoModelos, summary="Modelos y reglas que usa la predicción")
async def modelos(ctx: Contexto = Depends(requiere("prediccion.ver"))):
    return CatalogoModelos(
        modelos=[
            ModeloInfo(nombre=c.nombre, descripcion=c.descripcion, avanzado=c.avanzado, es_linea_base=c.nombre == LINEA_BASE)
            for c in CANDIDATOS
        ],
        minimo_dias_historia=pipeline.MIN_DIAS_HISTORIA,
        minimo_dias_con_ventas=pipeline.MIN_DIAS_CON_VENTAS,
        mejora_minima_modelo_avanzado_pct=pipeline.MEJORA_MINIMA_AVANZADO * 100,
    )
