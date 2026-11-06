"""Respuestas ampliadas de inventario y catálogo: rankings de existencias, umbrales, precios, inactivos, clasificación ABC y capital inmovilizado."""

import re
from dataclasses import replace

from sqlalchemy import case, func, select

from app.model.catalogo import Categoria, Producto
from app.model.inventario import InventarioSede
from app.model.operaciones import Venta, VentaItem
from app.service.asistente import bloques as B
from app.service.asistente.analisis import nombre_producto, nota_listado, pide_lo_menor, ultimos
from app.service.asistente.datos import ESTADO_SQL, cond_inventario, cond_ventas, desde_ventas, enlaces_a
from app.service.asistente.peticion import Peticion, cuenta, manejador

_POR_VALOR = re.compile(r"\b(valor|plata|dinero|capital|invertid\w+|inversion|vale|valen|costo|costos)\b")
_MAS_DE = re.compile(r"\b(?:mas|mayor|mayores|superior|superiores|encima) (?:de|que|a|del)?\s*(\d+)")
_MENOS_DE = re.compile(r"\b(?:menos|menor|menores|inferior|inferiores|debajo) (?:de|que|a|del)?\s*(\d+)")
_ENTRE = re.compile(r"\bentre (\d+) y (\d+)")
_COSTO_PALABRA = re.compile(r"\bcostos?\b")
_PRECIO_PALABRA = re.compile(r"\bprecios?\b")
_CLASE = re.compile(r"\bclase ([abc])\b")


def _valor_sql():
    return func.coalesce(func.sum(case((Producto.costo.is_not(None), InventarioSede.cantidad * Producto.costo), else_=0)), 0)


# ================================================================================================ ranking de existencias
@manejador("ranking_stock")
async def ranking_stock(p: Peticion) -> B.Resp:
    por_valor = bool(_POR_VALOR.search(p.frase))
    asc = pide_lo_menor(p.frase)
    unidades, valor = func.coalesce(func.sum(InventarioSede.cantidad), 0), _valor_sql()
    consulta = (
        select(Producto.id, Producto.codigo, Producto.nombre, Categoria.nombre.label("categoria"), unidades.label("u"), valor.label("v"))
        .select_from(InventarioSede)
        .join(Producto, Producto.id == InventarioSede.producto_id)
        .join(Categoria, Categoria.id == Producto.categoria_id)
        .where(*cond_inventario(p))
        .group_by(Producto.id, Producto.codigo, Producto.nombre, Categoria.nombre)
    )
    medida = valor if por_valor else unidades
    consulta = consulta.order_by(medida.asc() if asc else medida.desc(), Producto.nombre)
    total = int(await p.db.scalar(cuenta(consulta)) or 0)
    if total == 0:
        return B.Resp(f"No hay existencias registradas {p.en_alcance} para armar el ranking.", sugerencias=["¿Cómo está el inventario?"])
    filas = (await p.db.execute(consulta.limit(p.limite(10)))).all()
    primero = filas[0]
    cual = "menos" if asc else "más"
    if por_valor:
        texto = f"El producto con {cual} valor en inventario {p.en_alcance} es **{nombre_producto(primero.codigo, primero.nombre)}**: **{B.moneda(primero.v)}** a costo ({B.entero(primero.u)} unidades)."
    else:
        texto = f"El producto con {cual} existencias {p.en_alcance} es **{nombre_producto(primero.codigo, primero.nombre)}**: **{B.entero(primero.u)} unidades**."
        if asc and primero.u == 0:
            agotados = sum(1 for f in filas if f.u == 0)
            texto += f" Hay **{B.n_de(agotados, 'producto')} sin ninguna unidad** entre los primeros de la lista."
    tabla = B.tabla(
        f"{'Menor' if asc else 'Mayor'} {'valor' if por_valor else 'existencias'}",
        [B.col("producto", "Producto"), B.col("categoria", "Categoría"), B.col("unidades", "Existencias", "entero"), B.col("valor", "Valor a costo", "moneda")],
        [B.fila({"producto": nombre_producto(f.codigo, f.nombre), "categoria": f.categoria, "unidades": int(f.u), "valor": float(f.v)}, ruta="/inventario") for f in filas],
        total=total, nota=nota_listado(len(filas), total, "productos"),
    )
    return B.Resp(texto, [tabla], enlaces_a(p, "/inventario"), ["¿Qué productos están agotados?", "Valor del inventario", "¿Qué tengo en exceso?"])


