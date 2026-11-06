"""Comparación entre dos o más sedes, categorías o productos: existencias, ventas y alertas lado a lado."""

from dataclasses import replace

from sqlalchemy import case, func, select

from app.model.catalogo import Producto
from app.model.inventario import Alerta
from app.service.asistente import bloques as B
from app.service.asistente.analisis import porcentaje_de
from app.service.asistente.datos import enlaces_a, periodo_de_ventas, totales_inventario, totales_ventas
from app.service.asistente.intencion import INV
from app.service.asistente.peticion import MANEJADORES, Peticion, manejador

_MAXIMO = 6


def _dimension(p: Peticion) -> tuple[str, list[int], list[str]] | None:
    """(tipo, ids, nombres) de lo que se compara, o ``None`` si la frase no nombra al menos dos cosas del mismo tipo."""
    if p.sede_ids is not None and p.sedes_nombradas and len(p.sede_ids) >= 2:
        ids = p.sede_ids[:_MAXIMO]
        nombres = {s.id: s.nombre for s in p.d.sedes}
        return "sede", ids, [nombres.get(i, f"Sede {i}") for i in ids]
    if len(p.categoria_ids) >= 2:
        ids = p.categoria_ids[:_MAXIMO]
        nombres = {c.id: c.nombre for c in p.d.categorias}
        return "categoria", ids, [nombres.get(i, f"Categoría {i}") for i in ids]
    if len(p.producto_ids) >= 2:
        ids = p.producto_ids[:_MAXIMO]
        nombres = {x.id: x.nombre for x in p.d.productos}
        return "producto", ids, [nombres.get(i, f"Producto {i}") for i in ids]
    if p.clave == "comparar_sedes" and not p.sedes_nombradas and not p.categoria_ids and not p.producto_ids:
        visibles = [s for s in p.d.sedes if p.sede_ids is None or s.id in p.sede_ids][:_MAXIMO]  # «compara las sedes»: todas las que la persona puede ver
        if len(visibles) >= 2:
            return "sede", [s.id for s in visibles], [s.nombre for s in visibles]
    return None


def _solo(p: Peticion, tipo: str, id_: int) -> Peticion:
    """La misma petición reducida a una sola sede, categoría o producto."""
    if tipo == "sede":
        return replace(p, sede_ids=[id_], sedes_nombradas=True)
    if tipo == "categoria":
        return replace(p, categoria_ids=[id_], producto_ids=[])
    return replace(p, producto_ids=[id_])


async def _alertas(q: Peticion) -> tuple[int, int]:
    """(activas, críticas) del alcance de la petición."""
    consulta = select(func.count(), func.coalesce(func.sum(case((Alerta.prioridad == "critica", 1), else_=0)), 0)).select_from(Alerta)
    condiciones = [Alerta.empresa_id == q.ctx.empresa_id, Alerta.estado == "activa"]
    if q.categoria_ids:
        consulta = consulta.join(Producto, Producto.id == Alerta.producto_id)
        condiciones.append(Producto.categoria_id.in_(q.categoria_ids))
    if q.sede_ids is not None:
        condiciones.append(Alerta.sede_id.in_(q.sede_ids))
    if q.producto_ids:
        condiciones.append(Alerta.producto_id.in_(q.producto_ids))
    f = (await q.db.execute(consulta.where(*condiciones))).one()
    return int(f[0]), int(f[1])


def _lider(nombres: list[str], valores: list[float], mayor: bool = True) -> tuple[str, float, str, float]:
    """(nombre del primero, su valor, nombre del último, su valor) según el orden pedido."""
    orden = sorted(zip(nombres, valores, strict=True), key=lambda par: par[1], reverse=mayor)
    return orden[0][0], orden[0][1], orden[-1][0], orden[-1][1]


