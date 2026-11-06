"""Respuestas de traslados, alertas, cobertura, predicción de demanda y recomendaciones."""

import re
from datetime import timedelta

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import aliased

from app.model.catalogo import Producto
from app.model.enums import EstadoEjecucion
from app.model.inventario import Alerta, InventarioSede
from app.model.operaciones import Traslado, TrasladoItem, Venta, VentaItem
from app.model.prediccion import EjecucionPrediccion, Prediccion, Recomendacion
from app.model.sede import Sede
from app.model.usuario import Usuario
from app.service.alertas_service import VIGENCIA_PREDICCION_DIAS
from app.service.asistente import bloques as B
from app.service.asistente.datos import cond_inventario, enlaces_a
from app.service.asistente.peticion import Peticion, manejador
from app.util.tiempo import a_fecha_local, fin_de_dia_utc, inicio_de_dia_utc

_ORDEN_PRIORIDAD = {"critica": 0, "alta": 1, "media": 2, "baja": 3}


def _de(p: Peticion) -> str:
    f = p.descripcion_filtro()
    return f" {f}" if f else ""


def _producto(codigo: str, nombre: str) -> str:
    return f"{nombre} ({codigo})"


def _prioridad_sql(columna):
    return case((columna == "critica", 0), (columna == "alta", 1), (columna == "media", 2), else_=3)


# =============================================================================================== TRASLADOS
_HACIA = re.compile(r"\b(llegan|llegaron|llegada|reciben|recibe|recibieron|entran|entraron|con destino|destino|hacia|enviados? a|enviadas? a|para)\b")
_DESDE = re.compile(r"\b(salen|salieron|salida|con origen|origen|desde|despachad\w+|enviad\w+ (de|desde)|de la sede|de sede)\b")


def _tramo(p: Peticion) -> tuple[str, list[int]] | None:
    """Si la persona habla de un sentido concreto («de Norte a Sur», «los que llegan a Norte»): (texto, sedes en orden origen→destino)."""
    if not p.sedes_nombradas:
        return None
    ids = [s.id for s in p.e.sedes if p.sede_ids is None or s.id in p.sede_ids]
    nombre = {s.id: s.nombre for s in p.d.sedes}
    if len(ids) == 2 and re.search(r"\b(de|desde)\b.*\b(a|hacia|para)\b", p.frase):
        return f"de {nombre[ids[0]]} a {nombre[ids[1]]}", ids
    if len(ids) == 1 and _HACIA.search(p.frase) and not _DESDE.search(p.frase):
        return f"con destino a {nombre[ids[0]]}", ids
    if len(ids) == 1 and _DESDE.search(p.frase) and not _HACIA.search(p.frase):
        return f"con origen en {nombre[ids[0]]}", ids
    return None


def _donde_traslados(p: Peticion) -> str:
    tramo = _tramo(p)
    return f"{tramo[0]}" if tramo else p.en_alcance


def _cond_traslados(p: Peticion) -> list:
    c = [Traslado.empresa_id == p.ctx.empresa_id]
    tramo = _tramo(p)
    if tramo:
        texto, ids = tramo
        if texto.startswith("de "):
            c += [Traslado.sede_origen_id == ids[0], Traslado.sede_destino_id == ids[1]]
        elif texto.startswith("con destino"):
            c.append(Traslado.sede_destino_id == ids[0])
        else:
            c.append(Traslado.sede_origen_id == ids[0])
    elif p.sede_ids is not None:
        c.append(or_(Traslado.sede_origen_id.in_(p.sede_ids), Traslado.sede_destino_id.in_(p.sede_ids)))
    if p.producto_ids or p.categoria_ids:
        sub = select(TrasladoItem.traslado_id).join(Producto, Producto.id == TrasladoItem.producto_id)
        if p.producto_ids:
            sub = sub.where(TrasladoItem.producto_id.in_(p.producto_ids))
        if p.categoria_ids:
            sub = sub.where(Producto.categoria_id.in_(p.categoria_ids))
        c.append(Traslado.id.in_(sub))
    return c


async def _filas_traslados(p: Peticion, condiciones: list, limite: int):
    origen, destino = aliased(Sede), aliased(Sede)
    unidades = select(func.coalesce(func.sum(TrasladoItem.cantidad), 0)).where(TrasladoItem.traslado_id == Traslado.id).scalar_subquery()
    consulta = (
        select(Traslado, origen.nombre.label("origen"), destino.nombre.label("destino"), unidades.label("unidades"))
        .join(origen, origen.id == Traslado.sede_origen_id).join(destino, destino.id == Traslado.sede_destino_id)
        .where(*condiciones).order_by(Traslado.solicitado_en.desc(), Traslado.id.desc()).limit(limite)
    )
    return (await p.db.execute(consulta)).all()


def _tabla_traslados(filas, total: int):
    cols = [B.col("numero", "Traslado"), B.col("origen", "Origen"), B.col("destino", "Destino"), B.col("unidades", "Unidades", "entero"), B.col("estado", "Estado"), B.col("fecha", "Solicitado", "fecha_hora")]
    salida = []
    for f in filas:
        t = f.Traslado
        etiqueta, tono = B.ESTADO_TRASLADO.get(t.estado, (t.estado, "neutral"))
        salida.append(B.fila({"numero": f"N.º {t.numero}", "origen": f.origen, "destino": f.destino, "unidades": int(f.unidades), "estado": etiqueta, "fecha": t.solicitado_en}, tonos={"estado": tono}, ruta="/traslados"))
    return B.tabla(None, cols, salida, total=total, nota=f"Mostrando {len(filas)} de {total}." if total > len(filas) else None)


