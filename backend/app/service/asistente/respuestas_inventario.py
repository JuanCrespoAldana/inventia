"""Respuestas sobre existencias, valor del inventario y catálogo de productos."""

import re

from sqlalchemy import case, func, select

from app.model.catalogo import Categoria, Producto
from app.model.inventario import InventarioSede
from app.model.sede import Sede
from app.service.asistente import bloques as B
from app.service.asistente.datos import (
    ESTADO_SQL,
    cond_inventario,
    enlaces_a,
    totales_inventario,
)
from app.service.asistente.peticion import Peticion, manejador

_MAX_FILAS = 15


def _nombre_producto(codigo: str, nombre: str) -> str:
    return f"{nombre} ({codigo})"


def _tabla_stock(titulo: str | None, filas, *, con_sede: bool, total: int, nota: str | None = None):
    columnas = [B.col("producto", "Producto")]
    if con_sede:
        columnas.append(B.col("sede", "Sede"))
    columnas += [B.col("cantidad", "Cantidad", "entero"), B.col("minimo", "Mínimo", "entero"), B.col("maximo", "Máximo", "entero"), B.col("estado", "Estado")]
    salida = []
    for f in filas:
        etiqueta, tono = B.ESTADO_STOCK[f.estado]
        celdas = {"producto": _nombre_producto(f.codigo, f.nombre), "cantidad": f.cantidad, "minimo": f.stock_minimo, "maximo": f.stock_maximo, "estado": etiqueta}
        if con_sede:
            celdas["sede"] = f.sede
        salida.append(B.fila(celdas, tonos={"estado": tono}, ruta="/inventario"))
    return B.tabla(titulo, columnas, salida, total=total, nota=nota)


async def _filas_stock(p: Peticion, extra: tuple = (), orden=(), limite: int | None = None):
    consulta = (
        select(
            Producto.id.label("producto_id"), Producto.codigo, Producto.nombre, Producto.costo, Producto.categoria_id,
            Sede.id.label("sede_id"), Sede.nombre.label("sede"),
            InventarioSede.cantidad, InventarioSede.stock_minimo, InventarioSede.stock_maximo, ESTADO_SQL.label("estado"),
        )
        .select_from(InventarioSede)
        .join(Producto, Producto.id == InventarioSede.producto_id)
        .join(Sede, Sede.id == InventarioSede.sede_id)
        .where(*cond_inventario(p), *extra)
        .order_by(*orden, Producto.nombre, Sede.nombre)
    )
    if limite:
        consulta = consulta.limit(limite)
    return (await p.db.execute(consulta)).all()


async def _contar_filas(p: Peticion, extra: tuple = ()) -> int:
    consulta = (
        select(func.count())
        .select_from(InventarioSede)
        .join(Producto, Producto.id == InventarioSede.producto_id)
        .where(*cond_inventario(p), *extra)
    )
    return int(await p.db.scalar(consulta) or 0)


def _sugerir_productos(p: Peticion, cuantos: int = 3) -> list[str]:
    activos = [x for x in p.d.productos if x.activo][:cuantos]
    return [f"¿Cuánto hay de {x.nombre}?" for x in activos]


