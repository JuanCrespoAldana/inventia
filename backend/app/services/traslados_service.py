"""Traslados entre sedes (RF-022, RF-023).

Flujo: solicitado → aprobado → confirmado, o rechazado / cancelado.
 * Solicitar: quien opera la sede de origen O la de destino (o un rol de toda la empresa).
 * Aprobar o rechazar: quien administra la sede de ORIGEN (la que cede la mercancía).
 * Confirmar: quien administra la sede de DESTINO (recibe la mercancía) o un rol de toda la empresa.
 * Las existencias SOLO cambian al confirmar, en una única transacción que descuenta del origen y suma
   al destino. Si falta stock en el origen no se mueve nada. Dos confirmaciones simultáneas: gana una.
"""

from datetime import date

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.acceso import Contexto
from app.core.exceptions import Conflicto, NoEncontrado, ReglaNegocio, SinPermiso
from app.core.sql import siguiente_secuencia
from app.core.tiempo import ahora_utc
from app.models.catalogo import Producto
from app.models.enums import EstadoTraslado, TipoMovimiento
from app.models.inventario import InventarioSede
from app.models.operaciones import Traslado, TrasladoItem
from app.models.sede import Sede
from app.models.usuario import Usuario
from app.schemas.catalogo import ProductoResumen
from app.schemas.comunes import ParametrosPagina
from app.schemas.sede import SedeResumen
from app.schemas.traslados import TrasladoCrear, TrasladoDetalle, TrasladoItemSalida, TrasladoResumen
from app.services import auditoria_service, inventario_service
from app.services.alcance import obtener_sede_de_empresa

PENDIENTES = (EstadoTraslado.SOLICITADO, EstadoTraslado.APROBADO)


def _alcanza(ctx: Contexto, sede_id: int) -> bool:
    autorizadas = ctx.sedes_autorizadas()
    return autorizadas is None or sede_id in autorizadas


def _exigir_alcance(ctx: Contexto, sede_id: int, mensaje: str) -> None:
    if not _alcanza(ctx, sede_id):
        raise SinPermiso(mensaje, codigo="fuera_de_alcance")


async def crear_traslado(
    db: AsyncSession, ctx: Contexto, datos: TrasladoCrear, *, recomendacion_id: int | None = None, confirmar: bool = True
) -> Traslado:
    origen = await obtener_sede_de_empresa(db, ctx.empresa_id, datos.sede_origen_id, requerir_activa=True)
    destino = await obtener_sede_de_empresa(db, ctx.empresa_id, datos.sede_destino_id, requerir_activa=True)
    if not (_alcanza(ctx, origen.id) or _alcanza(ctx, destino.id)):
        raise SinPermiso("Solo puedes solicitar traslados que salgan de tu sede o lleguen a ella", codigo="fuera_de_alcance")
    productos = await inventario_service.productos_de_empresa(
        db, ctx.empresa_id, [i.producto_id for i in datos.items], requerir_activos=True
    )
    traslado = Traslado(
        empresa_id=ctx.empresa_id, numero=await siguiente_secuencia(db, ctx.empresa_id, "traslado"),
        sede_origen_id=origen.id, sede_destino_id=destino.id, estado=EstadoTraslado.SOLICITADO,
        observacion=datos.observacion, recomendacion_id=recomendacion_id, solicitado_por=ctx.usuario_id,
        solicitado_en=ahora_utc(),
        items=[TrasladoItem(producto_id=i.producto_id, cantidad=i.cantidad) for i in datos.items],
    )
    db.add(traslado)
    await db.flush()
    await auditoria_service.registrar(
        db, modulo="traslados", accion="solicitar", ctx=ctx, entidad="traslado", entidad_id=traslado.id,
        sede_id=origen.id,
        detalle={"numero": traslado.numero, "origen": origen.nombre, "destino": destino.nombre,
                 "lineas": [{"producto": productos[i.producto_id].codigo, "cantidad": i.cantidad} for i in datos.items],
                 "recomendacion_id": recomendacion_id},
    )
    if confirmar:
        await db.commit()
        await db.refresh(traslado)
    return traslado