@manejador("traslado_detalle")
async def traslado_detalle(p: Peticion) -> B.Resp:
    if p.e.numero is None:
        return B.Resp("¿De qué traslado? Dime el número, por ejemplo «detalle del traslado 3».", sugerencias=["¿Qué traslados están pendientes?"])
    filas = await _filas_traslados(p, [*_cond_traslados(p), Traslado.numero == p.e.numero], 1)
    if not filas:
        return B.Resp(f"No encontré el traslado N.º {p.e.numero}" + (" en tu sede." if p.limitado else "."), sugerencias=["¿Qué traslados están pendientes?"])
    f = filas[0]
    t = f.Traslado
    etiqueta, tono = B.ESTADO_TRASLADO.get(t.estado, (t.estado, "neutral"))
    ids = {i for i in (t.solicitado_por, t.aprobado_por, t.confirmado_por, t.cerrado_por) if i}
    nombres = dict((await p.db.execute(select(Usuario.id, Usuario.nombre).where(Usuario.id.in_(ids)))).all()) if ids else {}
    productos = {x.id: x for x in (await p.db.scalars(select(Producto).where(Producto.id.in_([i.producto_id for i in t.items])))).all()}
    texto = f"El traslado **N.º {t.numero}** va de **{f.origen}** a **{f.destino}** (**{B.entero(f.unidades)} unidades**) y está **{etiqueta.lower()}**."
    historia = [f"Solicitado por {nombres.get(t.solicitado_por, '—')} el {B.fecha_corta(a_fecha_local(t.solicitado_en))}"]
    if t.aprobado_en:
        historia.append(f"Aprobado por {nombres.get(t.aprobado_por, '—')} el {B.fecha_corta(a_fecha_local(t.aprobado_en))}")
    if t.confirmado_en:
        historia.append(f"Confirmado por {nombres.get(t.confirmado_por, '—')} el {B.fecha_corta(a_fecha_local(t.confirmado_en))}")
    if t.cerrado_en:
        historia.append(f"{etiqueta} por {nombres.get(t.cerrado_por, '—')} el {B.fecha_corta(a_fecha_local(t.cerrado_en))}" + (f": {t.motivo_cierre}" if t.motivo_cierre else ""))
    bloques = [
        B.metricas(None, ("Estado", etiqueta, None, tono), ("Origen", f.origen), ("Destino", f.destino), ("Unidades", B.entero(f.unidades))),
        B.tabla("Productos", [B.col("producto", "Producto"), B.col("cantidad", "Cantidad", "entero")],
                [B.fila({"producto": _producto(productos[i.producto_id].codigo, productos[i.producto_id].nombre) if i.producto_id in productos else "—", "cantidad": i.cantidad}) for i in t.items]),
        B.lista("Historia", historia),
    ]
    if t.estado in ("solicitado", "aprobado"):
        texto += " Las existencias solo cambian cuando se **confirma** el traslado."
    return B.Resp(texto, bloques, enlaces_a(p, "/traslados"), ["¿Qué traslados están pendientes?", "Traslados de este mes"])


@manejador("traslados_pendientes")
async def traslados_pendientes(p: Peticion) -> B.Resp:
    cond = [*_cond_traslados(p), Traslado.estado.in_(("solicitado", "aprobado"))]
    total = int(await p.db.scalar(select(func.count()).select_from(Traslado).where(*cond)) or 0)
    if not total:
        return B.Resp(f"No hay traslados pendientes{_de(p)} {_donde_traslados(p)}.", sugerencias=["Traslados de este mes", "¿Qué debo trasladar entre sedes?"], enlaces=enlaces_a(p, "/traslados"))
    por_estado = dict((await p.db.execute(select(Traslado.estado, func.count()).where(*cond).group_by(Traslado.estado))).all())
    filas = await _filas_traslados(p, cond, p.limite(10))
    texto = (f"Hay **{B.n_de(total, 'traslado')} pendientes**{_de(p)} {_donde_traslados(p)}: **{por_estado.get('solicitado', 0)} por aprobar** y **{por_estado.get('aprobado', 0)} por confirmar** (aprobados que aún no llegan).")
    if total == 1:
        texto = f"Hay **1 traslado pendiente**{_de(p)} {_donde_traslados(p)}, {'por aprobar' if por_estado.get('solicitado') else 'por confirmar'}."
    return B.Resp(texto, [B.metricas(None, ("Por aprobar", B.entero(por_estado.get("solicitado", 0)), None, "warning" if por_estado.get("solicitado") else "neutral"), ("Por confirmar", B.entero(por_estado.get("aprobado", 0)), None, "accent" if por_estado.get("aprobado") else "neutral")),
                           _tabla_traslados(filas, total)], enlaces_a(p, "/traslados"), ["Detalle del traslado " + str(filas[0].Traslado.numero), "Recomendaciones de traslado"])


@manejador("traslados_lista")
async def traslados_lista(p: Peticion) -> B.Resp:
    periodo = p.ultimos_dias(30)
    cond = [*_cond_traslados(p), Traslado.solicitado_en >= inicio_de_dia_utc(periodo.desde), Traslado.solicitado_en < fin_de_dia_utc(periodo.hasta)]
    if p.e.estado_traslado:
        cond.append(Traslado.estado == p.e.estado_traslado)
    total = int(await p.db.scalar(select(func.count()).select_from(Traslado).where(*cond)) or 0)
    estado_txt = f" {B.ESTADO_TRASLADO[p.e.estado_traslado][0].lower()}s" if p.e.estado_traslado else ""
    if not total:
        return B.Resp(f"No hay traslados{estado_txt}{_de(p)} {_donde_traslados(p)} {p.en_periodo(periodo)}.", sugerencias=["¿Qué traslados están pendientes?"], enlaces=enlaces_a(p, "/traslados"))
    por_estado = dict((await p.db.execute(select(Traslado.estado, func.count()).where(*cond).group_by(Traslado.estado))).all())
    resumen = ", ".join(f"{n} {B.ESTADO_TRASLADO.get(e, (e,))[0].lower()}" + ("s" if n != 1 else "") for e, n in sorted(por_estado.items(), key=lambda x: -x[1]))
    texto = f"{p.periodo_inicio(periodo)} hubo **{B.n_de(total, 'traslado')}**{estado_txt}{_de(p)} {_donde_traslados(p)}" + (f" ({resumen})." if not p.e.estado_traslado else ".")
    return B.Resp(texto, [_tabla_traslados(await _filas_traslados(p, cond, p.limite(10)), total)], enlaces_a(p, "/traslados"), ["¿Qué traslados están pendientes?", "¿Qué debo trasladar entre sedes?"])


