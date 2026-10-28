"""Especificaciones de filtros del módulo de calidad (no conformidades y garantías)."""

from datetime import date

from sqlalchemy import func, or_, select

from app.model.calidad import Garantia, NoConformidad
from app.model.catalogo import Producto
from app.security.acceso import Contexto
from app.service.alcance import resolver_filtro_sede


def condiciones_no_conformidades(
    ctx: Contexto, *, sede_id, estado, tipo, producto_id, entrada_id, desde: date | None, hasta: date | None, q: str | None
) -> list:
    condiciones = [NoConformidad.empresa_id == ctx.empresa_id]
    sede_ids = resolver_filtro_sede(ctx, sede_id)
    if sede_ids is not None:
        condiciones.append(NoConformidad.sede_id.in_(sede_ids))
    for columna, valor in ((NoConformidad.estado, estado), (NoConformidad.tipo, tipo), (NoConformidad.producto_id, producto_id),
                           (NoConformidad.entrada_id, entrada_id)):
        if valor:
            condiciones.append(columna == valor)
    if desde:
        condiciones.append(NoConformidad.fecha_deteccion >= desde)
    if hasta:
        condiciones.append(NoConformidad.fecha_deteccion <= hasta)
    if q:
        patron = f"%{q.strip().lower()}%"
        filtro = or_(
            func.lower(NoConformidad.referencia).like(patron),
            NoConformidad.producto_id.in_(
                select(Producto.id).where(
                    Producto.empresa_id == ctx.empresa_id,
                    or_(func.lower(Producto.nombre).like(patron), func.lower(Producto.codigo).like(patron)),
                )
            ),
        )
        if q.strip().isdigit():
            filtro = or_(filtro, NoConformidad.numero == int(q.strip()))
        condiciones.append(filtro)
    return condiciones


def condiciones_garantias(
    ctx: Contexto, *, sede_id, estado, producto_id, proveedor: str | None, desde: date | None, hasta: date | None, q: str | None
) -> list:
    condiciones = [Garantia.empresa_id == ctx.empresa_id]
    sede_ids = resolver_filtro_sede(ctx, sede_id)
    if sede_ids is not None:
        condiciones.append(Garantia.sede_id.in_(sede_ids))
    if estado:
        condiciones.append(Garantia.estado == estado)
    if producto_id:
        condiciones.append(Garantia.producto_id == producto_id)
    if proveedor:
        condiciones.append(func.lower(Garantia.proveedor).like(f"%{proveedor.strip().lower()}%"))
    if desde:
        condiciones.append(Garantia.fecha_reporte >= desde)
    if hasta:
        condiciones.append(Garantia.fecha_reporte <= hasta)
    if q:
        patron = f"%{q.strip().lower()}%"
        filtro = or_(
            func.lower(Garantia.documento_referencia).like(patron),
            Garantia.producto_id.in_(
                select(Producto.id).where(
                    Producto.empresa_id == ctx.empresa_id,
                    or_(func.lower(Producto.nombre).like(patron), func.lower(Producto.codigo).like(patron)),
                )
            ),
        )
        if q.strip().isdigit():
            filtro = or_(filtro, Garantia.numero == int(q.strip()))
        condiciones.append(filtro)
    return condiciones
