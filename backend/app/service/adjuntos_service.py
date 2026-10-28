"""Evidencias adjuntas a PQRS, no conformidades y garantías.

Seguridad:
 * Solo imágenes (JPEG, PNG, WebP) y PDF. El tipo se determina por los PRIMEROS BYTES del archivo, no por la
   extensión ni por el ``Content-Type`` que declara el navegador.
 * Máximo 3 MB por archivo y 5 por registro.
 * El nombre original se limpia (sin rutas ni caracteres de control) y nunca se usa como ruta en disco: el
   contenido vive en la base de datos.
 * La descarga siempre se entrega como adjunto con ``nosniff`` (el navegador no lo interpreta ni lo ejecuta).
La autorización (¿puede esta persona ver/adjuntar en este registro?) la resuelve la capa de API usando el
servicio del módulo dueño del registro; aquí solo se guarda y se lee."""

import hashlib
import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from app.dto.adjunto_dto import AdjuntoSalida
from app.exception.excepciones import NoEncontrado, ReglaNegocio
from app.model.adjunto import Adjunto
from app.service.sig_util import nombres_usuarios

MAX_BYTES = 3 * 1024 * 1024
MAX_POR_REGISTRO = 5

_CAMPO = {"pqrs": "pqrs_id", "no_conformidad": "no_conformidad_id", "garantia": "garantia_id"}
_EXTENSION = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "application/pdf": ".pdf"}


def detectar_tipo(contenido: bytes) -> str | None:
    """Tipo MIME real según la firma del archivo, o ``None`` si no es un formato permitido."""
    if contenido.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return "image/webp"
    if contenido.startswith(b"%PDF-"):
        return "application/pdf"
    return None


def limpiar_nombre(nombre: str | None, tipo_mime: str) -> str:
    """Nombre seguro para mostrar y descargar: sin rutas ni caracteres raros y con la extensión del tipo real."""
    base = (nombre or "").replace("\\", "/").split("/")[-1]
    base = re.sub(r"[\x00-\x1f\x7f]", "", base)
    base = re.sub(r"[^\w\-. ()áéíóúÁÉÍÓÚñÑüÜ]", "_", base).strip(" .")
    cuerpo, punto, extension = base.rpartition(".")
    if punto and extension.lower() in {"jpg", "jpeg", "png", "webp", "pdf"}:
        base = cuerpo
    return f"{(base.strip(' .') or 'evidencia')[:190]}{_EXTENSION[tipo_mime]}"


def _filtro(entidad: str, entidad_id: int):
    return getattr(Adjunto, _CAMPO[entidad]) == entidad_id


async def listar(
    db: AsyncSession, entidad: str, entidad_id: int, *, ver_usuario_id: int | None = None, es_gestor: bool = False
) -> list[AdjuntoSalida]:
    """Metadatos de los adjuntos (el contenido no se carga). ``puede_eliminar``: quien lo subió o un gestor."""
    filas = (await db.scalars(select(Adjunto).where(_filtro(entidad, entidad_id)).order_by(Adjunto.id))).all()
    nombres = await nombres_usuarios(db, {a.subido_por for a in filas})
    return [
        AdjuntoSalida(
            id=a.id, nombre=a.nombre, tipo_mime=a.tipo_mime, tamano=a.tamano, created_at=a.created_at,
            subido_por=a.subido_por, subido_por_nombre=nombres.get(a.subido_por),
            puede_eliminar=es_gestor or a.subido_por == ver_usuario_id,
        )
        for a in filas
    ]


async def contar(db: AsyncSession, entidad: str, ids: list[int]) -> dict[int, int]:
    if not ids:
        return {}
    campo = getattr(Adjunto, _CAMPO[entidad])
    return dict((await db.execute(select(campo, func.count()).where(campo.in_(ids)).group_by(campo))).all())


async def guardar(
    db: AsyncSession, *, empresa_id: int, usuario_id: int, entidad: str, entidad_id: int, nombre: str | None, contenido: bytes
) -> Adjunto:
    if not contenido:
        raise ReglaNegocio("El archivo está vacío", codigo="archivo_vacio")
    if len(contenido) > MAX_BYTES:
        raise ReglaNegocio("El archivo supera el tamaño máximo de 3 MB", codigo="archivo_muy_grande")
    tipo = detectar_tipo(contenido)
    if tipo is None:
        raise ReglaNegocio("Solo se permiten imágenes (JPG, PNG, WebP) y archivos PDF", codigo="tipo_no_permitido")
    existentes = await db.scalar(select(func.count()).select_from(Adjunto).where(_filtro(entidad, entidad_id))) or 0
    if existentes >= MAX_POR_REGISTRO:
        raise ReglaNegocio(f"Cada registro admite hasta {MAX_POR_REGISTRO} archivos", codigo="demasiados_archivos")
    adjunto = Adjunto(
        empresa_id=empresa_id, nombre=limpiar_nombre(nombre, tipo), tipo_mime=tipo, tamano=len(contenido),
        sha256=hashlib.sha256(contenido).hexdigest(), contenido=contenido, subido_por=usuario_id,
        **{_CAMPO[entidad]: entidad_id},
    )
    db.add(adjunto)
    await db.flush()
    return adjunto


async def obtener(db: AsyncSession, empresa_id: int, adjunto_id: int, *, con_contenido: bool = False) -> Adjunto:
    consulta = select(Adjunto).where(Adjunto.id == adjunto_id, Adjunto.empresa_id == empresa_id)
    if con_contenido:
        consulta = consulta.options(undefer(Adjunto.contenido))
    adjunto = await db.scalar(consulta)
    if adjunto is None:
        raise NoEncontrado("El archivo no existe")
    return adjunto


def destino(adjunto: Adjunto) -> tuple[str, int]:
    """(entidad, id) del registro al que pertenece el adjunto."""
    if adjunto.pqrs_id:
        return "pqrs", adjunto.pqrs_id
    if adjunto.no_conformidad_id:
        return "no_conformidad", adjunto.no_conformidad_id
    return "garantia", adjunto.garantia_id  # type: ignore[return-value]
