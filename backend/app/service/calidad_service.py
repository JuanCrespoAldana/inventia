"""Calidad: no conformidades (NC) y garantías.

Reglas de fondo:
 * Registrar una NC o una garantía NO toca existencias ni crea movimientos: son registros de seguimiento. Si
   la solución exige ajustar inventario, se hace aparte con las operaciones normales de inventario.
 * Una NC puede nacer de una entrada de mercancía (y de una observación concreta de esa entrada): se guarda el
   vínculo, así no hay que volver a digitar lo que ya se dijo al recibir.
 * Las observaciones y los cambios de estado se acumulan en un historial inmodificable (fecha, usuario,
   contenido); nunca se sobrescribe un campo único de observaciones.
 * Ver/crear/observar se limitan a las sedes de la persona; cambiar estados, asignar responsables y cerrar es
   de quien tenga ``calidad.gestionar``."""


from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dto.calidad_dto import (
    ConteoEstado,
    EntradaVinculo,
    EventoSalida,
    GarantiaCrear,
    GarantiaDetalle,
    GarantiaGestionar,
    GarantiaResumen,
    NoConformidadCrear,
    NoConformidadDetalle,
    NoConformidadGestionar,
    NoConformidadResumen,
    ObservacionCrear,
    ResumenCalidad,
)
from app.dto.catalogo_dto import ProductoResumen
from app.dto.comunes_dto import ParametrosPagina
from app.dto.sede_dto import SedeResumen
from app.exception.excepciones import Conflicto, NoEncontrado, ReglaNegocio
from app.model.calidad import Garantia, GarantiaHistorial, NoConformidad, NoConformidadHistorial
from app.model.catalogo import Producto
from app.model.inventario import EntradaInventario, EntradaObservacion, Movimiento
from app.model.operaciones import Venta
from app.model.sede import Sede
from app.model.usuario import Usuario
from app.security.acceso import Contexto
from app.service import adjuntos_service, auditoria_service, entradas_service, inventario_service
from app.service.alcance import obtener_sede_autorizada, resolver_filtro_sede
from app.service.sig_util import nombres_usuarios
from app.specification.calidad_spec import condiciones_garantias, condiciones_no_conformidades
from app.util.sql import siguiente_secuencia
from app.util.tiempo import ahora_utc, hoy_local

ESTADOS_NC = ("reportado", "en_revision", "en_proceso_solucion", "resuelto", "cerrado")
ESTADOS_GARANTIA = ("reportada", "pendiente_revision", "enviada_proveedor", "aprobada", "rechazada", "solucionada", "cerrada")
ABIERTOS_NC = ("reportado", "en_revision", "en_proceso_solucion")
ABIERTOS_GARANTIA = ("reportada", "pendiente_revision", "enviada_proveedor", "aprobada")

# Transiciones de garantía permitidas (cerrada es final).
TRANSICIONES_GARANTIA: dict[str, tuple[str, ...]] = {
    "reportada": ("pendiente_revision", "enviada_proveedor", "rechazada", "cerrada"),
    "pendiente_revision": ("enviada_proveedor", "aprobada", "rechazada", "cerrada"),
    "enviada_proveedor": ("aprobada", "rechazada", "cerrada"),
    "aprobada": ("solucionada", "cerrada"),
    "rechazada": ("enviada_proveedor", "cerrada"),
    "solucionada": ("cerrada",),
    "cerrada": (),
}


def transicion_nc_valida(actual: str, nuevo: str) -> bool:
    """Las NC avanzan en orden; solo una NC «resuelta» puede reabrirse (volver a «en proceso de solución»)."""
    if actual == "cerrado" or actual == nuevo:
        return False
    if actual == "resuelto" and nuevo == "en_proceso_solucion":
        return True
    return ESTADOS_NC.index(nuevo) > ESTADOS_NC.index(actual)


# --------------------------------------------------------------------------- utilidades