async def obtener_traslado(db: AsyncSession, ctx: Contexto, traslado_id: int) -> Traslado:
    traslado = await db.scalar(select(Traslado).where(Traslado.id == traslado_id, Traslado.empresa_id == ctx.empresa_id))
    if traslado is None:
        raise NoEncontrado("El traslado no existe")
    if not (_alcanza(ctx, traslado.sede_origen_id) or _alcanza(ctx, traslado.sede_destino_id)):
        raise NoEncontrado("El traslado no existe")  # ni siquiera se revela que existe
    return traslado


async def _cerrar(db: AsyncSession, ctx: Contexto, traslado: Traslado, nuevo: str, motivo: str, desde: tuple[str, ...]) -> None:
    res = await db.execute(
        update(Traslado)
        .where(Traslado.id == traslado.id, Traslado.estado.in_(desde))
        .values(estado=nuevo, cerrado_por=ctx.usuario_id, cerrado_en=ahora_utc(), motivo_cierre=motivo)
        .returning(Traslado.id)
    )
    if res.scalar_one_or_none() is None:
        raise Conflicto("El traslado cambió de estado mientras lo revisabas. Actualiza la pantalla.", codigo="estado_cambiado")


async def aprobar(db: AsyncSession, ctx: Contexto, traslado_id: int) -> Traslado:
    traslado = await obtener_traslado(db, ctx, traslado_id)
    _exigir_alcance(ctx, traslado.sede_origen_id, "Solo quien administra la sede de origen puede aprobar el traslado")
    res = await db.execute(
        update(Traslado)
        .where(Traslado.id == traslado.id, Traslado.estado == EstadoTraslado.SOLICITADO)
        .values(estado=EstadoTraslado.APROBADO, aprobado_por=ctx.usuario_id, aprobado_en=ahora_utc())
        .returning(Traslado.id)
    )
    if res.scalar_one_or_none() is None:
        raise Conflicto("Solo se pueden aprobar traslados en estado «solicitado»", codigo="estado_invalido")
    await auditoria_service.registrar(
        db, modulo="traslados", accion="aprobar", ctx=ctx, entidad="traslado", entidad_id=traslado.id,
        sede_id=traslado.sede_origen_id, detalle={"numero": traslado.numero},
    )
    await db.commit()
    await db.refresh(traslado)
    return traslado


async def rechazar(db: AsyncSession, ctx: Contexto, traslado_id: int, motivo: str) -> Traslado:
    traslado = await obtener_traslado(db, ctx, traslado_id)
    _exigir_alcance(ctx, traslado.sede_origen_id, "Solo quien administra la sede de origen puede rechazar el traslado")
    await _cerrar(db, ctx, traslado, EstadoTraslado.RECHAZADO, motivo, (EstadoTraslado.SOLICITADO,))
    await auditoria_service.registrar(
        db, modulo="traslados", accion="rechazar", ctx=ctx, entidad="traslado", entidad_id=traslado.id,
        sede_id=traslado.sede_origen_id, detalle={"numero": traslado.numero, "motivo": motivo},
    )
    await db.commit()
    await db.refresh(traslado)
    return traslado


async def cancelar(db: AsyncSession, ctx: Contexto, traslado_id: int, motivo: str) -> Traslado:
    traslado = await obtener_traslado(db, ctx, traslado_id)
    await _cerrar(db, ctx, traslado, EstadoTraslado.CANCELADO, motivo, PENDIENTES)
    await auditoria_service.registrar(
        db, modulo="traslados", accion="cancelar", ctx=ctx, entidad="traslado", entidad_id=traslado.id,
        sede_id=traslado.sede_origen_id, detalle={"numero": traslado.numero, "motivo": motivo},
    )
    await db.commit()
    await db.refresh(traslado)
    return traslado