# ----------------------------------------------------------------------------------------------------- resúmenes
@manejador("resumen_inventario")
async def resumen_inventario(p: Peticion) -> B.Resp:
    t = (await totales_inventario(p))[None]
    objetivo = p.con_filtro("el inventario")
    if t.unidades == 0 and t.agotados == 0 and t.bajos == 0 and t.normales == 0 and t.excesivos == 0:
        return B.Resp(f"No hay existencias registradas {p.en_alcance} para {objetivo}.", sugerencias=["¿Qué productos hay?"])
    if p.hay_producto or p.hay_categoria:
        texto = f"En {p.alcance.lower() if p.sede_ids is None else p.alcance}, {objetivo} suma **{B.entero(t.unidades)} unidades** en **{B.n_de(t.referencias, 'referencia')}**, valoradas en **{B.moneda(t.valor)}**."
    else:
        texto = f"{B.mayuscula_inicial(p.en_alcance)} hay **{B.entero(t.unidades)} unidades** en **{B.n_de(t.referencias, 'referencia')}** con existencias, valoradas en **{B.moneda(t.valor)}**."
    bloques = [
        B.metricas(
            None,
            ("Unidades", B.entero(t.unidades)),
            ("Referencias con stock", B.entero(t.referencias)),
            ("Valor del inventario", B.moneda(t.valor), f"{B.n_de(t.sin_costo, 'referencia')} sin costo" if t.sin_costo else None),
            ("Agotados", B.entero(t.agotados), None, "danger" if t.agotados else "neutral"),
            ("Stock bajo", B.entero(t.bajos), None, "warning" if t.bajos else "neutral"),
            ("Excesivos", B.entero(t.excesivos), None, "accent" if t.excesivos else "neutral"),
        )
    ]
    avisos = []
    if t.sin_costo:
        avisos.append(f"El valor no incluye {B.n_de(t.sin_costo, 'referencia')} sin costo registrado.")
    if t.agotados or t.bajos:
        texto += f" Ojo: hay **{B.n_de(t.agotados, 'producto')} agotado{'' if t.agotados == 1 else 's'}** y **{B.n_de(t.bajos, 'producto')} con stock bajo** (contando cada producto por sede)."
    if (p.sede_ids is None or len(p.sede_ids) > 1) and not p.hay_producto:
        por_sede = await totales_inventario(p, agrupar_por=InventarioSede.sede_id)
        filas = [
            B.fila({"sede": s.nombre, "unidades": por_sede[s.id].unidades, "valor": por_sede[s.id].valor, "agotados": por_sede[s.id].agotados, "bajos": por_sede[s.id].bajos},
                   ruta="/inventario")
            for s in p.d.sedes if s.id in por_sede and (p.sede_ids is None or s.id in p.sede_ids)
        ]
        if len(filas) > 1:
            bloques.append(B.tabla("Por sede", [B.col("sede", "Sede"), B.col("unidades", "Unidades", "entero"), B.col("valor", "Valor", "moneda"), B.col("agotados", "Agotados", "entero"), B.col("bajos", "Stock bajo", "entero")], filas))
    return B.Resp(
        texto, bloques, enlaces_a(p, "/inventario", "/inventario/consolidado"),
        ["¿Qué productos están agotados?", "¿Qué productos tienen stock bajo?", "Valor del inventario por categoría", "¿Qué tengo en exceso?"], avisos,
    )


@manejador("valor_inventario")
async def valor_inventario(p: Peticion) -> B.Resp:
    t = (await totales_inventario(p))[None]
    objetivo = p.con_filtro("el inventario")
    if t.unidades == 0:
        return B.Resp(f"No hay existencias {p.en_alcance} para valorar {objetivo}.")
    texto = f"El valor {p.con_filtro('del inventario')} {p.en_alcance} es de **{B.moneda(t.valor)}** (**{B.entero(t.unidades)} unidades** valoradas a su costo de compra)."
    bloques = [B.metricas(None, ("Valor a costo", B.moneda(t.valor)), ("Unidades", B.entero(t.unidades)), ("Costo promedio por unidad", B.moneda(t.valor / t.unidades if t.unidades else 0)))]
    avisos = []
    if t.sin_costo:
        avisos.append(f"{B.n_de(t.sin_costo, 'referencia')} con existencias no tiene costo registrado, así que no suma al valor. Regístralo en Productos para un valor completo.")
    # Por sede y por categoría (cuando aplica).
    if not p.hay_producto:
        por_cat = await totales_inventario(p, agrupar_por=Producto.categoria_id)
        nombres = {c.id: c.nombre for c in p.d.categorias}
        filas_cat = sorted(
            ((nombres.get(i, "—"), v) for i, v in por_cat.items()), key=lambda par: par[1].valor, reverse=True
        )
        if len(filas_cat) > 1 and not p.hay_categoria:
            bloques.append(B.barras("Valor por categoría", [(n, v.valor, B.moneda(v.valor)) for n, v in filas_cat if v.valor > 0]))
        if p.sede_ids is None or len(p.sede_ids) > 1:
            por_sede = await totales_inventario(p, agrupar_por=InventarioSede.sede_id)
            pares = [(s.nombre, por_sede[s.id].valor, B.moneda(por_sede[s.id].valor)) for s in p.d.sedes if s.id in por_sede]
            if len(pares) > 1:
                bloques.append(B.barras("Valor por sede", sorted(pares, key=lambda x: x[1], reverse=True)))
    return B.Resp(texto, bloques, enlaces_a(p, "/inventario/consolidado", "/inventario"), ["¿Qué tengo en exceso?", "Inventario por categoría", "¿Cuál es el margen de los productos?"], avisos)