async def _sede_del_registro(db: AsyncSession, ctx: Contexto, sede_id: int | None, entrada: EntradaInventario | None) -> Sede:
    if entrada is not None:
        if sede_id is not None and sede_id != entrada.sede_id:
            raise ReglaNegocio("La sede no coincide con la de la entrada seleccionada", codigo="sede_no_coincide")
        sede_id = entrada.sede_id
    elif sede_id is None:
        if ctx.limitado_a_sede and ctx.sede_id:
            sede_id = ctx.sede_id
        else:
            raise ReglaNegocio("Indica la sede donde ocurrió", codigo="sede_requerida")
    return await obtener_sede_autorizada(db, ctx, sede_id)


async def _entrada_con_producto(db: AsyncSession, ctx: Contexto, entrada_id: int, producto_id: int) -> EntradaInventario:
    entrada = await entradas_service.obtener_entrada(db, ctx, entrada_id)
    esta = await db.scalar(
        select(func.count()).select_from(Movimiento).where(Movimiento.entrada_id == entrada.id, Movimiento.producto_id == producto_id)
    )
    if not esta:
        raise ReglaNegocio("El producto no hace parte de la entrada seleccionada", codigo="producto_fuera_de_entrada")
    return entrada


async def _usuario_de_empresa(db: AsyncSession, ctx: Contexto, usuario_id: int) -> Usuario:
    usuario = await db.scalar(select(Usuario).where(Usuario.id == usuario_id, Usuario.empresa_id == ctx.empresa_id))
    if usuario is None or not usuario.activo:
        raise ReglaNegocio("El responsable no existe o está inhabilitado", codigo="responsable_invalido")
    return usuario


def _eventos(filas, nombres: dict[int, str]) -> list[EventoSalida]:
    return [
        EventoSalida(
            id=e.id, fecha=e.fecha, usuario_id=e.usuario_id, usuario_nombre=nombres.get(e.usuario_id), evento=e.evento,
            estado_anterior=e.estado_anterior, estado_nuevo=e.estado_nuevo, contenido=e.contenido,
        )
        for e in filas
    ]


async def _vinculos_entrada(db: AsyncSession, ids: set[int | None]) -> dict[int, EntradaVinculo]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    filas = (await db.execute(select(EntradaInventario.id, EntradaInventario.numero, EntradaInventario.fecha).where(EntradaInventario.id.in_(ids)))).all()
    return {i: EntradaVinculo(id=i, numero=n, fecha=f) for i, n, f in filas}


async def _productos_y_sedes(db: AsyncSession, registros) -> tuple[dict[int, Producto], dict[int, Sede]]:
    productos = {p.id: p for p in (await db.scalars(select(Producto).where(Producto.id.in_({r.producto_id for r in registros})))).all()}
    sedes = {s.id: s for s in (await db.scalars(select(Sede).where(Sede.id.in_({r.sede_id for r in registros})))).all()}
    return productos, sedes


async def _conteo_observaciones(db: AsyncSession, modelo, campo, ids: list[int]) -> dict[int, int]:
    if not ids:
        return {}
    return dict(
        (await db.execute(select(campo, func.count()).where(campo.in_(ids), modelo.contenido.is_not(None)).group_by(campo))).all()
    )


# --------------------------------------------------------------------------- no conformidades


async def obtener_nc(db: AsyncSession, ctx: Contexto, nc_id: int, *, bloquear: bool = False) -> NoConformidad:
    consulta = select(NoConformidad).where(NoConformidad.id == nc_id, NoConformidad.empresa_id == ctx.empresa_id)
    if bloquear:
        consulta = consulta.with_for_update()
    nc = await db.scalar(consulta)
    if nc is None:
        raise NoEncontrado("La no conformidad no existe")
    await obtener_sede_autorizada(db, ctx, nc.sede_id)
    return nc