# ================================================================================================ ALERTAS
def _filtra_por_periodo(p: Peticion) -> bool:
    """«Alertas de hoy» quiere decir las que hay que atender hoy, no solo las que se abrieron hoy."""
    return p.periodo is not None and not (p.periodo.etiqueta == "hoy" and p.e.estado_alerta != "resuelta")


def _cond_alertas(p: Peticion) -> list:
    resueltas = p.e.estado_alerta == "resuelta"
    c = [Alerta.empresa_id == p.ctx.empresa_id, Alerta.estado == ("resuelta" if resueltas else "activa")]
    if _filtra_por_periodo(p):
        columna = Alerta.resuelta_en if resueltas else Alerta.abierta_en
        c += [columna >= inicio_de_dia_utc(p.periodo.desde), columna < fin_de_dia_utc(p.periodo.hasta)]
    if p.sede_ids is not None:
        c.append(Alerta.sede_id.in_(p.sede_ids))
    if p.producto_ids:
        c.append(Alerta.producto_id.in_(p.producto_ids))
    if p.categoria_ids:
        c.append(Alerta.producto_id.in_(select(Producto.id).where(Producto.categoria_id.in_(p.categoria_ids))))
    if p.e.prioridad:
        c.append(Alerta.prioridad == p.e.prioridad)
    if p.e.tipo_alerta:
        c.append(Alerta.tipo == p.e.tipo_alerta)
    return c


def _estado_alertas(p: Peticion) -> str:
    return "resueltas" if p.e.estado_alerta == "resuelta" else "activas"


def _cuando(p: Peticion) -> str:
    return f" {p.en_periodo(p.periodo)}" if _filtra_por_periodo(p) else ""


def _con_punto(texto: str) -> str:
    texto = texto.strip()
    return texto if texto.endswith((".", "!", "?")) else texto + "."


@manejador("alertas_resumen")
async def alertas_resumen(p: Peticion) -> B.Resp:
    cond = _cond_alertas(p)
    total = int(await p.db.scalar(select(func.count()).select_from(Alerta).where(*cond)) or 0)
    if not total:
        return B.Resp(f"No hay alertas {_estado_alertas(p)}{_de(p)} {p.en_alcance}{_cuando(p)}." + (" El inventario está dentro de lo esperado." if _estado_alertas(p) == "activas" else ""), sugerencias=["¿Cómo está el inventario?", "¿Qué productos tienen stock bajo?"], enlaces=enlaces_a(p, "/alertas"))
    por_prioridad = dict((await p.db.execute(select(Alerta.prioridad, func.count()).where(*cond).group_by(Alerta.prioridad))).all())
    por_tipo = dict((await p.db.execute(select(Alerta.tipo, func.count()).where(*cond).group_by(Alerta.tipo))).all())
    texto = f"Hay **{B.n_de(total, 'alerta')} {_estado_alertas(p)}**{_de(p)} {p.en_alcance}{_cuando(p)}: " + ", ".join(
        f"{por_prioridad[k]} {B.PRIORIDAD[k][0].lower()}{'s' if por_prioridad[k] != 1 else ''}".replace("críticas", "críticas") for k in ("critica", "alta", "media", "baja") if por_prioridad.get(k)
    ) + "."
    bloques = [
        B.metricas("Por prioridad", *[(B.PRIORIDAD[k][0], B.entero(por_prioridad.get(k, 0)), None, B.PRIORIDAD[k][1] if por_prioridad.get(k) else "neutral") for k in ("critica", "alta", "media", "baja")]),
        B.barras("Por tipo", [(B.TIPO_ALERTA.get(t, t), n, B.entero(n)) for t, n in sorted(por_tipo.items(), key=lambda x: -x[1])]),
    ]
    return B.Resp(texto, bloques, enlaces_a(p, "/alertas"), ["Alertas críticas", "Alertas de inventario bajo", "¿Qué debo revisar hoy?"])


