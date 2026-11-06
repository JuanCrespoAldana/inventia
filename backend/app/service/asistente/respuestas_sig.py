"""Respuestas del Sistema Integrado de Gestión: PQRS, calidad, garantías, pausas activas y gestión ambiental."""

import re
from datetime import date

from sqlalchemy import case, func, select

from app.model.ambiental import AmbConfiguracion, AmbRegistro
from app.model.calidad import Garantia, NoConformidad
from app.model.catalogo import Producto
from app.model.pqrs import Pqrs
from app.model.sede import Sede
from app.model.sst import SstConfiguracion, SstPausa
from app.model.usuario import Usuario
from app.service.asistente import bloques as B
from app.service.asistente.datos import enlaces_a
from app.service.asistente.peticion import Peticion, manejador
from app.util import lenguaje as L
from app.util.tiempo import a_fecha_local, fin_de_dia_utc, inicio_de_dia_utc

_ABIERTA_NC = ("reportado", "en_revision", "en_proceso_solucion")
_ABIERTA_GARANTIA = ("reportada", "pendiente_revision", "enviada_proveedor", "aprobada")


def _de(p: Peticion) -> str:
    f = p.descripcion_filtro()
    return f" {f}" if f else ""


def _masa(kg: float) -> str:
    return f"{B.entero(kg)} kg" if kg < 1000 else f"{B.decimal(kg / 1000, 2)} toneladas"


# ================================================================================================== PQRS
_ESTADOS_PQRS = (
    (re.compile(r"\babiert\w+|\bsin (resolver|cerrar)\b|\bvigentes?\b"), ("pendiente", "en_revision", "en_proceso")),
    (re.compile(r"\bpendient\w+|\bsin (responder|atender|contestar|respuesta)\b|\bnuev\w+"), ("pendiente",)),
    (re.compile(r"\ben revision\b"), ("en_revision",)),
    (re.compile(r"\ben (proceso|tramite|gestion|curso)\b"), ("en_proceso",)),
    (re.compile(r"\bresuelt\w+|\bcerrad\w+|\bcontestad\w+|\batendid\w+|\brespondid\w+"), ("resuelta",)),
)
_TIPOS_PQRS = (
    (re.compile(r"\bquejas?\b"), "queja"), (re.compile(r"\breclamos?\b"), "reclamo"), (re.compile(r"\bpeticion\w*|\bsolicitud\w*"), "peticion"), (re.compile(r"\bsugerencias?\b"), "sugerencia"),
)
_NOMBRE_PQRS = {"queja": ("queja", "quejas", True), "reclamo": ("reclamo", "reclamos", False), "peticion": ("petición", "peticiones", True), "sugerencia": ("sugerencia", "sugerencias", True)}
_ESTADO_PQRS_TXT = {"pendiente": "pendiente", "en_revision": "en revisión", "en_proceso": "en proceso", "resuelta": "resuelta"}


def _pqrs_texto(n: int, tipos: list[str], estados: list[str], *, solo_nombre: bool = False) -> str:
    """«3 quejas pendientes», «1 reclamo resuelto», «2 quejas y reclamos abiertos», «PQRS en revisión»."""
    if not tipos:
        nombre, femenino = "PQRS", True
    else:
        nombres = [_NOMBRE_PQRS[t][0 if n == 1 else 1] for t in tipos]
        nombre, femenino = " y ".join(nombres), all(_NOMBRE_PQRS[t][2] for t in tipos)
    if len(estados) > 1:
        estado_txt = ("abierta" if femenino else "abierto") + ("" if n == 1 else "s")
    elif estados == ["resuelta"]:
        estado_txt = ("resuelta" if femenino else "resuelto") + ("" if n == 1 else "s")
    elif estados == ["pendiente"]:
        estado_txt = "pendiente" + ("" if n == 1 else "s")
    elif estados:
        estado_txt = _ESTADO_PQRS_TXT[estados[0]]
    else:
        estado_txt = ""
    cuerpo = f"{nombre}{' ' + estado_txt if estado_txt else ''}"
    return cuerpo if solo_nombre else f"{B.entero(n)} {cuerpo}"


