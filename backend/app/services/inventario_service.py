"""Motor de existencias: entradas, salidas, ajustes, niveles y consultas (RF-015 a RF-019, RF-024).

Garantías (RNF-005, RNF-006, RNF-007):
 * ``inventario_sede`` es la ÚNICA fuente de existencias. El consolidado se calcula sumando.
 * Cada cambio de existencias es una sola sentencia atómica ``UPDATE ... SET cantidad = cantidad + :d
   WHERE cantidad + :d >= 0 RETURNING``: dos salidas simultáneas nunca dejan el stock en negativo ni
   se pisan, sin necesidad de bloqueos largos.
 * Cada cambio genera un ``Movimiento`` inmutable con saldo anterior y posterior, en la misma transacción.
 * Las operaciones con varias líneas se aplican en orden (sede, producto) para evitar interbloqueos.
 * Las alertas se re-evalúan dentro de la misma transacción.
"""

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.acceso import Contexto
from app.core.exceptions import ExistenciasInsuficientes, NoEncontrado, ReglaNegocio
from app.core.niveles import clasificar_stock, sql_estado_stock
from app.core.sql import insertar, siguiente_secuencia
from app.core.tiempo import ahora_utc, fin_de_dia_utc, inicio_de_dia_utc
from app.models.catalogo import Categoria, Producto
from app.models.enums import TipoMovimiento
from app.models.inventario import EntradaInventario, EntradaObservacion, InventarioSede, Movimiento
from app.models.operaciones import Traslado, Venta
from app.models.sede import Sede
from app.models.usuario import Usuario
from app.schemas.catalogo import ProductoResumen
from app.schemas.comunes import ParametrosPagina
from app.schemas.inventario import (
    AjusteCrear,
    ConsolidadoFila,
    DesgloseSede,
    EntradaCrear,
    InventarioFila,
    MovimientoSalida,
    NivelesActualizar,
    SalidaCrear,
)
from app.schemas.sede import SedeResumen
from app.services import alertas_service, auditoria_service
from app.services.alcance import obtener_sede_autorizada, resolver_filtro_sede

# --------------------------------------------------------------------------- operación atómica


@dataclass
class Operacion:
    """Un cambio de existencias a aplicar (``delta`` > 0 entra, < 0 sale)."""

    sede_id: int
    producto: Producto
    delta: int
    tipo: str
    motivo: str | None = None
    observacion: str | None = None
    sede_contraparte_id: int | None = None
    venta_id: int | None = None
    traslado_id: int | None = None
    entrada_id: int | None = None


async def _asegurar_fila(db: AsyncSession, empresa_id: int, sede_id: int, producto_id: int) -> None:
    await db.execute(
        insertar(db, InventarioSede)
        .values(empresa_id=empresa_id, sede_id=sede_id, producto_id=producto_id, cantidad=0, stock_minimo=0)
        .on_conflict_do_nothing(index_elements=["sede_id", "producto_id"])
    )


async def aplicar_movimiento(
    db: AsyncSession, *, empresa_id: int, usuario_id: int, fecha: datetime, operacion: Operacion
) -> Movimiento:
    """Aplica UN cambio de existencias y registra su movimiento. Lanza ``ExistenciasInsuficientes``."""
    if operacion.delta == 0:
        raise ReglaNegocio("La cantidad no puede ser cero", codigo="cantidad_cero")
    sede_id, producto = operacion.sede_id, operacion.producto
    if operacion.delta > 0:
        await _asegurar_fila(db, empresa_id, sede_id, producto.id)
    resultado = await db.execute(
        update(InventarioSede)
        .where(
            InventarioSede.sede_id == sede_id,
            InventarioSede.producto_id == producto.id,
            InventarioSede.empresa_id == empresa_id,
            InventarioSede.cantidad + operacion.delta >= 0,
        )
        .values(cantidad=InventarioSede.cantidad + operacion.delta, updated_at=func.now())
        .returning(InventarioSede.cantidad)
    )
    saldo = resultado.scalar_one_or_none()
    if saldo is None:
        disponibles = (
            await db.scalar(
                select(InventarioSede.cantidad).where(
                    InventarioSede.sede_id == sede_id, InventarioSede.producto_id == producto.id
                )
            )
            or 0
        )
        sede = await db.get(Sede, sede_id)
        raise ExistenciasInsuficientes(
            f"Existencias insuficientes de «{producto.nombre}» en {sede.nombre if sede else 'la sede'}: "
            f"hay {disponibles} y se necesitan {-operacion.delta}",
            extra={"producto_id": producto.id, "disponibles": int(disponibles), "solicitadas": -operacion.delta},
        )
    movimiento = Movimiento(
        empresa_id=empresa_id, sede_id=sede_id, producto_id=producto.id, tipo=operacion.tipo, motivo=operacion.motivo,
        delta=operacion.delta, saldo_anterior=saldo - operacion.delta, saldo_posterior=saldo,
        sede_contraparte_id=operacion.sede_contraparte_id, usuario_id=usuario_id, fecha=fecha,
        observacion=operacion.observacion, venta_id=operacion.venta_id, traslado_id=operacion.traslado_id,
        entrada_id=operacion.entrada_id,
    )
    db.add(movimiento)
    return movimiento