@manejador("alertas_lista")
async def alertas_lista(p: Peticion) -> B.Resp:
    cond = _cond_alertas(p)
    total = int(await p.db.scalar(select(func.count()).select_from(Alerta).where(*cond)) or 0)
    filtros = []
    if p.e.prioridad:
        filtros.append(B.PRIORIDAD[p.e.prioridad][0].lower() + "s")
    if p.e.tipo_alerta:
        filtros.append("de " + B.TIPO_ALERTA[p.e.tipo_alerta].lower())
    etiqueta = " ".join(filtros)
    revisar = any(w in p.frase for w in ("revisar", "atender", "resolver", "enfocarme", "toca", "hoy", "pendiente", "vigilar"))
    bloques = []
    pendientes = []
    if revisar:
        pendientes = await _pendientes_de_gestion(p)
    if not total:
        texto = f"No hay alertas {etiqueta + ' ' if etiqueta else ''}{_estado_alertas(p)}{_de(p)} {p.en_alcance}{_cuando(p)}."
        if pendientes:
            texto += " Lo que sí está pendiente: " + "; ".join(pendientes) + "."
        return B.Resp(texto, sugerencias=["Resumen de alertas", "¿Cómo está el inventario?"], enlaces=enlaces_a(p, "/alertas"))
    consulta = (
        select(Alerta, Producto.codigo, Producto.nombre, Sede.nombre.label("sede"))
        .join(Producto, Producto.id == Alerta.producto_id).join(Sede, Sede.id == Alerta.sede_id)
        .where(*cond).order_by(*((Alerta.resuelta_en.desc(), Alerta.id.desc()) if p.e.estado_alerta == "resuelta" else (_prioridad_sql(Alerta.prioridad), Alerta.abierta_en.desc(), Alerta.id))).limit(p.limite(10))
    )
    filas = (await p.db.execute(consulta)).all()
    texto = f"Hay **{B.n_de(total, 'alerta')} {etiqueta + ' ' if etiqueta else ''}{_estado_alertas(p)}**{_de(p)} {p.en_alcance}{_cuando(p)}."
    if filas:
        texto += f" {'La más reciente en resolverse' if p.e.estado_alerta == 'resuelta' else 'La más urgente'}: {_con_punto(filas[0].Alerta.mensaje)}"
    if pendientes:
        texto += " Además tienes pendiente: " + "; ".join(pendientes) + "."
    con_sede = p.sede_ids is None or len(p.sede_ids) > 1
    cols = [B.col("prioridad", "Prioridad"), B.col("tipo", "Tipo"), B.col("producto", "Producto")] + ([B.col("sede", "Sede")] if con_sede else []) + [B.col("mensaje", "Detalle")]
    tabla_filas = []
    for f in filas:
        etq, tono = B.PRIORIDAD.get(f.Alerta.prioridad, (f.Alerta.prioridad, "neutral"))
        celdas = {"prioridad": etq, "tipo": B.TIPO_ALERTA.get(f.Alerta.tipo, f.Alerta.tipo), "producto": _producto(f.codigo, f.nombre), "sede": f.sede, "mensaje": f.Alerta.mensaje}
        tabla_filas.append(B.fila(celdas, tonos={"prioridad": tono}, ruta="/alertas"))
    bloques.append(B.tabla(None, cols, tabla_filas, total=total, nota=f"Mostrando {len(filas)} de {total}." if total > len(filas) else None))
    return B.Resp(texto, bloques, enlaces_a(p, "/alertas", "/recomendaciones"), ["Resumen de alertas", "¿Qué debo reponer?", "¿Qué se va a agotar pronto?"])


async def _pendientes_de_gestion(p: Peticion) -> list[str]:
    """Traslados y recomendaciones que esperan una decisión (solo los que la persona puede consultar)."""
    salida = []
    if p.tiene("traslados.ver"):
        n = int(await p.db.scalar(select(func.count()).select_from(Traslado).where(*_cond_traslados(p), Traslado.estado.in_(("solicitado", "aprobado")))) or 0)
        if n:
            salida.append(f"{B.n_de(n, 'traslado')} por gestionar")
    if p.tiene("recomendaciones.ver"):
        n = int(await p.db.scalar(select(func.count()).select_from(Recomendacion).where(*_cond_recomendaciones(p, estado="pendiente"))) or 0)
        if n:
            salida.append(f"{B.n_de(n, 'recomendación', 'recomendaciones')} por revisar")
    return salida


# ======================================================================================== PREDICCIÓN Y COBERTURA
async def _ultima_ejecucion(p: Peticion, solo_completada: bool = True) -> EjecucionPrediccion | None:
    consulta = select(EjecucionPrediccion).where(EjecucionPrediccion.empresa_id == p.ctx.empresa_id)
    if solo_completada:
        consulta = consulta.where(EjecucionPrediccion.estado == EstadoEjecucion.COMPLETADA)
    return await p.db.scalar(consulta.order_by(EjecucionPrediccion.creada_en.desc(), EjecucionPrediccion.id.desc()).limit(1))


def _cond_prediccion(p: Peticion, ejecucion_id: int) -> list:
    c = [Prediccion.empresa_id == p.ctx.empresa_id, Prediccion.ejecucion_id == ejecucion_id]
    if p.sede_ids is not None:
        c.append(Prediccion.sede_id.in_(p.sede_ids))
    if p.producto_ids:
        c.append(Prediccion.producto_id.in_(p.producto_ids))
    if p.categoria_ids:
        c.append(Prediccion.producto_id.in_(select(Producto.id).where(Producto.categoria_id.in_(p.categoria_ids))))
    return c


def _sin_prediccion(p: Peticion) -> B.Resp:
    texto = "Todavía no se ha generado ninguna predicción de demanda."
    if p.tiene("prediccion.ejecutar"):
        texto += " Puedes generarla desde la pantalla de Predicciones."
    else:
        texto += " Pídele a quien administra el sistema que la genere."
    return B.Resp(texto, enlaces=enlaces_a(p, "/predicciones"), sugerencias=["¿Cuánto vendimos este mes?", "¿Qué productos tienen stock bajo?"])


def _frescura(p: Peticion, e: EjecucionPrediccion) -> str | None:
    if e.fecha_corte is None:
        return None
    dias = (p.hoy - e.fecha_corte).days
    if dias > VIGENCIA_PREDICCION_DIAS:
        return f"La última predicción se calculó con ventas hasta el {B.fecha_corta(e.fecha_corte)} (hace {dias} días): está desactualizada, genera una nueva para cifras confiables."
    return None