@manejador("pqrs_resumen")
async def pqrs_resumen(p: Peticion) -> B.Resp:
    gestiona = p.tiene("pqrs.gestionar")
    cond = [Pqrs.empresa_id == p.ctx.empresa_id]
    if not gestiona:
        cond.append(Pqrs.usuario_id == p.ctx.usuario_id)
    elif p.sede_ids is not None:
        cond.append(Pqrs.sede_id.in_(p.sede_ids))
    if p.e.numero is not None and re.search(r"\b(pqrs|radicado)\b", p.frase):
        fila = (await p.db.execute(select(Pqrs).where(*cond, Pqrs.numero == p.e.numero))).scalars().first()
        if fila is None:
            return B.Resp(f"No encontré la PQRS N.º {p.e.numero}" + ("" if gestiona else " entre las tuyas") + ".", sugerencias=["¿Cuántas PQRS hay pendientes?"])
        etq, tono = B.ESTADO_PQRS.get(fila.estado, (fila.estado, "neutral"))
        texto = f"La {B.TIPO_PQRS.get(fila.tipo, fila.tipo).lower()} **N.º {fila.numero}** («{fila.asunto}») está **{etq.lower()}**."
        if fila.respuesta:
            texto += f" Última respuesta: {fila.respuesta}"
        return B.Resp(texto, [B.metricas(None, ("Estado", etq, None, tono), ("Tipo", B.TIPO_PQRS.get(fila.tipo, fila.tipo)), ("Enviada", B.fecha_corta(a_fecha_local(fila.created_at))))], enlaces_a(p, "/sig/pqrs"))
    estados = list(next((v for r, v in _ESTADOS_PQRS if r.search(p.frase)), ()))
    tipos = [v for r, v in _TIPOS_PQRS if r.search(p.frase)]
    if gestiona and re.search(r"\b(mis|mias|mio|mios|las que (yo )?(envie|puse|radique))\b", p.frase):
        cond.append(Pqrs.usuario_id == p.ctx.usuario_id)
        gestiona = False
    if p.periodo:
        cond += [Pqrs.created_at >= inicio_de_dia_utc(p.periodo.desde), Pqrs.created_at < fin_de_dia_utc(p.periodo.hasta)]
    base = list(cond)
    if estados:
        cond.append(Pqrs.estado.in_(estados))
    if tipos:
        cond.append(Pqrs.tipo.in_(tipos))
    total = int(await p.db.scalar(select(func.count()).select_from(Pqrs).where(*cond)) or 0)
    quien = (p.en_alcance if p.sede_ids is not None else "en la empresa") if gestiona else "tuyas"
    if not total:
        sin = f"No tienes {_pqrs_texto(0, tipos, estados, solo_nombre=True)}" if quien == "tuyas" else f"No hay {_pqrs_texto(0, tipos, estados, solo_nombre=True)} {quien}"
        aclaracion = " Con tu rol solo ves las PQRS que tú mismo enviaste." if quien == "tuyas" and not re.search(r"\b(mis|mias|mio|mios)\b", p.frase) else ""
        return B.Resp(sin + (f" {p.en_periodo(p.periodo)}" if p.periodo else "") + "." + aclaracion, enlaces=enlaces_a(p, "/sig/pqrs"), sugerencias=["Mis quejas y reclamos"])
    por_estado = dict((await p.db.execute(select(Pqrs.estado, func.count()).where(*base).group_by(Pqrs.estado))).all())
    por_tipo = dict((await p.db.execute(select(Pqrs.tipo, func.count()).where(*base).group_by(Pqrs.tipo))).all())
    texto = f"Hay **{_pqrs_texto(total, tipos, estados)}** {quien}" + (f" {p.en_periodo(p.periodo)}" if p.periodo else "") + "."
    if quien == "tuyas" and not re.search(r"\b(mis|mias|mio|mios)\b", p.frase):
        texto += " Con tu rol solo ves las PQRS que tú mismo enviaste."
    if not estados:
        texto += f" Pendientes: **{por_estado.get('pendiente', 0)}**; en revisión o proceso: {por_estado.get('en_revision', 0) + por_estado.get('en_proceso', 0)}; resueltas: {por_estado.get('resuelta', 0)}."
    bloques = [
        B.metricas(None, *[(B.ESTADO_PQRS[k][0], B.entero(por_estado.get(k, 0)), None, B.ESTADO_PQRS[k][1] if por_estado.get(k) else "neutral") for k in ("pendiente", "en_revision", "en_proceso", "resuelta")]),
        B.barras("Por tipo", [(B.TIPO_PQRS.get(k, k), v, B.entero(v)) for k, v in sorted(por_tipo.items(), key=lambda x: -x[1])]),
    ]
    filas = (await p.db.execute(select(Pqrs).where(*cond).order_by(Pqrs.created_at.desc(), Pqrs.id.desc()).limit(p.limite(8)))).scalars().all()
    bloques.append(B.tabla(None, [B.col("numero", "N.º"), B.col("tipo", "Tipo"), B.col("asunto", "Asunto"), B.col("estado", "Estado"), B.col("fecha", "Enviada", "fecha")],
                           [B.fila({"numero": f"N.º {f.numero}", "tipo": B.TIPO_PQRS.get(f.tipo, f.tipo), "asunto": f.asunto, "estado": B.ESTADO_PQRS.get(f.estado, (f.estado,))[0], "fecha": a_fecha_local(f.created_at).isoformat()},
                                    tonos={"estado": B.ESTADO_PQRS.get(f.estado, ("", "neutral"))[1]}, ruta="/sig/pqrs") for f in filas], total=total))
    return B.Resp(texto, bloques, enlaces_a(p, "/sig/pqrs"), ["Resumen de calidad", "¿Qué garantías están abiertas?"])