# ---------------------------------------------------------------------------------------------- por producto/sede
@manejador("stock_producto")
async def stock_producto(p: Peticion) -> B.Resp:
    if not p.hay_producto:
        if p.hay_categoria:
            return await inventario_categoria(p)
        palabras = f" «{' '.join(p.e.sin_resolver)}»" if p.e.sin_resolver else ""
        return B.Resp(
            f"No encontré en el catálogo un producto que coincida con{palabras or ' tu pregunta'}. Prueba con el nombre o el código (por ejemplo, BAT-004).",
            sugerencias=[*_sugerir_productos(p), "¿Qué productos manejamos?"], entendida=True,
        )
    filas = await _filas_stock(p)
    if not filas:
        return B.Resp(f"No hay existencias registradas de {p.descripcion_filtro().removeprefix('de ')} {p.en_alcance}.", sugerencias=["¿Qué productos están agotados?"])
    total = sum(f.cantidad for f in filas)
    productos = {f.producto_id: f for f in filas}
    bloques = []
    if len(productos) == 1:
        f0 = filas[0]
        nombre = _nombre_producto(f0.codigo, f0.nombre)
        partes = [f"{f.sede} {B.entero(f.cantidad)}" for f in filas]
        texto = f"De **{nombre}** hay **{B.entero(total)} unidades** {p.en_alcance}"
        texto += (": " + ", ".join(partes) + ".") if len(filas) > 1 else "."
        problemas = [f for f in filas if f.estado in ("agotado", "bajo")]
        if problemas:
            texto += " Atención: " + "; ".join(f"en {f.sede} está {B.ESTADO_STOCK[f.estado][0].lower()}" for f in problemas[:3]) + "."
        bloques.append(B.metricas(None, ("Total", B.entero(total)), ("Sedes con stock", B.entero(sum(1 for f in filas if f.cantidad > 0)))))
        if len(filas) > 1:
            bloques.append(_tabla_stock("Existencias por sede", filas, con_sede=True, total=len(filas)).model_copy(update={"columnas": [c for c in _tabla_stock(None, filas, con_sede=True, total=0).columnas if c.clave != "producto"]}))
        else:
            bloques.append(_tabla_stock(None, filas, con_sede=False, total=len(filas)))
    else:
        por_producto: dict[int, int] = {}
        for f in filas:
            por_producto[f.producto_id] = por_producto.get(f.producto_id, 0) + f.cantidad
        texto = f"Encontré **{len(productos)} productos** que coinciden; en total hay **{B.entero(total)} unidades** {p.en_alcance}."
        orden = sorted(productos.values(), key=lambda f: -por_producto[f.producto_id])
        tabla_filas = [
            B.fila({"producto": _nombre_producto(f.codigo, f.nombre), "cantidad": por_producto[f.producto_id]}, ruta="/inventario") for f in orden[:_MAX_FILAS]
        ]
        bloques.append(B.tabla("Existencias por producto", [B.col("producto", "Producto"), B.col("cantidad", "Unidades", "entero")], tabla_filas, total=len(orden)))
        if len(orden) > _MAX_FILAS:
            texto += f" Te muestro los {_MAX_FILAS} con más unidades; sé más específico para ver uno solo."
    return B.Resp(texto, bloques, enlaces_a(p, "/inventario"), ["¿Qué productos están agotados?", "¿Cuántos días me dura?", "¿Cuánto cuesta?"])


@manejador("niveles_producto")
async def niveles_producto(p: Peticion) -> B.Resp:
    if not p.hay_producto:
        return B.Resp(
            "El stock **mínimo** es la cantidad a partir de la cual el producto se considera en nivel bajo, y el **máximo** el tope a partir del cual hay exceso. "
            "Dime de qué producto quieres saberlos, por ejemplo: «stock mínimo de BAT-004».", sugerencias=_sugerir_productos(p),
        )
    filas = await _filas_stock(p)
    if not filas:
        return B.Resp("No hay niveles registrados para ese producto en tu alcance.")
    productos = {f.producto_id for f in filas}
    cols = [B.col("producto", "Producto"), B.col("sede", "Sede"), B.col("minimo", "Mínimo", "entero"), B.col("maximo", "Máximo", "entero"), B.col("cantidad", "Hay ahora", "entero")]
    tabla_filas = [
        B.fila({"producto": _nombre_producto(f.codigo, f.nombre), "sede": f.sede, "minimo": f.stock_minimo, "maximo": f.stock_maximo if f.stock_maximo is not None else "Sin tope", "cantidad": f.cantidad}, ruta="/inventario")
        for f in filas[:30]
    ]
    sin_nivel = sum(1 for f in filas if f.stock_minimo == 0)
    texto = f"Estos son los niveles de {p.descripcion_filtro().removeprefix('de ')} {p.en_alcance}."
    if len(productos) == 1 and len(filas) == 1:
        f = filas[0]
        maximo = f"{B.entero(f.stock_maximo)}" if f.stock_maximo is not None else "sin tope definido"
        texto = f"En **{f.sede}**, **{_nombre_producto(f.codigo, f.nombre)}** tiene mínimo **{B.entero(f.stock_minimo)}** y máximo **{maximo}**; hoy hay **{B.entero(f.cantidad)}** ({B.ESTADO_STOCK[f.estado][0].lower()})."
    avisos = ["Hay sedes donde el mínimo es 0: sin mínimo, el sistema no puede avisar de stock bajo."] if sin_nivel else []
    return B.Resp(texto, [B.tabla(None, cols, tabla_filas, total=len(filas))], enlaces_a(p, "/inventario"), ["¿Qué productos tienen stock bajo?"], avisos)