@manejador("prediccion_demanda")
async def prediccion_demanda(p: Peticion) -> B.Resp:
    ejecucion = await _ultima_ejecucion(p)
    if ejecucion is None:
        return _sin_prediccion(p)
    cond = _cond_prediccion(p, ejecucion.id)
    aviso = _frescura(p, ejecucion)
    avisos = [aviso] if aviso else []
    avisos.append("Es una estimación estadística, no una venta real. Úsala como guía y revísala antes de comprar.")
    if p.hay_producto:
        consulta = (
            select(Prediccion, Producto.codigo, Producto.nombre, Sede.nombre.label("sede"))
            .join(Producto, Producto.id == Prediccion.producto_id).join(Sede, Sede.id == Prediccion.sede_id).where(*cond).order_by(Producto.nombre, Sede.nombre)
        )
        filas = (await p.db.execute(consulta)).all()
        if not filas:
            return B.Resp(f"No hay predicción de demanda{_de(p)} {p.en_alcance}: probablemente tiene muy pocas ventas para estimarla.", enlaces=enlaces_a(p, "/predicciones"), sugerencias=["¿Cuántas unidades se han vendido este mes?"])
        # Si piden otro horizonte, se escala la tasa diaria (estimación lineal, se avisa).
        def dias_de(f) -> int:
            return (f.Prediccion.fecha_fin - f.Prediccion.fecha_inicio).days + 1
        horizonte = p.e.horizonte
        total = 0.0
        tabla_filas = []
        for f in filas:
            pr = f.Prediccion
            dias = dias_de(f)
            factor = (horizonte / dias) if horizonte else 1
            valor = float(pr.demanda_estimada) * factor
            total += valor
            confianza, tono = B.CONFIANZA.get(pr.confianza, (pr.confianza, "neutral"))
            tabla_filas.append(B.fila({"producto": _producto(f.codigo, f.nombre), "sede": f.sede, "demanda": round(valor, 1), "diaria": round(float(pr.demanda_estimada) / dias, 2),
                                       "rango": (f"{float(pr.limite_inferior) * factor:.0f} – {float(pr.limite_superior) * factor:.0f}" if pr.limite_inferior is not None and pr.limite_superior is not None else "—"),
                                       "confianza": confianza}, tonos={"confianza": tono}, ruta="/predicciones"))
        periodo_txt = f"los próximos {horizonte} días" if horizonte else f"del {B.fecha_corta(filas[0].Prediccion.fecha_inicio)} al {B.fecha_corta(filas[0].Prediccion.fecha_fin)}"
        if horizonte:
            avisos.append(f"Calculé {horizonte} días a partir del ritmo diario estimado; la predicción original cubre {dias_de(filas[0])} días.")
        nombres = {f.nombre for f in filas}
        sujeto = f"**{filas[0].nombre} ({filas[0].codigo})**" if len(nombres) == 1 else f"los {len(nombres)} productos"
        texto = f"Se estima una demanda de **{B.entero(round(total))} unidades** de {sujeto} {p.en_alcance} para {periodo_txt}."
        cols = [B.col("producto", "Producto"), B.col("sede", "Sede"), B.col("demanda", "Demanda estimada", "decimal"), B.col("diaria", "Por día", "decimal"), B.col("rango", "Rango probable"), B.col("confianza", "Confianza")]
        return B.Resp(texto, [B.tabla(None, cols, tabla_filas[:20], total=len(filas))], enlaces_a(p, "/predicciones"), ["¿Cuántos días me dura?", "¿Qué debo reponer?"], avisos)
    # Sin producto: ranking por demanda total.
    demanda = func.sum(Prediccion.demanda_estimada)
    asc = p.e.orden == "asc"
    consulta = (
        select(Producto.codigo, Producto.nombre, demanda.label("d"), func.min(Prediccion.fecha_inicio).label("ini"), func.max(Prediccion.fecha_fin).label("fin"))
        .join(Producto, Producto.id == Prediccion.producto_id).where(*cond).group_by(Producto.id, Producto.codigo, Producto.nombre)
        .order_by(demanda.asc() if asc else demanda.desc(), Producto.nombre)
    )
    todas = (await p.db.execute(consulta)).all()
    if not todas:
        return B.Resp(f"No hay predicciones{_de(p)} {p.en_alcance}.", enlaces=enlaces_a(p, "/predicciones"))
    mostrar = todas[: p.limite(10)]
    ini, fin = todas[0].ini, todas[0].fin
    dias_pred = max(1, (fin - ini).days + 1)
    factor = p.e.horizonte / dias_pred if p.e.horizonte else 1.0
    if p.e.horizonte and p.e.horizonte != dias_pred:
        avisos.append(f"Calculé {p.e.horizonte} días a partir del ritmo diario estimado; la predicción original cubre {dias_pred} días.")
    total = sum(float(f.d) for f in todas) * factor
    cuando = f"los próximos {p.e.horizonte} días" if p.e.horizonte else f"el periodo del {B.fecha_corta(ini)} al {B.fecha_corta(fin)}"
    texto = (f"Para {cuando} se estima una demanda total de **{B.entero(round(total))} unidades**{_de(p)} {p.en_alcance}. "
             f"{'El de menor demanda' if asc else 'El de mayor demanda'} es **{_producto(mostrar[0].codigo, mostrar[0].nombre)}** con {B.entero(round(float(mostrar[0].d) * factor))} unidades.")
    tabla = B.tabla(None, [B.col("pos", "N.º", "entero"), B.col("producto", "Producto"), B.col("demanda", "Demanda estimada", "entero")],
                    [B.fila({"pos": i, "producto": _producto(f.codigo, f.nombre), "demanda": round(float(f.d) * factor)}, ruta="/predicciones") for i, f in enumerate(mostrar, 1)], total=len(todas))
    bloques = [B.barras("Demanda estimada", [(f.nombre, float(f.d) * factor, B.entero(round(float(f.d) * factor))) for f in mostrar]), tabla] if len(mostrar) > 1 else [tabla]
    return B.Resp(texto, bloques, enlaces_a(p, "/predicciones", "/recomendaciones"), ["¿Qué debo reponer?", "¿Qué se va a agotar pronto?", "¿Qué tan precisa es la predicción?"], avisos)