@manejador("stock_umbral")
async def stock_umbral(p: Peticion) -> B.Resp:
    if p.producto_ids and not p.e.producto_exacto:  # las cifras de la frase («10 y 50») se parecen a nombres como «10 pulgadas»: no son un producto
        p = replace(p, producto_ids=[])
    f = p.frase
    entre, mas, menos = _ENTRE.search(f), _MAS_DE.search(f), _MENOS_DE.search(f)
    unidades = func.coalesce(func.sum(InventarioSede.cantidad), 0)
    if entre:
        bajo, alto = sorted((int(entre.group(1)), int(entre.group(2))))
        condicion, descripcion = [unidades >= bajo, unidades <= alto], f"entre {B.entero(bajo)} y {B.entero(alto)} unidades"
    elif mas and (not menos or mas.start() < menos.start()):
        condicion, descripcion = [unidades > int(mas.group(1))], f"más de {B.entero(int(mas.group(1)))} unidades"
    elif menos:
        condicion, descripcion = [unidades < int(menos.group(1))], f"menos de {B.entero(int(menos.group(1)))} unidades"
    else:
        return B.Resp("¿Con qué cantidad? Por ejemplo: «productos con más de 100 unidades» o «productos con menos de 20 unidades».", sugerencias=["Productos con más de 100 unidades", "Productos con menos de 20 unidades"], entendida=False)
    consulta = (
        select(Producto.id, Producto.codigo, Producto.nombre, unidades.label("u"), _valor_sql().label("v"))
        .select_from(InventarioSede).join(Producto, Producto.id == InventarioSede.producto_id)
        .where(*cond_inventario(p)).group_by(Producto.id, Producto.codigo, Producto.nombre).having(*condicion)
        .order_by(unidades.asc() if menos and not mas else unidades.desc(), Producto.nombre)
    )
    total = int(await p.db.scalar(cuenta(consulta)) or 0)
    if total == 0:
        return B.Resp(f"Ningún producto {p.con_filtro('').strip()} tiene {descripcion} {p.en_alcance}.".replace("  ", " "), sugerencias=["¿Qué producto tiene más existencias?", "¿Cómo está el inventario?"])
    filas = (await p.db.execute(consulta.limit(p.limite(15)))).all()
    texto = f"**{B.n_de(total, 'producto')}** {'tiene' if total == 1 else 'tienen'} {descripcion} {p.en_alcance}."
    if p.sede_ids is None or len(p.sede_ids) > 1:
        texto += " (Se suman las existencias de todas las sedes de cada producto.)"
    tabla = B.tabla(None, [B.col("producto", "Producto"), B.col("unidades", "Existencias", "entero"), B.col("valor", "Valor a costo", "moneda")],
                    [B.fila({"producto": nombre_producto(x.codigo, x.nombre), "unidades": int(x.u), "valor": float(x.v)}, ruta="/inventario") for x in filas],
                    total=total, nota=nota_listado(len(filas), total, "productos"))
    return B.Resp(texto, [tabla], enlaces_a(p, "/inventario"), ["¿Qué producto tiene más existencias?", "Productos con stock bajo"])


# =================================================================================================== precios y catálogo
def _filtro_catalogo(p: Peticion) -> list:
    c = [Producto.empresa_id == p.ctx.empresa_id, Producto.activo.is_(True)]
    if p.producto_ids:
        c.append(Producto.id.in_(p.producto_ids))
    if p.categoria_ids:
        c.append(Producto.categoria_id.in_(p.categoria_ids))
    return c