# ------------------------------------------------------------------------------------------------------ listados
async def _listado_estado(p: Peticion, estado: str) -> B.Resp:
    extra = (ESTADO_SQL == estado,)  # noqa: SIM300
    total = await _contar_filas(p, extra)
    etiqueta = {"agotado": "agotados", "bajo": "con stock bajo", "excesivo": "con exceso de stock"}[estado]
    if total == 1 and estado == "agotado":
        etiqueta = "agotado"
    sugerencias = {
        "agotado": ["¿Qué productos tienen stock bajo?", "¿Qué debo reponer?", "Resumen de alertas"],
        "bajo": ["¿Qué productos están agotados?", "¿Qué debo reponer?", "¿Qué se va a agotar pronto?"],
        "excesivo": ["Valor del inventario", "Productos sin ventas", "¿Qué debo trasladar entre sedes?"],
    }[estado]
    if total == 0:
        return B.Resp(f"No hay productos {etiqueta} {p.en_alcance}" + (f" {p.descripcion_filtro()}" if p.descripcion_filtro() else "") + ".", sugerencias=sugerencias)
    if estado == "agotado":
        orden = (Producto.nombre,)
    elif estado == "bajo":
        orden = ((InventarioSede.cantidad * 1.0 / func.nullif(InventarioSede.stock_minimo, 0)),)
    else:
        orden = ((InventarioSede.cantidad - InventarioSede.stock_maximo).desc(),)
    limite = p.limite(_MAX_FILAS)
    filas = await _filas_stock(p, extra, orden, limite)
    con_sede = p.sede_ids is None or len(p.sede_ids) > 1
    # Reparto por sede.
    reparto = ""
    if con_sede:
        consulta = (
            select(Sede.nombre, func.count())
            .select_from(InventarioSede).join(Producto, Producto.id == InventarioSede.producto_id).join(Sede, Sede.id == InventarioSede.sede_id)
            .where(*cond_inventario(p), *extra).group_by(Sede.nombre).order_by(func.count().desc(), Sede.nombre)
        )
        por_sede = (await p.db.execute(consulta)).all()
        reparto = " Por sede: " + ", ".join(f"{n} ({c})" for n, c in por_sede) + "."
    texto = f"Hay **{B.n_de(total, 'producto')} {etiqueta}** {p.en_alcance}" + (f" {p.descripcion_filtro()}" if p.descripcion_filtro() else "") + (" (cada producto cuenta una vez por sede)." if total > 1 else ".") + reparto
    if p.sede_ids is not None and len(p.sede_ids) == 1:
        texto = f"En **{p.alcance}** hay **{B.n_de(total, 'producto')} {etiqueta}**" + (f" {p.descripcion_filtro()}" if p.descripcion_filtro() else "") + "."
    bloques = []
    if estado == "excesivo":
        exceso = await p.db.scalar(
            select(func.coalesce(func.sum(case((Producto.costo.is_not(None), (InventarioSede.cantidad - InventarioSede.stock_maximo) * Producto.costo), else_=0)), 0))
            .select_from(InventarioSede).join(Producto, Producto.id == InventarioSede.producto_id).where(*cond_inventario(p), *extra)
        )
        if exceso:
            texto += f" El capital en exceso sobre el máximo es de **{B.moneda(exceso)}**."
    nota = f"Mostrando {len(filas)} de {B.entero(total)}." if total > len(filas) else None
    bloques.append(_tabla_stock(None, filas, con_sede=con_sede, total=total, nota=nota))
    return B.Resp(texto, bloques, enlaces_a(p, "/inventario", "/alertas"), sugerencias)


@manejador("listar_agotados")
async def listar_agotados(p: Peticion) -> B.Resp:
    return await _listado_estado(p, "agotado")


@manejador("listar_bajos")
async def listar_bajos(p: Peticion) -> B.Resp:
    return await _listado_estado(p, "bajo")


@manejador("listar_excesivos")
async def listar_excesivos(p: Peticion) -> B.Resp:
    return await _listado_estado(p, "excesivo")