@manejador("prediccion_estado")
async def prediccion_estado(p: Peticion) -> B.Resp:
    ultima = await _ultima_ejecucion(p, solo_completada=False)
    if ultima is None:
        return _sin_prediccion(p)
    completada = ultima if ultima.estado == EstadoEjecucion.COMPLETADA else await _ultima_ejecucion(p)
    estado_txt = {"en_cola": "en cola", "ejecutando": "ejecutándose", "completada": "completada", "fallida": "fallida"}.get(ultima.estado, ultima.estado)
    fecha = B.fecha_corta(a_fecha_local(ultima.finalizada_en or ultima.creada_en))
    if completada is None:
        return B.Resp(f"La última ejecución de predicción está **{estado_txt}** (del {fecha}) y todavía no hay resultados.", enlaces=enlaces_a(p, "/predicciones"))
    r = dict(completada.resumen or {})
    wape, mejora = r.get("wape_global"), r.get("mejora_vs_linea_base_pct")
    texto = (f"La última predicción completada se generó el **{B.fecha_corta(a_fecha_local(completada.finalizada_en or completada.creada_en))}** con ventas hasta el "
             f"{B.fecha_corta(completada.fecha_corte)} y un horizonte de **{completada.horizonte_dias} días**: cubre {r.get('series_con_prediccion', 0)} de {r.get('series_total', 0)} combinaciones sede-producto.")
    if wape is not None:
        texto += f" Su error porcentual ponderado (WAPE) fue de **{B.porcentaje(float(wape) * 100 if float(wape) <= 3 else float(wape))}**"
        if mejora is not None:
            texto += f", {'mejor' if float(mejora) > 0 else 'peor'} que el método sencillo de referencia en {B.porcentaje(abs(float(mejora)))}"
        texto += "."
    if ultima.id != completada.id:
        texto += f" Hay una ejecución más reciente {estado_txt}."
    metricas = [("Generada", fecha), ("Ventas hasta", B.fecha_corta(completada.fecha_corte)), ("Horizonte", f"{completada.horizonte_dias} días"), ("Series con predicción", B.entero(r.get("series_con_prediccion", 0)), f"{B.entero(r.get('series_omitidas', 0))} omitidas")]
    if wape is not None:
        metricas.append(("Error (WAPE)", B.porcentaje(float(wape) * 100 if float(wape) <= 3 else float(wape))))
    bloques = [B.metricas(None, *metricas)]
    confianza = r.get("series_por_confianza") or {}
    if confianza:
        bloques.append(B.barras("Series por confianza", [(B.CONFIANZA.get(k, (k,))[0], v, B.entero(v)) for k, v in confianza.items()]))
    modelos = r.get("modelos_elegidos") or {}
    explicacion = ["WAPE es el error porcentual medido sobre las ventas reales de los últimos días: cuanto más bajo, mejor.",
                   "El sistema prueba varios modelos por cada producto y sede, y se queda con el que mejor acierta en datos que no vio al entrenar."]
    if modelos:
        explicacion.insert(0, "Modelos elegidos: " + ", ".join(f"{k} ({v})" for k, v in sorted(modelos.items(), key=lambda x: -x[1])))
    bloques.append(B.lista("Cómo leer esto", explicacion))
    aviso = _frescura(p, completada)
    return B.Resp(texto, bloques, enlaces_a(p, "/predicciones"), ["¿Qué productos tendrán más demanda?", "¿Qué debo reponer?"], [aviso] if aviso else [])