async def crear_nc(db: AsyncSession, ctx: Contexto, datos: NoConformidadCrear) -> NoConformidad:
    ctx.exigir("calidad.reportar", "calidad.gestionar")
    producto = (await inventario_service.productos_de_empresa(db, ctx.empresa_id, [datos.producto_id], requerir_activos=False))[datos.producto_id]
    entrada = observacion = None
    if datos.entrada_id:
        entrada = await _entrada_con_producto(db, ctx, datos.entrada_id, producto.id)
        if datos.entrada_observacion_id:
            observacion = await db.scalar(
                select(EntradaObservacion).where(
                    EntradaObservacion.id == datos.entrada_observacion_id, EntradaObservacion.entrada_id == entrada.id
                )
            )
            if observacion is None:
                raise NoEncontrado("La observación no existe en esa entrada")
            if observacion.producto_id and observacion.producto_id != producto.id:
                raise ReglaNegocio("La observación seleccionada se refiere a otro producto de la entrada", codigo="observacion_de_otro_producto")
    sede = await _sede_del_registro(db, ctx, datos.sede_id, entrada)

    nc = NoConformidad(
        empresa_id=ctx.empresa_id, numero=await siguiente_secuencia(db, ctx.empresa_id, "no_conformidad"), sede_id=sede.id,
        producto_id=producto.id, referencia=datos.referencia, tipo=datos.tipo, descripcion=datos.descripcion,
        fecha_deteccion=datos.fecha_deteccion, cantidad_afectada=datos.cantidad_afectada, estado="reportado",
        proveedor=datos.proveedor, entrada_id=entrada.id if entrada else None,
        entrada_observacion_id=observacion.id if observacion else None, usuario_id=ctx.usuario_id,
    )
    db.add(nc)
    await db.flush()
    db.add(
        NoConformidadHistorial(
            no_conformidad_id=nc.id, usuario_id=ctx.usuario_id, evento="creacion", estado_nuevo="reportado",
            contenido=datos.observaciones,
        )
    )
    await auditoria_service.registrar(
        db, modulo="calidad", accion="reportar_nc", ctx=ctx, entidad="no_conformidad", entidad_id=nc.id, sede_id=sede.id,
        detalle={"numero": nc.numero, "producto": producto.codigo, "cantidad": nc.cantidad_afectada,
                 "entrada": entrada.numero if entrada else None},
    )
    await db.commit()
    await db.refresh(nc)
    return nc


async def resumenes_nc(db: AsyncSession, ncs: list[NoConformidad]) -> list[NoConformidadResumen]:
    if not ncs:
        return []
    productos, sedes = await _productos_y_sedes(db, ncs)
    nombres = await nombres_usuarios(db, {n.usuario_id for n in ncs} | {n.responsable_id for n in ncs})
    entradas = await _vinculos_entrada(db, {n.entrada_id for n in ncs})
    ids = [n.id for n in ncs]
    obs = await _conteo_observaciones(db, NoConformidadHistorial, NoConformidadHistorial.no_conformidad_id, ids)
    adj = await adjuntos_service.contar(db, "no_conformidad", ids)
    return [
        NoConformidadResumen(
            id=n.id, numero=n.numero, producto=ProductoResumen.model_validate(productos[n.producto_id]),
            sede=SedeResumen.model_validate(sedes[n.sede_id]), tipo=n.tipo, estado=n.estado,
            fecha_deteccion=n.fecha_deteccion, cantidad_afectada=n.cantidad_afectada, referencia=n.referencia,
            usuario_id=n.usuario_id, usuario_nombre=nombres.get(n.usuario_id),
            responsable_nombre=nombres.get(n.responsable_id) if n.responsable_id else None,
            entrada=entradas.get(n.entrada_id) if n.entrada_id else None, created_at=n.created_at,
            observaciones=int(obs.get(n.id, 0)), adjuntos=int(adj.get(n.id, 0)),
        )
        for n in ncs
    ]


async def listar_nc(db: AsyncSession, ctx: Contexto, pag: ParametrosPagina, **filtros) -> tuple[list[NoConformidadResumen], int]:
    condiciones = condiciones_no_conformidades(ctx, **filtros)
    total = await db.scalar(select(func.count()).select_from(NoConformidad).where(*condiciones)) or 0
    filas = (
        await db.scalars(
            select(NoConformidad).where(*condiciones)
            .order_by(NoConformidad.created_at.desc(), NoConformidad.id.desc()).offset(pag.offset).limit(pag.tamano)
        )
    ).all()
    return await resumenes_nc(db, list(filas)), total


