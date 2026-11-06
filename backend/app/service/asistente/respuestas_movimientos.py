"""Respuestas sobre movimientos de inventario: entradas, salidas y pérdidas, ajustes y kardex."""

import re

from sqlalchemy import func, select

from app.model.catalogo import Producto
from app.model.inventario import Movimiento
from app.model.sede import Sede
from app.model.usuario import Usuario
from app.service.asistente import bloques as B
from app.service.asistente.datos import enlaces_a
from app.service.asistente.peticion import Peticion, manejador
from app.util import lenguaje as L
from app.util.tiempo import a_fecha_local, fin_de_dia_utc, inicio_de_dia_utc

_PIDE_PERDIDAS = re.compile(r"\b(merma\w*|perdida\w*|deterioro\w*|danad\w*|rotura\w*|robo\w*|hurto\w*|desperdicio\w*|bajas? de inventario)\b")


def _condiciones(p: Peticion, periodo: L.Periodo | None, tipos: tuple[str, ...] | None) -> list:
    c = [Movimiento.empresa_id == p.ctx.empresa_id]
    if tipos:
        c.append(Movimiento.tipo.in_(tipos))
    if periodo:
        c += [Movimiento.fecha >= inicio_de_dia_utc(periodo.desde), Movimiento.fecha < fin_de_dia_utc(periodo.hasta)]
    if p.sede_ids is not None:
        c.append(Movimiento.sede_id.in_(p.sede_ids))
    if p.producto_ids:
        c.append(Movimiento.producto_id.in_(p.producto_ids))
    if p.categoria_ids:
        c.append(Producto.categoria_id.in_(p.categoria_ids))
    return c


async def _totales(p: Peticion, condiciones: list) -> tuple[int, int, float]:
    """(líneas, unidades en valor absoluto, valor a costo)."""
    f = (
        await p.db.execute(
            select(func.count(), func.coalesce(func.sum(func.abs(Movimiento.delta)), 0), func.coalesce(func.sum(func.abs(Movimiento.delta) * Producto.costo), 0))
            .select_from(Movimiento).join(Producto, Producto.id == Movimiento.producto_id).where(*condiciones)
        )
    ).one()
    return int(f[0]), int(f[1]), float(f[2])


async def _por_motivo(p: Peticion, condiciones: list) -> list[tuple[str, int, int]]:
    filas = (
        await p.db.execute(
            select(Movimiento.motivo, func.count(), func.coalesce(func.sum(func.abs(Movimiento.delta)), 0))
            .select_from(Movimiento).join(Producto, Producto.id == Movimiento.producto_id).where(*condiciones)
            .group_by(Movimiento.motivo).order_by(func.sum(func.abs(Movimiento.delta)).desc())
        )
    ).all()
    return [(B.MOTIVO.get(m or "", "Sin motivo") if m else "Sin motivo", int(n), int(u)) for m, n, u in filas]


async def _lineas(p: Peticion, condiciones: list, limite: int):
    return (
        await p.db.execute(
            select(Movimiento, Producto.codigo, Producto.nombre, Sede.nombre.label("sede"), Usuario.nombre.label("usuario"))
            .join(Producto, Producto.id == Movimiento.producto_id).join(Sede, Sede.id == Movimiento.sede_id).join(Usuario, Usuario.id == Movimiento.usuario_id)
            .where(*condiciones).order_by(Movimiento.fecha.desc(), Movimiento.id.desc()).limit(limite)
        )
    ).all()


def _tabla_lineas(filas, total: int, *, con_saldo: bool = False):
    cols = [B.col("fecha", "Fecha", "fecha_hora"), B.col("producto", "Producto"), B.col("sede", "Sede")]
    if con_saldo:
        cols += [B.col("tipo", "Tipo"), B.col("delta", "Cambio", "entero"), B.col("saldo", "Saldo", "entero")]
    else:
        cols += [B.col("cantidad", "Cantidad", "entero"), B.col("motivo", "Motivo")]
    cols.append(B.col("usuario", "Registró"))
    salida = []
    for f in filas:
        m = f.Movimiento
        celdas = {"fecha": m.fecha, "producto": f"{f.nombre} ({f.codigo})", "sede": f.sede, "usuario": f.usuario}
        if con_saldo:
            celdas.update({"tipo": B.TIPO_MOVIMIENTO.get(m.tipo, m.tipo), "delta": m.delta, "saldo": m.saldo_posterior})
        else:
            celdas.update({"cantidad": abs(m.delta), "motivo": B.MOTIVO.get(m.motivo or "", "—") if m.motivo else "—"})
        salida.append(B.fila(celdas, tonos={"delta": "success" if m.delta > 0 else "danger"} if con_saldo else {}, ruta="/movimientos"))
    nota = f"Mostrando {len(filas)} de {B.entero(total)}." if total > len(filas) else None
    return B.tabla(None, cols, salida, total=total, nota=nota)


