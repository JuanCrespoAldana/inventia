"""Respuestas ampliadas de operación: análisis de alertas, traslados y movimientos, compras, devoluciones, pendientes del día, inversión en reposición y consejos."""

import re
from collections import defaultdict
from datetime import timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import aliased

from app.model.calidad import Garantia, NoConformidad
from app.model.catalogo import Categoria, Producto
from app.model.inventario import Alerta, Movimiento
from app.model.operaciones import Traslado, TrasladoItem
from app.model.pqrs import Pqrs
from app.model.prediccion import Recomendacion
from app.model.sede import Sede
from app.model.usuario import Usuario
from app.service.asistente import bloques as B
from app.service.asistente.analisis import nombre_producto, nota_listado, ultimos
from app.service.asistente.datos import enlaces_a, totales_inventario, totales_ventas
from app.service.asistente.peticion import Peticion, manejador
from app.service.asistente.respuestas_analitica import _cond_alertas, _cond_recomendaciones, _cond_traslados
from app.service.asistente.respuestas_movimientos import _condiciones, _lineas, _tabla_lineas, _totales, _vacio
from app.util.tiempo import asegurar_utc, fin_de_dia_utc, inicio_de_dia_utc


def _dias_entre(desde, hasta) -> float:
    return (asegurar_utc(hasta) - asegurar_utc(desde)).total_seconds() / 86400


def _duracion(dias: float) -> str:
    if dias * 24 < 1:
        return "menos de 1 hora"
    if dias < 1:
        return f"{B.decimal(dias * 24, 1)} horas"
    return f"{B.decimal(dias, 1)} días"


