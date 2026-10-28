"""Ventas (RF-020, RF-021): cabecera + detalle, descuento atómico de existencias y anulación.

* El número de venta es consecutivo por empresa y sin duplicados aunque haya ventas simultáneas.
* Registrar una venta descuenta las existencias en la MISMA transacción: si falta stock en cualquier
  línea no se guarda nada.
* Anular no borra: la venta queda «anulada» y se reintegran las existencias con movimientos
  compensatorios. Solo se puede anular una vez, dentro del plazo configurable de la empresa.
"""

from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.dto.catalogo_dto import ProductoResumen
from app.dto.comunes_dto import ParametrosPagina
from app.dto.sede_dto import SedeResumen
from app.dto.ventas_dto import VentaCrear, VentaDetalle, VentaItemSalida, VentaResumen
from app.exception.excepciones import Conflicto, NoEncontrado, ReglaNegocio
from app.model.catalogo import Producto
from app.model.empresa import Empresa
from app.model.enums import EstadoVenta, TipoMovimiento
from app.model.operaciones import Venta, VentaItem
from app.model.sede import Sede
from app.model.usuario import Usuario
from app.security.acceso import Contexto
from app.service import ambiental_service, auditoria_service, inventario_service
from app.service.alcance import obtener_sede_autorizada
from app.specification.ventas_spec import condiciones_ventas
from app.util.sql import siguiente_secuencia
from app.util.tiempo import a_fecha_local, ahora_utc, asegurar_utc

CENTAVO = Decimal("0.01")


def _dinero(valor: Decimal) -> Decimal:
    return Decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


async def registrar_venta(
    db: AsyncSession, ctx: Contexto, datos: VentaCrear, *, fecha: datetime | None = None, confirmar: bool = True
) -> Venta:
    """``fecha`` solo se usa al cargar históricos (datos de demostración / migraciones)."""
    fecha = fecha or ahora_utc()
    sede = await obtener_sede_autorizada(db, ctx, datos.sede_id, requerir_activa=True)
    productos = await inventario_service.productos_de_empresa(
        db, ctx.empresa_id, [i.producto_id for i in datos.items], requerir_activos=True
    )
    lineas: list[tuple[Producto, int, Decimal]] = []
    for item in datos.items:
        producto = productos[item.producto_id]
        precio = item.precio_unitario if item.precio_unitario is not None else producto.precio_venta
        if precio is None:
            raise ReglaNegocio(
                f"«{producto.nombre}» no tiene precio de venta: indícalo en la línea o configúralo en el producto",
                codigo="precio_requerido",
            )
        lineas.append((producto, item.cantidad, _dinero(precio)))

    numero = await siguiente_secuencia(db, ctx.empresa_id, "venta")
    venta = Venta(
        empresa_id=ctx.empresa_id, sede_id=sede.id, numero=numero, usuario_id=ctx.usuario_id, fecha=fecha,
        fecha_dia=a_fecha_local(fecha), total=_dinero(sum((c * p for _, c, p in lineas), Decimal(0))),
        estado=EstadoVenta.REGISTRADA, observacion=datos.observacion,
        items=[
            VentaItem(producto_id=prod.id, cantidad=cant, precio_unitario=precio, subtotal=_dinero(cant * precio))
            for prod, cant, precio in lineas
        ],
    )
    db.add(venta)
    await db.flush()

    ops = [
        inventario_service.Operacion(
            sede.id, prod, -cant, TipoMovimiento.VENTA, observacion=f"Venta #{numero}", venta_id=venta.id
        )
        for prod, cant, _ in lineas
    ]
    await inventario_service.aplicar_lote(db, empresa_id=ctx.empresa_id, usuario_id=ctx.usuario_id, operaciones=ops, fecha=fecha)
    # Gestión ambiental: cuenta las líneas que sean vehículos (misma transacción: si la venta falla, no se cuenta).
    await ambiental_service.contabilizar_venta(db, venta, {prod.id: prod for prod, _, _ in lineas})
    await auditoria_service.registrar(
        db, modulo="ventas", accion="registrar", ctx=ctx, entidad="venta", entidad_id=venta.id, sede_id=sede.id,
        detalle={"numero": numero, "total": venta.total, "lineas": len(lineas)},
    )
    if confirmar:
        await db.commit()
        await db.refresh(venta)
    return venta


async def obtener_venta(db: AsyncSession, ctx: Contexto, venta_id: int) -> Venta:
    venta = await db.scalar(select(Venta).where(Venta.id == venta_id, Venta.empresa_id == ctx.empresa_id))
    if venta is None:
        raise NoEncontrado("La venta no existe")
    await obtener_sede_autorizada(db, ctx, venta.sede_id)  # 403 si es de otra sede y el usuario está limitado
    return venta