async def detalle_nc(db: AsyncSession, ctx: Contexto, nc: NoConformidad) -> NoConformidadDetalle:
    base = (await resumenes_nc(db, [nc]))[0]
    filas = (
        await db.scalars(
            select(NoConformidadHistorial).where(NoConformidadHistorial.no_conformidad_id == nc.id)
            .order_by(NoConformidadHistorial.id)
        )
    ).all()
    nombres = await nombres_usuarios(db, {f.usuario_id for f in filas})
    origen = None
    if nc.entrada_observacion_id:
        origen = await db.scalar(select(EntradaObservacion.contenido).where(EntradaObservacion.id == nc.entrada_observacion_id))
    gestor = ctx.tiene("calidad.gestionar")
    puede_escribir = (gestor or ctx.tiene("calidad.reportar")) and nc.estado != "cerrado"
    return NoConformidadDetalle(
        **base.model_dump(),
        descripcion=nc.descripcion, proveedor=nc.proveedor, solucion=nc.solucion, responsable_id=nc.responsable_id,
        resuelta_en=nc.resuelta_en, cerrada_en=nc.cerrada_en, observacion_origen=origen,
        historial=_eventos(filas, nombres),
        archivos=await adjuntos_service.listar(db, "no_conformidad", nc.id, ver_usuario_id=ctx.usuario_id, es_gestor=gestor),
        puede_gestionar=gestor and nc.estado != "cerrado", puede_observar=puede_escribir, puede_adjuntar=puede_escribir,
    )


async def gestionar_nc(db: AsyncSession, ctx: Contexto, nc_id: int, datos: NoConformidadGestionar) -> NoConformidad:
    ctx.exigir("calidad.gestionar")
    nc = await obtener_nc(db, ctx, nc_id, bloquear=True)
    if nc.estado == "cerrado":
        raise Conflicto("La no conformidad está cerrada y no admite cambios", codigo="registro_cerrado")
    lineas: list[str] = [datos.comentario] if datos.comentario else []
    ahora = ahora_utc()
    anterior = nc.estado

    if datos.responsable_id is not None and datos.responsable_id != nc.responsable_id:
        responsable = await _usuario_de_empresa(db, ctx, datos.responsable_id)
        nc.responsable_id = responsable.id
        lineas.append(f"Responsable asignado: {responsable.nombre}")
    if datos.proveedor is not None and datos.proveedor != nc.proveedor:
        nc.proveedor = datos.proveedor
        lineas.append(f"Proveedor: {datos.proveedor}")
    if datos.solucion is not None and datos.solucion != nc.solucion:
        nc.solucion = datos.solucion
        lineas.append(f"Solución: {datos.solucion}")

    cambia_estado = datos.estado is not None and datos.estado != nc.estado
    if cambia_estado:
        if not transicion_nc_valida(nc.estado, datos.estado):
            raise ReglaNegocio(
                f"No se puede pasar de «{nc.estado}» a «{datos.estado}»: las no conformidades avanzan en orden",
                codigo="transicion_invalida",
            )
        if datos.estado in ("resuelto", "cerrado") and not nc.solucion:
            raise ReglaNegocio("Registra la solución antes de marcarla como resuelta o cerrada", codigo="solucion_requerida")
        nc.estado = datos.estado
        if datos.estado == "resuelto":
            nc.resuelta_en = ahora
        elif datos.estado == "cerrado":
            nc.cerrada_en = ahora
            nc.resuelta_en = nc.resuelta_en or ahora
        elif anterior == "resuelto":
            nc.resuelta_en = None  # reabierta
    elif datos.estado is not None and not lineas:
        raise ReglaNegocio("La no conformidad ya está en ese estado", codigo="sin_cambios")
    if not lineas and not cambia_estado:
        raise ReglaNegocio("No hay cambios que guardar", codigo="sin_cambios")

    db.add(
        NoConformidadHistorial(
            no_conformidad_id=nc.id, usuario_id=ctx.usuario_id,
            evento="estado" if cambia_estado else ("gestion" if len(lineas) > (1 if datos.comentario else 0) else "observacion"),
            estado_anterior=anterior if cambia_estado else None, estado_nuevo=nc.estado if cambia_estado else None,
            contenido="\n".join(lineas) or None,
        )
    )
    await auditoria_service.registrar(
        db, modulo="calidad", accion="gestionar_nc", ctx=ctx, entidad="no_conformidad", entidad_id=nc.id, sede_id=nc.sede_id,
        detalle={"numero": nc.numero, "antes": anterior, "despues": nc.estado},
    )
    await db.commit()
    await db.refresh(nc)
    return nc