async def aplicar_lote(
    db: AsyncSession, *, empresa_id: int, usuario_id: int, operaciones: list[Operacion], fecha: datetime | None = None
) -> tuple[list[Movimiento], dict[str, int]]:
    """Aplica varias operaciones en un orden determinista (sede, producto) y re-evalúa las alertas.

    El orden único evita interbloqueos cuando dos transacciones tocan las mismas filas en sentidos opuestos."""
    fecha = fecha or ahora_utc()
    movimientos: list[Movimiento] = []
    for op in sorted(operaciones, key=lambda o: (o.sede_id, o.producto.id)):
        movimientos.append(await aplicar_movimiento(db, empresa_id=empresa_id, usuario_id=usuario_id, fecha=fecha, operacion=op))
    await db.flush()
    alertas = await alertas_service.sincronizar(db, empresa_id, {(o.sede_id, o.producto.id) for o in operaciones})
    return movimientos, alertas


# --------------------------------------------------------------------------- validaciones


async def productos_de_empresa(
    db: AsyncSession, empresa_id: int, ids: list[int], *, requerir_activos: bool
) -> dict[int, Producto]:
    productos = {
        p.id: p
        for p in (await db.scalars(select(Producto).where(Producto.empresa_id == empresa_id, Producto.id.in_(ids)))).all()
    }
    faltantes = [i for i in ids if i not in productos]
    if faltantes:
        raise NoEncontrado(f"El producto {faltantes[0]} no existe", extra={"producto_id": faltantes[0]})
    if requerir_activos:
        inactivo = next((p for p in productos.values() if not p.activo), None)
        if inactivo:
            raise ReglaNegocio(
                f"El producto «{inactivo.nombre}» está inhabilitado y no admite esta operación", codigo="producto_inactivo"
            )
    return productos


# --------------------------------------------------------------------------- operaciones


async def registrar_entrada(db: AsyncSession, ctx: Contexto, datos: EntradaCrear):
    sede = await obtener_sede_autorizada(db, ctx, datos.sede_id, requerir_activa=True)
    productos = await productos_de_empresa(db, ctx.empresa_id, [i.producto_id for i in datos.items], requerir_activos=True)
    fecha = ahora_utc()
    # Cabecera de la entrada: agrupa las líneas y es el punto de anclaje de las observaciones y de las no
    # conformidades. Las existencias siguen cambiando SOLO a través de los movimientos de abajo.
    entrada = EntradaInventario(
        empresa_id=ctx.empresa_id, sede_id=sede.id, numero=await siguiente_secuencia(db, ctx.empresa_id, "entrada"),
        motivo=datos.motivo, usuario_id=ctx.usuario_id, fecha=fecha,
    )
    db.add(entrada)
    await db.flush()
    if datos.observacion:
        db.add(EntradaObservacion(entrada_id=entrada.id, usuario_id=ctx.usuario_id, fecha=fecha, contenido=datos.observacion))
    ops = [
        Operacion(
            sede.id, productos[i.producto_id], i.cantidad, TipoMovimiento.ENTRADA, datos.motivo, datos.observacion,
            entrada_id=entrada.id,
        )
        for i in datos.items
    ]
    movs, alertas = await aplicar_lote(db, empresa_id=ctx.empresa_id, usuario_id=ctx.usuario_id, operaciones=ops, fecha=fecha)
    await auditoria_service.registrar(
        db, modulo="inventario", accion="entrada", ctx=ctx, entidad="entrada", entidad_id=entrada.id, sede_id=sede.id,
        detalle={"numero": entrada.numero, "motivo": datos.motivo,
                 "lineas": [{"producto": o.producto.codigo, "cantidad": o.delta} for o in ops]},
    )
    await db.commit()
    return movs, alertas