# ============================================================================================= CALIDAD
def _cond_nc(p: Peticion) -> list:
    c = [NoConformidad.empresa_id == p.ctx.empresa_id]
    if p.sede_ids is not None:
        c.append(NoConformidad.sede_id.in_(p.sede_ids))
    if p.producto_ids:
        c.append(NoConformidad.producto_id.in_(p.producto_ids))
    if p.categoria_ids:
        c.append(NoConformidad.producto_id.in_(select(Producto.id).where(Producto.categoria_id.in_(p.categoria_ids))))
    if p.periodo:
        c += [NoConformidad.fecha_deteccion >= p.periodo.desde, NoConformidad.fecha_deteccion <= p.periodo.hasta]
    return c


@manejador("calidad_resumen")
async def calidad_resumen(p: Peticion) -> B.Resp:
    cond = _cond_nc(p)
    total = int(await p.db.scalar(select(func.count()).select_from(NoConformidad).where(*cond)) or 0)
    if not total:
        return B.Resp(f"No hay no conformidades registradas{_de(p)} {p.en_alcance}" + (f" {p.en_periodo(p.periodo)}" if p.periodo else "") + ".", enlaces=enlaces_a(p, "/sig/calidad"),
                      sugerencias=["¿Qué garantías están abiertas?", "¿Cuántas PQRS hay pendientes?"])
    por_estado = dict((await p.db.execute(select(NoConformidad.estado, func.count()).where(*cond).group_by(NoConformidad.estado))).all())
    por_tipo = dict((await p.db.execute(select(NoConformidad.tipo, func.count()).where(*cond).group_by(NoConformidad.tipo))).all())
    abiertas = sum(n for e, n in por_estado.items() if e in _ABIERTA_NC)
    afectadas = int(await p.db.scalar(select(func.coalesce(func.sum(NoConformidad.cantidad_afectada), 0)).where(*cond, NoConformidad.estado.in_(_ABIERTA_NC))) or 0)
    texto = f"Hay **{B.n_de(total, 'no conformidad', 'no conformidades')}**{_de(p)} {p.en_alcance}, de las cuales **{abiertas} siguen abiertas** ({B.entero(afectadas)} unidades afectadas)."
    bloques = [B.metricas(None, *[(B.ESTADO_NC[k], B.entero(por_estado.get(k, 0)), None, "warning" if k in _ABIERTA_NC and por_estado.get(k) else "neutral") for k in ("reportado", "en_revision", "en_proceso_solucion", "resuelto", "cerrado")]),
               B.barras("Por tipo", [(B.TIPO_NC.get(k, k), v, B.entero(v)) for k, v in sorted(por_tipo.items(), key=lambda x: -x[1])])]
    filas = (await p.db.execute(
        select(NoConformidad, Producto.codigo, Producto.nombre, Sede.nombre.label("sede")).join(Producto, Producto.id == NoConformidad.producto_id).join(Sede, Sede.id == NoConformidad.sede_id)
        .where(*cond, NoConformidad.estado.in_(_ABIERTA_NC)).order_by(NoConformidad.fecha_deteccion.desc(), NoConformidad.id.desc()).limit(p.limite(8))
    )).all()
    if filas:
        bloques.append(B.tabla("Abiertas", [B.col("numero", "N.º"), B.col("producto", "Producto"), B.col("sede", "Sede"), B.col("tipo", "Tipo"), B.col("cantidad", "Unidades", "entero"), B.col("estado", "Estado"), B.col("fecha", "Detectada", "fecha")],
                               [B.fila({"numero": f"N.º {f.NoConformidad.numero}", "producto": f"{f.nombre} ({f.codigo})", "sede": f.sede, "tipo": B.TIPO_NC.get(f.NoConformidad.tipo, f.NoConformidad.tipo),
                                        "cantidad": f.NoConformidad.cantidad_afectada, "estado": B.ESTADO_NC.get(f.NoConformidad.estado, f.NoConformidad.estado), "fecha": f.NoConformidad.fecha_deteccion.isoformat()}, ruta="/sig/calidad") for f in filas], total=abiertas))
    return B.Resp(texto, bloques, enlaces_a(p, "/sig/calidad"), ["¿Qué garantías están abiertas?", "¿Qué mercancía entró este mes?"])