def _tabla_precios(filas, titulo: str | None, total: int):
    columnas = [B.col("producto", "Producto"), B.col("categoria", "Categoría"), B.col("costo", "Costo", "moneda"), B.col("precio", "Precio de venta", "moneda"), B.col("margen", "Margen", "porcentaje")]
    salida = []
    for f in filas:
        costo, precio = (float(f.costo) if f.costo is not None else None), (float(f.precio_venta) if f.precio_venta is not None else None)
        margen = ((precio - costo) / precio * 100) if costo is not None and precio else None
        salida.append(B.fila({"producto": nombre_producto(f.codigo, f.nombre), "categoria": f.categoria, "costo": costo, "precio": precio, "margen": round(margen, 1) if margen is not None else None}, ruta="/productos"))
    return B.tabla(titulo, columnas, salida, total=total, nota=nota_listado(len(filas), total, "productos"))


@manejador("ranking_precio")
async def ranking_precio(p: Peticion) -> B.Resp:
    barato = pide_lo_menor(p.frase)
    usa_costo = bool(_COSTO_PALABRA.search(p.frase)) and not _PRECIO_PALABRA.search(p.frase)
    columna = Producto.costo if usa_costo else Producto.precio_venta
    base = (
        select(Producto.codigo, Producto.nombre, Producto.costo, Producto.precio_venta, Categoria.nombre.label("categoria"))
        .join(Categoria, Categoria.id == Producto.categoria_id).where(*_filtro_catalogo(p), columna.is_not(None))
    )
    total = int(await p.db.scalar(cuenta(base)) or 0)
    if total == 0:
        return B.Resp(f"No hay productos con {'costo' if usa_costo else 'precio'} registrado para comparar.", enlaces=enlaces_a(p, "/productos"))
    medida = "costo" if usa_costo else "precio de venta"
    if re.search(r"\b(mas|menos) (caro|cara|costoso|costosa)\b|\bmayor precio\b", p.frase) and re.search(r"\b(mas|menos) (barato|barata)\b|\bmenor precio\b|\bmas economic\w+", p.frase):
        caro = (await p.db.execute(base.order_by(columna.desc(), Producto.nombre).limit(1))).one()  # piden los dos extremos: «el más caro y el más barato»
        barato_ = (await p.db.execute(base.order_by(columna.asc(), Producto.nombre).limit(1))).one()
        v = (lambda f: f.costo if usa_costo else f.precio_venta)
        texto = (f"El más caro (por {medida}) es **{nombre_producto(caro.codigo, caro.nombre)}**, a **{B.moneda(v(caro))}**, y el más barato es "
                 f"**{nombre_producto(barato_.codigo, barato_.nombre)}**, a **{B.moneda(v(barato_))}**.")
        return B.Resp(texto, [_tabla_precios([caro, barato_], "Más caro y más barato", 2)], enlaces_a(p, "/productos"), ["Lista de precios", "¿Qué productos tienen mayor margen?"])
    filas = (await p.db.execute(base.order_by(columna.asc() if barato else columna.desc(), Producto.nombre).limit(p.limite(8)))).all()
    primero = filas[0]
    valor = primero.costo if usa_costo else primero.precio_venta
    texto = f"El producto {p.descripcion_filtro() + ' ' if p.hay_categoria else ''}{'más barato' if barato else 'más caro'} (por {medida}) es **{nombre_producto(primero.codigo, primero.nombre)}**, a **{B.moneda(valor)}**."
    avisos = []
    sin = int(await p.db.scalar(select(func.count()).select_from(Producto).where(*_filtro_catalogo(p), columna.is_(None))) or 0)
    if sin:
        avisos.append(f"{B.n_de(sin, 'producto')} no tiene {medida} registrado y no entra en el ranking.")
    return B.Resp(texto, [_tabla_precios(filas, "Más baratos" if barato else "Más caros", total)], enlaces_a(p, "/productos"), ["Lista de precios", "¿Qué productos tienen mayor margen?"], avisos)


@manejador("lista_precios")
async def lista_precios(p: Peticion) -> B.Resp:
    base = (
        select(Producto.codigo, Producto.nombre, Producto.costo, Producto.precio_venta, Categoria.nombre.label("categoria"))
        .join(Categoria, Categoria.id == Producto.categoria_id).where(*_filtro_catalogo(p)).order_by(Categoria.nombre, Producto.nombre)
    )
    total = int(await p.db.scalar(cuenta(base)) or 0)
    if total == 0:
        return B.Resp(f"No hay productos activos {p.descripcion_filtro()} para mostrar.".replace("  ", " "), enlaces=enlaces_a(p, "/productos"))
    filas = (await p.db.execute(base.limit(p.limite(15)))).all()
    sin_precio = sum(1 for f in filas if f.precio_venta is None)
    texto = f"Estos son los costos y precios de venta {p.descripcion_filtro() or 'de los productos activos'} ({B.n_de(total, 'producto')})."
    avisos = [f"{B.n_de(sin_precio, 'producto')} de los mostrados no tiene precio de venta registrado."] if sin_precio else []
    return B.Resp(texto, [_tabla_precios(filas, None, total)], enlaces_a(p, "/productos"), ["¿Cuál es el producto más caro?", "¿Qué productos tienen mayor margen?"], avisos)