async def confirmar(db: AsyncSession, ctx: Contexto, traslado_id: int) -> Traslado:
    traslado = await obtener_traslado(db, ctx, traslado_id)
    _exigir_alcance(ctx, traslado.sede_destino_id, "Solo quien administra la sede de destino puede confirmar la recepción")
    # La transición de estado es la «llave»: si otra confirmación llegó antes, esta falla y no mueve nada.
    ahora = ahora_utc()
    res = await db.execute(
        update(Traslado)
        .where(Traslado.id == traslado.id, Traslado.estado == EstadoTraslado.APROBADO)
        .values(estado=EstadoTraslado.CONFIRMADO, confirmado_por=ctx.usuario_id, confirmado_en=ahora)
        .returning(Traslado.id)
    )
    if res.scalar_one_or_none() is None:
        raise Conflicto("Solo se pueden confirmar traslados aprobados que no hayan sido confirmados", codigo="estado_invalido")
    productos = await inventario_service.productos_de_empresa(
        db, ctx.empresa_id, [i.producto_id for i in traslado.items], requerir_activos=True
    )
    ops = []
    for item in traslado.items:
        producto = productos[item.producto_id]
        ops.append(inventario_service.Operacion(
            traslado.sede_origen_id, producto, -item.cantidad, TipoMovimiento.TRASLADO_SALIDA,
            observacion=f"Traslado #{traslado.numero}", sede_contraparte_id=traslado.sede_destino_id, traslado_id=traslado.id,
        ))
        ops.append(inventario_service.Operacion(
            traslado.sede_destino_id, producto, item.cantidad, TipoMovimiento.TRASLADO_ENTRADA,
            observacion=f"Traslado #{traslado.numero}", sede_contraparte_id=traslado.sede_origen_id, traslado_id=traslado.id,
        ))
    _, alertas = await inventario_service.aplicar_lote(db, empresa_id=ctx.empresa_id, usuario_id=ctx.usuario_id, operaciones=ops, fecha=ahora)
    await auditoria_service.registrar(
        db, modulo="traslados", accion="confirmar", ctx=ctx, entidad="traslado", entidad_id=traslado.id,
        sede_id=traslado.sede_destino_id,
        detalle={"numero": traslado.numero, "unidades": sum(i.cantidad for i in traslado.items), "alertas": alertas},
    )
    await db.commit()
    await db.refresh(traslado)
    return traslado


# ------------------------------------------------------------------------------ consultas


async def listar_traslados(
    db: AsyncSession,
    ctx: Contexto,
    pag: ParametrosPagina,
    *,
    sede_id: int | None,
    estado: str | None,
    desde: date | None,
    hasta: date | None,
    numero: int | None,
) -> tuple[list[TrasladoResumen], int]:
    condiciones = [Traslado.empresa_id == ctx.empresa_id]
    autorizadas = ctx.sedes_autorizadas()
    if autorizadas is not None:
        condiciones.append(or_(Traslado.sede_origen_id.in_(autorizadas), Traslado.sede_destino_id.in_(autorizadas)))
    if sede_id:
        if autorizadas is not None and sede_id not in autorizadas:
            raise SinPermiso("No tienes acceso a esta sede")
        condiciones.append(or_(Traslado.sede_origen_id == sede_id, Traslado.sede_destino_id == sede_id))
    if estado:
        condiciones.append(Traslado.estado == estado)
    if desde:
        condiciones.append(func.date(Traslado.solicitado_en) >= desde)
    if hasta:
        condiciones.append(func.date(Traslado.solicitado_en) <= hasta)
    if numero:
        condiciones.append(Traslado.numero == numero)
    total = await db.scalar(select(func.count()).select_from(Traslado).where(*condiciones)) or 0
    filas = (
        await db.scalars(
            select(Traslado).where(*condiciones).order_by(Traslado.solicitado_en.desc(), Traslado.id.desc())
            .offset(pag.offset).limit(pag.tamano)
        )
    ).all()
    return await resumenes(db, list(filas)), total