async def observar_nc(db: AsyncSession, ctx: Contexto, nc_id: int, datos: ObservacionCrear) -> NoConformidad:
    ctx.exigir("calidad.reportar", "calidad.gestionar")
    nc = await obtener_nc(db, ctx, nc_id, bloquear=True)
    if nc.estado == "cerrado":
        raise Conflicto("La no conformidad está cerrada y no admite observaciones", codigo="registro_cerrado")
    db.add(NoConformidadHistorial(no_conformidad_id=nc.id, usuario_id=ctx.usuario_id, evento="observacion", contenido=datos.contenido))
    await auditoria_service.registrar(
        db, modulo="calidad", accion="observar_nc", ctx=ctx, entidad="no_conformidad", entidad_id=nc.id, sede_id=nc.sede_id,
        detalle={"numero": nc.numero},
    )
    await db.commit()
    await db.refresh(nc)
    return nc


# --------------------------------------------------------------------------- garantías


async def obtener_garantia(db: AsyncSession, ctx: Contexto, garantia_id: int, *, bloquear: bool = False) -> Garantia:
    consulta = select(Garantia).where(Garantia.id == garantia_id, Garantia.empresa_id == ctx.empresa_id)
    if bloquear:
        consulta = consulta.with_for_update()
    garantia = await db.scalar(consulta)
    if garantia is None:
        raise NoEncontrado("La garantía no existe")
    await obtener_sede_autorizada(db, ctx, garantia.sede_id)
    return garantia


async def crear_garantia(db: AsyncSession, ctx: Contexto, datos: GarantiaCrear) -> Garantia:
    ctx.exigir("calidad.reportar", "calidad.gestionar")
    producto = (await inventario_service.productos_de_empresa(db, ctx.empresa_id, [datos.producto_id], requerir_activos=False))[datos.producto_id]
    entrada = venta = None
    referencia = datos.documento_referencia
    if datos.entrada_id:
        entrada = await _entrada_con_producto(db, ctx, datos.entrada_id, producto.id)
        if datos.documento_tipo == "entrada_inventario":
            referencia = referencia or f"Entrada #{entrada.numero}"
    if datos.venta_id:
        venta = await db.scalar(select(Venta).where(Venta.id == datos.venta_id, Venta.empresa_id == ctx.empresa_id))
        if venta is None:
            raise NoEncontrado("La venta no existe")
        await obtener_sede_autorizada(db, ctx, venta.sede_id)
        if venta.estado != "registrada":
            raise ReglaNegocio("La venta está anulada: no respalda una garantía", codigo="venta_anulada")
        if not any(i.producto_id == producto.id for i in venta.items):
            raise ReglaNegocio("El producto no hace parte de esa venta", codigo="producto_fuera_de_venta")
        if datos.documento_tipo == "venta":
            referencia = referencia or f"Venta #{venta.numero}"
        if datos.sede_id and datos.sede_id != venta.sede_id:
            raise ReglaNegocio("La sede no coincide con la de la venta seleccionada", codigo="sede_no_coincide")
    sede = await _sede_del_registro(db, ctx, venta.sede_id if venta else datos.sede_id, None if venta else entrada)
    if venta and entrada and venta.sede_id != entrada.sede_id:
        raise ReglaNegocio("La entrada y la venta son de sedes distintas", codigo="sede_no_coincide")

    garantia = Garantia(
        empresa_id=ctx.empresa_id, numero=await siguiente_secuencia(db, ctx.empresa_id, "garantia"), sede_id=sede.id,
        producto_id=producto.id, cantidad=datos.cantidad, documento_tipo=datos.documento_tipo, documento_referencia=referencia,
        entrada_id=entrada.id if entrada else None, venta_id=venta.id if venta else None, fecha_compra=datos.fecha_compra,
        garantia_hasta=datos.garantia_hasta, fecha_reporte=datos.fecha_reporte or hoy_local(), defecto=datos.defecto,
        estado="reportada", proveedor=datos.proveedor, usuario_id=ctx.usuario_id,
    )
    db.add(garantia)
    await db.flush()
    db.add(
        GarantiaHistorial(
            garantia_id=garantia.id, usuario_id=ctx.usuario_id, evento="creacion", estado_nuevo="reportada", contenido=datos.observaciones
        )
    )
    await auditoria_service.registrar(
        db, modulo="calidad", accion="reportar_garantia", ctx=ctx, entidad="garantia", entidad_id=garantia.id, sede_id=sede.id,
        detalle={"numero": garantia.numero, "producto": producto.codigo, "cantidad": garantia.cantidad},
    )
    await db.commit()
    await db.refresh(garantia)
    return garantia