async def anular_venta(db: AsyncSession, ctx: Contexto, venta_id: int, motivo: str) -> Venta:
    venta = await obtener_venta(db, ctx, venta_id)
    if venta.estado == EstadoVenta.ANULADA:
        raise Conflicto("La venta ya está anulada", codigo="venta_ya_anulada")
    empresa = await db.get(Empresa, ctx.empresa_id)
    plazo = int(empresa.parametros()["dias_max_anulacion"])
    if (ahora_utc() - asegurar_utc(venta.fecha)) > timedelta(days=plazo):
        raise ReglaNegocio(
            f"Solo se pueden anular ventas de los últimos {plazo} días. Registra un ajuste de inventario si es necesario.",
            codigo="plazo_de_anulacion_vencido",
        )
    # Transición atómica: si dos personas anulan a la vez, solo una gana.
    ahora = ahora_utc()
    res = await db.execute(
        update(Venta)
        .where(Venta.id == venta.id, Venta.estado == EstadoVenta.REGISTRADA)
        .values(estado=EstadoVenta.ANULADA, anulada_por=ctx.usuario_id, anulada_en=ahora, motivo_anulacion=motivo)
        .returning(Venta.id)
    )
    if res.scalar_one_or_none() is None:
        raise Conflicto("La venta ya está anulada", codigo="venta_ya_anulada")
    productos = {p.id: p for p in (await db.scalars(select(Producto).where(Producto.id.in_([i.producto_id for i in venta.items])))).all()}
    ops = [
        inventario_service.Operacion(
            venta.sede_id, productos[i.producto_id], i.cantidad, TipoMovimiento.ANULACION_VENTA,
            observacion=f"Anulación de la venta #{venta.numero}", venta_id=venta.id,
        )
        for i in venta.items
    ]
    await inventario_service.aplicar_lote(db, empresa_id=ctx.empresa_id, usuario_id=ctx.usuario_id, operaciones=ops)
    await ambiental_service.anular_venta(db, venta.id)  # deja de contar para los indicadores ambientales
    await auditoria_service.registrar(
        db, modulo="ventas", accion="anular", ctx=ctx, entidad="venta", entidad_id=venta.id, sede_id=venta.sede_id,
        detalle={"numero": venta.numero, "motivo": motivo, "total": venta.total},
    )
    await db.commit()
    await db.refresh(venta)
    return venta


async def listar_ventas(db: AsyncSession, ctx: Contexto, pag: ParametrosPagina, **filtros) -> tuple[list[VentaResumen], int]:
    condiciones = condiciones_ventas(ctx, **filtros)
    total = await db.scalar(select(func.count()).select_from(Venta).where(*condiciones)) or 0
    ventas = (
        await db.scalars(
            select(Venta).where(*condiciones).order_by(Venta.fecha.desc(), Venta.id.desc()).offset(pag.offset).limit(pag.tamano)
        )
    ).all()
    return await resumenes(db, list(ventas)), total


async def resumenes(db: AsyncSession, ventas: list[Venta]) -> list[VentaResumen]:
    if not ventas:
        return []
    sedes = {s.id: s for s in (await db.scalars(select(Sede).where(Sede.id.in_({v.sede_id for v in ventas})))).all()}
    usuarios = {u.id: u.nombre for u in (await db.execute(select(Usuario.id, Usuario.nombre).where(Usuario.id.in_({v.usuario_id for v in ventas})))).all()}
    return [
        VentaResumen(
            id=v.id, numero=v.numero, fecha=v.fecha, fecha_dia=v.fecha_dia, sede=SedeResumen.model_validate(sedes[v.sede_id]),
            usuario_nombre=usuarios.get(v.usuario_id), total=v.total, unidades=sum(i.cantidad for i in v.items),
            lineas=len(v.items), estado=v.estado, observacion=v.observacion,
        )
        for v in ventas
    ]


async def detalle(db: AsyncSession, ctx: Contexto, venta: Venta) -> VentaDetalle:
    base = (await resumenes(db, [venta]))[0]
    productos = {p.id: p for p in (await db.scalars(select(Producto).where(Producto.id.in_([i.producto_id for i in venta.items])))).all()}
    anulada_por = await db.scalar(select(Usuario.nombre).where(Usuario.id == venta.anulada_por)) if venta.anulada_por else None
    empresa = await db.get(Empresa, ctx.empresa_id)
    plazo = int(empresa.parametros()["dias_max_anulacion"])
    vigente = (ahora_utc() - asegurar_utc(venta.fecha)) <= timedelta(days=plazo)
    return VentaDetalle(
        **base.model_dump(),
        items=[
            VentaItemSalida(
                producto=ProductoResumen.model_validate(productos[i.producto_id]), cantidad=i.cantidad,
                precio_unitario=i.precio_unitario, subtotal=i.subtotal,
            )
            for i in venta.items
        ],
        anulada_por_nombre=anulada_por, anulada_en=venta.anulada_en, motivo_anulacion=venta.motivo_anulacion,
        puede_anularse=venta.estado == EstadoVenta.REGISTRADA and vigente and ctx.tiene("ventas.anular"),
    )
