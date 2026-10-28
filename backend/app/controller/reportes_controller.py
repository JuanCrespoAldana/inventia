import asyncio
import re
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.security.acceso import Contexto
from app.security.dependencias import contexto_actual
from app.service import reportes_service as svc
from app.util.tiempo import hoy_local

router = APIRouter(prefix="/api/reportes", tags=["Reportes"])


class ColumnaSalida(BaseModel):
    clave: str
    titulo: str
    tipo: str


class ReporteSalida(BaseModel):
    tipo: str
    titulo: str
    columnas: list[ColumnaSalida]
    filas: list[dict]
    resumen: dict
    total: int
    truncado: bool


class TipoReporte(BaseModel):
    tipo: str
    titulo: str
    permiso: str


@router.get("", response_model=list[TipoReporte], summary="Reportes que el usuario puede generar")
async def catalogo(ctx: Contexto = Depends(contexto_actual)):
    return [TipoReporte(tipo=t, titulo=titulo, permiso=p) for t, (p, titulo) in svc.TIPOS.items() if ctx.tiene(p)]


@router.get(
    "/{tipo}",
    summary="Generar un reporte: vista previa (json) o descarga (csv, xlsx, pdf)",
    responses={200: {"content": {"application/json": {}, "text/csv": {}, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}, "application/pdf": {}}}},
)
async def generar(
    tipo: str,
    formato: str = Query("json", pattern="^(json|csv|xlsx|pdf)$"),
    sede_id: int | None = Query(None, gt=0),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    categoria_id: int | None = Query(None, gt=0),
    estado: str | None = Query(None, max_length=20),
    tipo_filtro: str | None = Query(None, alias="clase", max_length=30, description="Filtro por tipo (movimientos, alertas, recomendaciones)"),
    ctx: Contexto = Depends(contexto_actual),
    db: AsyncSession = Depends(get_db),
):
    filtros = svc.Filtros(sede_id=sede_id, desde=desde, hasta=hasta, categoria_id=categoria_id, estado=estado, tipo=tipo_filtro)
    if formato == "json":
        reporte = await svc.generar(db, ctx, tipo, filtros, limite=svc.LIMITE_VISTA_PREVIA)
        return ReporteSalida(
            tipo=reporte.tipo, titulo=reporte.titulo, columnas=[ColumnaSalida(clave=c.clave, titulo=c.titulo, tipo=c.tipo) for c in reporte.columnas],
            filas=[{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in f.items()} for f in reporte.filas],
            resumen=reporte.resumen, total=reporte.total, truncado=reporte.truncado,
        )
    reporte = await svc.generar(db, ctx, tipo, filtros, limite=svc.LIMITE_PDF if formato == "pdf" else svc.LIMITE_EXPORTACION)
    await svc.auditar_exportacion(db, ctx, tipo, formato, filtros, reporte.total)
    base = re.sub(r"[^a-z0-9]+", "-", f"{tipo}-{hoy_local().isoformat()}")
    # Armar el archivo es trabajo de CPU: se hace en un hilo aparte para no detener al resto de las peticiones.
    if formato == "csv":
        contenido, media = await asyncio.to_thread(svc.a_csv, reporte), "text/csv; charset=utf-8"
    elif formato == "pdf":
        contenido = await asyncio.to_thread(
            svc.a_pdf, reporte, empresa=await svc.nombre_empresa(db, ctx), usuario=ctx.usuario.nombre,
            filtros_texto=svc.descripcion_filtros(filtros), generado=svc.hora_local_actual(),
        )
        media = "application/pdf"
    else:
        contenido = await asyncio.to_thread(
            svc.a_xlsx, reporte, empresa=await svc.nombre_empresa(db, ctx), usuario=ctx.usuario.nombre,
            filtros_texto=svc.descripcion_filtros(filtros),
        )
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return Response(contenido, media_type=media, headers={"Content-Disposition": f'attachment; filename="{base}.{formato}"'})