@manejador("garantias")
async def garantias(p: Peticion) -> B.Resp:
    cond = [Garantia.empresa_id == p.ctx.empresa_id]
    if p.sede_ids is not None:
        cond.append(Garantia.sede_id.in_(p.sede_ids))
    if p.producto_ids:
        cond.append(Garantia.producto_id.in_(p.producto_ids))
    if p.categoria_ids:
        cond.append(Garantia.producto_id.in_(select(Producto.id).where(Producto.categoria_id.in_(p.categoria_ids))))
    if p.periodo:
        cond += [Garantia.fecha_reporte >= p.periodo.desde, Garantia.fecha_reporte <= p.periodo.hasta]
    estado = None
    vencidas = bool(re.search(r"\bvencid\w+|\bexpirad\w+|\bcaducad\w+", p.frase))
    for patron, valor in ((r"\bapro\w+", "aprobada"), (r"\brechaz\w+", "rechazada"), (r"\benviad\w+|\bproveedor\b", "enviada_proveedor"), (r"\bsolucionad\w+|\bresuelt\w+", "solucionada"), (r"\bcerrad\w+", "cerrada"), (r"\bpendient\w+", "pendiente_revision")):
        if re.search(patron, p.frase):
            estado = valor
            break
    total_todas = int(await p.db.scalar(select(func.count()).select_from(Garantia).where(*cond)) or 0)
    if not total_todas:
        return B.Resp(f"No hay garantías registradas{_de(p)} {p.en_alcance}.", enlaces=enlaces_a(p, "/sig/calidad"), sugerencias=["Resumen de calidad"])
    por_estado = dict((await p.db.execute(select(Garantia.estado, func.count()).where(*cond).group_by(Garantia.estado))).all())
    abiertas = sum(n for e, n in por_estado.items() if e in _ABIERTA_GARANTIA)
    if estado:
        cond.append(Garantia.estado == estado)
    elif "abiert" in p.frase or "vigente" in p.frase or "activ" in p.frase or "pendient" in p.frase:
        cond.append(Garantia.estado.in_(_ABIERTA_GARANTIA))
    total = int(await p.db.scalar(select(func.count()).select_from(Garantia).where(*cond)) or 0)
    texto = f"Hay **{B.n_de(total_todas, 'garantía')}** registradas{_de(p)} {p.en_alcance}; **{abiertas} {'sigue abierta' if abiertas == 1 else 'siguen abiertas'}**."
    if vencidas:
        hoy = p.hoy
        cond.append(Garantia.garantia_hasta < hoy)
        total = int(await p.db.scalar(select(func.count()).select_from(Garantia).where(*cond)) or 0)
        texto = f"Hay **{B.n_de(total, 'garantía')} con la cobertura vencida**{_de(p)} {p.en_alcance} (la fecha de garantía ya pasó)." if total else f"Ninguna garantía registrada{_de(p)} {p.en_alcance} tiene la cobertura vencida."
    if estado:
        texto = f"Hay **{B.n_de(total, 'garantía')} {B.ESTADO_GARANTIA[estado].lower()}s**{_de(p)} {p.en_alcance}." if total else f"No hay garantías {B.ESTADO_GARANTIA[estado].lower()}s{_de(p)} {p.en_alcance}."
    bloques = [B.metricas(None, *[(B.ESTADO_GARANTIA[k], B.entero(por_estado.get(k, 0)), None, "warning" if k in _ABIERTA_GARANTIA and por_estado.get(k) else "neutral") for k in B.ESTADO_GARANTIA if por_estado.get(k)])]
    filas = (await p.db.execute(
        select(Garantia, Producto.codigo, Producto.nombre, Sede.nombre.label("sede")).join(Producto, Producto.id == Garantia.producto_id).join(Sede, Sede.id == Garantia.sede_id)
        .where(*cond).order_by(Garantia.fecha_reporte.desc(), Garantia.id.desc()).limit(p.limite(8))
    )).all()
    if filas:
        bloques.append(B.tabla(None, [B.col("numero", "N.º"), B.col("producto", "Producto"), B.col("sede", "Sede"), B.col("cantidad", "Unidades", "entero"), B.col("estado", "Estado"), B.col("fecha", "Reportada", "fecha"), B.col("hasta", "Vigente hasta", "fecha")],
                               [B.fila({"numero": f"N.º {f.Garantia.numero}", "producto": f"{f.nombre} ({f.codigo})", "sede": f.sede, "cantidad": f.Garantia.cantidad, "estado": B.ESTADO_GARANTIA.get(f.Garantia.estado, f.Garantia.estado),
                                        "fecha": f.Garantia.fecha_reporte.isoformat(), "hasta": f.Garantia.garantia_hasta.isoformat() if f.Garantia.garantia_hasta else "—"}, ruta="/sig/calidad") for f in filas], total=total))
    return B.Resp(texto, bloques, enlaces_a(p, "/sig/calidad"), ["Resumen de calidad", "¿Qué mercancía entró este mes?"])