def _de(p: Peticion) -> str:
    f = p.descripcion_filtro()
    return f" {f}" if f else ""


async def _vacio(p: Peticion, que: str, periodo: L.Periodo, tipos: tuple[str, ...] | None = None, extra: list | None = None) -> B.Resp:
    texto = f"No hay {que}{_de(p)} {p.en_alcance} {p.en_periodo(periodo)}."
    ultima = await p.db.scalar(
        select(func.max(Movimiento.fecha)).select_from(Movimiento).join(Producto, Producto.id == Movimiento.producto_id).where(*_condiciones(p, None, tipos), *(extra or []))
    )
    if ultima:
        texto += f" Lo último registrado fue el {L.fecha_larga(a_fecha_local(ultima))}."
    return B.Resp(texto, sugerencias=["Últimos movimientos de inventario", "¿Qué mercancía entró este mes?"], enlaces=enlaces_a(p, "/movimientos"))


# ---------------------------------------------------------------------------------------------------- entradas
@manejador("entradas_mercancia")
async def entradas_mercancia(p: Peticion) -> B.Resp:
    periodo = p.ultimos_dias(30)
    cond = _condiciones(p, periodo, ("entrada",))
    lineas, unidades, valor = await _totales(p, cond)
    if not lineas:
        return await _vacio(p, "entradas de mercancía", periodo, ("entrada",))
    recepciones = int(await p.db.scalar(select(func.count(func.distinct(Movimiento.entrada_id))).select_from(Movimiento).join(Producto, Producto.id == Movimiento.producto_id).where(*cond)) or 0)
    motivos = await _por_motivo(p, cond)
    texto = (f"{p.periodo_inicio(periodo)} entraron **{B.entero(unidades)} unidades**{_de(p)} {p.en_alcance} en **{B.n_de(lineas, 'línea')}**"
             f"{' (' + B.n_de(recepciones, 'recepción', 'recepciones') + ')' if recepciones else ''}, por un valor a costo de **{B.moneda(valor)}**.")
    bloques = [B.metricas(None, ("Unidades recibidas", B.entero(unidades)), ("Líneas", B.entero(lineas)), ("Valor a costo", B.moneda(valor)))]
    if len(motivos) > 1:
        bloques.append(B.barras("Por motivo", [(m, u, f"{B.entero(u)} u.") for m, _, u in motivos]))
    bloques.append(_tabla_lineas(await _lineas(p, cond, p.limite(10)), lineas))
    return B.Resp(texto, bloques, enlaces_a(p, "/movimientos", "/inventario"), ["¿Qué salidas hubo este mes?", "Ajustes de inventario", "¿Qué no conformidades hay?"])


# ----------------------------------------------------------------------------------------------------- salidas
@manejador("salidas_mercancia")
async def salidas_mercancia(p: Peticion) -> B.Resp:
    periodo = p.ultimos_dias(30)
    cond = _condiciones(p, periodo, ("salida",))
    perdidas = bool(_PIDE_PERDIDAS.search(p.frase))
    if perdidas:
        cond.append(Movimiento.motivo.in_(("perdida", "deterioro")))
    lineas, unidades, valor = await _totales(p, cond)
    etiqueta = "pérdidas y deterioros" if perdidas else "salidas de inventario (sin contar ventas ni traslados)"
    if not lineas:
        return await _vacio(p, etiqueta, periodo, ("salida",), [Movimiento.motivo.in_(("perdida", "deterioro"))] if perdidas else None)
    motivos = await _por_motivo(p, cond)
    texto = f"{p.periodo_inicio(periodo)} hubo **{B.entero(unidades)} unidades** en {etiqueta}{_de(p)} {p.en_alcance}, equivalentes a **{B.moneda(valor)}** a costo."
    bloques = [B.metricas(None, ("Unidades", B.entero(unidades), None, "warning" if perdidas else "neutral"), ("Líneas", B.entero(lineas)), ("Valor a costo", B.moneda(valor), None, "warning" if perdidas else "neutral"))]
    if len(motivos) > 1:
        bloques.append(B.barras("Por motivo", [(m, u, f"{B.entero(u)} u.") for m, _, u in motivos]))
    bloques.append(_tabla_lineas(await _lineas(p, cond, p.limite(10)), lineas))
    avisos = ["Las ventas no son «salidas»: se consultan con «ventas». Aquí van las pérdidas, el deterioro, el consumo interno y las devoluciones a proveedor."] if not perdidas else []
    return B.Resp(texto, bloques, enlaces_a(p, "/movimientos"), ["Ajustes de inventario", "¿Cuánto vendimos este mes?", "Calidad: no conformidades"], avisos)


