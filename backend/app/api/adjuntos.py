"""Evidencias (imágenes y PDF) de PQRS, no conformidades y garantías.

La carga es el CUERPO crudo de la petición (no multipart): ``POST /api/sig/adjuntos?entidad=…&entidad_id=…&nombre=…``.
El tipo se valida por el contenido real y se rechaza lo que supere el límite antes de leerlo completo."""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import contexto_actual
from app.core.acceso import Contexto
from app.core.database import get_db
from app.core.exceptions import ReglaNegocio, SinPermiso
from app.core.limiter import limiter
from app.schemas.adjunto import AdjuntoSalida, EntidadAdjuntoT
from app.schemas.comunes import Mensaje
from app.services import adjuntos_service, auditoria_service, calidad_service, pqrs_service

router = APIRouter(prefix="/api/sig/adjuntos", tags=["SIG · Evidencias"])


async def _autorizar(db: AsyncSession, ctx: Contexto, entidad: str, entidad_id: int, *, escribir: bool):
    """Devuelve (sede_id, es_gestor) tras verificar que la persona puede ver (o adjuntar en) el registro."""
    if entidad == "pqrs":
        ctx.exigir("pqrs.crear", "pqrs.gestionar")
        registro = await pqrs_service.obtener(db, ctx, entidad_id)  # propia o gestor
        gestor = ctx.tiene("pqrs.gestionar")
        if escribir and not gestor and registro.estado == "resuelta":
            raise ReglaNegocio("La solicitud ya está resuelta: no admite más archivos", codigo="registro_cerrado")
        return registro.sede_id, gestor
    ctx.exigir("calidad.ver")
    if entidad == "no_conformidad":
        registro = await calidad_service.obtener_nc(db, ctx, entidad_id)
        cerrado = registro.estado == "cerrado"
    else:
        registro = await calidad_service.obtener_garantia(db, ctx, entidad_id)
        cerrado = registro.estado == "cerrada"
    gestor = ctx.tiene("calidad.gestionar")
    if escribir:
        ctx.exigir("calidad.reportar", "calidad.gestionar")
        if cerrado:
            raise ReglaNegocio("El registro está cerrado: no admite más archivos", codigo="registro_cerrado")
    return registro.sede_id, gestor


async def _leer_cuerpo(request: Request, limite: int) -> bytes:
    declarado = request.headers.get("content-length")
    if declarado and declarado.isdigit() and int(declarado) > limite:
        raise ReglaNegocio("El archivo supera el tamaño máximo de 3 MB", codigo="archivo_muy_grande")
    partes: list[bytes] = []
    total = 0
    async for trozo in request.stream():
        total += len(trozo)
        if total > limite:
            raise ReglaNegocio("El archivo supera el tamaño máximo de 3 MB", codigo="archivo_muy_grande")
        partes.append(trozo)
    return b"".join(partes)


@router.get("", response_model=list[AdjuntoSalida], summary="Archivos de un registro")
async def listar(
    entidad: EntidadAdjuntoT = Query(...), entidad_id: int = Query(..., gt=0),
    ctx: Contexto = Depends(contexto_actual), db: AsyncSession = Depends(get_db),
):
    _, gestor = await _autorizar(db, ctx, entidad, entidad_id, escribir=False)
    return await adjuntos_service.listar(db, entidad, entidad_id, ver_usuario_id=ctx.usuario_id, es_gestor=gestor)


@router.post("", response_model=AdjuntoSalida, status_code=status.HTTP_201_CREATED, summary="Adjuntar un archivo")
@limiter.limit("60/minute")
async def subir(
    request: Request,
    entidad: EntidadAdjuntoT = Query(...), entidad_id: int = Query(..., gt=0),
    nombre: str | None = Query(None, max_length=255),
    ctx: Contexto = Depends(contexto_actual), db: AsyncSession = Depends(get_db),
):
    sede_id, gestor = await _autorizar(db, ctx, entidad, entidad_id, escribir=True)
    contenido = await _leer_cuerpo(request, adjuntos_service.MAX_BYTES)
    adjunto = await adjuntos_service.guardar(
        db, empresa_id=ctx.empresa_id, usuario_id=ctx.usuario_id, entidad=entidad, entidad_id=entidad_id,
        nombre=nombre, contenido=contenido,
    )
    await auditoria_service.registrar(
        db, modulo="sig", accion="adjuntar", ctx=ctx, entidad=entidad, entidad_id=entidad_id, sede_id=sede_id,
        detalle={"archivo": adjunto.nombre, "tipo": adjunto.tipo_mime, "bytes": adjunto.tamano},
    )
    await db.commit()
    return AdjuntoSalida(
        id=adjunto.id, nombre=adjunto.nombre, tipo_mime=adjunto.tipo_mime, tamano=adjunto.tamano,
        created_at=adjunto.created_at, subido_por=adjunto.subido_por, subido_por_nombre=ctx.usuario.nombre, puede_eliminar=True,
    )


@router.get("/{adjunto_id}/archivo", summary="Descargar un archivo")
async def descargar(adjunto_id: int, ctx: Contexto = Depends(contexto_actual), db: AsyncSession = Depends(get_db)):
    adjunto = await adjuntos_service.obtener(db, ctx.empresa_id, adjunto_id, con_contenido=True)
    entidad, entidad_id = adjuntos_service.destino(adjunto)
    await _autorizar(db, ctx, entidad, entidad_id, escribir=False)
    return Response(
        content=adjunto.contenido,
        media_type=adjunto.tipo_mime,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(adjunto.nombre)}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.delete("/{adjunto_id}", response_model=Mensaje, summary="Eliminar un archivo")
async def eliminar(adjunto_id: int, ctx: Contexto = Depends(contexto_actual), db: AsyncSession = Depends(get_db)):
    adjunto = await adjuntos_service.obtener(db, ctx.empresa_id, adjunto_id)
    entidad, entidad_id = adjuntos_service.destino(adjunto)
    sede_id, gestor = await _autorizar(db, ctx, entidad, entidad_id, escribir=True)
    if not gestor and adjunto.subido_por != ctx.usuario_id:
        raise SinPermiso("Solo quien subió el archivo o la administración puede eliminarlo")
    nombre = adjunto.nombre
    await db.delete(adjunto)
    await auditoria_service.registrar(
        db, modulo="sig", accion="eliminar_adjunto", ctx=ctx, entidad=entidad, entidad_id=entidad_id, sede_id=sede_id,
        detalle={"archivo": nombre},
    )
    await db.commit()
    return Mensaje(mensaje="Archivo eliminado")
