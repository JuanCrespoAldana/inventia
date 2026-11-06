"""Respuestas ampliadas de ventas: utilidad, horas pico, venta mayor, promedios, «mis ventas», proyección del mes y última venta de un producto."""

import calendar
from collections import defaultdict
from datetime import date

from sqlalchemy import case, func, select

from app.model.catalogo import Producto
from app.model.operaciones import Venta, VentaItem
from app.service.asistente import bloques as B
from app.service.asistente.analisis import hora_local, nombre_producto, nota_listado, pide_lo_menor, porcentaje_de, ultimos
from app.service.asistente.datos import cond_ventas, desde_ventas, enlaces_a, periodo_anterior, periodo_de_ventas, totales_ventas, variacion
from app.service.asistente.peticion import Peticion, manejador
from app.service.asistente.respuestas_ventas import _sin_ventas, _tabla_ventas, _ventas_listado
from app.util import lenguaje as L


# =========================================================================================================== utilidad
async def _utilidad(p: Peticion, periodo: L.Periodo):
    """(ventas, costo, utilidad, monto sin costo, nº de ventas): las líneas de productos sin costo se excluyen de la utilidad."""
    sin_costo = Producto.costo.is_(None)
    f = (await p.db.execute(
        desde_ventas(select(
            func.coalesce(func.sum(VentaItem.subtotal), 0),
            func.coalesce(func.sum(case((sin_costo, 0), else_=VentaItem.cantidad * Producto.costo)), 0),
            func.coalesce(func.sum(case((sin_costo, VentaItem.subtotal), else_=0)), 0),
            func.count(func.distinct(Venta.id)),
        )).where(*cond_ventas(p, periodo))
    )).one()
    monto, costo, sin_costo_monto, n = float(f[0]), float(f[1]), float(f[2]), int(f[3])
    base = monto - sin_costo_monto
    return monto, costo, base - costo, sin_costo_monto, n


@manejador("utilidad_ventas")
async def utilidad_ventas(p: Peticion) -> B.Resp:
    periodo = await periodo_de_ventas(p)
    monto, costo, utilidad, sin_costo_monto, n = await _utilidad(p, periodo)
    if n == 0:
        return await _sin_ventas(p, periodo)
    base = monto - sin_costo_monto
    margen = porcentaje_de(utilidad, base)
    anterior = await _utilidad(p, periodo_anterior(periodo))
    var = variacion(utilidad, anterior[2]) if anterior[4] else None
    texto = (f"{p.periodo_inicio(periodo)} la utilidad bruta {p.en_alcance} fue de **{B.moneda(utilidad)}**: vendiste {B.moneda(base)} y esos productos te costaron {B.moneda(costo)} "
             f"(margen del **{B.porcentaje(margen)}**).")
    if var:
        texto += f" Frente al periodo anterior: {var[0].split(' frente')[0]}."
    metricas = [("Ventas", B.moneda(base)), ("Costo de lo vendido", B.moneda(costo)), ("Utilidad bruta", B.moneda(utilidad), var[0] if var else None, var[1] if var else "neutral"),
                ("Margen bruto", B.porcentaje(margen))]
    filas = (await p.db.execute(
        desde_ventas(select(Producto.codigo, Producto.nombre, func.sum(VentaItem.cantidad).label("u"), func.sum(VentaItem.subtotal).label("m"),
                            func.sum(VentaItem.subtotal - VentaItem.cantidad * Producto.costo).label("ut")))
        .where(*cond_ventas(p, periodo), Producto.costo.is_not(None)).group_by(Producto.codigo, Producto.nombre).order_by(func.sum(VentaItem.subtotal - VentaItem.cantidad * Producto.costo).desc())
    )).all()
    bloques = [B.metricas(None, *metricas)]
    if filas and not p.hay_producto:
        mostrar = filas[: p.limite(5)]
        bloques.append(B.tabla("Productos que más utilidad dejaron", [B.col("producto", "Producto"), B.col("u", "Unidades", "entero"), B.col("m", "Vendido", "moneda"), B.col("ut", "Utilidad", "moneda")],
                               [B.fila({"producto": nombre_producto(f.codigo, f.nombre), "u": int(f.u), "m": float(f.m), "ut": float(f.ut)}, ruta="/productos") for f in mostrar],
                               total=len(filas), nota=nota_listado(len(mostrar), len(filas), "productos")))
    avisos = ["Es utilidad bruta: ventas menos el costo de compra registrado de cada producto (no incluye gastos de operación, nómina ni impuestos)."]
    if sin_costo_monto:
        avisos.append(f"{B.moneda(sin_costo_monto)} vendidos corresponden a productos sin costo registrado y no entran en la utilidad.")
    return B.Resp(texto, bloques, enlaces_a(p, "/ventas", "/productos"), ["Ventas por categoría", "¿Qué productos tienen mayor margen?", "Compara con el mes pasado"], avisos)