@manejador("comparar_entidades", "comparar_sedes", "comparar_categorias", "comparar_productos")
async def comparar_entidades(p: Peticion) -> B.Resp:
    dimension = _dimension(p)
    if dimension is None:
        if (p.e.periodo_b or p.periodo) and "ventas_comparar" in MANEJADORES and p.tiene("ventas.ver"):
            return await MANEJADORES["ventas_comparar"](p)
        if p.clave == "comparar_sedes" and not p.sedes_nombradas and p.sede_ids is not None and len(p.sede_ids) < 2:
            propia = next((s.nombre for s in p.d.sedes if s.id in p.sede_ids), "tu sede")
            return B.Resp(f"Con tu rol solo puedes consultar la información de tu sede ({propia}), así que no hay otra sede con la que compararla. Puedes comparar categorías o productos.",
                          sugerencias=["Compara bicicletas con monopatines", "Ventas de esta semana"])
        return B.Resp(
            "Para comparar necesito al menos dos cosas del mismo tipo: dos sedes, dos categorías o dos productos. Por ejemplo, «compara la sede Norte con la sede Sur», "
            "«compara bicicletas con monopatines» o «compara BAT-001 con BAT-002».",
            sugerencias=["Compara las sedes", "Compara bicicletas con monopatines", "Ventas por sede este mes"],
        )
    tipo, ids, nombres = dimension
    ver_inventario, ver_ventas, ver_alertas = p.tiene(*INV), p.tiene("ventas.ver"), p.tiene("alertas.ver")
    periodo = await periodo_de_ventas(p) if ver_ventas else None

    inventario, ventas, alertas = [], [], []
    for id_ in ids:
        q = _solo(p, tipo, id_)
        inventario.append((await totales_inventario(q))[None] if ver_inventario else None)
        ventas.append(await totales_ventas(q, periodo) if ver_ventas and periodo else None)
        alertas.append(await _alertas(q) if ver_alertas else None)

    columnas = [B.col("nombre", {"sede": "Sede", "categoria": "Categoría", "producto": "Producto"}[tipo])]
    if ver_inventario:
        columnas += [B.col("unidades", "Unidades", "entero"), B.col("valor", "Valor inventario", "moneda"), B.col("agotados", "Agotados", "entero"), B.col("bajos", "Bajos", "entero")]
    if ver_ventas:
        columnas += [B.col("vendido", "Vendido", "moneda"), B.col("ventas", "Ventas", "entero"), B.col("vendidas", "Unid. vendidas", "entero"), B.col("ticket", "Ticket prom.", "moneda")]
    if ver_alertas:
        columnas += [B.col("alertas", "Alertas activas", "entero"), B.col("criticas", "Críticas", "entero")]
    filas = []
    for i, nombre in enumerate(nombres):
        celdas: dict = {"nombre": nombre}
        if (inv := inventario[i]) is not None:
            celdas.update(unidades=inv.unidades, valor=inv.valor, agotados=inv.agotados, bajos=inv.bajos)
        if (v := ventas[i]) is not None:
            celdas.update(vendido=v.monto, ventas=v.ventas, vendidas=v.unidades, ticket=v.ticket)
        if (a := alertas[i]) is not None:
            celdas.update(alertas=a[0], criticas=a[1])
        filas.append(B.fila(celdas))

    frases: list[str] = []
    if ver_ventas and periodo is not None:
        montos = [v.monto for v in ventas if v is not None]
        if any(montos):
            mejor, monto_mejor, peor, monto_peor = _lider(nombres, montos)
            if len(nombres) == 2 and monto_peor:
                frases.append(f"Vendió más **{mejor}**: {B.moneda(monto_mejor)} frente a {B.moneda(monto_peor)} de {peor} ({B.porcentaje(porcentaje_de(monto_mejor - monto_peor, monto_peor))} más).")
            else:
                frases.append(f"Vendió más **{mejor}** ({B.moneda(monto_mejor)}) y menos **{peor}** ({B.moneda(monto_peor)}).")
        else:
            frases.append("No hay ventas registradas en ese periodo para ninguno de los dos." if len(nombres) == 2 else "No hay ventas registradas en ese periodo.")
    if ver_inventario:
        valores = [i.valor for i in inventario if i is not None]
        if any(valores):
            mejor, valor_mejor, peor, valor_peor = _lider(nombres, valores)
            if mejor != peor and valor_mejor != valor_peor:
                frases.append(f"Tiene más inventario (a costo) **{mejor}** con {B.moneda(valor_mejor)}; el menor es {peor} con {B.moneda(valor_peor)}.")
    if ver_alertas:
        conteo = [a[0] for a in alertas if a is not None]
        if any(conteo):
            mejor, n_mejor, _, _ = _lider(nombres, [float(c) for c in conteo])
            frases.append(f"Más alertas activas: **{mejor}** ({B.entero(n_mejor)}).")
    cabecera = f"Comparación de {B.lista_natural([f'**{n}**' for n in nombres])}"
    if periodo is not None:
        cabecera += f" ({p.periodo_texto(periodo)})"
    texto = cabecera + ". " + " ".join(frases) if frases else cabecera + "."

    bloques: list = [B.tabla(None, columnas, filas)]
    if ver_ventas and periodo is not None and any(v.monto for v in ventas if v is not None):
        bloques.append(B.barras("Vendido", [(n, v.monto, B.moneda(v.monto)) for n, v in zip(nombres, ventas, strict=True) if v is not None]))
    elif ver_inventario:
        bloques.append(B.barras("Unidades en inventario", [(n, float(i.unidades), B.entero(i.unidades)) for n, i in zip(nombres, inventario, strict=True) if i is not None]))
    avisos = []
    if tipo == "producto" and len(p.producto_ids) > _MAXIMO:
        avisos.append(f"Tu búsqueda coincide con {len(p.producto_ids)} productos; comparé los primeros {_MAXIMO}. Usa los códigos para ser más preciso.")
    if tipo == "sede" and len(p.sede_ids or []) > _MAXIMO:
        avisos.append(f"Comparé las primeras {_MAXIMO} sedes.")
    ruta = {"sede": "/sedes", "categoria": "/categorias", "producto": "/productos"}[tipo]
    return B.Resp(texto, bloques, enlaces_a(p, "/ventas", ruta)[:2], ["Ventas por sede este mes", "¿Qué productos están agotados?", "Compara con el mes pasado"], avisos)
