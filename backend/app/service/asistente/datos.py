"""Consultas compartidas por las respuestas del asistente (existencias, ventas, enlaces)."""

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import func, select

from app.dto.asistente_dto import Enlace
from app.model.catalogo import Producto
from app.model.inventario import InventarioSede
from app.model.operaciones import Venta, VentaItem
from app.service.asistente.catalogo import NOMBRE_DE_RUTA, PERMISOS_DE_RUTA
from app.service.asistente.peticion import Peticion
from app.util import lenguaje as L
from app.util.niveles import sql_estado_stock

ESTADO_SQL = sql_estado_stock(InventarioSede.cantidad, InventarioSede.stock_minimo, InventarioSede.stock_maximo)


# ------------------------------------------------------------------------------------------------------ enlaces
def enlaces_a(p: Peticion, *rutas: str) -> list[Enlace]:
    """Enlaces a pantallas, solo a las que la persona puede abrir."""
    salida = []
    for ruta in rutas:
        permisos = PERMISOS_DE_RUTA.get(ruta, ())
        if not permisos or p.tiene(*permisos):
            salida.append(Enlace(etiqueta=f"Abrir {NOMBRE_DE_RUTA.get(ruta, ruta)}", ruta=ruta))
    return salida


# -------------------------------------------------------------------------------------------------- existencias
def cond_inventario(p: Peticion, *, solo_activos: bool = True) -> list:
    """Condiciones sobre ``InventarioSede`` unido a ``Producto``: empresa, sedes, producto y categoría."""
    c = [InventarioSede.empresa_id == p.ctx.empresa_id]
    if p.sede_ids is not None:
        c.append(InventarioSede.sede_id.in_(p.sede_ids))
    if p.producto_ids:
        c.append(InventarioSede.producto_id.in_(p.producto_ids))
    if p.categoria_ids:
        c.append(Producto.categoria_id.in_(p.categoria_ids))
    if solo_activos:
        c.append(Producto.activo.is_(True))
    return c


@dataclass
class TotalesInventario:
    unidades: int
    referencias: int  # productos distintos con existencias
    valor: float
    sin_costo: int  # referencias con existencias y sin costo registrado
    agotados: int
    bajos: int
    excesivos: int
    normales: int


async def totales_inventario(p: Peticion, *, agrupar_por=None) -> dict:
    """Totales de existencias. Con ``agrupar_por`` (una columna) devuelve ``{clave: TotalesInventario}``."""
    from sqlalchemy import case

    cant = InventarioSede.cantidad
    columnas = [
        func.coalesce(func.sum(cant), 0),
        func.count(func.distinct(case((cant > 0, InventarioSede.producto_id)))),
        func.coalesce(func.sum(case((Producto.costo.is_not(None), cant * Producto.costo), else_=0)), 0),
        func.count(func.distinct(case(((cant > 0) & Producto.costo.is_(None), InventarioSede.producto_id)))),
        func.coalesce(func.sum(case((ESTADO_SQL == "agotado", 1), else_=0)), 0),
        func.coalesce(func.sum(case((ESTADO_SQL == "bajo", 1), else_=0)), 0),
        func.coalesce(func.sum(case((ESTADO_SQL == "excesivo", 1), else_=0)), 0),
        func.coalesce(func.sum(case((ESTADO_SQL == "normal", 1), else_=0)), 0),
    ]
    consulta = (
        select(*([agrupar_por] if agrupar_por is not None else []), *columnas)
        .select_from(InventarioSede)
        .join(Producto, Producto.id == InventarioSede.producto_id)
        .where(*cond_inventario(p))
    )
    if agrupar_por is not None:
        filas = (await p.db.execute(consulta.group_by(agrupar_por))).all()
        return {f[0]: _totales(f[1:]) for f in filas}
    fila = (await p.db.execute(consulta)).one()
    return {None: _totales(fila)}


def _totales(f) -> TotalesInventario:
    return TotalesInventario(int(f[0]), int(f[1]), float(f[2]), int(f[3]), int(f[4]), int(f[5]), int(f[6]), int(f[7]))