async def registrar_salida(db: AsyncSession, ctx: Contexto, datos: SalidaCrear):
    sede = await obtener_sede_autorizada(db, ctx, datos.sede_id, requerir_activa=True)
    productos = await productos_de_empresa(db, ctx.empresa_id, [i.producto_id for i in datos.items], requerir_activos=False)
    ops = [
        Operacion(sede.id, productos[i.producto_id], -i.cantidad, TipoMovimiento.SALIDA, datos.motivo, datos.observacion)
        for i in datos.items
    ]
    movs, alertas = await aplicar_lote(db, empresa_id=ctx.empresa_id, usuario_id=ctx.usuario_id, operaciones=ops)
    await auditoria_service.registrar(
        db, modulo="inventario", accion="salida", ctx=ctx, entidad="sede", entidad_id=sede.id, sede_id=sede.id,
        detalle={"motivo": datos.motivo, "lineas": [{"producto": o.producto.codigo, "cantidad": -o.delta} for o in ops]},
    )
    await db.commit()
    return movs, alertas


async def ajustar(db: AsyncSession, ctx: Contexto, datos: AjusteCrear):
    sede = await obtener_sede_autorizada(db, ctx, datos.sede_id, requerir_activa=True)
    producto = (await productos_de_empresa(db, ctx.empresa_id, [datos.producto_id], requerir_activos=False))[datos.producto_id]
    await _asegurar_fila(db, ctx.empresa_id, sede.id, producto.id)
    # Bloquea la fila (PostgreSQL) para que el cálculo de la diferencia no se mezcle con otro movimiento.
    actual = await db.scalar(
        select(InventarioSede.cantidad)
        .where(InventarioSede.sede_id == sede.id, InventarioSede.producto_id == producto.id)
        .with_for_update()
    )
    delta = datos.cantidad_real - int(actual or 0)
    if delta == 0:
        raise ReglaNegocio(
            "El conteo coincide con las existencias registradas: no hay nada que ajustar", codigo="sin_diferencia"
        )
    op = Operacion(sede.id, producto, delta, TipoMovimiento.AJUSTE, datos.motivo, datos.observacion)
    movs, alertas = await aplicar_lote(db, empresa_id=ctx.empresa_id, usuario_id=ctx.usuario_id, operaciones=[op])
    await auditoria_service.registrar(
        db, modulo="inventario", accion="ajuste", ctx=ctx, entidad="producto", entidad_id=producto.id, sede_id=sede.id,
        detalle={"producto": producto.codigo, "antes": int(actual or 0), "despues": datos.cantidad_real,
                 "motivo": datos.motivo, "observacion": datos.observacion},
    )
    await db.commit()
    return movs, alertas


async def configurar_niveles(db: AsyncSession, ctx: Contexto, datos: NivelesActualizar) -> InventarioSede:
    sede = await obtener_sede_autorizada(db, ctx, datos.sede_id)
    producto = (await productos_de_empresa(db, ctx.empresa_id, [datos.producto_id], requerir_activos=False))[datos.producto_id]
    await _asegurar_fila(db, ctx.empresa_id, sede.id, producto.id)
    fila = await db.scalar(
        select(InventarioSede)
        .where(InventarioSede.sede_id == sede.id, InventarioSede.producto_id == producto.id)
        .execution_options(populate_existing=True)
    )
    antes = {"stock_minimo": fila.stock_minimo, "stock_maximo": fila.stock_maximo}
    fila.stock_minimo, fila.stock_maximo = datos.stock_minimo, datos.stock_maximo
    await db.flush()
    await alertas_service.sincronizar(db, ctx.empresa_id, [(sede.id, producto.id)])
    await auditoria_service.registrar(
        db, modulo="inventario", accion="configurar_niveles", ctx=ctx, entidad="producto", entidad_id=producto.id,
        sede_id=sede.id,
        detalle={"producto": producto.codigo, "antes": antes,
                 "despues": {"stock_minimo": datos.stock_minimo, "stock_maximo": datos.stock_maximo}},
    )
    await db.commit()
    await db.refresh(fila)
    return fila


# --------------------------------------------------------------------------- consultas


def _resolver_sede_unica(ctx: Contexto, sede_id: int | None) -> int:
    if sede_id is None:
        if ctx.limitado_a_sede and ctx.sede_id:
            return ctx.sede_id
        raise ReglaNegocio("Indica la sede que quieres consultar", codigo="sede_requerida")
    return sede_id