@manejador("riesgo_desabastecimiento")
async def riesgo_desabastecimiento(p: Peticion) -> B.Resp:
    """Días de cobertura = existencias ÷ demanda diaria estimada (predicción vigente o, si no hay, ventas de los últimos 30 días)."""
    ejecucion = await _ultima_ejecucion(p)
    fuente = ""
    demanda: dict[tuple[int, int], float] = {}
    if ejecucion is not None:
        filas = (await p.db.execute(select(Prediccion.sede_id, Prediccion.producto_id, Prediccion.demanda_estimada, Prediccion.fecha_inicio, Prediccion.fecha_fin).where(*_cond_prediccion(p, ejecucion.id)))).all()
        for s, pr, d, ini, fin in filas:
            demanda[(s, pr)] = float(d) / max(1, (fin - ini).days + 1)
        fuente = f"la predicción de demanda del {B.fecha_corta(a_fecha_local(ejecucion.finalizada_en or ejecucion.creada_en))}"
    avisos = []
    if ejecucion is not None and (aviso := _frescura(p, ejecucion)):
        avisos.append(aviso)
    if not demanda:
        desde = p.hoy - timedelta(days=29)
        cond_v = [Venta.empresa_id == p.ctx.empresa_id, Venta.estado == "registrada", Venta.fecha_dia >= desde, Venta.fecha_dia <= p.hoy]
        if p.sede_ids is not None:
            cond_v.append(Venta.sede_id.in_(p.sede_ids))
        if p.producto_ids:
            cond_v.append(VentaItem.producto_id.in_(p.producto_ids))
        filas = (await p.db.execute(select(Venta.sede_id, VentaItem.producto_id, func.sum(VentaItem.cantidad)).select_from(Venta).join(VentaItem, VentaItem.venta_id == Venta.id).where(*cond_v).group_by(Venta.sede_id, VentaItem.producto_id))).all()
        demanda = {(s, pr): float(u) / 30 for s, pr, u in filas}
        fuente = "tus ventas de los últimos 30 días (aún no hay una predicción generada)" if ejecucion is None else "tus ventas de los últimos 30 días"
    if not demanda:
        return B.Resp("No tengo ventas ni predicciones suficientes para estimar cuántos días dura el inventario" + (f" {p.descripcion_filtro()}" if p.descripcion_filtro() else "") + ".", enlaces=enlaces_a(p, "/predicciones"))
    inventario = (
        await p.db.execute(
            select(InventarioSede.sede_id, InventarioSede.producto_id, InventarioSede.cantidad, Producto.codigo, Producto.nombre, Sede.nombre.label("sede"))
            .select_from(InventarioSede).join(Producto, Producto.id == InventarioSede.producto_id).join(Sede, Sede.id == InventarioSede.sede_id).where(*cond_inventario(p))
        )
    ).all()
    umbral = (await p.parametros()).get("umbral_cobertura_alerta_dias", 5)
    horizonte = p.e.horizonte or max(14, umbral * 2)
    filas_cob = []
    for f in inventario:
        d = demanda.get((f.sede_id, f.producto_id), 0.0)
        if d <= 0:
            continue
        filas_cob.append((f.cantidad / d, f, d))
    filas_cob.sort(key=lambda x: (x[0], x[1].nombre))
    if not filas_cob:
        return B.Resp("Ninguno de los productos consultados tiene ventas recientes, así que no puedo estimar su cobertura.", enlaces=enlaces_a(p, "/inventario"))
    avisos.append("Cobertura = existencias ÷ demanda diaria estimada; supone que el ritmo de ventas se mantiene parejo.")
    def fila_tabla(c, f, d):
        tono = "danger" if c < umbral else ("warning" if c < horizonte else "success")
        fecha = p.hoy + timedelta(days=int(c)) if c < 365 else None
        return B.fila({"producto": _producto(f.codigo, f.nombre), "sede": f.sede, "existencias": f.cantidad, "diaria": round(d, 2), "dias": round(c, 1), "hasta": fecha.isoformat() if fecha else "Más de un año"},
                      tonos={"dias": tono}, ruta="/inventario")
    cols = [B.col("producto", "Producto"), B.col("sede", "Sede"), B.col("existencias", "Hay", "entero"), B.col("diaria", "Demanda por día", "decimal"), B.col("dias", "Días de cobertura", "decimal"), B.col("hasta", "Alcanza hasta", "fecha")]
    if p.hay_producto:
        productos = {f.producto_id for _, f, _ in filas_cob}
        total_existencias = sum(f.cantidad for _, f, _ in filas_cob)
        total_demanda = sum(d for _, _, d in filas_cob)
        dias_total = total_existencias / total_demanda if total_demanda else 0
        texto = f"Según {fuente}, {'el producto' if len(productos) == 1 else 'los productos'} {p.descripcion_filtro().removeprefix('de ')} {p.en_alcance} alcanza para unos **{B.decimal(dias_total, 0)} días** (≈ {B.decimal(total_demanda, 1)} unidades por día; hay {B.entero(total_existencias)})."
        return B.Resp(texto, [B.tabla(None, cols, [fila_tabla(*x) for x in filas_cob[:20]], total=len(filas_cob))], enlaces_a(p, "/inventario", "/recomendaciones"), ["¿Qué debo reponer?", "¿Qué productos se van a agotar pronto?"], avisos)
    riesgo = [x for x in filas_cob if x[0] < horizonte]
    filtro = f" {p.descripcion_filtro()}" if p.hay_categoria else ""  # «de la categoría Baterías y cargadores»
    if not riesgo:
        return B.Resp(f"Según {fuente}, ningún producto{filtro} {p.en_alcance} se agota en los próximos {horizonte} días. La menor cobertura es de {B.decimal(filas_cob[0][0], 1)} días ({_producto(filas_cob[0][1].codigo, filas_cob[0][1].nombre)}).",
                      enlaces=enlaces_a(p, "/inventario"), sugerencias=["¿Qué tengo en exceso?"], avisos=avisos)
    texto = (f"Según {fuente}, **{B.n_de(len(riesgo), 'combinación', 'combinaciones')} producto-sede**{filtro} se agotarían en menos de {horizonte} días {p.en_alcance}. "
             f"La más urgente: **{_producto(riesgo[0][1].codigo, riesgo[0][1].nombre)}** en {riesgo[0][1].sede}, " + ("que ya no tiene existencias." if riesgo[0][0] < 0.05 else f"con {B.decimal(riesgo[0][0], 1)} días de cobertura."))
    if p.hay_categoria:  # «¿cuántos días me dura la cobertura de los cargadores?»: además del riesgo, el conjunto
        total_demanda = sum(d for _, _, d in filas_cob)
        if total_demanda:
            texto += f" En conjunto, las existencias{filtro} alcanzan para unos **{B.decimal(sum(f.cantidad for _, f, _ in filas_cob) / total_demanda, 0)} días** al ritmo de la demanda estimada."
    mostrar = riesgo[: p.limite(10)]
    return B.Resp(texto, [B.tabla(None, cols, [fila_tabla(*x) for x in mostrar], total=len(riesgo), nota=f"Mostrando {len(mostrar)} de {len(riesgo)}." if len(riesgo) > len(mostrar) else None)],
                  enlaces_a(p, "/alertas", "/recomendaciones"), ["¿Qué debo reponer?", "¿Qué debo trasladar entre sedes?", "Alertas críticas"], avisos)


# ============================================================================================ RECOMENDACIONES
def _cond_recomendaciones(p: Peticion, *, estado: str | None, con_tipo: bool = True) -> list:
    c = [Recomendacion.empresa_id == p.ctx.empresa_id]
    if estado:
        c.append(Recomendacion.estado == estado)
    if p.sede_ids is not None:
        c.append(or_(Recomendacion.sede_id.in_(p.sede_ids), Recomendacion.sede_origen_id.in_(p.sede_ids)))
    if p.producto_ids:
        c.append(Recomendacion.producto_id.in_(p.producto_ids))
    if p.categoria_ids:
        c.append(Recomendacion.producto_id.in_(select(Producto.id).where(Producto.categoria_id.in_(p.categoria_ids))))
    if p.e.tipo_recomendacion and con_tipo:
        c.append(Recomendacion.tipo == p.e.tipo_recomendacion)
    if p.e.prioridad:
        c.append(Recomendacion.prioridad == p.e.prioridad)
    return c


