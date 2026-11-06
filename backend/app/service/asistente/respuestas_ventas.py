"""Respuestas sobre ventas: totales, comparaciones, ranking de productos, tendencia, vendedores y detalle."""

import calendar
import re
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func, select

from app.model.catalogo import Producto
from app.model.inventario import InventarioSede
from app.model.operaciones import Venta, VentaItem
from app.model.sede import Sede
from app.model.usuario import Usuario
from app.service.asistente import bloques as B
from app.service.asistente.datos import (
    cond_inventario,
    cond_ventas,
    desde_ventas,
    enlaces_a,
    periodo_anterior,
    periodo_de_ventas,
    totales_ventas,
    variacion,
)
from app.service.asistente.peticion import HISTORIAL, Peticion, manejador
from app.util import lenguaje as L
from app.util.tiempo import a_fecha_local

_PIDE_TICKET = re.compile(r"\b(ticket\w*|venta promedio|compra promedio|promedio (por|de) (venta|compra|factura)s?)\b")
_PIDE_DINERO = re.compile(r"\b(ingres\w+|monto|dinero|plata|valor|facturad\w+|recaud\w+|pesos)\b")


def _nombre_producto(codigo: str, nombre: str) -> str:
    return f"{nombre} ({codigo})"


def _dinero(f: str) -> bool:
    return bool(_PIDE_DINERO.search(f))


def _de_filtro(p: Peticion) -> str:
    f = p.descripcion_filtro()
    return f" {f}" if f else ""


async def _sin_ventas(p: Peticion, periodo: L.Periodo) -> B.Resp:
    ultima = await p.db.scalar(
        desde_ventas(select(func.max(Venta.fecha_dia))).where(*cond_ventas(p, L.Periodo(date(2000, 1, 1), p.hoy, "")))
    )
    texto = f"No hay ventas registradas{_de_filtro(p)} {p.en_alcance} {p.en_periodo(periodo)}."
    bloques = []
    if ultima:
        texto += f" La última venta registrada fue el {L.fecha_larga(ultima)}."
        mes_ref = L.Periodo(ultima.replace(day=1), ultima, f"{L.NOMBRES_MES[ultima.month]} de {ultima.year}")
        if periodo.desde > mes_ref.hasta:  # lo pedido es posterior a lo último que se vendió: se da una referencia
            ref = await totales_ventas(p, mes_ref)
            if ref.ventas:
                texto += f" Como referencia, entre el {mes_ref.desde.day} y el {L.fecha_larga(ultima)} se vendieron **{B.moneda(ref.monto)}** en **{B.n_de(ref.ventas, 'venta')}**."
                bloques.append(B.metricas(f"Último mes con ventas ({mes_ref.etiqueta})", ("Vendido", B.moneda(ref.monto)), ("Ventas", B.entero(ref.ventas)), ("Unidades", B.entero(ref.unidades)), ("Ticket promedio", B.moneda(ref.ticket))))
    return B.Resp(texto, bloques, enlaces_a(p, "/ventas"), ["Ventas del mes pasado", "Últimas 10 ventas", "¿Cuáles son los productos más vendidos?"])


# ------------------------------------------------------------------------------------------------------ resumen
def _sin_preposicion(texto: str) -> str:
    """«en octubre de 2026» → «octubre de 2026»; «el lunes» → «el lunes» (para «frente a …»)."""
    return re.sub(r"^el ", "el ", re.sub(r"^en ", "", texto))