# ================================================================================================== SST
@manejador("sst")
async def sst(p: Peticion) -> B.Resp:
    gestiona = p.tiene("sst.gestionar")
    periodo = p.ultimos_dias(30)
    cond = [SstPausa.empresa_id == p.ctx.empresa_id, SstPausa.mostrada_en >= inicio_de_dia_utc(periodo.desde), SstPausa.mostrada_en < fin_de_dia_utc(periodo.hasta)]
    if not gestiona:
        cond.append(SstPausa.usuario_id == p.ctx.usuario_id)
    por_estado = dict((await p.db.execute(select(SstPausa.estado, func.count()).where(*cond).group_by(SstPausa.estado))).all())
    config = await p.db.scalar(select(SstConfiguracion).where(SstConfiguracion.empresa_id == p.ctx.empresa_id))
    realizadas, omitidas, abiertas = por_estado.get("realizada", 0), por_estado.get("omitida", 0), por_estado.get("mostrada", 0)
    cerradas = realizadas + omitidas
    estado_config = ""
    if config:
        estado_config = f" Las pausas activas están **{'activadas' if config.pausas_activas else 'desactivadas'}**" + (f", cada {config.intervalo_minutos} minutos." if config.pausas_activas else ".")
    quien = "de toda la empresa" if gestiona else "tuyas"
    if not (cerradas + abiertas):
        texto = f"No hay pausas activas {quien} {p.en_periodo(periodo)}."
        ultima = await p.db.scalar(select(func.max(SstPausa.mostrada_en)).where(SstPausa.empresa_id == p.ctx.empresa_id, *([] if gestiona else [SstPausa.usuario_id == p.ctx.usuario_id])))
        if ultima:
            texto += f" La última se registró el {L.fecha_larga(a_fecha_local(ultima))}."
        return B.Resp(texto + estado_config, enlaces=enlaces_a(p, "/sig/sst"), sugerencias=["Cumplimiento de pausas activas del último mes"])
    cumplimiento = realizadas / cerradas * 100 if cerradas else 0
    if re.search(r"\bomitid\w+|\bno (se )?hic\w+|\bincumpl\w+", p.frase):
        texto = f"{p.periodo_inicio(periodo)} se omitieron **{B.n_de(omitidas, 'pausa activa', 'pausas activas')}** {quien} ({B.porcentaje(100 - cumplimiento)} de las {B.entero(cerradas)} cerradas); se realizaron {B.entero(realizadas)}." + estado_config
    else:
        texto = f"{p.periodo_inicio(periodo)} el cumplimiento de las pausas activas {quien} es de **{B.porcentaje(cumplimiento)}**: {B.n_de(realizadas, 'realizada')} y {B.n_de(omitidas, 'omitida')}." + estado_config
    bloques = [B.metricas(None, ("Cumplimiento", B.porcentaje(cumplimiento), None, "success" if cumplimiento >= 80 else "warning"), ("Realizadas", B.entero(realizadas), None, "success"), ("Omitidas", B.entero(omitidas), None, "warning" if omitidas else "neutral"), ("Abiertas", B.entero(abiertas)))]
    if gestiona and cerradas:
        filas = (await p.db.execute(
            select(Usuario.nombre, func.sum(case((SstPausa.estado == "realizada", 1), else_=0)), func.count())
            .select_from(SstPausa).join(Usuario, Usuario.id == SstPausa.usuario_id).where(*cond, SstPausa.estado.in_(("realizada", "omitida"))).group_by(Usuario.id, Usuario.nombre).order_by(Usuario.nombre).limit(20)
        )).all()
        bloques.append(B.tabla("Por persona", [B.col("persona", "Persona"), B.col("realizadas", "Realizadas", "entero"), B.col("total", "Pausas", "entero"), B.col("cumplimiento", "Cumplimiento", "porcentaje")],
                               [B.fila({"persona": n, "realizadas": int(r or 0), "total": int(t), "cumplimiento": (int(r or 0) / int(t) * 100) if t else 0}) for n, r, t in filas]))
    return B.Resp(texto, bloques, enlaces_a(p, "/sig/sst"), ["Resumen de calidad", "¿Cuánto CO₂ evitamos este año?"])