# ======================================================================================================= horas de venta
@manejador("ventas_por_hora")
async def ventas_por_hora(p: Peticion) -> B.Resp:
    periodo = ultimos(p, 90)
    filas = (await p.db.execute(
        desde_ventas(select(Venta.id, Venta.fecha, func.sum(VentaItem.subtotal))).where(*cond_ventas(p, periodo)).group_by(Venta.id, Venta.fecha)
    )).all()
    if not filas:
        return await _sin_ventas(p, periodo)
    por_hora: dict[int, list[float]] = defaultdict(lambda: [0.0, 0])
    for _, fecha, monto in filas:
        acum = por_hora[hora_local(fecha)]
        acum[0] += float(monto)
        acum[1] += 1
    mejor = max(por_hora.items(), key=lambda kv: (kv[1][1], kv[1][0]))
    menor = min(por_hora.items(), key=lambda kv: (kv[1][1], kv[1][0]))
    asc = pide_lo_menor(p.frase)
    elegida = menor if asc else mejor
    hora, (monto, n) = elegida
    texto = (f"{'La hora con menos ventas' if asc else 'La hora en que más se vende'} {p.en_alcance} {p.en_periodo(periodo)} es **{hora:02d}:00 a {hora:02d}:59**: "
             f"{B.n_de(n, 'venta')} por {B.moneda(monto)} ({B.porcentaje(porcentaje_de(n, len(filas)), 0)} de las ventas).")
    pares = [(f"{h:02d}:00", float(v[1]), f"{B.n_de(int(v[1]), 'venta')} · {B.moneda(v[0])}") for h, v in sorted(por_hora.items())]
    orden = sorted(por_hora.items(), key=lambda kv: -kv[1][1])[:3]
    if len(orden) > 1 and not asc:
        texto += " Le siguen " + B.lista_natural([f"{h:02d}:00 ({int(v[1])})" for h, v in orden[1:]]) + "."
    return B.Resp(texto, [B.barras("Ventas por hora del día (hora local)", pares)], enlaces_a(p, "/ventas"), ["¿Qué día se vende más?", "Ventas por vendedor"],
                  ["Las horas se muestran en la zona horaria de la empresa."])


# ======================================================================================================== venta mayor/menor
@manejador("venta_mayor")
async def venta_mayor(p: Peticion) -> B.Resp:
    periodo = await periodo_de_ventas(p)
    asc = pide_lo_menor(p.frase)
    extra = (Venta.estado == "registrada", Venta.fecha_dia >= periodo.desde, Venta.fecha_dia <= periodo.hasta)
    filas = await _ventas_listado(p, extra, p.limite(5), orden=((Venta.total.asc() if asc else Venta.total.desc()), Venta.id.desc()))
    if not filas:
        return await _sin_ventas(p, periodo)
    v = filas[0].Venta
    texto = f"La venta de {'menor' if asc else 'mayor'} valor {p.en_periodo(periodo)} {p.en_alcance} es la **N.º {v.numero}**: **{B.moneda(v.total)}**, el {L.fecha_larga(v.fecha_dia)} en {filas[0].sede}, atendida por {filas[0].vendedor}."
    return B.Resp(texto, [_tabla_ventas(filas)], enlaces_a(p, "/ventas"), [f"Detalle de la venta {v.numero}", "Últimas 10 ventas"])