async def listar_inventario(
    db: AsyncSession,
    ctx: Contexto,
    pag: ParametrosPagina,
    *,
    sede_id: int | None,
    q: str | None,
    categoria_id: int | None,
    estado: str | None,
) -> tuple[list[InventarioFila], int, Sede]:
    sede = await obtener_sede_autorizada(db, ctx, _resolver_sede_unica(ctx, sede_id))
    cantidad = func.coalesce(InventarioSede.cantidad, 0)
    minimo = func.coalesce(InventarioSede.stock_minimo, 0)
    base = (
        select(Producto, Categoria.nombre, InventarioSede, sql_estado_stock(cantidad, minimo, InventarioSede.stock_maximo).label("estado"))
        .join(Categoria, Categoria.id == Producto.categoria_id)
        .outerjoin(InventarioSede, (InventarioSede.producto_id == Producto.id) & (InventarioSede.sede_id == sede.id))
        .where(Producto.empresa_id == ctx.empresa_id, (Producto.activo.is_(True)) | (cantidad > 0))
    )
    if q:
        patron = f"%{q.strip().lower()}%"
        base = base.where(func.lower(Producto.nombre).like(patron) | func.lower(Producto.codigo).like(patron))
    if categoria_id:
        base = base.where(Producto.categoria_id == categoria_id)
    if estado:
        base = base.where(sql_estado_stock(cantidad, minimo, InventarioSede.stock_maximo) == estado)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    filas = (await db.execute(base.order_by(func.lower(Producto.nombre)).offset(pag.offset).limit(pag.tamano))).all()
    salida = []
    for producto, categoria, inv, est in filas:
        cant = inv.cantidad if inv else 0
        salida.append(
            InventarioFila(
                producto=ProductoResumen.model_validate(producto), categoria=categoria, producto_activo=producto.activo,
                cantidad=cant, stock_minimo=inv.stock_minimo if inv else 0, stock_maximo=inv.stock_maximo if inv else None,
                estado=est, costo=producto.costo, valor=(producto.costo * cant) if producto.costo is not None else None,
                actualizado_en=inv.updated_at if inv else None,
            )
        )
    return salida, total, sede


async def consolidado(
    db: AsyncSession,
    ctx: Contexto,
    pag: ParametrosPagina,
    *,
    q: str | None,
    categoria_id: int | None,
    solo_con_existencias: bool,
) -> tuple[list[ConsolidadoFila], int]:
    autorizadas = ctx.sedes_autorizadas()
    sub = select(InventarioSede.producto_id, func.sum(InventarioSede.cantidad).label("total")).where(
        InventarioSede.empresa_id == ctx.empresa_id
    )
    if autorizadas is not None:
        sub = sub.where(InventarioSede.sede_id.in_(autorizadas))
    sub = sub.group_by(InventarioSede.producto_id).subquery()
    total_col = func.coalesce(sub.c.total, 0)
    base = (
        select(Producto, Categoria.nombre, total_col.label("total"))
        .join(Categoria, Categoria.id == Producto.categoria_id)
        .outerjoin(sub, sub.c.producto_id == Producto.id)
        .where(Producto.empresa_id == ctx.empresa_id, (Producto.activo.is_(True)) | (total_col > 0))
    )
    if q:
        patron = f"%{q.strip().lower()}%"
        base = base.where(func.lower(Producto.nombre).like(patron) | func.lower(Producto.codigo).like(patron))
    if categoria_id:
        base = base.where(Producto.categoria_id == categoria_id)
    if solo_con_existencias:
        base = base.where(total_col > 0)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    filas = (await db.execute(base.order_by(func.lower(Producto.nombre)).offset(pag.offset).limit(pag.tamano))).all()

    ids = [p.id for p, _, _ in filas]
    desglose: dict[int, list[DesgloseSede]] = {i: [] for i in ids}
    if ids:
        consulta = (
            select(InventarioSede, Sede.nombre)
            .join(Sede, Sede.id == InventarioSede.sede_id)
            .where(InventarioSede.empresa_id == ctx.empresa_id, InventarioSede.producto_id.in_(ids))
            .order_by(Sede.nombre)
        )
        if autorizadas is not None:
            consulta = consulta.where(InventarioSede.sede_id.in_(autorizadas))
        for inv, nombre_sede in (await db.execute(consulta)).all():
            desglose[inv.producto_id].append(
                DesgloseSede(
                    sede_id=inv.sede_id, sede=nombre_sede, cantidad=inv.cantidad, stock_minimo=inv.stock_minimo,
                    stock_maximo=inv.stock_maximo, estado=clasificar_stock(inv.cantidad, inv.stock_minimo, inv.stock_maximo),
                )
            )
    salida = []
    for producto, categoria, tot in filas:
        sedes = desglose[producto.id]
        tot = int(tot or 0)
        salida.append(
            ConsolidadoFila(
                producto=ProductoResumen.model_validate(producto), categoria=categoria, producto_activo=producto.activo,
                total=tot, costo=producto.costo, valor=(producto.costo * tot) if producto.costo is not None else None,
                sedes_en_alerta=sum(1 for s in sedes if s.estado in ("agotado", "bajo")), sedes=sedes,
            )
        )
    return salida, total