# ============================================================================================== AMBIENTAL
@manejador("ambiental")
async def ambiental(p: Peticion) -> B.Resp:
    periodo = p.periodo or L.Periodo(date(p.hoy.year, 1, 1), p.hoy, "este año")
    cond = [AmbRegistro.empresa_id == p.ctx.empresa_id, AmbRegistro.estado == "activo", AmbRegistro.fecha >= periodo.desde, AmbRegistro.fecha <= periodo.hasta]
    if p.sede_ids is not None:
        cond.append(AmbRegistro.sede_id.in_(p.sede_ids))
    if p.producto_ids:
        cond.append(AmbRegistro.producto_id.in_(p.producto_ids))
    if p.categoria_ids:
        cond.append(AmbRegistro.categoria_id.in_(p.categoria_ids))
    f = (await p.db.execute(select(func.coalesce(func.sum(AmbRegistro.unidades), 0), func.coalesce(func.sum(AmbRegistro.co2_evitado_kg), 0),
                                   func.coalesce(func.sum(case((AmbRegistro.co2_evitado_kg.is_(None), 1), else_=0)), 0)).where(*cond))).one()
    unidades, co2, sin_parametros = int(f[0]), float(f[1]), int(f[2])
    if not unidades:
        return B.Resp(f"No hay vehículos eléctricos vendidos{_de(p)} {p.en_alcance} {p.en_periodo(periodo)}.", enlaces=enlaces_a(p, "/sig/ambiental"), sugerencias=["¿Cuánto vendimos este mes?"])
    por_tipo = (await p.db.execute(select(AmbRegistro.tipo_vehiculo, func.sum(AmbRegistro.unidades), func.coalesce(func.sum(AmbRegistro.co2_evitado_kg), 0)).where(*cond).group_by(AmbRegistro.tipo_vehiculo).order_by(func.sum(AmbRegistro.unidades).desc()))).all()
    texto = f"{p.periodo_inicio(periodo)} se vendieron **{B.n_de(unidades, 'vehículo eléctrico', 'vehículos eléctricos')}**{_de(p)} {p.en_alcance}"
    texto += f", con un CO₂ evitado estimado de **{_masa(co2)}**." if co2 else ". Todavía no hay parámetros para estimar el CO₂ evitado."
    bloques = [B.metricas(None, ("Vehículos vendidos", B.entero(unidades)), ("CO₂ evitado (estimado)", _masa(co2)))]
    bloques.append(B.tabla(None, [B.col("tipo", "Tipo de vehículo"), B.col("unidades", "Unidades", "entero"), B.col("co2", "CO₂ evitado (kg)", "entero")],
                           [B.fila({"tipo": B.TIPO_VEHICULO.get(t, t), "unidades": int(u), "co2": float(c)}) for t, u, c in por_tipo]))
    avisos = ["Las unidades son reales; el CO₂ evitado es una estimación con los parámetros que configura la administración."]
    if sin_parametros:
        avisos.append(f"{B.n_de(sin_parametros, 'registro')} no tiene parámetros y cuenta solo como unidades vendidas.")
    configuracion = await p.db.scalar(select(AmbConfiguracion).where(AmbConfiguracion.empresa_id == p.ctx.empresa_id))
    if configuracion is None or configuracion.factor_red_kgco2_kwh is None:
        avisos.append("Falta el factor de emisión de la red eléctrica; sin él no se puede calcular el CO₂ evitado.")
    return B.Resp(texto, bloques, enlaces_a(p, "/sig/ambiental"), ["¿Cuánto vendimos este mes?", "Ventas por categoría"], avisos)