async def _comparar_periodos(p: Peticion, a: L.Periodo, b: L.Periodo) -> B.Resp:
    """«Compara octubre con septiembre»: dos periodos lado a lado (el más reciente primero)."""
    ta, tb = await totales_ventas(p, a), await totales_ventas(p, b)
    nombre_a, nombre_b = p.en_periodo(a), p.en_periodo(b)
    if b.etiqueta == "el periodo anterior":
        nombre_b = f"el periodo anterior ({L.describir_rango(b.desde, b.hasta)})"
    if not ta.ventas and not tb.ventas:
        return B.Resp(f"No hay ventas {p.en_alcance}{_de_filtro(p)} ni {nombre_a} ni {nombre_b}.", sugerencias=["Ventas del mes pasado"])
    var = variacion(ta.monto, tb.monto)
    texto = (f"{B.mayuscula_inicial(nombre_a)} se vendieron **{B.moneda(ta.monto)}** ({B.n_de(ta.ventas, 'venta')}) y {nombre_b} **{B.moneda(tb.monto)}** ({B.n_de(tb.ventas, 'venta')})"
             f"{_de_filtro(p)} {p.en_alcance}.")
    if var:
        texto += f" La variación es de **{var[0].split(' frente')[0]}** frente a {_sin_preposicion(nombre_b)}.".replace("frente a el ", "frente al ")
    elif ta.monto and not tb.monto:
        texto += f" No hubo ventas {nombre_b}, así que no hay con qué calcular la variación."
    etiqueta_a, etiqueta_b = L.describir_rango(a.desde, a.hasta), L.describir_rango(b.desde, b.hasta)
    tabla = B.tabla(None, [B.col("periodo", "Periodo"), B.col("vendido", "Vendido", "moneda"), B.col("ventas", "Ventas", "entero"), B.col("unidades", "Unidades", "entero"), B.col("ticket", "Ticket promedio", "moneda")],
                    [B.fila({"periodo": etiqueta_a, "vendido": ta.monto, "ventas": ta.ventas, "unidades": ta.unidades, "ticket": ta.ticket}),
                     B.fila({"periodo": etiqueta_b, "vendido": tb.monto, "ventas": tb.ventas, "unidades": tb.unidades, "ticket": tb.ticket})])
    bloques = [B.metricas(None, ("Variación del monto", var[0].split(" frente")[0] if var else "—", None, var[1] if var else "neutral")), tabla]  # type: ignore[arg-type]
    avisos = []
    if abs(a.dias - b.dias) > max(3, max(a.dias, b.dias) // 10):
        avisos.append(f"Los periodos no duran lo mismo ({a.dias} y {b.dias} días): la variación compara totales, no promedios diarios.")
    return B.Resp(texto, bloques, enlaces_a(p, "/ventas"), ["Ventas por sede", "¿Cuáles son los productos más vendidos?"], avisos)


@manejador("ventas_comparar")
async def ventas_comparar(p: Peticion) -> B.Resp:
    """Dos periodos nombrados («octubre con septiembre») o uno solo, que se compara con el periodo anterior."""
    if p.e.periodo and p.e.periodo_b:
        return await _comparar_periodos(p, p.e.periodo, p.e.periodo_b)
    periodo = await periodo_de_ventas(p)
    if (await totales_ventas(p, periodo)).ventas == 0:  # «este mes» recién empieza o no hay ventas: se explica, no se compara contra cero
        return await _sin_ventas(p, periodo)
    return await _comparar_periodos(p, periodo, periodo_anterior(periodo))


@manejador("ventas_resumen")
async def ventas_resumen(p: Peticion) -> B.Resp:
    if p.e.periodo and p.e.periodo_b:
        return await _comparar_periodos(p, p.e.periodo, p.e.periodo_b)
    periodo = await periodo_de_ventas(p)
    actual = await totales_ventas(p, periodo)
    if actual.ventas == 0:
        return await _sin_ventas(p, periodo)
    anterior = await totales_ventas(p, periodo_anterior(periodo))
    var = variacion(actual.monto, anterior.monto) if periodo.dias > 0 else None
    por_unidades = (p.hay_producto or p.hay_categoria) and not _dinero(p.frase)
    if _PIDE_TICKET.search(p.frase):
        texto = f"El ticket promedio {p.en_periodo(periodo)}{_de_filtro(p)} {p.en_alcance} fue de **{B.moneda(actual.ticket)}** por venta ({B.n_de(actual.ventas, 'venta')} por un total de {B.moneda(actual.monto)})."
    elif por_unidades:
        texto = f"Se vendieron **{B.entero(actual.unidades)} unidades**{_de_filtro(p)} {p.en_alcance} {p.en_periodo(periodo)}, por **{B.moneda(actual.monto)}** en **{B.n_de(actual.ventas, 'venta')}**."
    else:
        texto = f"{p.periodo_inicio(periodo)} se vendieron **{B.moneda(actual.monto)}**{_de_filtro(p)} {p.en_alcance}, en **{B.n_de(actual.ventas, 'venta')}** y **{B.entero(actual.unidades)} unidades**."
    if var and not _PIDE_TICKET.search(p.frase):
        texto += f" Frente al periodo anterior: {var[0].split(' frente')[0]}."
    metricas = [
        ("Vendido", B.moneda(actual.monto), var[0] if var else None, var[1] if var else "neutral"),  # type: ignore[arg-type]
        ("Ventas", B.entero(actual.ventas)),
        ("Unidades", B.entero(actual.unidades)),
        ("Ticket promedio", B.moneda(actual.ticket)),
    ]
    bloques = [B.metricas(None, *metricas)]
    avisos = []
    if not p.periodo:
        hoy = await totales_ventas(p, p.hoy_periodo())
        bloques[0].metricas.append(B.Metrica(etiqueta="Hoy", valor=B.moneda(hoy.monto), detalle=f"{B.n_de(hoy.ventas, 'venta')}"))
    anuladas = await totales_ventas(p, periodo, estado="anulada")
    if anuladas.ventas:
        avisos.append(f"Hubo {B.n_de(anuladas.ventas, 'venta anulada')} en el periodo; no se cuentan en estos totales.")
    return B.Resp(
        texto, bloques, enlaces_a(p, "/ventas"),
        ["Ventas por sede", "¿Cuáles son los productos más vendidos?", "¿Qué día se vende más?", "Ventas por categoría"], avisos,
    )


# ----------------------------------------------------------------------------------------------------- por sede
@manejador("ventas_por_sede")
async def ventas_por_sede(p: Peticion) -> B.Resp:
    periodo = await periodo_de_ventas(p)
    consulta = desde_ventas(
        select(Venta.sede_id, func.count(func.distinct(Venta.id)), func.coalesce(func.sum(VentaItem.subtotal), 0), func.coalesce(func.sum(VentaItem.cantidad), 0))
    ).where(*cond_ventas(p, periodo)).group_by(Venta.sede_id)
    filas = (await p.db.execute(consulta)).all()
    if not filas:
        return await _sin_ventas(p, periodo)
    nombres = {s.id: s.nombre for s in p.d.sedes}
    datos = sorted(((nombres.get(i, "—"), int(n), float(m), int(u)) for i, n, m, u in filas), key=lambda x: -x[2])
    asc = p.e.orden == "asc"
    total = sum(d[2] for d in datos)
    extremo = (datos[-1] if asc else datos[0]) if len(datos) > 1 else datos[0]
    if len(datos) == 1:
        texto = f"{p.periodo_inicio(periodo)}, **{datos[0][0]}** vendió **{B.moneda(datos[0][2])}** en {B.n_de(datos[0][1], 'venta')}."
    else:
        texto = (f"{p.periodo_inicio(periodo)} {'vendió menos' if asc else 'vendió más'} **{extremo[0]}** con **{B.moneda(extremo[2])}** "
                 f"({B.porcentaje(extremo[2] / total * 100 if total else 0)} del total de {B.moneda(total)}).")
    tabla = B.tabla(None, [B.col("sede", "Sede"), B.col("monto", "Vendido", "moneda"), B.col("ventas", "Ventas", "entero"), B.col("unidades", "Unidades", "entero"), B.col("ticket", "Ticket promedio", "moneda")],
                    [B.fila({"sede": n, "monto": m, "ventas": v, "unidades": u, "ticket": m / v if v else 0}, ruta="/ventas") for n, v, m, u in datos])
    bloques = [B.barras("Vendido por sede", [(n, m, B.moneda(m)) for n, _, m, _ in datos])] if len(datos) > 1 else []
    return B.Resp(texto, [*bloques, tabla], enlaces_a(p, "/ventas"), ["¿Cuáles son los productos más vendidos?", "Ventas por categoría", "¿Cómo está el inventario por sede?"])


# ------------------------------------------------------------------------------------------------ top productos
@manejador("ventas_top_productos")
async def ventas_top_productos(p: Peticion) -> B.Resp:
    periodo = await periodo_de_ventas(p)
    por_dinero = _dinero(p.frase)
    unidades = func.coalesce(func.sum(VentaItem.cantidad), 0)
    monto = func.coalesce(func.sum(VentaItem.subtotal), 0)
    asc = p.e.orden == "asc"
    medida = monto if por_dinero else unidades
    consulta = desde_ventas(
        select(Producto.id, Producto.codigo, Producto.nombre, unidades.label("u"), monto.label("m"), func.count(func.distinct(Venta.id)).label("n"))
    ).where(*cond_ventas(p, periodo)).group_by(Producto.id, Producto.codigo, Producto.nombre)
    consulta = consulta.order_by(medida.asc() if asc else medida.desc(), Producto.nombre)
    total = int(await p.db.scalar(select(func.count()).select_from(consulta.order_by(None).subquery())) or 0)
    if not total:
        return await _sin_ventas(p, periodo)
    limite = p.limite(5 if "top" in p.frase else 10)
    filas = (await p.db.execute(consulta.limit(limite))).all()
    primero = filas[0]
    producto = f"**{_nombre_producto(primero.codigo, primero.nombre)}** con **{B.entero(primero.u)} unidades** ({B.moneda(primero.m)})"
    donde = f"{p.en_periodo(periodo)}{(' ' + p.en_alcance) if p.sede_ids is not None else ''}{_de_filtro(p)}"
    if total > 1 and len(filas) > 1:
        texto = f"{'Los menos vendidos' if asc else 'Los más vendidos'} {donde}: {'el que menos se vendió' if asc else 'el primero'} es {producto}."
    else:
        texto = f"El producto {'menos vendido' if asc else 'más vendido'} {donde} es {producto}."
    tabla = B.tabla(
        None, [B.col("pos", "N.º", "entero"), B.col("producto", "Producto"), B.col("unidades", "Unidades", "entero"), B.col("monto", "Vendido", "moneda"), B.col("ventas", "Ventas", "entero")],
        [B.fila({"pos": i, "producto": _nombre_producto(f.codigo, f.nombre), "unidades": int(f.u), "monto": float(f.m), "ventas": int(f.n)}, ruta="/ventas") for i, f in enumerate(filas, 1)],
        total=total, nota=f"Mostrando {len(filas)} de {total} productos con ventas." if total > len(filas) else None,
    )
    bloques = []
    if len(filas) > 1:
        bloques.append(B.barras("Unidades vendidas" if not por_dinero else "Monto vendido", [(f.nombre, float(f.m if por_dinero else f.u), B.moneda(f.m) if por_dinero else B.entero(f.u)) for f in filas]))
    avisos = ["Solo cuenta productos que sí tuvieron ventas. Para ver los que no se vendieron, pregunta «productos sin ventas»."] if asc else []
    return B.Resp(texto, [*bloques, tabla], enlaces_a(p, "/ventas"), ["Productos sin ventas", "Ventas por categoría", "¿Qué debo reponer?"], avisos)


_PIDE_ROTACION_BAJA = re.compile(r"\b(baja|poca|lenta|mala|menor|minima) rotacion\b|\brotacion (baja|lenta|mala)\b|\blent[oa]s?\b")
_PIDE_RAPIDOS = re.compile(r"\b(rapid[oa]s?|mas (se )?(mueve\w*|rota\w*|sale\w*)|alta rotacion|mejor rotacion|mayor rotacion|mas rotacion)\b")


@manejador("rotacion_inventario")
async def rotacion_inventario(p: Peticion) -> B.Resp:
    """Rotación aproximada: lo vendido en el periodo (a costo) frente al inventario de hoy, y los días que dura cada producto."""
    periodo = await periodo_de_ventas(p)
    dias_periodo = max(1, (periodo.hasta - periodo.desde).days + 1)
    costo = func.coalesce(Producto.costo, 0)
    vendido = (await p.db.execute(
        desde_ventas(select(VentaItem.producto_id.label("pid"), func.sum(VentaItem.cantidad).label("u"), func.sum(VentaItem.cantidad * costo).label("c")))
        .where(*cond_ventas(p, periodo)).group_by(VentaItem.producto_id)
    )).all()
    if not vendido:
        return await _sin_ventas(p, periodo)
    ventas = {f.pid: (int(f.u or 0), float(f.c or 0)) for f in vendido}
    existencias = (await p.db.execute(
        select(Producto.id, Producto.codigo, Producto.nombre, func.sum(InventarioSede.cantidad).label("u"), func.sum(InventarioSede.cantidad * costo).label("valor"))
        .select_from(InventarioSede).join(Producto, Producto.id == InventarioSede.producto_id)
        .where(*cond_inventario(p), InventarioSede.cantidad > 0).group_by(Producto.id, Producto.codigo, Producto.nombre)
    )).all()
    if not existencias:
        return B.Resp(f"No hay existencias{_de_filtro(p)} {p.en_alcance} para calcular la rotación.", sugerencias=["¿Qué productos están agotados?", "Valor del inventario"])
    valor_inventario = sum(float(f.valor or 0) for f in existencias)
    costo_vendido = sum(c for _, c in ventas.values())
    unidades_inventario = sum(int(f.u) for f in existencias)
    unidades_vendidas = sum(u for u, _ in ventas.values())
    por_valor = valor_inventario > 0 and costo_vendido > 0
    veces = (costo_vendido / valor_inventario) if por_valor else (unidades_vendidas / unidades_inventario)
    ritmo = (costo_vendido if por_valor else unidades_vendidas) / dias_periodo  # lo que sale por día, en la misma medida
    dias_inventario = ((valor_inventario if por_valor else unidades_inventario) / ritmo) if ritmo else None

    filas = []  # productos con existencias y ventas: días que dura el stock actual al ritmo del periodo
    sin_ventas = 0
    for f in existencias:
        vendidas = ventas.get(f.id, (0, 0))[0]
        if not vendidas:
            sin_ventas += 1
            continue
        filas.append((f, vendidas, int(f.u) / (vendidas / dias_periodo), vendidas / int(f.u)))
    rapidos = bool(_PIDE_RAPIDOS.search(p.frase))
    filas.sort(key=lambda x: (x[2] if rapidos else -x[2], x[0].nombre))
    limite = p.limite(8)
    mostrar = filas[:limite]

    donde = f"{p.en_periodo(periodo)}{(' ' + p.en_alcance) if p.sede_ids is not None else ''}{_de_filtro(p)}"
    texto = (f"La rotación {donde} es de **{B.decimal(veces, 2)} veces**: se vendió el equivalente al {B.porcentaje(veces * 100, 0)} del inventario actual"
             f"{' (a costo)' if por_valor else ''}" + (f", lo que alcanza para cerca de **{B.entero(dias_inventario)} días** de inventario." if dias_inventario else "."))
    if mostrar:
        primero = mostrar[0][0]
        texto += (f" {'El que más rápido rota' if rapidos else 'El que más lento rota'} es **{_nombre_producto(primero.codigo, primero.nombre)}**: "
                  f"le alcanza para **{B.entero(mostrar[0][2])} días** al ritmo de ese periodo.")
    bloques = [B.metricas(None, ("Rotación del periodo", f"{B.decimal(veces, 2)} veces"), ("Días de inventario", B.entero(dias_inventario) if dias_inventario else "—"),
                          ("Inventario actual", B.moneda(valor_inventario) if por_valor else f"{B.entero(unidades_inventario)} u."),
                          ("Vendido en el periodo", B.moneda(costo_vendido) if por_valor else f"{B.entero(unidades_vendidas)} u.", "a costo" if por_valor else None))]
    if mostrar:
        bloques.append(B.tabla(
            "Más rápidos (menos días de inventario)" if rapidos else "Más lentos (más días de inventario)",
            [B.col("producto", "Producto"), B.col("vendidas", "Vendidas", "entero"), B.col("existencias", "Existencias", "entero"), B.col("dias", "Días de inventario", "entero"), B.col("rotacion", "Rotación (veces)", "decimal")],
            [B.fila({"producto": _nombre_producto(f.codigo, f.nombre), "vendidas": v, "existencias": int(f.u), "dias": round(d), "rotacion": round(r, 2)}, ruta="/inventario") for f, v, d, r in mostrar],
            total=len(filas), nota=f"Mostrando {len(mostrar)} de {len(filas)} productos con ventas." if len(filas) > len(mostrar) else None))
    avisos = ["Es una aproximación: usa el inventario de hoy (no el promedio del periodo) y supone que el ritmo de ventas del periodo se mantiene."]
    if sin_ventas:
        avisos.append(f"{B.n_de(sin_ventas, 'producto')} con existencias no tuvieron ventas en el periodo y no entran en el ranking; pregunta «productos sin ventas» para verlos.")
    return B.Resp(texto, bloques, enlaces_a(p, "/inventario", "/ventas"), ["Productos sin ventas", "¿Qué productos se van a agotar pronto?", "¿Qué tengo en exceso?"], avisos)


@manejador("productos_sin_ventas")
async def productos_sin_ventas(p: Peticion) -> B.Resp:
    parametros = await p.parametros()
    dias = parametros.get("dias_sin_rotacion", 60)
    periodo = p.ultimos_dias(dias)
    vendidos = (
        select(VentaItem.producto_id).select_from(Venta).join(VentaItem, VentaItem.venta_id == Venta.id)
        .where(Venta.empresa_id == p.ctx.empresa_id, Venta.estado == "registrada", Venta.fecha_dia >= periodo.desde, Venta.fecha_dia <= periodo.hasta)
    )
    if p.sede_ids is not None:
        vendidos = vendidos.where(Venta.sede_id.in_(p.sede_ids))
    valor = func.coalesce(func.sum(InventarioSede.cantidad * Producto.costo), 0)
    consulta = (
        select(Producto.id, Producto.codigo, Producto.nombre, func.sum(InventarioSede.cantidad).label("u"), valor.label("valor"))
        .select_from(InventarioSede).join(Producto, Producto.id == InventarioSede.producto_id)
        .where(*cond_inventario(p), InventarioSede.cantidad > 0, Producto.id.not_in(vendidos))
        .group_by(Producto.id, Producto.codigo, Producto.nombre).order_by(valor.desc(), Producto.nombre)
    )
    todas = (await p.db.execute(consulta)).all()
    if not todas:
        todos_vendieron = f"Todos los productos con existencias{_de_filtro(p)} {p.en_alcance} tuvieron ventas {p.en_periodo(periodo)}."
        if _PIDE_ROTACION_BAJA.search(p.frase):  # «baja rotación»: si nadie está parado, se muestran los que rotan más lento
            rotacion = await rotacion_inventario(p)
            rotacion.texto = f"{todos_vendieron} {rotacion.texto}"
            return rotacion
        return B.Resp(todos_vendieron, sugerencias=["¿Cuáles son los productos más vendidos?"])
    inmovilizado = sum(float(f.valor) for f in todas)
    limite = p.limite(_MAX_FILAS_SIN_VENTAS)
    mostrar = todas[:limite]
    ultimas = {}
    ids = [f.id for f in mostrar]
    if ids:
        consulta_ultima = select(VentaItem.producto_id, func.max(Venta.fecha_dia)).select_from(Venta).join(VentaItem, VentaItem.venta_id == Venta.id).where(
            Venta.empresa_id == p.ctx.empresa_id, Venta.estado == "registrada", VentaItem.producto_id.in_(ids)).group_by(VentaItem.producto_id)
        if p.sede_ids is not None:
            consulta_ultima = consulta_ultima.where(Venta.sede_id.in_(p.sede_ids))
        ultimas = dict((await p.db.execute(consulta_ultima)).all())
    texto = (f"Hay **{B.n_de(len(todas), 'producto')}** con existencias{_de_filtro(p)} {p.en_alcance} que no se han vendido {p.en_periodo(periodo)}"
             f"{', con ' + B.moneda(inmovilizado) + ' inmovilizados a costo' if inmovilizado else ''}.")
    tabla = B.tabla(
        None, [B.col("producto", "Producto"), B.col("unidades", "Existencias", "entero"), B.col("valor", "Valor a costo", "moneda"), B.col("ultima", "Última venta", "fecha")],
        [B.fila({"producto": _nombre_producto(f.codigo, f.nombre), "unidades": int(f.u), "valor": float(f.valor), "ultima": ultimas[f.id].isoformat() if f.id in ultimas else "Nunca"}, ruta="/inventario") for f in mostrar],
        total=len(todas), nota=f"Mostrando {len(mostrar)} de {len(todas)}." if len(todas) > len(mostrar) else None,
    )
    return B.Resp(texto, [tabla], enlaces_a(p, "/inventario", "/ventas"), ["¿Qué tengo en exceso?", "Valor del inventario", "¿Qué debo trasladar entre sedes?"],
                  [f"El periodo por defecto son {dias} días (parámetro de la empresa). Puedes preguntar por otro, por ejemplo «sin ventas en los últimos 30 días»."] if not p.periodo else [])


_MAX_FILAS_SIN_VENTAS = 15


# --------------------------------------------------------------------------------------------- por categoría
@manejador("ventas_por_categoria")
async def ventas_por_categoria(p: Peticion) -> B.Resp:
    periodo = await periodo_de_ventas(p)
    consulta = desde_ventas(
        select(Producto.categoria_id, func.coalesce(func.sum(VentaItem.subtotal), 0), func.coalesce(func.sum(VentaItem.cantidad), 0), func.count(func.distinct(Venta.id)))
    ).where(*cond_ventas(p, periodo)).group_by(Producto.categoria_id)
    filas = (await p.db.execute(consulta)).all()
    if not filas:
        return await _sin_ventas(p, periodo)
    nombres = {c.id: c.nombre for c in p.d.categorias}
    datos = sorted(((nombres.get(i, "—"), float(m), int(u), int(n)) for i, m, u, n in filas), key=lambda x: -x[1])
    total = sum(d[1] for d in datos)
    asc = p.e.orden == "asc"
    extremo = datos[-1] if asc else datos[0]
    texto = (f"{p.periodo_inicio(periodo)} la categoría {'que menos vendió' if asc else 'que más vendió'}{_en_sede(p)} fue **{extremo[0]}** con **{B.moneda(extremo[1])}** "
             f"({B.porcentaje(extremo[1] / total * 100 if total else 0)} de {B.moneda(total)}).") if len(datos) > 1 else f"{p.periodo_inicio(periodo)}, **{datos[0][0]}** vendió **{B.moneda(datos[0][1])}** ({B.n_de(datos[0][2], 'unidad', 'unidades')})."
    bloques = []
    if len(datos) > 1:
        bloques.append(B.barras("Vendido por categoría", [(n, m, B.moneda(m)) for n, m, _, _ in datos]))
    bloques.append(B.tabla(None, [B.col("categoria", "Categoría"), B.col("monto", "Vendido", "moneda"), B.col("unidades", "Unidades", "entero"), B.col("participacion", "Participación", "porcentaje")],
                           [B.fila({"categoria": n, "monto": m, "unidades": u, "participacion": m / total * 100 if total else 0}) for n, m, u, _ in datos]))
    return B.Resp(texto, bloques, enlaces_a(p, "/ventas"), ["Inventario por categoría", "Ventas por sede", "¿Cuáles son los productos más vendidos?"])


def _en_sede(p: Peticion) -> str:
    return f" {p.en_alcance}" if p.sede_ids is not None else ""


# -------------------------------------------------------------------------------------------- tendencia / días
@manejador("ventas_por_dia")
async def ventas_por_dia(p: Peticion) -> B.Resp:
    modo = p.e.agrupar
    if p.periodo:
        periodo = p.periodo
    elif modo == "mes":
        inicio = (p.hoy.replace(day=1) - timedelta(days=150)).replace(day=1)
        periodo = L.Periodo(inicio, p.hoy, "los últimos 6 meses")
    elif modo == "dia_semana":
        periodo = p.ultimos_dias(90)
    elif modo == "semana":
        periodo = p.ultimos_dias(56)
    else:
        periodo = p.ultimos_dias(30)
    consulta = desde_ventas(
        select(Venta.fecha_dia, func.coalesce(func.sum(VentaItem.subtotal), 0), func.coalesce(func.sum(VentaItem.cantidad), 0), func.count(func.distinct(Venta.id)))
    ).where(*cond_ventas(p, periodo)).group_by(Venta.fecha_dia)
    filas = (await p.db.execute(consulta)).all()
    if not filas:
        return await _sin_ventas(p, periodo)
    por_dia = {f[0]: (float(f[1]), int(f[2]), int(f[3])) for f in filas}
    # Agrupar.
    grupos: dict = defaultdict(lambda: [0.0, 0, 0])
    dias_en_grupo: dict = defaultdict(set)
    for dia, (m, u, n) in por_dia.items():
        if modo == "mes":
            clave = (dia.year, dia.month)
        elif modo == "semana":
            clave = dia - timedelta(days=dia.weekday())
        elif modo == "dia_semana":
            clave = dia.weekday()
        else:
            clave = dia
        grupos[clave][0] += m
        grupos[clave][1] += u
        grupos[clave][2] += n
        dias_en_grupo[clave].add(dia)
    if modo == "dia":  # rellena los días sin ventas con cero
        d = periodo.desde
        while d <= periodo.hasta and (periodo.hasta - periodo.desde).days <= 62:
            grupos.setdefault(d, [0.0, 0, 0])
            d += timedelta(days=1)
    if modo == "mes":
        y, m = periodo.desde.year, periodo.desde.month
        while (y, m) <= (periodo.hasta.year, periodo.hasta.month):
            grupos.setdefault((y, m), [0.0, 0, 0])
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    claves = sorted(grupos)
    if modo == "dia_semana":
        # Promedio por día de la semana: cuántos de esos días hubo en el periodo.
        ocurrencias = defaultdict(int)
        d = periodo.desde
        while d <= min(periodo.hasta, max(por_dia)):  # los días posteriores a la última venta registrada no cuentan como «sin ventas»
            ocurrencias[d.weekday()] += 1
            d += timedelta(days=1)
        valores = {k: grupos[k][0] / ocurrencias[k] if ocurrencias[k] else 0.0 for k in claves}
        etiquetas = {k: L.NOMBRES_DIA[k].capitalize() for k in claves}
    else:
        valores = {k: grupos[k][0] for k in claves}
        etiquetas = {
            k: (f"{L.NOMBRES_MES[k[1]][:3].capitalize()} {k[0]}" if modo == "mes" else B.fecha_corta(k).rsplit(" ", 1)[0] if modo != "dia_semana" else str(k)) for k in claves
        }
        if modo == "semana":
            etiquetas = {k: f"Sem. {B.fecha_corta(k).rsplit(' ', 1)[0]}" for k in claves}
    ultimo_dia = max(por_dia)

    def completo(k) -> bool:  # semanas y meses cortados por el borde del periodo o por la última venta no sirven para decir «el más flojo»
        if modo == "semana":
            return k >= periodo.desde and k + timedelta(days=6) <= min(periodo.hasta, ultimo_dia)
        if modo == "mes":
            return date(k[0], k[1], 1) >= periodo.desde and date(k[0], k[1], calendar.monthrange(k[0], k[1])[1]) <= min(periodo.hasta, ultimo_dia)
        return True

    mejor = max(claves, key=lambda k: valores[k])
    candidatos = [k for k in claves if valores[k] > 0 and completo(k)] or [k for k in claves if valores[k] > 0]
    peor_con_ventas = min(candidatos, key=lambda k: valores[k], default=mejor)
    total = sum(g[0] for g in grupos.values())
    unidad = {"dia": "día", "semana": "semana", "mes": "mes", "dia_semana": "día de la semana"}[modo]
    asc = p.e.orden == "asc"
    objetivo = peor_con_ventas if asc else mejor
    pide_ranking = p.e.orden is not None or bool(re.search(r"\bque (dia|mes|semana)|\b(mejor|peor|pico)\b", p.frase))
    if modo == "dia_semana":
        texto = f"{p.periodo_inicio(periodo)}, el día de la semana {'más flojo' if asc else 'con más ventas'} es el **{etiquetas[objetivo].lower()}**, con un promedio de **{B.moneda(valores[objetivo])}** por jornada."
    elif not pide_ranking:
        texto = f"Ventas por {unidad} {p.en_periodo(periodo)}: en total **{B.moneda(total)}**."
        nombre_mejor = f"el mes de {L.NOMBRES_MES[mejor[1]]} de {mejor[0]}" if modo == "mes" else (f"la semana del {etiquetas[mejor].removeprefix('Sem. ')}" if modo == "semana" else f"el {L.NOMBRES_DIA[mejor.weekday()]} {L.fecha_larga(mejor)}")
        texto += f" Lo más alto fue {nombre_mejor}, con **{B.moneda(valores[mejor])}**."
    else:
        articulo = "La" if modo == "semana" else "El"
        flojo = "más floja" if modo == "semana" else "más flojo"
        if modo == "mes":
            nombre = f"**{L.NOMBRES_MES[objetivo[1]]} de {objetivo[0]}**"
        elif modo == "semana":
            nombre = f"la que empezó el **{etiquetas[objetivo].removeprefix('Sem. ')}**"
        else:
            nombre = f"**{L.NOMBRES_DIA[objetivo.weekday()]} {L.fecha_larga(objetivo)}**"
        texto = f"{articulo} {unidad} {flojo if asc else 'con más ventas'} {p.en_periodo(periodo)} fue {nombre}, con **{B.moneda(valores[objetivo])}**. En total se vendieron **{B.moneda(total)}**."
    # Tendencia: compara la primera y la segunda mitad, sin contar el tramo en curso (incompleto) ni los últimos tramos aún sin ventas.
    tramos = list(claves)
    while tramos and valores[tramos[-1]] == 0:
        tramos.pop()
    if tramos and ((modo == "mes" and tramos[-1] == (p.hoy.year, p.hoy.month)) or (modo == "semana" and tramos[-1] == p.hoy - timedelta(days=p.hoy.weekday()))):
        tramos.pop()
    if modo in ("dia", "semana", "mes") and len(tramos) >= 4:
        mitad = len(tramos) // 2
        primera, segunda = sum(valores[k] for k in tramos[:mitad]), sum(valores[k] for k in tramos[-mitad:])
        if primera > 0:
            cambio = (segunda - primera) / primera * 100
            if abs(cambio) >= 5:
                texto += f" La tendencia es {'al alza' if cambio > 0 else 'a la baja'}: la segunda mitad del periodo vendió {B.porcentaje(abs(cambio))} {'más' if cambio > 0 else 'menos'} que la primera."
    barras = [(etiquetas[k], valores[k], B.moneda(valores[k])) for k in claves[-31:]]
    return B.Resp(texto, [B.barras("Ventas" + (" promedio" if modo == "dia_semana" else ""), barras)], enlaces_a(p, "/ventas"), ["Ventas por mes", "¿Qué día de la semana se vende más?", "Ventas por sede"])


# ------------------------------------------------------------------------------------------------- vendedores
@manejador("ventas_por_vendedor")
async def ventas_por_vendedor(p: Peticion) -> B.Resp:
    periodo = await periodo_de_ventas(p)
    consulta = desde_ventas(
        select(Venta.usuario_id, func.count(func.distinct(Venta.id)), func.coalesce(func.sum(VentaItem.subtotal), 0), func.coalesce(func.sum(VentaItem.cantidad), 0))
    ).where(*cond_ventas(p, periodo)).group_by(Venta.usuario_id)
    filas = (await p.db.execute(consulta)).all()
    if not filas:
        return await _sin_ventas(p, periodo)
    nombres = dict((await p.db.execute(select(Usuario.id, Usuario.nombre).where(Usuario.id.in_([f[0] for f in filas])))).all())
    datos = sorted(((nombres.get(i, "—"), int(n), float(m), int(u)) for i, n, m, u in filas), key=lambda x: -x[2], reverse=False)
    asc = p.e.orden == "asc"
    datos.sort(key=lambda x: x[2], reverse=not asc)
    primero = datos[0]
    texto = f"{p.periodo_inicio(periodo)} {'vendió menos' if asc else 'vendió más'} **{primero[0]}**: **{B.moneda(primero[2])}** en {B.n_de(primero[1], 'venta')}."
    tabla = B.tabla(None, [B.col("vendedor", "Persona"), B.col("monto", "Vendido", "moneda"), B.col("ventas", "Ventas", "entero"), B.col("unidades", "Unidades", "entero")],
                    [B.fila({"vendedor": n, "monto": m, "ventas": v, "unidades": u}) for n, v, m, u in datos[: p.limite(15)]], total=len(datos))
    return B.Resp(texto, [tabla], enlaces_a(p, "/ventas"), ["Ventas por sede", "Últimas 10 ventas"])


# ------------------------------------------------------------------------------------------ listados y detalle
async def _ventas_listado(p: Peticion, extra: tuple, limite: int, orden=None):
    consulta = (
        select(Venta, Sede.nombre.label("sede"), Usuario.nombre.label("vendedor"))
        .join(Sede, Sede.id == Venta.sede_id).join(Usuario, Usuario.id == Venta.usuario_id)
        .where(Venta.empresa_id == p.ctx.empresa_id, *extra)
        .order_by(*(orden or (Venta.fecha.desc(), Venta.id.desc()))).limit(limite)
    )
    if p.sede_ids is not None:
        consulta = consulta.where(Venta.sede_id.in_(p.sede_ids))
    if p.producto_ids or p.categoria_ids:
        sub = select(VentaItem.venta_id).join(Producto, Producto.id == VentaItem.producto_id)
        if p.producto_ids:
            sub = sub.where(VentaItem.producto_id.in_(p.producto_ids))
        if p.categoria_ids:
            sub = sub.where(Producto.categoria_id.in_(p.categoria_ids))
        consulta = consulta.where(Venta.id.in_(sub))
    return (await p.db.execute(consulta)).all()


def _tabla_ventas(filas, total: int | None = None):
    cols = [B.col("numero", "Venta"), B.col("fecha", "Fecha", "fecha_hora"), B.col("sede", "Sede"), B.col("vendedor", "Atendió"), B.col("total", "Total", "moneda"), B.col("estado", "Estado")]
    salida = []
    for f in filas:
        v = f.Venta
        anulada = v.estado == "anulada"
        salida.append(B.fila({"numero": f"N.º {v.numero}", "fecha": v.fecha, "sede": f.sede, "vendedor": f.vendedor, "total": float(v.total), "estado": "Anulada" if anulada else "Registrada"},
                             tonos={"estado": "danger" if anulada else "success"}, ruta="/ventas"))
    return B.tabla(None, cols, salida, total=total)


@manejador("ventas_recientes")
async def ventas_recientes(p: Peticion) -> B.Resp:
    extra = ()
    if p.periodo:
        extra = (Venta.fecha_dia >= p.periodo.desde, Venta.fecha_dia <= p.periodo.hasta)
    limite = p.limite(10)
    filas = await _ventas_listado(p, extra, limite)
    if not filas:
        return B.Resp(f"No hay ventas registradas{_de_filtro(p)} {p.en_alcance}" + (f" {p.en_periodo(p.periodo)}" if p.periodo else "") + ".")
    ultima = filas[0].Venta
    texto = (f"Estas son las **{len(filas)} ventas más recientes**{_de_filtro(p)} {p.en_alcance}" + (f" {p.en_periodo(p.periodo)}" if p.periodo else "")
             + f". La última es la **N.º {ultima.numero}** por **{B.moneda(ultima.total)}** ({B.fecha_corta(a_fecha_local(ultima.fecha))}).")
    return B.Resp(texto, [_tabla_ventas(filas)], enlaces_a(p, "/ventas"), [f"Detalle de la venta {ultima.numero}", "¿Cuánto vendimos hoy?", "Ventas anuladas"])


@manejador("venta_detalle")
async def venta_detalle(p: Peticion) -> B.Resp:
    numero = p.e.numero
    if numero is None:
        return B.Resp("¿De qué venta? Dime el número, por ejemplo «detalle de la venta 15».", sugerencias=["Últimas 10 ventas"])
    consulta = (
        select(Venta, Sede.nombre.label("sede"), Usuario.nombre.label("vendedor"))
        .join(Sede, Sede.id == Venta.sede_id).join(Usuario, Usuario.id == Venta.usuario_id)
        .where(Venta.empresa_id == p.ctx.empresa_id, Venta.numero == numero)
    )
    fila = (await p.db.execute(consulta)).first()
    if fila is None or (p.sede_ids is not None and fila.Venta.sede_id not in p.sede_ids):
        return B.Resp(f"No encontré la venta N.º {numero}" + (" en tu sede." if p.limitado else "."), sugerencias=["Últimas 10 ventas"])
    v = fila.Venta
    productos = {pr.id: pr for pr in (await p.db.scalars(select(Producto).where(Producto.id.in_([i.producto_id for i in v.items])))).all()}
    anulada = v.estado == "anulada"
    texto = (f"La venta **N.º {v.numero}** se registró el {B.fecha_corta(a_fecha_local(v.fecha))} en **{fila.sede}** (atendió {fila.vendedor}): "
             f"**{B.moneda(v.total)}** en {B.n_de(sum(i.cantidad for i in v.items), 'unidad', 'unidades')}." + (" Está **anulada**." if anulada else ""))
    bloques = [B.metricas(None, ("Total", B.moneda(v.total)), ("Estado", "Anulada" if anulada else "Registrada", None, "danger" if anulada else "success"), ("Sede", fila.sede), ("Fecha", B.fecha_corta(a_fecha_local(v.fecha))))]
    bloques.append(B.tabla("Productos vendidos", [B.col("producto", "Producto"), B.col("cantidad", "Cantidad", "entero"), B.col("precio", "Precio unitario", "moneda"), B.col("subtotal", "Subtotal", "moneda")],
                           [B.fila({"producto": _nombre_producto(productos[i.producto_id].codigo, productos[i.producto_id].nombre) if i.producto_id in productos else "—", "cantidad": i.cantidad,
                                    "precio": float(i.precio_unitario), "subtotal": float(i.subtotal)}) for i in v.items]))
    if anulada and v.motivo_anulacion:
        bloques.append(B.lista("Anulación", [f"Motivo: {v.motivo_anulacion}"] + ([f"Fecha: {B.fecha_corta(a_fecha_local(v.anulada_en))}"] if v.anulada_en else [])))
    return B.Resp(texto, bloques, enlaces_a(p, "/ventas"), ["Últimas 10 ventas", "Ventas anuladas"])


@manejador("ventas_anuladas")
async def ventas_anuladas(p: Peticion) -> B.Resp:
    periodo = p.periodo or L.Periodo(date(2000, 1, 1), p.hoy, HISTORIAL)
    anuladas = await totales_ventas(p, periodo, estado="anulada")
    validas = await totales_ventas(p, periodo)
    if anuladas.ventas == 0:
        return B.Resp(f"No hay ventas anuladas{_de_filtro(p)} {p.en_alcance} {p.en_periodo(periodo)}.", sugerencias=["¿Cuánto vendimos este mes?"])
    todas = anuladas.ventas + validas.ventas
    texto = (f"{p.periodo_inicio(periodo)} {p.en_alcance} se anularon **{B.n_de(anuladas.ventas, 'venta')}** por **{B.moneda(anuladas.monto)}** "
             f"({B.porcentaje(anuladas.ventas / todas * 100 if todas else 0)} de las ventas del periodo).")
    filas = await _ventas_listado(p, (Venta.estado == "anulada", Venta.fecha_dia >= periodo.desde, Venta.fecha_dia <= periodo.hasta), p.limite(10), (Venta.anulada_en.desc().nulls_last(), Venta.id.desc()))
    quienes = dict((await p.db.execute(select(Usuario.id, Usuario.nombre).where(Usuario.id.in_([f.Venta.anulada_por for f in filas if f.Venta.anulada_por])))).all()) if filas else {}
    tabla = B.tabla(None, [B.col("numero", "Venta"), B.col("sede", "Sede"), B.col("total", "Total", "moneda"), B.col("motivo", "Motivo"), B.col("quien", "Anulada por")],
                    [B.fila({"numero": f"N.º {f.Venta.numero}", "sede": f.sede, "total": float(f.Venta.total), "motivo": f.Venta.motivo_anulacion or "—", "quien": quienes.get(f.Venta.anulada_por, "—")}, ruta="/ventas") for f in filas],
                    total=anuladas.ventas)
    return B.Resp(texto, [tabla], enlaces_a(p, "/ventas"), ["Últimas 10 ventas", "¿Quién anuló ventas esta semana?"])