# ============================================================================================================ promedios
@manejador("ventas_promedio")
async def ventas_promedio(p: Peticion) -> B.Resp:
    periodo = await periodo_de_ventas(p)
    t = await totales_ventas(p, periodo)
    if t.ventas == 0:
        return await _sin_ventas(p, periodo)
    dias_con_ventas = int(await p.db.scalar(desde_ventas(select(func.count(func.distinct(Venta.fecha_dia)))).where(*cond_ventas(p, periodo))) or 0)
    dias = max(1, periodo.dias)
    diario = t.monto / dias
    texto = (f"{p.periodo_inicio(periodo)} el promedio {p.en_alcance} fue de **{B.moneda(diario)} por día** ({B.moneda(t.monto)} en {B.n_de(dias, 'día')}). "
             f"Cada venta promedió **{B.moneda(t.ticket)}** y **{B.decimal(t.unidades / t.ventas, 1)} unidades**.")
    metricas = [("Promedio por día", B.moneda(diario), f"{B.n_de(dias, 'día')} del periodo"), ("Promedio por día con ventas", B.moneda(t.monto / dias_con_ventas) if dias_con_ventas else "—", f"{B.n_de(dias_con_ventas, 'día')} con ventas"),
                ("Ventas por día", B.decimal(t.ventas / dias, 1)), ("Ticket promedio", B.moneda(t.ticket)), ("Unidades por venta", B.decimal(t.unidades / t.ventas, 1)),
                ("Equivale a (30 días)", B.moneda(diario * 30), "si se mantiene el ritmo")]
    return B.Resp(texto, [B.metricas(None, *metricas)], enlaces_a(p, "/ventas"), ["¿Cuánto voy a vender este mes?", "¿Qué día se vende más?", "Ventas por sede"],
                  ["El promedio por día cuenta todos los días del periodo, incluso los que no tuvieron ventas."])


# ============================================================================================================ mis ventas
@manejador("mis_ventas")
async def mis_ventas(p: Peticion) -> B.Resp:
    periodo = p.periodo or await periodo_de_ventas(p)
    yo = Venta.usuario_id == p.ctx.usuario_id
    f = (await p.db.execute(
        desde_ventas(select(func.count(func.distinct(Venta.id)), func.coalesce(func.sum(VentaItem.subtotal), 0), func.coalesce(func.sum(VentaItem.cantidad), 0)))
        .where(*cond_ventas(p, periodo), yo)
    )).one()
    n, monto, unidades = int(f[0]), float(f[1]), int(f[2])
    if n == 0:
        return B.Resp(f"No tienes ventas registradas {p.en_alcance} {p.en_periodo(periodo)}.", sugerencias=["¿Cuánto vendimos este mes?", "Últimas 10 ventas"], enlaces=enlaces_a(p, "/ventas"))
    total = await totales_ventas(p, periodo)
    texto = f"{p.periodo_inicio(periodo)} registraste **{B.n_de(n, 'venta')}** por **{B.moneda(monto)}** ({B.entero(unidades)} unidades), con un ticket promedio de {B.moneda(monto / n)}."
    if total.monto:
        texto += f" Eso es el {B.porcentaje(porcentaje_de(monto, total.monto), 0)} de lo vendido {p.en_alcance} en ese tiempo."
    recientes = await _ventas_listado(p, (Venta.estado == "registrada", yo, Venta.fecha_dia >= periodo.desde, Venta.fecha_dia <= periodo.hasta), 5)
    bloques = [B.metricas(None, ("Mis ventas", B.entero(n)), ("Vendido", B.moneda(monto)), ("Unidades", B.entero(unidades)), ("Ticket promedio", B.moneda(monto / n)))]
    if recientes:
        tabla = _tabla_ventas(recientes)
        tabla.titulo = "Mis últimas ventas"
        bloques.append(tabla)
    return B.Resp(texto, bloques, enlaces_a(p, "/ventas"), ["Mis ventas de hoy", "Mis ventas de la semana pasada", "Ventas por vendedor"])