@manejador("productos_inactivos")
async def productos_inactivos(p: Peticion) -> B.Resp:
    base = (
        select(Producto.codigo, Producto.nombre, Categoria.nombre.label("categoria"))
        .join(Categoria, Categoria.id == Producto.categoria_id)
        .where(Producto.empresa_id == p.ctx.empresa_id, Producto.activo.is_(False), *([Producto.categoria_id.in_(p.categoria_ids)] if p.categoria_ids else []))
        .order_by(Producto.nombre)
    )
    total = int(await p.db.scalar(cuenta(base)) or 0)
    activos = int(await p.db.scalar(select(func.count()).select_from(Producto).where(Producto.empresa_id == p.ctx.empresa_id, Producto.activo.is_(True))) or 0)
    if total == 0:
        return B.Resp(f"No hay productos inactivos: los **{B.entero(activos)} productos** del catálogo están activos.", enlaces=enlaces_a(p, "/productos"), sugerencias=["¿Cuántos productos manejamos?"])
    filas = (await p.db.execute(base.limit(p.limite(15)))).all()
    tabla = B.tabla(None, [B.col("producto", "Producto"), B.col("categoria", "Categoría")], [B.fila({"producto": nombre_producto(f.codigo, f.nombre), "categoria": f.categoria}, ruta="/productos") for f in filas],
                    total=total, nota=nota_listado(len(filas), total, "productos"))
    return B.Resp(f"Hay **{B.n_de(total, 'producto')} inactivo{'' if total == 1 else 's'}** (deshabilitados) y {B.entero(activos)} activos. Los inactivos no se pueden vender ni mover.", [tabla], enlaces_a(p, "/productos"))


@manejador("productos_sin_minimo")
async def productos_sin_minimo(p: Peticion) -> B.Resp:
    maximo = bool(re.search(r"\bmaximo\b", p.frase)) and not re.search(r"\bminimo\b", p.frase)
    condicion = InventarioSede.stock_maximo.is_(None) if maximo else InventarioSede.stock_minimo <= 0
    nombre = "máximo" if maximo else "mínimo"
    consulta = (
        select(Producto.codigo, Producto.nombre, func.count().label("sedes"), func.coalesce(func.sum(InventarioSede.cantidad), 0).label("u"))
        .select_from(InventarioSede).join(Producto, Producto.id == InventarioSede.producto_id)
        .where(*cond_inventario(p), condicion).group_by(Producto.codigo, Producto.nombre).order_by(func.count().desc(), Producto.nombre)
    )
    total = int(await p.db.scalar(cuenta(consulta)) or 0)
    if total == 0:
        return B.Resp(f"Todos los productos {p.en_alcance} tienen stock {nombre} configurado.", enlaces=enlaces_a(p, "/inventario"))
    filas = (await p.db.execute(consulta.limit(p.limite(15)))).all()
    tabla = B.tabla(None, [B.col("producto", "Producto"), B.col("sedes", "Sedes sin " + nombre, "entero"), B.col("unidades", "Existencias", "entero")],
                    [B.fila({"producto": nombre_producto(f.codigo, f.nombre), "sedes": int(f.sedes), "unidades": int(f.u)}, ruta="/inventario") for f in filas],
                    total=total, nota=nota_listado(len(filas), total, "productos"))
    texto = f"**{B.n_de(total, 'producto')}** {'no tiene' if total == 1 else 'no tienen'} stock {nombre} configurado en al menos una sede {p.en_alcance}."
    if not maximo:
        texto += " Sin mínimo, el sistema no puede avisar cuando el producto se está acabando."
    return B.Resp(texto, [tabla], enlaces_a(p, "/inventario"), ["¿Qué productos tienen stock bajo?"])