def _en_garantia(g: Garantia) -> bool | None:
    return None if g.garantia_hasta is None else g.fecha_reporte <= g.garantia_hasta


async def resumenes_garantia(db: AsyncSession, garantias: list[Garantia]) -> list[GarantiaResumen]:
    if not garantias:
        return []
    productos, sedes = await _productos_y_sedes(db, garantias)
    nombres = await nombres_usuarios(db, {g.usuario_id for g in garantias} | {g.responsable_id for g in garantias})
    ids = [g.id for g in garantias]
    obs = await _conteo_observaciones(db, GarantiaHistorial, GarantiaHistorial.garantia_id, ids)
    adj = await adjuntos_service.contar(db, "garantia", ids)
    return [
        GarantiaResumen(
            id=g.id, numero=g.numero, producto=ProductoResumen.model_validate(productos[g.producto_id]),
            sede=SedeResumen.model_validate(sedes[g.sede_id]), cantidad=g.cantidad, estado=g.estado,
            documento_tipo=g.documento_tipo, documento_referencia=g.documento_referencia, fecha_compra=g.fecha_compra,
            fecha_reporte=g.fecha_reporte, proveedor=g.proveedor, usuario_id=g.usuario_id,
            usuario_nombre=nombres.get(g.usuario_id),
            responsable_nombre=nombres.get(g.responsable_id) if g.responsable_id else None,
            en_garantia=_en_garantia(g), created_at=g.created_at, observaciones=int(obs.get(g.id, 0)),
            adjuntos=int(adj.get(g.id, 0)),
        )
        for g in garantias
    ]


async def listar_garantias(db: AsyncSession, ctx: Contexto, pag: ParametrosPagina, **filtros) -> tuple[list[GarantiaResumen], int]:
    condiciones = condiciones_garantias(ctx, **filtros)
    total = await db.scalar(select(func.count()).select_from(Garantia).where(*condiciones)) or 0
    filas = (
        await db.scalars(
            select(Garantia).where(*condiciones).order_by(Garantia.created_at.desc(), Garantia.id.desc())
            .offset(pag.offset).limit(pag.tamano)
        )
    ).all()
    return await resumenes_garantia(db, list(filas)), total