# --------------------------------------------------------------------------- movimientos


async def movimientos_a_salidas(db: AsyncSession, movimientos: list[Movimiento]) -> list[MovimientoSalida]:
    if not movimientos:
        return []
    productos = {p.id: p for p in (await db.scalars(select(Producto).where(Producto.id.in_({m.producto_id for m in movimientos})))).all()}
    sede_ids = {m.sede_id for m in movimientos} | {m.sede_contraparte_id for m in movimientos if m.sede_contraparte_id}
    sedes = {s.id: s for s in (await db.scalars(select(Sede).where(Sede.id.in_(sede_ids)))).all()}
    usuarios = {u.id: u.nombre for u in (await db.execute(select(Usuario.id, Usuario.nombre).where(Usuario.id.in_({m.usuario_id for m in movimientos})))).all()}
    venta_ids = {m.venta_id for m in movimientos if m.venta_id}
    traslado_ids = {m.traslado_id for m in movimientos if m.traslado_id}
    ventas = {i: n for i, n in (await db.execute(select(Venta.id, Venta.numero).where(Venta.id.in_(venta_ids)))).all()} if venta_ids else {}
    traslados = {i: n for i, n in (await db.execute(select(Traslado.id, Traslado.numero).where(Traslado.id.in_(traslado_ids)))).all()} if traslado_ids else {}
    entrada_ids = {m.entrada_id for m in movimientos if m.entrada_id}
    entradas = {i: n for i, n in (await db.execute(select(EntradaInventario.id, EntradaInventario.numero).where(EntradaInventario.id.in_(entrada_ids)))).all()} if entrada_ids else {}
    return [
        MovimientoSalida(
            id=m.id, fecha=m.fecha, tipo=m.tipo, motivo=m.motivo, delta=m.delta, saldo_anterior=m.saldo_anterior,
            saldo_posterior=m.saldo_posterior, observacion=m.observacion,
            producto=ProductoResumen.model_validate(productos[m.producto_id]),
            sede=SedeResumen.model_validate(sedes[m.sede_id]),
            sede_contraparte=SedeResumen.model_validate(sedes[m.sede_contraparte_id]) if m.sede_contraparte_id else None,
            usuario_id=m.usuario_id, usuario_nombre=usuarios.get(m.usuario_id),
            venta_id=m.venta_id, venta_numero=ventas.get(m.venta_id), traslado_id=m.traslado_id,
            traslado_numero=traslados.get(m.traslado_id),
            entrada_id=m.entrada_id, entrada_numero=entradas.get(m.entrada_id),
        )
        for m in movimientos
    ]


def condiciones_movimientos(
    ctx: Contexto,
    *,
    sede_id: int | None,
    producto_id: int | None,
    tipo: str | None,
    desde: date | None,
    hasta: date | None,
    usuario_id: int | None,
) -> list:
    sede_ids = resolver_filtro_sede(ctx, sede_id)
    condiciones = [Movimiento.empresa_id == ctx.empresa_id]
    if sede_ids is not None:
        condiciones.append(Movimiento.sede_id.in_(sede_ids))
    if producto_id:
        condiciones.append(Movimiento.producto_id == producto_id)
    if tipo:
        condiciones.append(Movimiento.tipo == tipo)
    if usuario_id:
        condiciones.append(Movimiento.usuario_id == usuario_id)
    if desde:
        condiciones.append(Movimiento.fecha >= inicio_de_dia_utc(desde))
    if hasta:
        condiciones.append(Movimiento.fecha < fin_de_dia_utc(hasta))
    return condiciones


async def listar_movimientos(
    db: AsyncSession,
    ctx: Contexto,
    pag: ParametrosPagina,
    **filtros,
) -> tuple[list[MovimientoSalida], int]:
    condiciones = condiciones_movimientos(ctx, **filtros)
    total = await db.scalar(select(func.count()).select_from(Movimiento).where(*condiciones)) or 0
    filas = (
        await db.scalars(
            select(Movimiento).where(*condiciones).order_by(Movimiento.fecha.desc(), Movimiento.id.desc())
            .offset(pag.offset).limit(pag.tamano)
        )
    ).all()
    return await movimientos_a_salidas(db, list(filas)), total