# ------------------------------------------------------------------------------------------- por sede / categoría
@manejador("inventario_por_sede")
async def inventario_por_sede(p: Peticion) -> B.Resp:
    if p.hay_producto:
        return await stock_producto(p)
    if p.hay_categoria and p.una_sola_sede:
        return await inventario_categoria(p)
    if re.search(r"\b(valor\w*|vale|valen|cuesta|cuestan|plata|dinero|capital|invertid\w+)\b", p.frase):
        return await valor_inventario(p)
    por_sede = await totales_inventario(p, agrupar_por=InventarioSede.sede_id)
    if not por_sede:
        return B.Resp(f"No hay existencias registradas {p.en_alcance}.")
    sedes = [s for s in p.d.sedes if s.id in por_sede]
    filas = [
        B.fila({"sede": s.nombre, "unidades": por_sede[s.id].unidades, "referencias": por_sede[s.id].referencias, "valor": por_sede[s.id].valor,
                "agotados": por_sede[s.id].agotados, "bajos": por_sede[s.id].bajos, "excesivos": por_sede[s.id].excesivos}, ruta="/inventario")
        for s in sedes
    ]
    mayor = max(sedes, key=lambda s: por_sede[s.id].unidades)
    total = sum(v.unidades for v in por_sede.values())
    objetivo = p.con_filtro("el inventario")
    if len(sedes) == 1:
        t = por_sede[sedes[0].id]
        texto = f"En **{sedes[0].nombre}** hay **{B.entero(t.unidades)} unidades** ({B.n_de(t.referencias, 'referencia')}) valoradas en **{B.moneda(t.valor)}**."
    else:
        texto = f"{B.mayuscula_inicial(objetivo)} suma **{B.entero(total)} unidades**; la sede con más es **{mayor.nombre}** ({B.entero(por_sede[mayor.id].unidades)})."
    cols = [B.col("sede", "Sede"), B.col("unidades", "Unidades", "entero"), B.col("referencias", "Referencias", "entero"), B.col("valor", "Valor", "moneda"),
            B.col("agotados", "Agotados", "entero"), B.col("bajos", "Stock bajo", "entero"), B.col("excesivos", "Exceso", "entero")]
    bloques = [B.tabla(None, cols, filas)]
    if len(sedes) > 1:
        bloques.insert(0, B.barras("Unidades por sede", [(s.nombre, por_sede[s.id].unidades, B.entero(por_sede[s.id].unidades)) for s in sorted(sedes, key=lambda s: -por_sede[s.id].unidades)]))
    return B.Resp(texto, bloques, enlaces_a(p, "/inventario", "/inventario/consolidado"), ["¿Qué productos están agotados?", "Ventas por sede", "¿Qué debo trasladar entre sedes?"])


@manejador("inventario_categoria")
async def inventario_categoria(p: Peticion) -> B.Resp:
    por_cat = await totales_inventario(p, agrupar_por=Producto.categoria_id)
    nombres = {c.id: c.nombre for c in p.d.categorias}
    if not por_cat:
        return B.Resp(f"No hay existencias registradas {p.en_alcance}" + (f" {p.descripcion_filtro()}" if p.descripcion_filtro() else "") + ".")
    orden = sorted(por_cat.items(), key=lambda par: -par[1].unidades)
    filas = [
        B.fila({"categoria": nombres.get(i, "—"), "unidades": t.unidades, "referencias": t.referencias, "valor": t.valor, "agotados": t.agotados, "bajos": t.bajos}, ruta="/inventario")
        for i, t in orden
    ]
    cols = [B.col("categoria", "Categoría"), B.col("unidades", "Unidades", "entero"), B.col("referencias", "Referencias", "entero"), B.col("valor", "Valor", "moneda"),
            B.col("agotados", "Agotados", "entero"), B.col("bajos", "Stock bajo", "entero")]
    bloques: list = []
    if len(orden) == 1:
        i, t = orden[0]
        texto = f"En la categoría **{nombres.get(i, '—')}** hay **{B.entero(t.unidades)} unidades** ({B.n_de(t.referencias, 'referencia')}) {p.en_alcance}, valoradas en **{B.moneda(t.valor)}**."
        detalle = await _filas_productos_de_categoria(p)
        bloques.append(B.metricas(None, ("Unidades", B.entero(t.unidades)), ("Valor", B.moneda(t.valor)), ("Agotados", B.entero(t.agotados), None, "danger" if t.agotados else "neutral"), ("Stock bajo", B.entero(t.bajos), None, "warning" if t.bajos else "neutral")))
        if detalle is not None:
            bloques.append(detalle)
    else:
        mayor = orden[0]
        texto = f"Hay **{B.entero(sum(t.unidades for _, t in orden))} unidades** repartidas en **{len(orden)} categorías** {p.en_alcance}; la que más tiene es **{nombres.get(mayor[0], '—')}** ({B.entero(mayor[1].unidades)})."
        bloques.append(B.barras("Unidades por categoría", [(nombres.get(i, "—"), t.unidades, B.entero(t.unidades)) for i, t in orden]))
        bloques.append(B.tabla(None, cols, filas))
    return B.Resp(texto, bloques, enlaces_a(p, "/inventario/consolidado", "/inventario"), ["Valor del inventario", "¿Qué productos están agotados?", "Ventas por categoría"])