async def detalle_garantia(db: AsyncSession, ctx: Contexto, g: Garantia) -> GarantiaDetalle:
    base = (await resumenes_garantia(db, [g]))[0]
    filas = (
        await db.scalars(select(GarantiaHistorial).where(GarantiaHistorial.garantia_id == g.id).order_by(GarantiaHistorial.id))
    ).all()
    nombres = await nombres_usuarios(db, {f.usuario_id for f in filas})
    entradas = await _vinculos_entrada(db, {g.entrada_id})
    venta_numero = await db.scalar(select(Venta.numero).where(Venta.id == g.venta_id)) if g.venta_id else None
    gestor = ctx.tiene("calidad.gestionar")
    puede_escribir = (gestor or ctx.tiene("calidad.reportar")) and g.estado != "cerrada"
    return GarantiaDetalle(
        **base.model_dump(),
        defecto=g.defecto, garantia_hasta=g.garantia_hasta, entrada=entradas.get(g.entrada_id) if g.entrada_id else None,
        venta_id=g.venta_id, venta_numero=venta_numero, responsable_id=g.responsable_id,
        fecha_envio_proveedor=g.fecha_envio_proveedor, respuesta_proveedor=g.respuesta_proveedor,
        fecha_respuesta_proveedor=g.fecha_respuesta_proveedor, solucion=g.solucion, fecha_solucion=g.fecha_solucion,
        cerrada_en=g.cerrada_en, historial=_eventos(filas, nombres),
        archivos=await adjuntos_service.listar(db, "garantia", g.id, ver_usuario_id=ctx.usuario_id, es_gestor=gestor),
        puede_gestionar=gestor and g.estado != "cerrada", puede_observar=puede_escribir, puede_adjuntar=puede_escribir,
    )


async def gestionar_garantia(db: AsyncSession, ctx: Contexto, garantia_id: int, datos: GarantiaGestionar) -> Garantia:
    ctx.exigir("calidad.gestionar")
    g = await obtener_garantia(db, ctx, garantia_id, bloquear=True)
    if g.estado == "cerrada":
        raise Conflicto("La garantía está cerrada y no admite cambios", codigo="registro_cerrado")
    lineas: list[str] = [datos.comentario] if datos.comentario else []
    campos_cambiados = 0
    anterior = g.estado
    hoy = hoy_local()

    if datos.responsable_id is not None and datos.responsable_id != g.responsable_id:
        responsable = await _usuario_de_empresa(db, ctx, datos.responsable_id)
        g.responsable_id = responsable.id
        lineas.append(f"Responsable asignado: {responsable.nombre}")
        campos_cambiados += 1
    if datos.proveedor is not None and datos.proveedor != g.proveedor:
        g.proveedor = datos.proveedor
        lineas.append(f"Proveedor: {datos.proveedor}")
        campos_cambiados += 1
    if datos.fecha_envio_proveedor is not None and datos.fecha_envio_proveedor != g.fecha_envio_proveedor:
        g.fecha_envio_proveedor = datos.fecha_envio_proveedor
        lineas.append(f"Enviada al proveedor el {datos.fecha_envio_proveedor.isoformat()}")
        campos_cambiados += 1
    if datos.respuesta_proveedor is not None and datos.respuesta_proveedor != g.respuesta_proveedor:
        g.respuesta_proveedor = datos.respuesta_proveedor
        lineas.append(f"Respuesta del proveedor: {datos.respuesta_proveedor}")
        campos_cambiados += 1
    if datos.fecha_respuesta_proveedor is not None and datos.fecha_respuesta_proveedor != g.fecha_respuesta_proveedor:
        g.fecha_respuesta_proveedor = datos.fecha_respuesta_proveedor
        lineas.append(f"Respuesta recibida el {datos.fecha_respuesta_proveedor.isoformat()}")
        campos_cambiados += 1
    if datos.solucion is not None and datos.solucion != g.solucion:
        g.solucion = datos.solucion
        lineas.append(f"Solución: {datos.solucion}")
        campos_cambiados += 1
    if datos.fecha_solucion is not None and datos.fecha_solucion != g.fecha_solucion:
        g.fecha_solucion = datos.fecha_solucion
        campos_cambiados += 1

    cambia_estado = datos.estado is not None and datos.estado != g.estado
    if cambia_estado:
        nuevo = datos.estado
        if nuevo not in TRANSICIONES_GARANTIA[g.estado]:
            raise ReglaNegocio(f"No se puede pasar de «{g.estado}» a «{nuevo}»", codigo="transicion_invalida")
        if nuevo == "enviada_proveedor":
            if not g.proveedor:
                raise ReglaNegocio("Indica el proveedor al que se envía la garantía", codigo="proveedor_requerido")
            g.fecha_envio_proveedor = g.fecha_envio_proveedor or hoy
        elif nuevo in ("aprobada", "rechazada"):
            if not g.respuesta_proveedor:
                raise ReglaNegocio("Registra la respuesta del proveedor antes de aprobar o rechazar", codigo="respuesta_requerida")
            g.fecha_respuesta_proveedor = g.fecha_respuesta_proveedor or hoy
        elif nuevo == "solucionada":
            if not g.solucion:
                raise ReglaNegocio("Registra la solución antes de marcarla como solucionada", codigo="solucion_requerida")
            g.fecha_solucion = g.fecha_solucion or hoy
        elif nuevo == "cerrada":
            g.cerrada_en = ahora_utc()
        g.estado = nuevo
    elif datos.estado is not None and not lineas and not campos_cambiados:
        raise ReglaNegocio("La garantía ya está en ese estado", codigo="sin_cambios")
    if not cambia_estado and not lineas and not campos_cambiados:
        raise ReglaNegocio("No hay cambios que guardar", codigo="sin_cambios")

    solo_comentario = bool(datos.comentario) and len(lineas) == 1 and not campos_cambiados
    db.add(
        GarantiaHistorial(
            garantia_id=g.id, usuario_id=ctx.usuario_id,
            evento="estado" if cambia_estado else ("observacion" if solo_comentario else "gestion"),
            estado_anterior=anterior if cambia_estado else None, estado_nuevo=g.estado if cambia_estado else None,
            contenido="\n".join(lineas) or None,
        )
    )
    await auditoria_service.registrar(
        db, modulo="calidad", accion="gestionar_garantia", ctx=ctx, entidad="garantia", entidad_id=g.id, sede_id=g.sede_id,
        detalle={"numero": g.numero, "antes": anterior, "despues": g.estado},
    )
    await db.commit()
    await db.refresh(g)
    return g