# ------------------------------------------------------------------------------------------------------- ventas
def cond_ventas(p: Peticion, periodo: L.Periodo, *, estado: str | None = "registrada") -> list:
    c = [Venta.empresa_id == p.ctx.empresa_id, Venta.fecha_dia >= periodo.desde, Venta.fecha_dia <= periodo.hasta]
    if estado:
        c.append(Venta.estado == estado)
    if p.sede_ids is not None:
        c.append(Venta.sede_id.in_(p.sede_ids))
    if p.producto_ids:
        c.append(VentaItem.producto_id.in_(p.producto_ids))
    if p.categoria_ids:
        c.append(Producto.categoria_id.in_(p.categoria_ids))
    return c


def desde_ventas(consulta):
    """Une ventas con sus líneas y productos (las condiciones de producto y categoría lo necesitan)."""
    return consulta.select_from(Venta).join(VentaItem, VentaItem.venta_id == Venta.id).join(Producto, Producto.id == VentaItem.producto_id)


@dataclass
class TotalesVentas:
    ventas: int
    monto: float
    unidades: int

    @property
    def ticket(self) -> float:
        return self.monto / self.ventas if self.ventas else 0.0


async def totales_ventas(p: Peticion, periodo: L.Periodo, *, estado: str | None = "registrada") -> TotalesVentas:
    consulta = desde_ventas(
        select(func.count(func.distinct(Venta.id)), func.coalesce(func.sum(VentaItem.subtotal), 0), func.coalesce(func.sum(VentaItem.cantidad), 0))
    ).where(*cond_ventas(p, periodo, estado=estado))
    f = (await p.db.execute(consulta)).one()
    return TotalesVentas(int(f[0]), float(f[1]), int(f[2]))


async def periodo_de_ventas(p: Peticion) -> L.Periodo:
    """El periodo que pidió la persona; si no pidió ninguno, este mes. Si este mes todavía no tiene ventas
    (primeros días del mes, o datos sin actualizar), usa el último mes con ventas y lo avisa."""
    if p.periodo:
        return p.periodo
    mes = p.este_mes()
    if (await totales_ventas(p, mes)).ventas:
        return mes
    ultima = await p.db.scalar(desde_ventas(select(func.max(Venta.fecha_dia))).where(*cond_ventas(p, L.Periodo(date(2000, 1, 1), p.hoy, ""))))
    if not ultima:
        return mes
    desde = ultima.replace(day=1)
    siguiente = (desde + timedelta(days=32)).replace(day=1)
    anterior = L.Periodo(desde, min(siguiente - timedelta(days=1), p.hoy), f"{L.NOMBRES_MES[desde.month]} de {desde.year}")
    p.avisos.append(f"Todavía no hay ventas registradas en este mes; te muestro el último mes con ventas ({anterior.etiqueta}).")
    return anterior


def periodo_anterior(periodo: L.Periodo) -> L.Periodo:
    """Con qué se compara un periodo: si es un mes (o lo que va del mes) o un año, el mes o año anterior; si no, el tramo de igual duración justo antes."""
    desde, dias = periodo.desde, periodo.dias
    previo_fin = desde - timedelta(days=1)
    if desde.day == 1 and periodo.hasta.year == desde.year and periodo.hasta.month == desde.month:
        inicio = previo_fin.replace(day=1)
        return L.Periodo(inicio, min(previo_fin, inicio + timedelta(days=dias - 1)), "el periodo anterior")
    if (desde.month, desde.day) == (1, 1) and periodo.hasta.year == desde.year:
        inicio = date(desde.year - 1, 1, 1)
        return L.Periodo(inicio, min(previo_fin, inicio + timedelta(days=dias - 1)), "el periodo anterior")
    return L.Periodo(previo_fin - timedelta(days=dias - 1), previo_fin, "el periodo anterior")


def variacion(actual: float, anterior: float) -> tuple[str, str] | None:
    """(texto, tono) de la variación porcentual; ``None`` si no hay base de comparación."""
    from app.service.asistente.bloques import porcentaje

    if not anterior:
        return None
    cambio = (actual - anterior) / anterior * 100
    if abs(cambio) < 0.05:
        return "igual que el periodo anterior", "neutral"
    signo = "+" if cambio > 0 else "−"
    return f"{signo}{porcentaje(abs(cambio))} frente al periodo anterior", ("success" if cambio > 0 else "warning")
