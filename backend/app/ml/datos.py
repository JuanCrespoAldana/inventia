"""Extracción de las series de demanda desde la base de datos.

La demanda de un producto en una sede es la suma de unidades de sus ventas REGISTRADAS por día
local de negocio (las ventas anuladas no cuentan). Las salidas por pérdida, consumo interno o
traslado no son demanda. Los días en que la sede no tenía existencias se marcan: ese día no se
pudo vender aunque hubiese clientes, así que no se interpreta como «demanda cero».
"""

from collections import defaultdict
from datetime import date, timedelta

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.pipeline import SerieEntrada
from app.model.catalogo import Producto
from app.model.inventario import InventarioSede, Movimiento
from app.model.operaciones import Venta, VentaItem
from app.model.sede import Sede
from app.util.tiempo import a_fecha_local, inicio_de_dia_utc


async def cargar_series(
    db: AsyncSession,
    empresa_id: int,
    corte: date,
    *,
    historia_max_dias: int,
    limite_series: int,
    sede_id: int | None = None,
    producto_id: int | None = None,
) -> tuple[list[SerieEntrada], bool]:
    """Series diarias de todos los pares sede-producto activos de la empresa, hasta el día ``corte``
    (inclusive). Devuelve ``(series, truncado)``; ``truncado`` indica que se superó ``limite_series``."""
    consulta = (
        select(InventarioSede.sede_id, InventarioSede.producto_id, InventarioSede.cantidad)
        .join(Sede, Sede.id == InventarioSede.sede_id)
        .join(Producto, Producto.id == InventarioSede.producto_id)
        .where(InventarioSede.empresa_id == empresa_id, Sede.activa.is_(True), Producto.activo.is_(True))
        .order_by(InventarioSede.sede_id, InventarioSede.producto_id)
    )
    if sede_id is not None:
        consulta = consulta.where(InventarioSede.sede_id == sede_id)
    if producto_id is not None:
        consulta = consulta.where(InventarioSede.producto_id == producto_id)
    pares = [((s, p), int(c)) for s, p, c in (await db.execute(consulta.limit(limite_series + 1))).all()]
    truncado = len(pares) > limite_series
    pares = pares[:limite_series]
    if not pares:
        return [], False
    existencias = dict(pares)
    sedes = {s for (s, _), _ in pares}
    productos = {p for (_, p), _ in pares}

    ventana_ini = corte - timedelta(days=historia_max_dias - 1)
    inicio_utc = inicio_de_dia_utc(ventana_ini)

    primer_movimiento: dict[tuple[int, int], date] = {}
    filas = await db.execute(
        select(Movimiento.sede_id, Movimiento.producto_id, func.min(Movimiento.fecha))
        .where(Movimiento.empresa_id == empresa_id, Movimiento.sede_id.in_(sedes), Movimiento.producto_id.in_(productos))
        .group_by(Movimiento.sede_id, Movimiento.producto_id)
    )
    for s, p, f in filas.all():
        if (s, p) in existencias:
            primer_movimiento[(s, p)] = a_fecha_local(f)

    ventas: dict[tuple[int, int], dict[date, int]] = defaultdict(dict)
    filas = await db.execute(
        select(Venta.sede_id, VentaItem.producto_id, Venta.fecha_dia, func.sum(VentaItem.cantidad))
        .join(Venta, Venta.id == VentaItem.venta_id)
        .where(
            Venta.empresa_id == empresa_id, Venta.estado == "registrada", Venta.fecha_dia >= ventana_ini,
            Venta.fecha_dia <= corte, Venta.sede_id.in_(sedes), VentaItem.producto_id.in_(productos),
        )
        .group_by(Venta.sede_id, VentaItem.producto_id, Venta.fecha_dia)
    )
    for s, p, d, n in filas.all():
        ventas[(s, p)][d] = int(n)

    # Saldo de cierre por día, a partir de los movimientos de la ventana (el último de cada día).
    cierres: dict[tuple[int, int], dict[date, int]] = defaultdict(dict)
    saldo_inicial: dict[tuple[int, int], int] = {}
    filas = await db.execute(
        select(Movimiento.sede_id, Movimiento.producto_id, Movimiento.fecha, Movimiento.saldo_anterior, Movimiento.saldo_posterior)
        .where(
            Movimiento.empresa_id == empresa_id, Movimiento.fecha >= inicio_utc, Movimiento.sede_id.in_(sedes),
            Movimiento.producto_id.in_(productos),
        )
        .order_by(Movimiento.sede_id, Movimiento.producto_id, Movimiento.id)
    )
    for s, p, f, anterior, posterior in filas.all():
        clave = (s, p)
        if clave not in existencias:
            continue
        saldo_inicial.setdefault(clave, int(anterior))
        cierres[clave][a_fecha_local(f)] = int(posterior)  # al estar ordenado, queda el último del día

    series: list[SerieEntrada] = []
    for (s, p), actual in pares:
        primer = primer_movimiento.get((s, p))
        inicio = max(primer, ventana_ini) if primer else corte + timedelta(days=1)
        n = max((corte - inicio).days + 1, 0)
        unidades = np.zeros(n)
        sin_stock = np.zeros(n, dtype=bool)
        if n:
            por_dia = ventas.get((s, p), {})
            cierre_dia = cierres.get((s, p), {})
            saldo = saldo_inicial.get((s, p), actual)
            for i in range(n):
                dia = inicio + timedelta(days=i)
                unidades[i] = por_dia.get(dia, 0)
                apertura = saldo
                saldo = cierre_dia.get(dia, saldo)
                sin_stock[i] = apertura == 0 and saldo == 0 and unidades[i] == 0
        series.append(SerieEntrada(sede_id=s, producto_id=p, inicio=inicio, unidades=unidades, sin_existencias=sin_stock))
    return series, truncado