@manejador("recomendaciones")
async def recomendaciones(p: Peticion) -> B.Resp:
    estado = p.e.estado_recomendacion or ("pendiente" if "historial" not in p.frase else None)
    cond = _cond_recomendaciones(p, estado=estado)
    total = int(await p.db.scalar(select(func.count()).select_from(Recomendacion).where(*cond)) or 0)
    tipo_txt = {"traslado": "de traslado", "reabastecimiento": "de reabastecimiento"}.get(p.e.tipo_recomendacion or "", "")
    estado_txt = (B.ESTADO_RECOMENDACION[estado][0].lower() + "s") if estado else ""
    if not total:
        texto = f"No hay recomendaciones {tipo_txt + ' ' if tipo_txt else ''}{estado_txt + ' ' if estado_txt else ''}{_de(p)} {p.en_alcance}.".replace("  ", " ")
        if estado == "pendiente":
            otras = int(await p.db.scalar(select(func.count()).select_from(Recomendacion).where(*_cond_recomendaciones(p, estado="pendiente", con_tipo=False))) or 0) if tipo_txt else 0
            if otras:
                texto += f" Sí hay {B.n_de(otras, 'recomendación pendiente', 'recomendaciones pendientes')} de otro tipo: pregúntame por «recomendaciones pendientes»."
            else:
                texto += " Todo lo sugerido ya fue revisado."
                if p.tiene("recomendaciones.generar"):
                    texto += " Puedes generar nuevas desde la pantalla de Recomendaciones."
        return B.Resp(texto, enlaces=enlaces_a(p, "/recomendaciones"), sugerencias=["Alertas críticas", "¿Qué productos tienen stock bajo?"])
    filas_tipo = (await p.db.execute(select(Recomendacion.tipo, func.count(), func.coalesce(func.sum(Recomendacion.cantidad_sugerida), 0)).where(*cond).group_by(Recomendacion.tipo))).all()
    por_tipo = {t: (int(n), int(u)) for t, n, u in filas_tipo}
    origen = aliased(Sede)
    consulta = (
        select(Recomendacion, Producto.codigo, Producto.nombre, Sede.nombre.label("sede"), origen.nombre.label("origen"))
        .join(Producto, Producto.id == Recomendacion.producto_id).join(Sede, Sede.id == Recomendacion.sede_id).outerjoin(origen, origen.id == Recomendacion.sede_origen_id)
        .where(*cond).order_by(_prioridad_sql(Recomendacion.prioridad), Recomendacion.generada_en.desc(), Recomendacion.id).limit(p.limite(10))
    )
    filas = (await p.db.execute(consulta)).all()
    partes = []
    if "reabastecimiento" in por_tipo:
        partes.append(f"{por_tipo['reabastecimiento'][0]} de reposición ({B.entero(por_tipo['reabastecimiento'][1])} unidades)")
    if "traslado" in por_tipo:
        partes.append(f"{por_tipo['traslado'][0]} de traslado ({B.entero(por_tipo['traslado'][1])} unidades)")
    texto = f"Hay **{B.n_de(total, 'recomendación', 'recomendaciones')}** {estado_txt}{_de(p)} {p.en_alcance}: {', '.join(partes)}."
    if len(por_tipo) == 1 and estado:
        texto = f"Hay **{B.n_de(total, 'recomendación', 'recomendaciones')} {tipo_txt + ' ' if tipo_txt else ''}{estado_txt}**{_de(p)} {p.en_alcance} ({B.entero(next(iter(por_tipo.values()))[1])} unidades sugeridas)."
    if filas:
        f0 = filas[0]
        r0 = f0.Recomendacion
        motivo = _con_punto(r0.resumen.split(". Se sugiere")[0])
        accion = (f"trasladar {B.n_de(r0.cantidad_sugerida, 'unidad', 'unidades')} desde {f0.origen} hacia {f0.sede}" if r0.tipo == "traslado" and f0.origen
                  else f"comprar {B.n_de(r0.cantidad_sugerida, 'unidad', 'unidades')} para {f0.sede}")
        texto += f" La más urgente: {motivo} Sugerencia: {accion}."
    cols = [B.col("prioridad", "Prioridad"), B.col("tipo", "Tipo"), B.col("producto", "Producto"), B.col("sede", "Sede que lo necesita"), B.col("cantidad", "Cantidad", "entero"), B.col("origen", "Desde"), B.col("estado", "Estado")]
    tabla_filas = []
    for f in filas:
        r = f.Recomendacion
        pr, tono = B.PRIORIDAD.get(r.prioridad, (r.prioridad, "neutral"))
        est, tono_e = B.ESTADO_RECOMENDACION.get(r.estado, (r.estado, "neutral"))
        tabla_filas.append(B.fila({"prioridad": pr, "tipo": B.TIPO_RECOMENDACION.get(r.tipo, r.tipo), "producto": _producto(f.codigo, f.nombre), "sede": f.sede, "cantidad": r.cantidad_sugerida,
                                   "origen": f.origen or "Compra a proveedor", "estado": est}, tonos={"prioridad": tono, "estado": tono_e}, ruta="/recomendaciones"))
    bloques = [B.tabla(None, cols, tabla_filas, total=total, nota=f"Mostrando {len(filas)} de {total}." if total > len(filas) else None)]
    avisos = ["Son sugerencias: una persona debe revisarlas y aprobarlas antes de convertirse en una compra o un traslado."]
    return B.Resp(texto, bloques, enlaces_a(p, "/recomendaciones", "/traslados"), ["¿Qué debo trasladar entre sedes?", "¿Qué se va a agotar pronto?", "¿Qué tan precisa es la predicción?"], avisos)