# ===================================================================================================== análisis de alertas
@manejador("alertas_analisis")
async def alertas_analisis(p: Peticion) -> B.Resp:
    f = p.frase
    cond = _cond_alertas(p)
    resueltas = p.e.estado_alerta == "resuelta"
    if re.search(r"\b(tiempo|demor\w+|tarda\w*|cuanto tard\w+|cuantos dias)\b", f) and re.search(r"\b(resol\w+|atend\w+|atencion|cierre|cerr\w+)\b", f):
        filas = (await p.db.execute(select(Alerta.abierta_en, Alerta.resuelta_en).where(*_cond_alertas_resueltas(p)).limit(5000))).all()
        filas = [x for x in filas if x.resuelta_en]
        if not filas:
            return B.Resp(f"Todavía no hay alertas resueltas {p.en_alcance} para calcular cuánto tardan en resolverse.", enlaces=enlaces_a(p, "/alertas"), sugerencias=["Resumen de alertas"])
        duraciones = sorted(_dias_entre(x.abierta_en, x.resuelta_en) for x in filas)
        promedio, mediana = sum(duraciones) / len(duraciones), duraciones[len(duraciones) // 2]
        texto = f"Las alertas {p.en_alcance} tardaron en promedio **{_duracion(promedio)}** en resolverse (mediana {_duracion(mediana)}), sobre {B.n_de(len(filas), 'alerta resuelta', 'alertas resueltas')}."
        return B.Resp(texto, [B.metricas(None, ("Promedio", _duracion(promedio)), ("Mediana", _duracion(mediana)), ("La más rápida", _duracion(duraciones[0])), ("La más lenta", _duracion(duraciones[-1])), ("Alertas resueltas", B.entero(len(filas))))],
                      enlaces_a(p, "/alertas"), ["Resumen de alertas", "Alertas más antiguas"])
    total = int(await p.db.scalar(select(func.count()).select_from(Alerta).where(*cond)) or 0)
    estado = "resueltas" if resueltas else "activas"
    if total == 0:
        return B.Resp(f"No hay alertas {estado} {p.en_alcance} para analizar.", enlaces=enlaces_a(p, "/alertas"), sugerencias=["¿Cómo está el inventario?"])
    if re.search(r"\b(antigua\w*|viej\w+|mas tiempo|abierta\w* (hace|desde)|llevan?\b.*\babiert\w+|sin atender|rezagad\w+)\b", f) and not resueltas:
        filas = (await p.db.execute(
            select(Alerta, Producto.codigo, Producto.nombre, Sede.nombre.label("sede")).join(Producto, Producto.id == Alerta.producto_id).join(Sede, Sede.id == Alerta.sede_id)
            .where(*cond).order_by(Alerta.abierta_en.asc(), Alerta.id).limit(p.limite(8))
        )).all()
        hoy_utc = inicio_de_dia_utc(p.hoy + timedelta(days=1))
        primera = filas[0]
        texto = f"La alerta activa más antigua {p.en_alcance} es de **{nombre_producto(primera.codigo, primera.nombre)}** en {primera.sede}: lleva **{B.n_de(max(0, int(_dias_entre(primera.Alerta.abierta_en, hoy_utc))), 'día')}** abierta."
        tabla = B.tabla(None, [B.col("producto", "Producto"), B.col("sede", "Sede"), B.col("tipo", "Tipo"), B.col("prioridad", "Prioridad"), B.col("dias", "Días abierta", "entero")],
                        [B.fila({"producto": nombre_producto(x.codigo, x.nombre), "sede": x.sede, "tipo": B.TIPO_ALERTA.get(x.Alerta.tipo, x.Alerta.tipo), "prioridad": B.PRIORIDAD.get(x.Alerta.prioridad, (x.Alerta.prioridad, "neutral"))[0],
                                  "dias": max(0, int(_dias_entre(x.Alerta.abierta_en, hoy_utc)))}, tonos={"prioridad": B.PRIORIDAD.get(x.Alerta.prioridad, ("", "neutral"))[1]}, ruta="/alertas") for x in filas],
                        total=total, nota=nota_listado(len(filas), total, "alertas"))
        return B.Resp(texto, [tabla], enlaces_a(p, "/alertas"), ["Alertas críticas", "¿Cuánto tardan en resolverse las alertas?"])
    if re.search(r"\bproductos?\b", f) and not re.search(r"\bpor (tipo|prioridad|sede|categoria)\b", f):
        filas = (await p.db.execute(
            select(Producto.codigo, Producto.nombre, func.count().label("n"), func.sum(case((Alerta.prioridad == "critica", 1), else_=0)).label("c")).select_from(Alerta).join(Producto, Producto.id == Alerta.producto_id)
            .where(*cond).group_by(Producto.codigo, Producto.nombre).order_by(func.count().desc(), Producto.nombre).limit(p.limite(8))
        )).all()
        texto = f"El producto con más alertas {estado} {p.en_alcance} es **{nombre_producto(filas[0].codigo, filas[0].nombre)}**, con **{B.n_de(int(filas[0].n), 'alerta')}**."
        tabla = B.tabla("Productos con más alertas", [B.col("producto", "Producto"), B.col("n", "Alertas", "entero"), B.col("c", "Críticas", "entero")],
                        [B.fila({"producto": nombre_producto(x.codigo, x.nombre), "n": int(x.n), "c": int(x.c or 0)}, ruta="/alertas") for x in filas])
        return B.Resp(texto, [tabla], enlaces_a(p, "/alertas"), ["Alertas por sede", "Alertas críticas"])
    if re.search(r"\bcategori\w+", f) and not p.hay_categoria:
        filas = (await p.db.execute(
            select(Categoria.nombre, func.count().label("n")).select_from(Alerta).join(Producto, Producto.id == Alerta.producto_id).join(Categoria, Categoria.id == Producto.categoria_id)
            .where(*cond).group_by(Categoria.nombre).order_by(func.count().desc())
        )).all()
        texto = f"La categoría con más alertas {estado} es **{filas[0].nombre}** ({B.n_de(int(filas[0].n), 'alerta')})."
        return B.Resp(texto, [B.barras("Alertas por categoría", [(x.nombre, float(x.n), B.entero(x.n)) for x in filas])], enlaces_a(p, "/alertas"), ["Alertas por sede", "Resumen de alertas"])
    bloques = []
    por_sede = (await p.db.execute(select(Sede.nombre, func.count().label("n")).select_from(Alerta).join(Sede, Sede.id == Alerta.sede_id).where(*cond).group_by(Sede.nombre).order_by(func.count().desc(), Sede.nombre))).all()
    por_tipo = (await p.db.execute(select(Alerta.tipo, func.count()).where(*cond).group_by(Alerta.tipo).order_by(func.count().desc()))).all()
    por_prioridad = dict((await p.db.execute(select(Alerta.prioridad, func.count()).where(*cond).group_by(Alerta.prioridad))).all())
    pide_tipo, pide_prioridad = bool(re.search(r"\btipo\b", f)), bool(re.search(r"\bprioridad\w*\b", f))
    if pide_tipo and not re.search(r"\bsede\b", f):
        texto = f"Hay **{B.n_de(total, 'alerta')} {estado}** {p.en_alcance}; la que más se repite es «{B.TIPO_ALERTA.get(por_tipo[0][0], por_tipo[0][0]).lower()}» ({B.n_de(int(por_tipo[0][1]), 'alerta')})."
        bloques.append(B.barras("Por tipo", [(B.TIPO_ALERTA.get(t, t), float(n), B.entero(n)) for t, n in por_tipo]))
    elif pide_prioridad and not re.search(r"\bsede\b", f):
        texto = f"Hay **{B.n_de(total, 'alerta')} {estado}** {p.en_alcance}: " + ", ".join(f"{por_prioridad[k]} {B.PRIORIDAD[k][0].lower()}{'s' if k == 'critica' and por_prioridad[k] != 1 else ''}" for k in ("critica", "alta", "media", "baja") if por_prioridad.get(k)) + "."
        bloques.append(B.barras("Por prioridad", [(B.PRIORIDAD[k][0], float(por_prioridad[k]), B.entero(por_prioridad[k])) for k in ("critica", "alta", "media", "baja") if por_prioridad.get(k)]))
    else:
        texto = f"La sede con más alertas {estado} es **{por_sede[0].nombre}** ({B.n_de(int(por_sede[0].n), 'alerta')} de {B.entero(total)})." if len(por_sede) > 1 else f"Hay **{B.n_de(total, 'alerta')} {estado}** {p.en_alcance}."
        bloques.append(B.barras("Por sede", [(x.nombre, float(x.n), B.entero(x.n)) for x in por_sede]))
        bloques.append(B.barras("Por tipo", [(B.TIPO_ALERTA.get(t, t), float(n), B.entero(n)) for t, n in por_tipo]))
    return B.Resp(texto, bloques, enlaces_a(p, "/alertas"), ["Alertas críticas", "Alertas más antiguas", "Productos con más alertas"])


def _cond_alertas_resueltas(p: Peticion) -> list:
    c = [Alerta.empresa_id == p.ctx.empresa_id, Alerta.estado == "resuelta", Alerta.resuelta_en.is_not(None)]
    if p.sede_ids is not None:
        c.append(Alerta.sede_id.in_(p.sede_ids))
    if p.producto_ids:
        c.append(Alerta.producto_id.in_(p.producto_ids))
    return c


# ==================================================================================================== análisis de traslados
@manejador("traslados_analisis")
async def traslados_analisis(p: Peticion) -> B.Resp:
    f = p.frase
    origen, destino = aliased(Sede), aliased(Sede)
    cond = _cond_traslados(p)
    unidades_sub = select(func.coalesce(func.sum(TrasladoItem.cantidad), 0)).where(TrasladoItem.traslado_id == Traslado.id).scalar_subquery()
    if re.search(r"\b(en transito|en camino|por llegar|sin recibir|sin llegar)\b", f):
        filas = (await p.db.execute(
            select(Traslado, origen.nombre.label("origen"), destino.nombre.label("destino"), unidades_sub.label("u"))
            .join(origen, origen.id == Traslado.sede_origen_id).join(destino, destino.id == Traslado.sede_destino_id)
            .where(*cond, Traslado.estado == "aprobado").order_by(Traslado.solicitado_en.desc())
        )).all()
        if not filas:
            return B.Resp(f"No hay mercancía en tránsito {p.en_alcance}: ningún traslado está aprobado a la espera de que la sede destino lo confirme.", enlaces=enlaces_a(p, "/traslados"), sugerencias=["¿Qué traslados están pendientes?"])
        unidades = sum(int(x.u) for x in filas)
        texto = f"Hay **{B.entero(unidades)} unidades en tránsito** {p.en_alcance}, repartidas en **{B.n_de(len(filas), 'traslado')}** aprobados que la sede destino aún no confirma."
        tabla = B.tabla(None, [B.col("numero", "Traslado"), B.col("origen", "Origen"), B.col("destino", "Destino"), B.col("u", "Unidades", "entero"), B.col("fecha", "Aprobado", "fecha_hora")],
                        [B.fila({"numero": f"N.º {x.Traslado.numero}", "origen": x.origen, "destino": x.destino, "u": int(x.u), "fecha": x.Traslado.aprobado_en}, ruta="/traslados") for x in filas[: p.limite(10)]],
                        total=len(filas), nota=nota_listado(min(len(filas), p.limite(10)), len(filas), "traslados"))
        return B.Resp(texto, [tabla], enlaces_a(p, "/traslados"), ["¿Qué traslados están pendientes?", "Tiempo promedio de un traslado"],
                      ["«En tránsito» = traslado aprobado y todavía sin confirmar su recepción; el inventario ya salió de la sede origen."])
    periodo = ultimos(p, 90)
    cond += [Traslado.solicitado_en >= inicio_de_dia_utc(periodo.desde), Traslado.solicitado_en < fin_de_dia_utc(periodo.hasta)]
    traslados = (await p.db.execute(
        select(Traslado, origen.nombre.label("origen"), destino.nombre.label("destino"), unidades_sub.label("u"))
        .join(origen, origen.id == Traslado.sede_origen_id).join(destino, destino.id == Traslado.sede_destino_id).where(*cond)
    )).all()
    if not traslados:
        return B.Resp(f"No hay traslados {p.en_alcance} {p.en_periodo(periodo)}.", enlaces=enlaces_a(p, "/traslados"), sugerencias=["¿Qué traslados están pendientes?"])
    if re.search(r"\b(tiempo|tarda\w*|demor\w+|rapido|lento|duracion)\b", f):
        aprob = [_dias_entre(x.Traslado.solicitado_en, x.Traslado.aprobado_en) for x in traslados if x.Traslado.aprobado_en]
        recib = [_dias_entre(x.Traslado.aprobado_en, x.Traslado.confirmado_en) for x in traslados if x.Traslado.aprobado_en and x.Traslado.confirmado_en]
        total = [_dias_entre(x.Traslado.solicitado_en, x.Traslado.confirmado_en) for x in traslados if x.Traslado.confirmado_en]
        if not total and not aprob:
            return B.Resp(f"Los traslados {p.en_periodo(periodo)} todavía no tienen aprobaciones ni confirmaciones para medir tiempos.", enlaces=enlaces_a(p, "/traslados"))
        partes, metricas = [], []
        for etiqueta, datos in (("En aprobarse", aprob), ("En llegar tras la aprobación", recib), ("Total (solicitud a recepción)", total)):
            if datos:
                prom = sum(datos) / len(datos)
                partes.append(f"{etiqueta.lower()}: {_duracion(prom)}")
                metricas.append((etiqueta, _duracion(prom), f"{B.n_de(len(datos), 'traslado')}"))
        return B.Resp(f"Tiempos promedio de los traslados {p.en_alcance} {p.en_periodo(periodo)} — " + "; ".join(partes) + ".", [B.metricas(None, *metricas)], enlaces_a(p, "/traslados"), ["Traslados por sede", "Mercancía en tránsito"])
    if re.search(r"\bproductos?\b", f) and not p.hay_producto:
        filas = (await p.db.execute(
            select(Producto.codigo, Producto.nombre, func.sum(TrasladoItem.cantidad).label("u"), func.count(func.distinct(Traslado.id)).label("n"))
            .select_from(TrasladoItem).join(Traslado, Traslado.id == TrasladoItem.traslado_id).join(Producto, Producto.id == TrasladoItem.producto_id)
            .where(*cond, Traslado.estado.in_(("aprobado", "confirmado"))).group_by(Producto.codigo, Producto.nombre).order_by(func.sum(TrasladoItem.cantidad).desc()).limit(p.limite(8))
        )).all()
        if filas:
            return B.Resp(f"El producto que más se traslada {p.en_alcance} {p.en_periodo(periodo)} es **{nombre_producto(filas[0].codigo, filas[0].nombre)}**: **{B.entero(filas[0].u)} unidades** en {B.n_de(int(filas[0].n), 'traslado')}.",
                          [B.tabla("Productos más trasladados (aprobados y confirmados)", [B.col("producto", "Producto"), B.col("u", "Unidades", "entero"), B.col("n", "Traslados", "entero")],
                                   [B.fila({"producto": nombre_producto(x.codigo, x.nombre), "u": int(x.u), "n": int(x.n)}, ruta="/traslados") for x in filas])], enlaces_a(p, "/traslados"), ["Traslados por sede"])
    if re.search(r"\b(ruta|trayecto|recorrido|de donde a donde|entre que sedes)\b", f):
        rutas: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
        for x in traslados:
            rutas[(x.origen, x.destino)][0] += 1
            rutas[(x.origen, x.destino)][1] += int(x.u)
        orden = sorted(rutas.items(), key=lambda kv: (-kv[1][0], -kv[1][1]))
        (o, d), (n, u) = orden[0]
        return B.Resp(f"La ruta de traslado más frecuente {p.en_periodo(periodo)} es de **{o}** a **{d}**: {B.n_de(n, 'traslado')} y {B.entero(u)} unidades.",
                      [B.tabla(None, [B.col("ruta", "Ruta"), B.col("n", "Traslados", "entero"), B.col("u", "Unidades", "entero")], [B.fila({"ruta": f"{a} → {b}", "n": v[0], "u": v[1]}, ruta="/traslados") for (a, b), v in orden[:8]])],
                      enlaces_a(p, "/traslados"), ["Traslados por sede"])
    if re.search(r"\bsede\w*\b|\benvia\w*\b|\brecibe\w*\b|\bmanda\w*\b|\bsalen\b|\bllegan\b", f):
        salen: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        llegan: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for x in traslados:
            salen[x.origen][0] += 1
            salen[x.origen][1] += int(x.u)
            llegan[x.destino][0] += 1
            llegan[x.destino][1] += int(x.u)
        nombres = sorted(set(salen) | set(llegan))
        mayor_envia = max(salen.items(), key=lambda kv: kv[1][1])[0] if salen else "—"
        mayor_recibe = max(llegan.items(), key=lambda kv: kv[1][1])[0] if llegan else "—"
        texto = f"{p.periodo_inicio(periodo)} la sede que más mercancía envió fue **{mayor_envia}** y la que más recibió fue **{mayor_recibe}** ({B.n_de(len(traslados), 'traslado')} en total)."
        tabla = B.tabla(None, [B.col("sede", "Sede"), B.col("env", "Traslados enviados", "entero"), B.col("uenv", "Unidades enviadas", "entero"), B.col("rec", "Traslados recibidos", "entero"), B.col("urec", "Unidades recibidas", "entero")],
                        [B.fila({"sede": n, "env": salen[n][0] if n in salen else 0, "uenv": salen[n][1] if n in salen else 0, "rec": llegan[n][0] if n in llegan else 0, "urec": llegan[n][1] if n in llegan else 0}, ruta="/traslados") for n in nombres])
        return B.Resp(texto, [tabla], enlaces_a(p, "/traslados"), ["Ruta de traslado más frecuente", "Mercancía en tránsito"])
    por_estado: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for x in traslados:
        por_estado[x.Traslado.estado][0] += 1
        por_estado[x.Traslado.estado][1] += int(x.u)
    texto = f"{p.periodo_inicio(periodo)} se solicitaron **{B.n_de(len(traslados), 'traslado')}** {p.en_alcance}, por **{B.entero(sum(int(x.u) for x in traslados))} unidades**."
    metricas = [(B.ESTADO_TRASLADO[k][0], B.entero(por_estado[k][0]), f"{B.entero(por_estado[k][1])} u.", B.ESTADO_TRASLADO[k][1]) for k in ("solicitado", "aprobado", "confirmado", "rechazado", "cancelado") if por_estado.get(k)]
    return B.Resp(texto, [B.metricas("Por estado", *metricas)], enlaces_a(p, "/traslados"), ["Traslados por sede", "Mercancía en tránsito", "Tiempo promedio de un traslado"])


# ================================================================================================ análisis de movimientos
@manejador("movimientos_analisis")
async def movimientos_analisis(p: Peticion) -> B.Resp:
    f = p.frase
    periodo = ultimos(p, 30)
    cond = _condiciones(p, periodo, None)
    lineas, _, _ = await _totales(p, cond)
    if not lineas:
        return await _vacio(p, "movimientos", periodo)
    if re.search(r"\b(quien|quienes|usuario\w*|persona\w*|empleado\w*|responsable\w*)\b", f):
        filas = (await p.db.execute(
            select(Usuario.nombre, func.count().label("n"), func.coalesce(func.sum(func.abs(Movimiento.delta)), 0).label("u")).select_from(Movimiento).join(Producto, Producto.id == Movimiento.producto_id)
            .join(Usuario, Usuario.id == Movimiento.usuario_id).where(*cond).group_by(Usuario.nombre).order_by(func.count().desc(), Usuario.nombre)
        )).all()
        texto = f"{p.periodo_inicio(periodo)} quien más movimientos registró {p.en_alcance} fue **{filas[0].nombre}**: {B.n_de(int(filas[0].n), 'movimiento')} y {B.entero(filas[0].u)} unidades."
        tabla = B.tabla("Movimientos por persona", [B.col("p", "Persona"), B.col("n", "Movimientos", "entero"), B.col("u", "Unidades movidas", "entero")],
                        [B.fila({"p": x.nombre, "n": int(x.n), "u": int(x.u)}, ruta="/movimientos") for x in filas[: p.limite(10)]], total=len(filas))
        return B.Resp(texto, [tabla], enlaces_a(p, "/movimientos"), ["Últimos movimientos de inventario", "Balance de entradas y salidas"])
    if re.search(r"\bsede\w*\b", f) and (p.sede_ids is None or len(p.sede_ids) > 1):
        filas = (await p.db.execute(
            select(Sede.nombre, func.count().label("n"), func.coalesce(func.sum(func.abs(Movimiento.delta)), 0).label("u")).select_from(Movimiento).join(Producto, Producto.id == Movimiento.producto_id)
            .join(Sede, Sede.id == Movimiento.sede_id).where(*cond).group_by(Sede.nombre).order_by(func.count().desc())
        )).all()
        return B.Resp(f"{p.periodo_inicio(periodo)} la sede con más movimientos es **{filas[0].nombre}** ({B.n_de(int(filas[0].n), 'movimiento')}).",
                      [B.barras("Movimientos por sede", [(x.nombre, float(x.n), f"{B.entero(x.n)} · {B.entero(x.u)} u.") for x in filas])], enlaces_a(p, "/movimientos"), ["Balance de entradas y salidas"])
    if re.search(r"\bproductos?\b", f) and not p.hay_producto:
        filas = (await p.db.execute(
            select(Producto.codigo, Producto.nombre, func.count().label("n"), func.coalesce(func.sum(func.abs(Movimiento.delta)), 0).label("u")).select_from(Movimiento).join(Producto, Producto.id == Movimiento.producto_id)
            .where(*cond).group_by(Producto.codigo, Producto.nombre).order_by(func.count().desc(), Producto.nombre).limit(p.limite(8))
        )).all()
        return B.Resp(f"{p.periodo_inicio(periodo)} el producto con más movimiento {p.en_alcance} es **{nombre_producto(filas[0].codigo, filas[0].nombre)}**: {B.n_de(int(filas[0].n), 'movimiento')}.",
                      [B.tabla(None, [B.col("producto", "Producto"), B.col("n", "Movimientos", "entero"), B.col("u", "Unidades movidas", "entero")], [B.fila({"producto": nombre_producto(x.codigo, x.nombre), "n": int(x.n), "u": int(x.u)}, ruta="/movimientos") for x in filas])],
                      enlaces_a(p, "/movimientos"), ["Movimientos por persona"])
    por_tipo = (await p.db.execute(
        select(Movimiento.tipo, func.count().label("n"), func.coalesce(func.sum(Movimiento.delta), 0).label("neto"), func.coalesce(func.sum(func.abs(Movimiento.delta)), 0).label("u"))
        .select_from(Movimiento).join(Producto, Producto.id == Movimiento.producto_id).where(*cond).group_by(Movimiento.tipo).order_by(func.count().desc())
    )).all()
    entran = sum(int(x.u) for x in por_tipo if x.neto > 0)
    salen = sum(int(x.u) for x in por_tipo if x.neto < 0)
    texto = (f"{p.periodo_inicio(periodo)} el inventario {p.en_alcance} recibió **{B.entero(entran)} unidades** y despachó **{B.entero(salen)}** (balance {'+' if entran >= salen else '−'}{B.entero(abs(entran - salen))}), "
             f"en {B.n_de(lineas, 'movimiento')}.")
    tabla = B.tabla("Por tipo de movimiento", [B.col("tipo", "Tipo"), B.col("n", "Movimientos", "entero"), B.col("u", "Unidades", "entero"), B.col("neto", "Efecto neto", "entero")],
                    [B.fila({"tipo": B.TIPO_MOVIMIENTO.get(x.tipo, x.tipo), "n": int(x.n), "u": int(x.u), "neto": int(x.neto)}, ruta="/movimientos") for x in por_tipo])
    bloques = [B.metricas(None, ("Entraron", B.entero(entran), None, "success"), ("Salieron", B.entero(salen), None, "warning"), ("Balance", f"{'+' if entran >= salen else '−'}{B.entero(abs(entran - salen))}")), tabla]
    return B.Resp(texto, bloques, enlaces_a(p, "/movimientos"), ["Movimientos por persona", "Movimientos por sede", "Producto con más movimientos"])


# ============================================================================================ compras y devoluciones
@manejador("compras_resumen")
async def compras_resumen(p: Peticion) -> B.Resp:
    periodo = ultimos(p, 30)
    cond = [*_condiciones(p, periodo, ("entrada",)), Movimiento.motivo == "compra"]
    lineas, unidades, valor = await _totales(p, cond)
    if not lineas:
        return await _vacio(p, "compras registradas (entradas por compra)", periodo, ("entrada",), [Movimiento.motivo == "compra"])
    por_sede = (await p.db.execute(
        select(Sede.nombre, func.coalesce(func.sum(Movimiento.delta), 0).label("u")).select_from(Movimiento).join(Producto, Producto.id == Movimiento.producto_id).join(Sede, Sede.id == Movimiento.sede_id)
        .where(*cond).group_by(Sede.nombre).order_by(func.sum(Movimiento.delta).desc())
    )).all()
    texto = f"{p.periodo_inicio(periodo)} se registraron compras {p.con_filtro('').strip() + ' ' if p.hay_producto or p.hay_categoria else ''}{p.en_alcance} por **{B.entero(unidades)} unidades** en {B.n_de(lineas, 'línea')}, con un valor a costo de **{B.moneda(valor)}**."
    bloques = [B.metricas(None, ("Unidades compradas", B.entero(unidades)), ("Líneas", B.entero(lineas)), ("Valor a costo", B.moneda(valor)))]
    if len(por_sede) > 1:
        bloques.append(B.barras("Por sede", [(x.nombre, float(x.u), f"{B.entero(x.u)} u.") for x in por_sede]))
    bloques.append(_tabla_lineas(await _lineas(p, cond, p.limite(8)), lineas))
    return B.Resp(texto, bloques, enlaces_a(p, "/movimientos"), ["¿Qué mercancía entró este mes?", "¿Qué debo reponer esta semana?", "Valor del inventario"],
                  ["Son las entradas de inventario con motivo «Compra»; Inventia no maneja órdenes de compra ni cuentas por pagar."])


@manejador("devoluciones")
async def devoluciones(p: Peticion) -> B.Resp:
    periodo = ultimos(p, 90)
    texto_partes, metricas, bloques = [], [], []
    if p.tiene("movimientos.ver"):
        for motivo, etiqueta in (("devolucion_cliente", "Devoluciones de clientes"), ("devolucion_proveedor", "Devoluciones a proveedores")):
            cond = [*_condiciones(p, periodo, None), Movimiento.motivo == motivo]
            lineas, unidades, valor = await _totales(p, cond)
            metricas.append((etiqueta, B.n_de(unidades, "unidad", "unidades"), f"{B.moneda(valor)} a costo · {B.n_de(lineas, 'línea')}"))
            texto_partes.append(f"{etiqueta.lower()}: {B.entero(unidades)} unidades ({B.n_de(lineas, 'registro')})")
    if p.tiene("ventas.ver"):
        anuladas = await totales_ventas(p, periodo, estado="anulada")
        metricas.append(("Ventas anuladas", B.entero(anuladas.ventas), B.moneda(anuladas.monto)))
        texto_partes.append(f"ventas anuladas: {B.n_de(anuladas.ventas, 'venta')} por {B.moneda(anuladas.monto)}")
    if not metricas:
        return B.Resp("Con tu rol no puedo consultar movimientos ni ventas, así que no tengo cómo ver devoluciones.")
    texto = f"{p.periodo_inicio(periodo)} {p.en_alcance}: " + "; ".join(texto_partes) + "."
    bloques.append(B.metricas(None, *metricas))
    return B.Resp(texto, bloques, enlaces_a(p, "/movimientos", "/ventas"), ["Ventas anuladas", "Pérdidas del mes", "Garantías abiertas"],
                  ["Inventia registra las devoluciones como movimientos de inventario con motivo «Devolución de cliente» o «Devolución a proveedor»; no hay un módulo de notas crédito."])


# =========================================================================================================== pendientes
@manejador("tareas_pendientes")
async def tareas_pendientes(p: Peticion) -> B.Resp:
    items: list[tuple[str, str, str]] = []  # (texto, ruta, tono)
    if p.tiene("alertas.ver"):
        cond = [Alerta.empresa_id == p.ctx.empresa_id, Alerta.estado == "activa", *([Alerta.sede_id.in_(p.sede_ids)] if p.sede_ids is not None else [])]
        criticas = int(await p.db.scalar(select(func.count()).select_from(Alerta).where(*cond, Alerta.prioridad == "critica")) or 0)
        total = int(await p.db.scalar(select(func.count()).select_from(Alerta).where(*cond)) or 0)
        if total:
            items.append((f"{B.n_de(total, 'alerta')} activa{'' if total == 1 else 's'}" + (f", {criticas} crítica{'' if criticas == 1 else 's'}" if criticas else ""), "/alertas", "danger" if criticas else "warning"))
    if p.tiene("inventario.ver", "inventario.consolidado"):
        t = (await totales_inventario(p))[None]
        if t.agotados:
            items.append((f"{B.n_de(t.agotados, 'producto')} agotado{'' if t.agotados == 1 else 's'} (contando cada producto por sede)", "/inventario", "danger"))
    if p.tiene("recomendaciones.ver"):
        n = int(await p.db.scalar(select(func.count()).select_from(Recomendacion).where(*_cond_recomendaciones(p, estado="pendiente", con_tipo=False))) or 0)
        if n:
            items.append((f"{B.n_de(n, 'recomendación', 'recomendaciones')} por revisar", "/recomendaciones", "accent"))
    if p.tiene("traslados.ver"):
        cond = _cond_traslados(p)
        solicitados = int(await p.db.scalar(select(func.count()).select_from(Traslado).where(*cond, Traslado.estado == "solicitado")) or 0)
        aprobados = int(await p.db.scalar(select(func.count()).select_from(Traslado).where(*cond, Traslado.estado == "aprobado")) or 0)
        if solicitados:
            items.append((f"{B.n_de(solicitados, 'traslado')} esperando aprobación", "/traslados", "warning"))
        if aprobados:
            items.append((f"{B.n_de(aprobados, 'traslado')} aprobado{'' if aprobados == 1 else 's'} por confirmar su recepción", "/traslados", "warning"))
    if p.tiene("pqrs.gestionar"):
        n = int(await p.db.scalar(select(func.count()).select_from(Pqrs).where(Pqrs.empresa_id == p.ctx.empresa_id, Pqrs.estado == "pendiente", *([Pqrs.sede_id.in_(p.sede_ids)] if p.sede_ids is not None else []))) or 0)
        if n:
            items.append((f"{B.n_de(n, 'PQRS')} pendiente{'' if n == 1 else 's'} de respuesta", "/sig/pqrs", "warning"))
    if p.tiene("calidad.ver", "calidad.gestionar"):
        sede_nc = [NoConformidad.sede_id.in_(p.sede_ids)] if p.sede_ids is not None else []
        sede_ga = [Garantia.sede_id.in_(p.sede_ids)] if p.sede_ids is not None else []
        nc = int(await p.db.scalar(select(func.count()).select_from(NoConformidad).where(NoConformidad.empresa_id == p.ctx.empresa_id, NoConformidad.estado.in_(("reportado", "en_revision", "en_proceso_solucion")), *sede_nc)) or 0)
        ga = int(await p.db.scalar(select(func.count()).select_from(Garantia).where(Garantia.empresa_id == p.ctx.empresa_id, Garantia.estado.in_(("reportada", "pendiente_revision", "enviada_proveedor")), *sede_ga)) or 0)
        if nc:
            items.append((f"{B.n_de(nc, 'no conformidad', 'no conformidades')} abierta{'' if nc == 1 else 's'}", "/sig/calidad", "warning"))
        if ga:
            items.append((f"{B.n_de(ga, 'garantía')} sin resolver", "/sig/calidad", "warning"))
    if not items:
        return B.Resp(f"No veo nada pendiente {p.en_alcance} con lo que tu rol puede consultar. Todo al día.", sugerencias=["Dame un resumen general", "¿Cómo está el inventario?"])
    orden = {"danger": 0, "warning": 1, "accent": 2}
    items.sort(key=lambda x: orden.get(x[2], 3))
    texto = f"Esto es lo que tienes pendiente {p.en_alcance}, de lo más urgente a lo menos:"
    rutas = list(dict.fromkeys(r for _, r, _ in items))
    return B.Resp(texto, [B.lista(None, [t for t, _, _ in items])], [e for r in rutas for e in enlaces_a(p, r)][:5], ["Alertas críticas", "¿Qué debo reponer esta semana?", "¿Qué traslados están pendientes?"])


# ================================================================================================= inversión en reposición
@manejador("inversion_reposicion")
async def inversion_reposicion(p: Peticion) -> B.Resp:
    cond = [*_cond_recomendaciones(p, estado="pendiente", con_tipo=False), Recomendacion.tipo == "reabastecimiento"]
    filas = (await p.db.execute(
        select(Producto.codigo, Producto.nombre, Producto.costo, Sede.nombre.label("sede"), Recomendacion.cantidad_sugerida, Recomendacion.prioridad)
        .select_from(Recomendacion).join(Producto, Producto.id == Recomendacion.producto_id).join(Sede, Sede.id == Recomendacion.sede_id).where(*cond)
    )).all()
    if not filas:
        return B.Resp(f"No hay recomendaciones de compra pendientes {p.en_alcance}, así que no hay inversión sugerida.", enlaces=enlaces_a(p, "/recomendaciones"), sugerencias=["Recomendaciones aprobadas", "¿Cómo está el inventario?"])
    con_costo = [x for x in filas if x.costo is not None]
    sin_costo = len(filas) - len(con_costo)
    total = sum(float(x.costo) * x.cantidad_sugerida for x in con_costo)
    unidades = sum(x.cantidad_sugerida for x in filas)
    por_sede: dict[str, float] = defaultdict(float)
    por_producto: dict[str, list[float]] = defaultdict(lambda: [0.0, 0])
    for x in con_costo:
        por_sede[x.sede] += float(x.costo) * x.cantidad_sugerida
        acum = por_producto[nombre_producto(x.codigo, x.nombre)]
        acum[0] += float(x.costo) * x.cantidad_sugerida
        acum[1] += x.cantidad_sugerida
    texto = f"Reponer lo que recomienda el sistema {p.en_alcance} costaría cerca de **{B.moneda(total)}** a costo: **{B.entero(unidades)} unidades** en **{B.n_de(len(filas), 'recomendación', 'recomendaciones')}** de compra pendientes."
    bloques = [B.metricas(None, ("Inversión estimada", B.moneda(total)), ("Unidades", B.entero(unidades)), ("Recomendaciones", B.entero(len(filas))))]
    if len(por_sede) > 1:
        bloques.append(B.barras("Por sede", sorted(((n, v, B.moneda(v)) for n, v in por_sede.items()), key=lambda x: -x[1])))
    top = sorted(por_producto.items(), key=lambda kv: -kv[1][0])[: p.limite(6)]
    if top:
        bloques.append(B.tabla("Mayor inversión por producto", [B.col("producto", "Producto"), B.col("u", "Unidades", "entero"), B.col("v", "Costo estimado", "moneda")],
                               [B.fila({"producto": n, "u": int(v[1]), "v": v[0]}, ruta="/recomendaciones") for n, v in top]))
    avisos = [f"{B.n_de(sin_costo, 'recomendación', 'recomendaciones')} sin costo registrado no suma(n) al valor."] if sin_costo else []
    return B.Resp(texto, bloques, enlaces_a(p, "/recomendaciones"), ["¿Qué debo reponer esta semana?", "Recomendaciones de traslado"], avisos)


# ======================================================================================================== consejos
@manejador("consejos_inventario")
async def consejos_inventario(p: Peticion) -> B.Resp:
    t = (await totales_inventario(p))[None]
    f = p.frase
    consejos: list[str] = []
    if re.search(r"\b(reduc\w+|reduzc\w+|bajar|disminu\w+|exceso|sobrestock|sobrante\w*|liquidar|inmovilizad\w+)\b", f):
        titulo = "Para reducir el inventario"
        consejos = [
            f"Empieza por lo que sobra: hoy hay {B.n_de(t.excesivos, 'producto')} en exceso (por sede). Pregúntame «¿Qué tengo en exceso?» para verlos.",
            "Antes de comprar más, mira si otra sede lo necesita: un traslado mueve el sobrante sin gastar dinero. Revisa las recomendaciones de traslado.",
            "Identifica lo que no rota: «Productos sin ventas» te dice qué tiene existencias y no se vendió en el periodo.",
            "Deja de reponer lo que está en exceso y ajusta su stock máximo para que las alertas no vuelvan a avisar por lo mismo.",
            "Revisa «¿Cuánto dinero tengo parado en inventario?» para dimensionar cuánto capital se libera.",
        ]
    elif re.search(r"\b(agotad\w+|faltantes?|quiebres?|desabastec\w+|evit\w+|no quedarme|quedarnos sin)\b", f):
        titulo = "Para evitar agotados"
        consejos = [
            f"Hoy hay {B.n_de(t.agotados, 'producto')} agotado{'' if t.agotados == 1 else 's'} y {B.n_de(t.bajos, 'producto')} con stock bajo (por sede).",
            "Define un stock mínimo en todos los productos (pregunta «¿Qué productos no tienen stock mínimo configurado?»).",
            "Mira la cobertura: «¿Qué productos se van a agotar pronto?» usa la demanda estimada para avisarte antes.",
            "Aprovecha las recomendaciones de reposición y de traslado: te dicen cuánto y dónde mover.",
            "Considera el plazo de entrega de tus proveedores: se configura en los parámetros de la empresa.",
        ]
    elif re.search(r"\b(rotacion|rotar|mover|dar salida|vender mas|aumentar ventas)\b", f):
        titulo = "Para mejorar la rotación"
        consejos = [
            "Mide primero: «Rotación del inventario» y «Análisis ABC» te muestran qué productos mueven el negocio y cuáles no.",
            "Concentra el stock en los productos clase A y reduce el de clase C.",
            "Revisa «Productos sin ventas»: son los que más frenan la rotación.",
            "Traslada los sobrantes hacia la sede donde más se vende ese producto.",
        ]
    else:
        titulo = "Buenas prácticas con los datos de Inventia"
        consejos = [
            f"Mantén el stock mínimo y máximo de cada producto al día (hoy hay {B.n_de(t.bajos, 'producto')} con stock bajo y {B.n_de(t.excesivos, 'producto')} en exceso, por sede).",
            "Revisa las alertas críticas cada día y atiende primero las de riesgo de desabastecimiento.",
            "Genera la predicción con regularidad y aprueba o rechaza las recomendaciones pendientes.",
            "Registra todas las entradas, mermas y ajustes: el kardex solo es confiable si todo movimiento queda anotado.",
            "Haz conteos físicos periódicos y corrige diferencias con un ajuste de inventario.",
        ]
    texto = f"{titulo} {p.en_alcance}, con base en tus datos:"
    return B.Resp(texto, [B.lista(None, consejos)], enlaces_a(p, "/inventario", "/recomendaciones", "/alertas"), ["¿Qué tengo en exceso?", "Análisis ABC", "¿Qué productos se van a agotar pronto?"],
                  ["Son sugerencias generales de gestión de inventario apoyadas en tus cifras; las decisiones las tomas tú."])