# ===================================================================================================== clasificación ABC
@manejador("abc_inventario")
async def abc_inventario(p: Peticion) -> B.Resp:
    periodo = ultimos(p, 90)
    ventas = (await p.db.execute(
        desde_ventas(select(Producto.id, Producto.codigo, Producto.nombre, func.coalesce(func.sum(VentaItem.subtotal), 0).label("m"), func.coalesce(func.sum(VentaItem.cantidad), 0).label("u")))
        .where(*cond_ventas(p, periodo)).group_by(Producto.id, Producto.codigo, Producto.nombre).order_by(func.sum(VentaItem.subtotal).desc(), Producto.nombre)
    )).all()
    total_monto = sum(float(f.m) for f in ventas)
    if not ventas or total_monto <= 0:
        return B.Resp(f"No hay ventas {p.en_alcance} {p.en_periodo(periodo)} para clasificar los productos.", sugerencias=["¿Cuánto vendimos este mes?"])
    con_ventas = {f.id for f in ventas}
    activos = [x for x in p.d.productos if x.activo and (not p.categoria_ids or x.categoria_id in p.categoria_ids) and x.id not in con_ventas]
    acumulado, clasificados = 0.0, []
    for f in ventas:
        clase = "A" if acumulado < 0.80 * total_monto else ("B" if acumulado < 0.95 * total_monto else "C")
        acumulado += float(f.m)
        clasificados.append((f, clase, acumulado / total_monto * 100))
    resumen = {c: [x for x in clasificados if x[1] == c] for c in "ABC"}
    metricas = []
    for c, descr in (("A", "≈80 % de las ventas"), ("B", "≈15 % siguiente"), ("C", "≈5 % restante")):
        monto = sum(float(x[0].m) for x in resumen[c])
        metricas.append((f"Clase {c}", f"{B.n_de(len(resumen[c]), 'producto')}", f"{B.porcentaje(monto / total_monto * 100, 0)} de las ventas · {descr}"))
    metricas.append(("Sin ventas", B.n_de(len(activos), "producto"), "activos sin ventas en el periodo", "warning" if activos else "neutral"))  # type: ignore[arg-type]
    pedida = _CLASE.search(p.frase)
    mostrar = resumen[pedida.group(1).upper()] if pedida else resumen["A"]
    etiqueta = pedida.group(1).upper() if pedida else "A"
    mostrar = mostrar[: p.limite(10)]
    texto = (f"Clasificación ABC por ventas {p.en_alcance} {p.en_periodo(periodo)}: **{B.n_de(len(resumen['A']), 'producto')}** de clase A generan cerca del 80 % de lo vendido "
             f"({B.moneda(sum(float(x[0].m) for x in resumen['A']))} de {B.moneda(total_monto)}), {len(resumen['B'])} de clase B y {len(resumen['C'])} de clase C.")
    if activos:
        texto += f" Además, **{B.n_de(len(activos), 'producto')} activo{'' if len(activos) == 1 else 's'}** no vendió nada en ese tiempo."
    tabla = B.tabla(
        f"Productos de clase {etiqueta}", [B.col("producto", "Producto"), B.col("monto", "Vendido", "moneda"), B.col("unidades", "Unidades", "entero"), B.col("acum", "% acumulado", "porcentaje")],
        [B.fila({"producto": nombre_producto(f.codigo, f.nombre), "monto": float(f.m), "unidades": int(f.u), "acum": round(a, 1)}, ruta="/ventas") for f, _, a in mostrar],
        total=len(resumen[etiqueta]), nota=nota_listado(len(mostrar), len(resumen[etiqueta]), "productos"))
    return B.Resp(texto, [B.metricas("Clasificación ABC", *metricas), tabla], enlaces_a(p, "/ventas", "/inventario"), ["Productos sin ventas", "Rotación del inventario", "Productos de clase C"],
                  ["La clasificación ABC se calcula por el valor vendido en el periodo (principio de Pareto): A = productos que suman el 80 % de las ventas, B = hasta el 95 %, C = el resto."])