async def _nombres_usuarios(db: AsyncSession, ids: set[int]) -> dict[int, str]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    return {i: n for i, n in (await db.execute(select(Usuario.id, Usuario.nombre).where(Usuario.id.in_(ids)))).all()}


async def resumenes(db: AsyncSession, traslados: list[Traslado]) -> list[TrasladoResumen]:
    if not traslados:
        return []
    sedes = {s.id: s for s in (await db.scalars(select(Sede).where(Sede.id.in_(
        {t.sede_origen_id for t in traslados} | {t.sede_destino_id for t in traslados})))).all()}
    usuarios = await _nombres_usuarios(db, {t.solicitado_por for t in traslados})
    return [
        TrasladoResumen(
            id=t.id, numero=t.numero, estado=t.estado, origen=SedeResumen.model_validate(sedes[t.sede_origen_id]),
            destino=SedeResumen.model_validate(sedes[t.sede_destino_id]), unidades=sum(i.cantidad for i in t.items),
            lineas=len(t.items), observacion=t.observacion, solicitado_en=t.solicitado_en,
            solicitado_por_nombre=usuarios.get(t.solicitado_por), recomendacion_id=t.recomendacion_id,
        )
        for t in traslados
    ]


def acciones_disponibles(ctx: Contexto, t: Traslado) -> list[str]:
    acciones = []
    if t.estado == EstadoTraslado.SOLICITADO and ctx.tiene("traslados.aprobar") and _alcanza(ctx, t.sede_origen_id):
        acciones += ["aprobar", "rechazar"]
    if t.estado == EstadoTraslado.APROBADO and ctx.tiene("traslados.confirmar") and _alcanza(ctx, t.sede_destino_id):
        acciones.append("confirmar")
    if t.estado in PENDIENTES and ctx.tiene_alguno("traslados.solicitar", "traslados.aprobar"):
        acciones.append("cancelar")
    return acciones


async def detalle(db: AsyncSession, ctx: Contexto, traslado: Traslado) -> TrasladoDetalle:
    base = (await resumenes(db, [traslado]))[0]
    productos = {p.id: p for p in (await db.scalars(select(Producto).where(Producto.id.in_([i.producto_id for i in traslado.items])))).all()}
    existencias = {
        (s, p): c
        for s, p, c in (
            await db.execute(
                select(InventarioSede.sede_id, InventarioSede.producto_id, InventarioSede.cantidad).where(
                    InventarioSede.sede_id.in_([traslado.sede_origen_id, traslado.sede_destino_id]),
                    InventarioSede.producto_id.in_(list(productos)),
                )
            )
        ).all()
    }
    nombres = await _nombres_usuarios(db, {traslado.aprobado_por, traslado.confirmado_por, traslado.cerrado_por})
    return TrasladoDetalle(
        **base.model_dump(),
        items=[
            TrasladoItemSalida(
                producto=ProductoResumen.model_validate(productos[i.producto_id]), cantidad=i.cantidad,
                existencias_origen=existencias.get((traslado.sede_origen_id, i.producto_id), 0),
                existencias_destino=existencias.get((traslado.sede_destino_id, i.producto_id), 0),
            )
            for i in traslado.items
        ],
        aprobado_por_nombre=nombres.get(traslado.aprobado_por), aprobado_en=traslado.aprobado_en,
        confirmado_por_nombre=nombres.get(traslado.confirmado_por), confirmado_en=traslado.confirmado_en,
        cerrado_por_nombre=nombres.get(traslado.cerrado_por), cerrado_en=traslado.cerrado_en,
        motivo_cierre=traslado.motivo_cierre, acciones=acciones_disponibles(ctx, traslado),
    )