async def _filas_productos_de_categoria(p: Peticion):
    consulta = (
        select(Producto.codigo, Producto.nombre, func.coalesce(func.sum(InventarioSede.cantidad), 0).label("unidades"))
        .select_from(InventarioSede).join(Producto, Producto.id == InventarioSede.producto_id)
        .where(*cond_inventario(p)).group_by(Producto.id, Producto.codigo, Producto.nombre)
        .order_by(func.sum(InventarioSede.cantidad).desc(), Producto.nombre).limit(_MAX_FILAS)
    )
    filas = (await p.db.execute(consulta)).all()
    if not filas:
        return None
    return B.tabla("Productos de la categoría", [B.col("producto", "Producto"), B.col("unidades", "Unidades", "entero")],
                   [B.fila({"producto": _nombre_producto(f.codigo, f.nombre), "unidades": int(f.unidades)}, ruta="/inventario") for f in filas])


# -------------------------------------------------------------------------------------------------- catálogo
async def _productos(p: Peticion, extra: tuple = (), limite: int | None = None, orden=()):
    consulta = (
        select(Producto, Categoria.nombre.label("categoria"))
        .join(Categoria, Categoria.id == Producto.categoria_id)
        .where(Producto.empresa_id == p.ctx.empresa_id, *extra)
        .order_by(*orden, Producto.nombre)
    )
    if p.producto_ids:
        consulta = consulta.where(Producto.id.in_(p.producto_ids))
    if p.categoria_ids:
        consulta = consulta.where(Producto.categoria_id.in_(p.categoria_ids))
    if limite:
        consulta = consulta.limit(limite)
    return (await p.db.execute(consulta)).all()


async def _unidades_por_producto(p: Peticion, ids: list[int]) -> dict[int, int]:
    if not ids or not p.tiene("inventario.ver", "inventario.consolidado"):
        return {}
    consulta = select(InventarioSede.producto_id, func.coalesce(func.sum(InventarioSede.cantidad), 0)).where(
        InventarioSede.empresa_id == p.ctx.empresa_id, InventarioSede.producto_id.in_(ids)
    )
    if p.sede_ids is not None:
        consulta = consulta.where(InventarioSede.sede_id.in_(p.sede_ids))
    return {i: int(c) for i, c in (await p.db.execute(consulta.group_by(InventarioSede.producto_id))).all()}


def _margen(precio, costo) -> float | None:
    if precio is None or costo is None or float(precio) <= 0:
        return None
    return (float(precio) - float(costo)) / float(precio) * 100