# ============================================================================================== capital inmovilizado
@manejador("capital_inmovilizado")
async def capital_inmovilizado(p: Peticion) -> B.Resp:
    costo = func.coalesce(Producto.costo, 0)
    exceso = (await p.db.execute(
        select(func.count(), func.coalesce(func.sum(InventarioSede.cantidad * costo), 0), func.coalesce(func.sum((InventarioSede.cantidad - InventarioSede.stock_maximo) * costo), 0))
        .select_from(InventarioSede).join(Producto, Producto.id == InventarioSede.producto_id).where(*cond_inventario(p), ESTADO_SQL == "excesivo")
    )).one()
    bloques, partes, avisos = [], [], []
    metricas = [("Stock excesivo (a costo)", B.moneda(exceso[1]), f"{B.n_de(int(exceso[0]), 'producto')} por sede sobre su máximo", "accent" if exceso[0] else "neutral")]
    partes.append(f"**{B.moneda(exceso[1])}** en stock excesivo (de los cuales **{B.moneda(exceso[2])}** son el excedente sobre el máximo)")
    sin_venta_valor = None
    if p.tiene("ventas.ver"):
        periodo = ultimos(p, 90)
        vendidos = select(VentaItem.producto_id).join(Venta, Venta.id == VentaItem.venta_id).where(
            Venta.empresa_id == p.ctx.empresa_id, Venta.estado == "registrada", Venta.fecha_dia >= periodo.desde, Venta.fecha_dia <= periodo.hasta,
            *([Venta.sede_id.in_(p.sede_ids)] if p.sede_ids is not None else []))
        parados = (await p.db.execute(
            select(Producto.id, Producto.codigo, Producto.nombre, func.sum(InventarioSede.cantidad).label("u"), func.sum(InventarioSede.cantidad * costo).label("v"))
            .select_from(InventarioSede).join(Producto, Producto.id == InventarioSede.producto_id)
            .where(*cond_inventario(p), InventarioSede.cantidad > 0, Producto.id.not_in(vendidos)).group_by(Producto.id, Producto.codigo, Producto.nombre).order_by(func.sum(InventarioSede.cantidad * costo).desc())
        )).all()
        sin_venta_valor = sum(float(f.v or 0) for f in parados)
        metricas.append(("Sin ventas en el periodo (a costo)", B.moneda(sin_venta_valor), f"{B.n_de(len(parados), 'referencia')} · {periodo.etiqueta}", "warning" if parados else "neutral"))  # type: ignore[arg-type]
        partes.append(f"**{B.moneda(sin_venta_valor)}** en {B.n_de(len(parados), 'producto')} que no se vendieron {p.en_periodo(periodo)}")
        if parados:
            bloques.append(B.tabla("Productos con existencias y sin ventas (mayor valor primero)", [B.col("producto", "Producto"), B.col("u", "Existencias", "entero"), B.col("v", "Valor a costo", "moneda")],
                                   [B.fila({"producto": nombre_producto(f.codigo, f.nombre), "u": int(f.u), "v": float(f.v or 0)}, ruta="/inventario") for f in parados[: p.limite(8)]],
                                   total=len(parados), nota=nota_listado(min(len(parados), p.limite(8)), len(parados), "productos")))
        avisos.append("Los dos montos pueden solaparse (un producto puede estar en exceso y sin ventas), por eso no se suman.")
    else:
        avisos.append("Con tu rol no puedo consultar ventas, así que solo calculo el exceso de stock.")
    sin_costo = int(await p.db.scalar(select(func.count()).select_from(InventarioSede).join(Producto, Producto.id == InventarioSede.producto_id).where(*cond_inventario(p), Producto.costo.is_(None), InventarioSede.cantidad > 0)) or 0)
    if sin_costo:
        avisos.append(f"{B.n_de(sin_costo, 'registro')} de inventario sin costo no suma(n) a los valores.")
    texto = f"Capital parado {p.en_alcance}: " + " y ".join(partes) + "."
    return B.Resp(texto, [B.metricas(None, *metricas), *bloques], enlaces_a(p, "/inventario", "/recomendaciones"), ["¿Qué tengo en exceso?", "Productos sin ventas", "¿Cómo reduzco el inventario?"], avisos)