# ----------------------------------------------------------------------------------------------------- ajustes
@manejador("ajustes_inventario")
async def ajustes_inventario(p: Peticion) -> B.Resp:
    periodo = p.ultimos_dias(30)
    cond = _condiciones(p, periodo, ("ajuste",))
    lineas, _, valor = await _totales(p, cond)
    if not lineas:
        return await _vacio(p, "ajustes de inventario", periodo, ("ajuste",))
    neto = int(await p.db.scalar(select(func.coalesce(func.sum(Movimiento.delta), 0)).select_from(Movimiento).join(Producto, Producto.id == Movimiento.producto_id).where(*cond)) or 0)
    sobrantes = int(await p.db.scalar(select(func.coalesce(func.sum(Movimiento.delta), 0)).select_from(Movimiento).join(Producto, Producto.id == Movimiento.producto_id).where(*cond, Movimiento.delta > 0)) or 0)
    faltantes = sobrantes - neto
    texto = (f"{p.periodo_inicio(periodo)} se hicieron **{B.n_de(lineas, 'ajuste')}**{_de(p)} {p.en_alcance}: sumaron **{B.entero(sobrantes)} unidades** y restaron **{B.entero(faltantes)}** "
             f"(neto {'+' if neto > 0 else ''}{B.entero(neto)}), con un valor absoluto de {B.moneda(valor)} a costo.")
    bloques = [B.metricas(None, ("Ajustes", B.entero(lineas)), ("Unidades que sumaron", B.entero(sobrantes), None, "success"), ("Unidades que restaron", B.entero(faltantes), None, "warning" if faltantes else "neutral"), ("Neto", f"{'+' if neto > 0 else ''}{B.entero(neto)}")),
               _tabla_lineas(await _lineas(p, cond, p.limite(10)), lineas, con_saldo=True)]
    return B.Resp(texto, bloques, enlaces_a(p, "/movimientos"), ["¿Cuántas pérdidas tuvimos este mes?", "Últimos movimientos de inventario"])


# ----------------------------------------------------------------------------------------------------- kardex
@manejador("movimientos_inventario")
async def movimientos_inventario(p: Peticion) -> B.Resp:
    cond = _condiciones(p, p.periodo, None)
    lineas, _, _ = await _totales(p, cond)
    if not lineas:
        return B.Resp(f"No hay movimientos{_de(p)} {p.en_alcance}" + (f" {p.en_periodo(p.periodo)}" if p.periodo else "") + ".")
    por_tipo = (
        await p.db.execute(
            select(Movimiento.tipo, func.count()).select_from(Movimiento).join(Producto, Producto.id == Movimiento.producto_id).where(*cond).group_by(Movimiento.tipo).order_by(func.count().desc())
        )
    ).all()
    resumen = ", ".join(f"{B.TIPO_MOVIMIENTO.get(t, t).lower()} ({n})" for t, n in por_tipo[:4])
    limite = p.limite(10)
    cabeza = f"Hay **{B.n_de(lineas, 'movimiento')}**{_de(p)} {p.en_alcance}" + (f" {p.en_periodo(p.periodo)}" if p.periodo else "") + f": {resumen}."
    texto = cabeza + f" Te muestro los {min(limite, lineas)} más recientes."
    return B.Resp(texto, [_tabla_lineas(await _lineas(p, cond, limite), lineas, con_saldo=True)], enlaces_a(p, "/movimientos"), ["¿Qué mercancía entró este mes?", "Ajustes de inventario", "Ventas recientes"])