# ============================================================================================ proyección de cierre de mes
@manejador("ventas_proyeccion")
async def ventas_proyeccion(p: Peticion) -> B.Resp:
    mes = p.este_mes()
    actual = await totales_ventas(p, mes)
    if actual.ventas == 0:
        periodo = await periodo_de_ventas(p)
        t = await totales_ventas(p, periodo)
        if t.ventas == 0:
            return await _sin_ventas(p, mes)
        return B.Resp(f"Este mes todavía no hay ventas registradas {p.en_alcance}, así que no hay con qué proyectar. En {periodo.etiqueta} se vendieron **{B.moneda(t.monto)}** en {B.n_de(t.ventas, 'venta')}.",
                      enlaces=enlaces_a(p, "/ventas"), sugerencias=["¿Cuánto vendimos el mes pasado?", "¿Cuánto voy a vender de BAT-001?"])
    transcurridos = max(1, (p.hoy - mes.desde).days + 1)
    dias_mes = calendar.monthrange(p.hoy.year, p.hoy.month)[1]
    diario = actual.monto / transcurridos
    proyeccion = diario * dias_mes
    anterior = periodo_anterior(L.Periodo(mes.desde, date(p.hoy.year, p.hoy.month, dias_mes), "este mes"))
    ref = await totales_ventas(p, anterior)
    texto = (f"Llevas **{B.moneda(actual.monto)}** en {B.n_de(transcurridos, 'día')} de {L.NOMBRES_MES[p.hoy.month]}. Si mantienes ese ritmo ({B.moneda(diario)} por día), el mes cerraría cerca de **{B.moneda(proyeccion)}**.")
    if ref.monto:
        var = variacion(proyeccion, ref.monto)
        texto += f" El mes anterior cerró en {B.moneda(ref.monto)}" + (f" ({var[0].split(' frente')[0]} con esta proyección)." if var else ".")
    bloques = [B.metricas(None, ("Vendido en el mes", B.moneda(actual.monto), f"{B.n_de(transcurridos, 'día')} de {dias_mes}"), ("Ritmo diario", B.moneda(diario)), ("Cierre proyectado", B.moneda(proyeccion), None, "accent"),
                          ("Mes anterior", B.moneda(ref.monto) if ref.monto else "—"))]
    return B.Resp(texto, bloques, enlaces_a(p, "/ventas", "/predicciones"), ["Promedio de ventas diarias", "Compara con el mes pasado", "¿Cuánto voy a vender de BAT-001?"],
                  ["Es una proyección lineal simple (ritmo diario × días del mes). Para la demanda por producto, pregunta por la predicción."])


# ================================================================================================= última venta de un producto
@manejador("ultima_venta_producto")
async def ultima_venta_producto(p: Peticion) -> B.Resp:
    if not p.producto_ids:
        return B.Resp("¿De qué producto? Dime el nombre o el código, por ejemplo: «¿Cuándo fue la última venta de BAT-001?».", entendida=False)
    ids = p.producto_ids[:6]
    desde30 = L.Periodo(date.fromordinal(p.hoy.toordinal() - 29), p.hoy, "")
    filas = []
    for pid in ids:
        info = p.d.producto(pid)
        if info is None:
            continue
        cond = [Venta.empresa_id == p.ctx.empresa_id, Venta.estado == "registrada", VentaItem.producto_id == pid, *([Venta.sede_id.in_(p.sede_ids)] if p.sede_ids is not None else [])]
        ultima = await p.db.scalar(select(func.max(Venta.fecha_dia)).select_from(Venta).join(VentaItem, VentaItem.venta_id == Venta.id).where(*cond))
        u30 = await p.db.scalar(select(func.coalesce(func.sum(VentaItem.cantidad), 0)).select_from(Venta).join(VentaItem, VentaItem.venta_id == Venta.id).where(*cond, Venta.fecha_dia >= desde30.desde, Venta.fecha_dia <= p.hoy))
        filas.append((info, ultima, int(u30 or 0)))
    if not filas:
        return B.Resp("No encontré ese producto.", entendida=False)
    partes = []
    for info, ultima, _u in filas:
        if ultima is None:
            partes.append(f"**{info.nombre} ({info.codigo})** no tiene ventas registradas {p.en_alcance}")
        else:
            dias = (p.hoy - ultima).days
            partes.append(f"**{info.nombre} ({info.codigo})** se vendió por última vez el {L.fecha_larga(ultima)} ({'hoy' if dias == 0 else 'hace ' + B.n_de(dias, 'día')})")
    texto = "; ".join(partes) + "."
    tabla = B.tabla(None, [B.col("producto", "Producto"), B.col("ultima", "Última venta", "fecha"), B.col("dias", "Días sin vender", "entero"), B.col("u30", "Unidades (30 días)", "entero")],
                    [B.fila({"producto": nombre_producto(i.codigo, i.nombre), "ultima": u, "dias": (p.hoy - u).days if u else None, "u30": x}, ruta="/ventas") for i, u, x in filas])
    return B.Resp(texto, [tabla], enlaces_a(p, "/ventas"), ["Productos sin ventas", "Rotación del inventario"])