@manejador("producto_info")
async def producto_info(p: Peticion) -> B.Resp:
    if not p.hay_producto:
        if p.hay_categoria:
            return await buscar_producto(p)
        palabras = f" «{' '.join(p.e.sin_resolver)}»" if p.e.sin_resolver else ""
        return B.Resp(f"No encontré un producto que coincida con{palabras or ' tu pregunta'}. Dime el nombre o el código, por ejemplo BAT-004.", sugerencias=_sugerir_productos(p))
    filas = await _productos(p)
    if not filas:
        return B.Resp("No encontré ese producto en el catálogo.")
    unidades = await _unidades_por_producto(p, [f.Producto.id for f in filas])
    if len(filas) > 1:
        cols = [B.col("producto", "Producto"), B.col("categoria", "Categoría"), B.col("precio", "Precio de venta", "moneda"), B.col("costo", "Costo", "moneda")]
        if unidades:
            cols.append(B.col("unidades", "Existencias", "entero"))
        tabla_filas = [
            B.fila({"producto": _nombre_producto(f.Producto.codigo, f.Producto.nombre), "categoria": f.categoria,
                    "precio": float(f.Producto.precio_venta) if f.Producto.precio_venta is not None else None,
                    "costo": float(f.Producto.costo) if f.Producto.costo is not None else None, "unidades": unidades.get(f.Producto.id, 0)}, ruta="/productos")
            for f in filas[:_MAX_FILAS]
        ]
        return B.Resp(f"Encontré **{len(filas)} productos** que coinciden con tu búsqueda.", [B.tabla(None, cols, tabla_filas, total=len(filas))], enlaces_a(p, "/productos"), ["¿Cuánto hay en total?"])
    prod, categoria = filas[0].Producto, filas[0].categoria
    nombre = _nombre_producto(prod.codigo, prod.nombre)
    precio = f"{B.moneda(prod.precio_venta)}" if prod.precio_venta is not None else None
    costo = f"{B.moneda(prod.costo)}" if prod.costo is not None else None
    margen = _margen(prod.precio_venta, prod.costo)
    f = p.frase
    if any(w in f for w in ("precio", "cuesta", "vale", "valen", "sale", "pvp", "cuestan")):
        texto = f"**{nombre}** tiene un precio de venta de **{precio}**." if precio else f"**{nombre}** no tiene precio de venta registrado."
    elif "costo" in f:
        texto = f"El costo de **{nombre}** es de **{costo}**." if costo else f"**{nombre}** no tiene costo registrado."
    elif "categoria" in f:
        texto = f"**{nombre}** está en la categoría **{categoria}**."
    else:
        texto = f"**{nombre}**: categoría {categoria}" + (f", precio de venta {precio}" if precio else "") + (f", costo {costo}" if costo else "") + "."
    if not prod.activo:
        texto += " Ojo: este producto está **inhabilitado**."
    metricas = [("Precio de venta", precio or "Sin precio"), ("Costo", costo or "Sin costo")]
    if margen is not None:
        metricas.append(("Margen", B.porcentaje(margen)))
    if p.tiene("inventario.ver", "inventario.consolidado"):
        metricas.append(("Existencias" + ("" if p.sede_ids is None else f" ({p.alcance})"), B.entero(unidades.get(prod.id, 0))))
    bloques = [B.metricas(None, *metricas), B.lista(None, [f"Código: {prod.codigo}", f"Categoría: {categoria}", f"Unidad de medida: {prod.unidad_medida}", f"Estado: {'Activo' if prod.activo else 'Inhabilitado'}"] + ([f"Descripción: {prod.descripcion}"] if prod.descripcion else []))]
    return B.Resp(texto, bloques, enlaces_a(p, "/productos", "/inventario"), ["¿Cuánto hay de este producto?", "¿Cuántos días me dura?", "¿Cuánto se vende al mes?"])


@manejador("margen_productos")
async def margen_productos(p: Peticion) -> B.Resp:
    filas = await _productos(p, (Producto.activo.is_(True),))
    con_margen = [(f, _margen(f.Producto.precio_venta, f.Producto.costo)) for f in filas]
    validas = [(f, m) for f, m in con_margen if m is not None]
    sin = len(filas) - len(validas)
    if not validas:
        return B.Resp("No hay productos con precio y costo registrados para calcular el margen." + (" Regístralos en Productos." if p.tiene("productos.editar") else ""), enlaces=enlaces_a(p, "/productos"))
    ascendente = p.e.orden == "asc"
    validas.sort(key=lambda par: par[1], reverse=not ascendente)
    promedio = sum(m for _, m in validas) / len(validas)
    limite = p.limite(10)
    mostrar = validas[:limite]
    tabla_filas = [
        B.fila({"producto": _nombre_producto(f.Producto.codigo, f.Producto.nombre), "precio": float(f.Producto.precio_venta), "costo": float(f.Producto.costo),
                "ganancia": float(f.Producto.precio_venta) - float(f.Producto.costo), "margen": m}, ruta="/productos")
        for f, m in mostrar
    ]
    cols = [B.col("producto", "Producto"), B.col("precio", "Precio", "moneda"), B.col("costo", "Costo", "moneda"), B.col("ganancia", "Ganancia por unidad", "moneda"), B.col("margen", "Margen", "porcentaje")]
    if len(validas) == 1:
        f, m = validas[0]
        texto = f"El margen de **{_nombre_producto(f.Producto.codigo, f.Producto.nombre)}** es de **{B.porcentaje(m)}** (gana {B.moneda(float(f.Producto.precio_venta) - float(f.Producto.costo))} por unidad)."
    else:
        texto = (f"{'Los de menor margen' if ascendente else 'Los de mayor margen'}: **{_nombre_producto(mostrar[0][0].Producto.codigo, mostrar[0][0].Producto.nombre)}** "
                 f"con {B.porcentaje(mostrar[0][1])}. El margen promedio es de **{B.porcentaje(promedio)}**.")
    avisos = [f"{B.n_de(sin, 'producto')} no tiene costo o precio registrado y no entra en el cálculo."] if sin else []
    avisos.append("Margen = (precio de venta − costo) ÷ precio de venta.")
    return B.Resp(texto, [B.tabla(None, cols, tabla_filas, total=len(validas))], enlaces_a(p, "/productos"), ["Valor del inventario", "¿Cuáles son los más vendidos?"], avisos)