async def observar_garantia(db: AsyncSession, ctx: Contexto, garantia_id: int, datos: ObservacionCrear) -> Garantia:
    ctx.exigir("calidad.reportar", "calidad.gestionar")
    g = await obtener_garantia(db, ctx, garantia_id, bloquear=True)
    if g.estado == "cerrada":
        raise Conflicto("La garantía está cerrada y no admite observaciones", codigo="registro_cerrado")
    db.add(GarantiaHistorial(garantia_id=g.id, usuario_id=ctx.usuario_id, evento="observacion", contenido=datos.contenido))
    await auditoria_service.registrar(
        db, modulo="calidad", accion="observar_garantia", ctx=ctx, entidad="garantia", entidad_id=g.id, sede_id=g.sede_id,
        detalle={"numero": g.numero},
    )
    await db.commit()
    await db.refresh(g)
    return g


# --------------------------------------------------------------------------- resumen


async def resumen(db: AsyncSession, ctx: Contexto, sede_id: int | None) -> ResumenCalidad:
    sede_ids = resolver_filtro_sede(ctx, sede_id)

    async def _contar(modelo, estados):
        cond = [modelo.empresa_id == ctx.empresa_id]
        if sede_ids is not None:
            cond.append(modelo.sede_id.in_(sede_ids))
        por_estado = dict((await db.execute(select(modelo.estado, func.count()).where(*cond).group_by(modelo.estado))).all())
        return [ConteoEstado(estado=e, total=int(por_estado.get(e, 0))) for e in estados]

    ncs = await _contar(NoConformidad, ESTADOS_NC)
    garantias = await _contar(Garantia, ESTADOS_GARANTIA)
    return ResumenCalidad(
        no_conformidades=ncs, garantias=garantias,
        no_conformidades_abiertas=sum(c.total for c in ncs if c.estado in ABIERTOS_NC),
        garantias_abiertas=sum(c.total for c in garantias if c.estado in ABIERTOS_GARANTIA),
    )