@manejador("catalogo_conteo")
async def catalogo_conteo(p: Peticion) -> B.Resp:
    cond = [Producto.empresa_id == p.ctx.empresa_id]
    if p.categoria_ids:
        cond.append(Producto.categoria_id.in_(p.categoria_ids))
    f = (await p.db.execute(select(
        func.count(), func.coalesce(func.sum(case((Producto.activo.is_(True), 1), else_=0)), 0),
        func.coalesce(func.sum(case((Producto.costo.is_(None), 1), else_=0)), 0), func.coalesce(func.sum(case((Producto.precio_venta.is_(None), 1), else_=0)), 0),
    ).where(*cond))).one()
    total, activos, sin_costo, sin_precio = int(f[0]), int(f[1]), int(f[2]), int(f[3])
    cats = (await p.db.execute(select(func.count(), func.coalesce(func.sum(case((Categoria.activa.is_(True), 1), else_=0)), 0)).where(Categoria.empresa_id == p.ctx.empresa_id))).one()
    objetivo = p.descripcion_filtro()
    texto = f"El catálogo{(' ' + objetivo) if objetivo else ''} tiene **{B.entero(total)} productos** (**{B.entero(activos)} activos**, {B.entero(total - activos)} inhabilitados) en **{B.entero(int(cats[0]))} categorías**."
    bloques = [B.metricas(None, ("Productos", B.entero(total)), ("Activos", B.entero(activos)), ("Inhabilitados", B.entero(total - activos)), ("Categorías", B.entero(int(cats[0]))),
                          ("Sin costo", B.entero(sin_costo), None, "warning" if sin_costo else "neutral"), ("Sin precio", B.entero(sin_precio), None, "warning" if sin_precio else "neutral"))]
    if any(w in p.frase for w in ("sin costo", "sin precio", "faltante", "sin registrar")) and (sin_costo or sin_precio):
        faltan = await _productos(p, (Producto.activo.is_(True), (Producto.costo.is_(None)) | (Producto.precio_venta.is_(None))), 15)
        bloques.append(B.tabla("Productos con datos faltantes", [B.col("producto", "Producto"), B.col("precio", "Precio de venta", "moneda"), B.col("costo", "Costo", "moneda")],
                               [B.fila({"producto": _nombre_producto(x.Producto.codigo, x.Producto.nombre), "precio": float(x.Producto.precio_venta) if x.Producto.precio_venta is not None else None,
                                        "costo": float(x.Producto.costo) if x.Producto.costo is not None else None}, ruta="/productos") for x in faltan]))
    return B.Resp(texto, bloques, enlaces_a(p, "/productos", "/categorias"), ["¿Qué productos no tienen costo registrado?", "Productos de la categoría baterías", "¿Cuál es el margen de los productos?"])


@manejador("buscar_producto")
async def buscar_producto(p: Peticion) -> B.Resp:
    filas = await _productos(p, (Producto.activo.is_(True),))
    if not filas:
        palabras = f" «{' '.join(p.e.sin_resolver)}»" if p.e.sin_resolver else ""
        return B.Resp(f"No encontré productos que coincidan con{palabras or ' tu búsqueda'}.", sugerencias=["¿Qué productos manejamos?", *_sugerir_productos(p, 2)])
    total = len(filas)
    mostrar = filas[:p.limite(_MAX_FILAS)]
    unidades = await _unidades_por_producto(p, [f.Producto.id for f in mostrar])
    cols = [B.col("producto", "Producto"), B.col("categoria", "Categoría"), B.col("precio", "Precio de venta", "moneda")]
    if unidades:
        cols.append(B.col("unidades", "Existencias", "entero"))
    tabla_filas = [
        B.fila({"producto": _nombre_producto(f.Producto.codigo, f.Producto.nombre), "categoria": f.categoria,
                "precio": float(f.Producto.precio_venta) if f.Producto.precio_venta is not None else None, "unidades": unidades.get(f.Producto.id, 0)}, ruta="/productos")
        for f in mostrar
    ]
    if p.hay_producto:
        texto = f"Encontré **{B.n_de(total, 'producto')}** que coinciden con tu búsqueda."
    elif p.hay_categoria:
        texto = f"Hay **{B.n_de(total, 'producto')}** activos {p.descripcion_filtro()}."
    else:
        texto = f"Hay **{B.n_de(total, 'producto')}** activos en el catálogo."
    nota = f"Mostrando {len(mostrar)} de {total}." if total > len(mostrar) else None
    return B.Resp(texto, [B.tabla(None, cols, tabla_filas, total=total, nota=nota)], enlaces_a(p, "/productos"), ["¿Cuántos productos manejamos?", "Inventario por categoría"])
