"""Respuestas generales: saludo, ayuda, perfil, navegación, resumen del negocio y datos de administración."""

import re
from dataclasses import replace
from datetime import timedelta

from sqlalchemy import func, select

from app.config.settings import settings
from app.dto.asistente_dto import AyudaAsistente, GrupoAyuda
from app.model.acceso import Rol
from app.model.auditoria import ApiKey, Auditoria
from app.model.empresa import CONFIGURACION_POR_DEFECTO, Empresa
from app.model.sede import Sede
from app.model.usuario import Usuario
from app.security.acceso import Contexto
from app.security.permisos import CODIGOS_PERMISOS, PERMISOS
from app.service.asistente import bloques as B
from app.service.asistente.catalogo import CATEGORIAS_AYUDA, INTENCIONES, TEMAS, tema_de
from app.service.asistente.datos import enlaces_a, periodo_de_ventas, totales_inventario, totales_ventas
from app.service.asistente.peticion import Peticion, manejador
from app.service.asistente.respuestas_conocimiento import respuesta_sin_registro
from app.util import lenguaje as L
from app.util.tiempo import ZONA, a_fecha_local, ahora_utc, fin_de_dia_utc, inicio_de_dia_utc

_INV = ("inventario.ver", "inventario.consolidado")

# Preguntas con las que se arranca la conversación, en orden de utilidad; solo se ofrecen las que la persona puede hacer.
_INICIALES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("¿Cómo está el inventario?", _INV),
    ("¿Cuánto vendimos este mes?", ("ventas.ver",)),
    ("¿Qué productos están agotados?", _INV),
    ("¿Qué debo revisar hoy?", ("alertas.ver",)),
    ("¿Qué debo reponer esta semana?", ("recomendaciones.ver",)),
    ("¿Cuáles son los productos más vendidos?", ("ventas.ver",)),
    ("¿Qué traslados están pendientes?", ("traslados.ver",)),
    ("Dame un resumen general", ()),
    ("¿Qué puedes hacer?", ()),
)


def _permitido(ctx: Contexto, permisos: tuple[str, ...]) -> bool:
    return not permisos or ctx.tiene_alguno(*permisos)


_EJEMPLOS_POR_GRUPO = 6


def _repartir(ejemplos: list[str], cuantos: int) -> list[str]:
    """Hasta ``cuantos`` ejemplos repartidos de manera pareja a lo largo de la lista (así los temas nuevos también se ven, no solo los primeros)."""
    if len(ejemplos) <= cuantos:
        return ejemplos
    return [ejemplos[round(k * (len(ejemplos) - 1) / (cuantos - 1))] for k in range(cuantos)]


def construir_ayuda(ctx: Contexto) -> AyudaAsistente:
    """Ejemplos de preguntas agrupados por tema, solo de lo que la persona tiene permiso de consultar."""
    iniciales = [pregunta for pregunta, permisos in _INICIALES if _permitido(ctx, permisos)][:6]
    grupos: dict[str, list[str]] = {}
    for i in INTENCIONES:
        if i.categoria == "General" or not i.ejemplos or not _permitido(ctx, i.permisos):
            continue
        grupos.setdefault(i.categoria, []).append(i.ejemplos[0])
    salida = [GrupoAyuda(titulo=c, ejemplos=_repartir(grupos[c], _EJEMPLOS_POR_GRUPO)) for c in CATEGORIAS_AYUDA if c in grupos]
    nombre = ctx.usuario.nombre.split()[0] if ctx.usuario.nombre else ""
    saludo = f"Hola{', ' + nombre if nombre else ''}. Soy el asistente de consultas de Inventia: te respondo con los datos reales de tu empresa. Pregúntame en tus palabras."
    return AyudaAsistente(saludo=saludo, iniciales=iniciales, grupos=salida)


def _momento_del_dia() -> str:
    hora = ahora_utc().astimezone(ZONA).hour
    return "Buenos días" if hora < 12 else ("Buenas tardes" if hora < 19 else "Buenas noches")


def _primer_nombre(p: Peticion) -> str:
    return p.ctx.usuario.nombre.split()[0] if p.ctx.usuario.nombre else ""


# ===================================================================================================== social
@manejador("saludo")
async def saludo(p: Peticion) -> B.Resp:
    ayuda = construir_ayuda(p.ctx)
    nombre = _primer_nombre(p)
    dicho = re.search(r"\bbuen(?:os dias|as tardes|as noches)\b", p.frase)
    saludo_inicial = {"buenos dias": "Buenos días", "buenas tardes": "Buenas tardes", "buenas noches": "Buenas noches"}[dicho.group(0)] if dicho else _momento_del_dia()
    return B.Resp(f"{saludo_inicial}{', ' + nombre if nombre else ''}. Soy el asistente de Inventia. Pregúntame por tu inventario, ventas, traslados, alertas o lo que necesites consultar.", sugerencias=ayuda.iniciales)


@manejador("despedida")
async def despedida(p: Peticion) -> B.Resp:
    return B.Resp("Hasta luego. Aquí estaré cuando necesites consultar algo.")


@manejador("gracias")
async def gracias(p: Peticion) -> B.Resp:
    return B.Resp("Con gusto. Si quieres saber algo más, pregúntame.", sugerencias=construir_ayuda(p.ctx).iniciales[:3])


@manejador("quien_eres")
async def quien_eres(p: Peticion) -> B.Resp:
    return B.Resp(
        "Soy el **asistente de consultas de Inventia**. Entiendo preguntas frecuentes sobre tu operación (inventario, ventas, traslados, alertas, predicción, calidad y administración) "
        "y las respondo con los datos reales de tu empresa, respetando tu rol y tu sede. No soy una inteligencia artificial generativa: trabajo con reglas, así que es mejor que me preguntes de forma directa. "
        "Solo consulto: no registro ni modifico nada.",
        sugerencias=["¿Qué puedes hacer?", "Dame un resumen general"],
    )


@manejador("ayuda")
async def ayuda(p: Peticion) -> B.Resp:
    a = construir_ayuda(p.ctx)
    bloques = [B.lista(g.titulo, g.ejemplos) for g in a.grupos]
    texto = ("Puedo responderte preguntas sobre tu operación. Escríbelas con tus palabras, con o sin tildes, y si quieres menciona un producto (por nombre o código), una sede, una categoría o un periodo "
             "(«hoy», «esta semana», «el mes pasado», «del 1 al 15 de octubre»). Estos son ejemplos de lo que puedes preguntarme:")
    return B.Resp(texto, bloques, sugerencias=a.iniciales)


@manejador("fecha_hoy")
async def fecha_hoy(p: Peticion) -> B.Resp:
    ahora = ahora_utc().astimezone(ZONA)
    return B.Resp(f"Hoy es **{L.NOMBRES_DIA[p.hoy.weekday()]} {L.fecha_larga(p.hoy)}**, y son las {ahora.strftime('%H:%M')} (hora de {settings.app_timezone.split('/')[-1].replace('_', ' ')}).")


@manejador("charla")
async def charla(p: Peticion) -> B.Resp:
    return B.Resp("De eso no sé mucho; me dedico a consultar la información de Inventia. Prueba preguntándome por tu inventario, tus ventas o lo que hay que revisar hoy.", sugerencias=construir_ayuda(p.ctx).iniciales[:4])


@manejador("fuera_de_alcance")
async def fuera_de_alcance(p: Peticion) -> B.Resp:
    if (especifica := respuesta_sin_registro(p)) is not None:
        return especifica
    return B.Resp(
        "Inventia no maneja ese tema (cartera, clientes, proveedores, nómina, impuestos o contabilidad). Lo que sí registra es el inventario, las ventas, los traslados entre sedes, la calidad (no conformidades y garantías) y las PQRS. "
        "Si buscas las quejas o reclamos de clientes, pregúntame por las PQRS.",
        sugerencias=["¿Cuántas PQRS hay pendientes?", "¿Cuánto vendimos este mes?", "¿Qué puedes hacer?"],
    )


# ================================================================================================= perfil
@manejador("mi_perfil")
async def mi_perfil(p: Peticion) -> B.Resp:
    u = p.ctx.usuario
    rol = u.rol
    sede = next((s.nombre for s in p.d.sedes if s.id == u.sede_id), None)
    alcance = f"solo la sede {sede}" if p.limitado and sede else ("sin sede asignada" if p.limitado else "todas las sedes de la empresa")
    texto = f"Eres **{u.nombre}** ({u.email}), con el rol **{rol.nombre}**. Tu alcance es {alcance}."
    if rol.descripcion:
        texto += f" {rol.descripcion}"
    permisos = p.ctx.permisos
    bloques = [B.metricas(None, ("Rol", rol.nombre), ("Alcance", "Una sede" if p.limitado else "Toda la empresa"), ("Sede", sede or "—"), ("Permisos", B.entero(len(permisos))))]
    if len(permisos & CODIGOS_PERMISOS) == len(CODIGOS_PERMISOS):
        bloques.append(B.lista("Qué puedes hacer", ["Tienes todos los permisos del sistema."]))
    else:
        por_modulo: dict[str, list[str]] = {}
        for d in PERMISOS:
            if d.codigo in permisos:
                por_modulo.setdefault(d.modulo, []).append(d.descripcion)
        bloques.append(B.lista("Qué puedes hacer", [f"{m}: {'; '.join(x)}" for m, x in por_modulo.items()]))
    pantallas = [t.nombre for t in TEMAS if t.permisos and p.tiene(*t.permisos)]
    if pantallas:
        bloques.append(B.lista("Pantallas a las que tienes acceso", pantallas))
    return B.Resp(texto, bloques, enlaces_a(p, "/perfil"), ["¿Qué puedes hacer?", "Dame un resumen general"])


# ============================================================================================== navegación
_VERBOS_CREAR = re.compile(r"\b(registr\w+|crear|creo|cree|nuev[oa]s?|solicit\w+|agreg\w+|anad\w+|hacer|hago|emit\w+|generar|ingres\w+)\b")


_SOLO_VER = re.compile(r"\b(ver|veo|mirar|miro|consultar|consulto|revisar|reviso|encontrar|encuentro)\b")


def _destino(p: Peticion):
    return tema_de(p.frase)


@manejador("navegacion")
async def navegacion(p: Peticion) -> B.Resp:
    tema = _destino(p)
    if tema is None:
        disponibles = [t for t in TEMAS if t.permisos and p.tiene(*t.permisos)][:12]
        return B.Resp("¿A qué pantalla quieres ir? Estas son algunas a las que tienes acceso:", [B.lista(None, [f"{t.nombre}" for t in disponibles])],
                      [e for t in disponibles[:6] for e in enlaces_a(p, t.ruta)], ["¿Dónde registro una venta?", "¿Cómo llego a las alertas?"])
    quiere_crear = bool(_VERBOS_CREAR.search(p.frase)) and not _SOLO_VER.search(p.frase) and tema.ruta_crear
    if quiere_crear and p.tiene(*tema.permisos_crear):
        enlaces = enlaces_a(p, tema.ruta_crear) + enlaces_a(p, tema.ruta)
        return B.Resp(f"Para hacerlo, abre **{tema.nombre}** y usa la opción de crear; te dejo el acceso directo.", enlaces=list(enlaces)[:2])
    if tema.permisos and not p.tiene(*tema.permisos):
        return B.Resp(f"La pantalla de **{tema.nombre}** no está disponible con tu rol ({p.ctx.rol.nombre}). Si la necesitas, pídele acceso a quien administra el sistema.")
    return B.Resp(f"Puedes ver **{tema.nombre}** desde el menú lateral o con este acceso directo.", enlaces=enlaces_a(p, tema.ruta))


@manejador("accion_no_soportada")
async def accion_no_soportada(p: Peticion) -> B.Resp:
    tema = _destino(p)
    texto = "Por ahora solo consulto información: no registro ni modifico datos desde el asistente."
    enlaces = []
    if tema is not None:
        if tema.ruta_crear and _VERBOS_CREAR.search(p.frase) and p.tiene(*tema.permisos_crear):
            texto += f" Para eso, ve a **{tema.nombre}**:"
            enlaces = enlaces_a(p, tema.ruta_crear)
        elif not tema.permisos or p.tiene(*tema.permisos):
            texto += f" Lo puedes hacer desde **{tema.nombre}**:"
            enlaces = enlaces_a(p, tema.ruta)
        else:
            texto += f" Además, tu rol ({p.ctx.rol.nombre}) no tiene acceso a {tema.nombre}."
    return B.Resp(texto, enlaces=enlaces, sugerencias=["¿Qué puedes hacer?", "Dame un resumen general"])


@manejador("reportes_ayuda")
async def reportes_ayuda(p: Peticion) -> B.Resp:
    nombres = {
        "reportes.inventario": "Inventario", "reportes.ventas": "Ventas", "reportes.movimientos": "Movimientos", "reportes.traslados": "Traslados",
        "reportes.alertas": "Alertas", "reportes.predicciones": "Predicciones", "reportes.recomendaciones": "Recomendaciones",
    }
    disponibles = [n for permiso, n in nombres.items() if p.tiene(permiso)]
    if not disponibles:
        return B.Resp("Tu rol no tiene permiso para generar reportes. Si los necesitas, pídele acceso a quien administra el sistema.")
    return B.Resp(
        f"En **Reportes** puedes ver una vista previa y descargar en Excel (.xlsx), CSV o PDF. Con tu rol tienes: {B.lista_natural(disponibles)}. "
        "Elige el reporte, ajusta los filtros (sede, fechas, categoría…) y descárgalo.", enlaces=enlaces_a(p, "/reportes"), sugerencias=["¿Cuánto vendimos este mes?", "Dame un resumen general"],
    )


# ============================================================================================ resumen general
@manejador("resumen_general")
async def resumen_general(p: Peticion) -> B.Resp:
    from app.model.operaciones import Traslado
    from app.service.asistente.respuestas_analitica import _cond_alertas, _cond_recomendaciones, _cond_traslados
    from app.model.inventario import Alerta
    from app.model.prediccion import Recomendacion

    metricas: list = []
    frases: list[str] = []
    vacio = True
    if p.tiene(*_INV):
        t = (await totales_inventario(p))[None]
        metricas += [("Unidades en inventario", B.entero(t.unidades)), ("Valor del inventario", B.moneda(t.valor)),
                     ("Agotados", B.entero(t.agotados), None, "danger" if t.agotados else "neutral"), ("Stock bajo", B.entero(t.bajos), None, "warning" if t.bajos else "neutral")]
        frases.append(f"hay **{B.entero(t.unidades)} unidades** valoradas en **{B.moneda(t.valor)}**")
        vacio = False
    if p.tiene("ventas.ver"):
        periodo_mes = await periodo_de_ventas(p)
        hoy, mes = await totales_ventas(p, p.hoy_periodo()), await totales_ventas(p, periodo_mes)
        del_mes = "Ventas del mes" if periodo_mes.etiqueta == "este mes" else f"Ventas de {periodo_mes.etiqueta}"
        metricas += [("Ventas de hoy", B.moneda(hoy.monto), B.n_de(hoy.ventas, "venta")), (del_mes, B.moneda(mes.monto), B.n_de(mes.ventas, "venta"))]
        frases.append(f"hoy se han vendido **{B.moneda(hoy.monto)}** y {'en el mes' if periodo_mes.etiqueta == 'este mes' else 'en ' + periodo_mes.etiqueta} **{B.moneda(mes.monto)}**")
        vacio = False
    if p.tiene("alertas.ver"):
        activas = int(await p.db.scalar(select(func.count()).select_from(Alerta).where(*_cond_alertas(p))) or 0)
        criticas = int(await p.db.scalar(select(func.count()).select_from(Alerta).where(*_cond_alertas(p), Alerta.prioridad == "critica")) or 0)
        metricas.append(("Alertas activas", B.entero(activas), f"{criticas} críticas", "danger" if criticas else ("warning" if activas else "neutral")))
        frases.append(f"hay **{activas} alertas activas** ({criticas} críticas)")
        vacio = False
    if p.tiene("traslados.ver"):
        n = int(await p.db.scalar(select(func.count()).select_from(Traslado).where(*_cond_traslados(p), Traslado.estado.in_(("solicitado", "aprobado")))) or 0)
        metricas.append(("Traslados pendientes", B.entero(n), None, "warning" if n else "neutral"))
        if n:
            frases.append(f"{B.n_de(n, 'traslado')} esperan gestión")
        vacio = False
    if p.tiene("recomendaciones.ver"):
        n = int(await p.db.scalar(select(func.count()).select_from(Recomendacion).where(*_cond_recomendaciones(p, estado="pendiente"))) or 0)
        metricas.append(("Recomendaciones por revisar", B.entero(n), None, "warning" if n else "neutral"))
        if n:
            frases.append(f"{B.n_de(n, 'recomendación', 'recomendaciones')} por revisar")
        vacio = False
    if vacio:
        return B.Resp("Con tu rol no tengo cifras de negocio para resumir. Pregúntame por tu perfil o por las pantallas a las que tienes acceso.", sugerencias=["¿Quién soy?", "¿Qué puedes hacer?"])
    texto = f"Resumen {p.en_alcance}: " + "; ".join(frases) + "."
    return B.Resp(texto, [B.metricas(None, *metricas)], enlaces_a(p, "/", "/alertas", "/inventario"), ["¿Qué debo revisar hoy?", "¿Qué productos están agotados?", "Ventas por sede", "¿Qué debo reponer?"])


# ======================================================================================== administración
@manejador("sedes_info")
async def sedes_info(p: Peticion) -> B.Resp:
    consulta = select(Sede).where(Sede.empresa_id == p.ctx.empresa_id).order_by(Sede.nombre)
    if p.sede_ids is not None and (p.sedes_nombradas or p.limitado):
        consulta = consulta.where(Sede.id.in_(p.sede_ids))
    sedes = (await p.db.scalars(consulta)).all()
    if not sedes:
        return B.Resp("No encontré sedes para mostrar.")
    activas = [s for s in sedes if s.activa]
    if len(sedes) == 1:
        s = sedes[0]
        ubicacion = ", ".join(x for x in (s.direccion, s.ciudad) if x)
        texto = f"**{s.nombre}** " + (f"queda en {ubicacion}" if ubicacion else "no tiene dirección registrada") + f" y está {'activa' if s.activa else 'inhabilitada'}."
        if p.limitado and not p.sedes_nombradas:
            texto = f"Con tu rol ves una sola sede. {texto}"
    elif re.search(r"\b(inhabilitad\w+|inactiv\w+|desactivad\w+|cerrad\w+)\b", p.frase):
        inactivas = [s for s in sedes if not s.activa]
        texto = (f"Hay **{len(inactivas)} {'sede inhabilitada' if len(inactivas) == 1 else 'sedes inhabilitadas'}**: {B.lista_natural([s.nombre for s in inactivas])}."
                 if inactivas else f"No hay sedes inhabilitadas: las {len(sedes)} sedes de la empresa están activas ({B.lista_natural([s.nombre for s in sedes])}).")
    else:
        texto = f"La empresa tiene **{len(sedes)} sedes** ({len(activas)} activas): {B.lista_natural([s.nombre for s in sedes])}."
    tabla = B.tabla(None, [B.col("sede", "Sede"), B.col("ciudad", "Ciudad"), B.col("direccion", "Dirección"), B.col("estado", "Estado")],
                    [B.fila({"sede": s.nombre, "ciudad": s.ciudad or "—", "direccion": s.direccion or "—", "estado": "Activa" if s.activa else "Inhabilitada"}, tonos={"estado": "success" if s.activa else "neutral"}, ruta="/sedes") for s in sedes])
    bloques = [tabla]
    if len(sedes) == 1:  # una sola sede: se acompaña de su inventario y sus ventas recientes, si la persona puede verlos
        propia = replace(p, sede_ids=[sedes[0].id], producto_ids=[], categoria_ids=[], periodo=None)
        datos: list = []
        if p.tiene(*_INV):
            t = (await totales_inventario(propia))[None]
            datos += [("Unidades en inventario", B.entero(t.unidades)), ("Valor del inventario", B.moneda(t.valor)), ("Agotados", B.entero(t.agotados), None, "danger" if t.agotados else "neutral")]
        if p.tiene("ventas.ver"):
            v = await totales_ventas(propia, L.Periodo(p.hoy - timedelta(days=29), p.hoy, "los últimos 30 días"))
            datos.append(("Vendido en 30 días", B.moneda(v.monto), B.n_de(v.ventas, "venta")))
        if datos:
            bloques.insert(0, B.metricas(None, *datos))
    return B.Resp(texto, bloques, enlaces_a(p, "/sedes"), ["Ventas por sede", "¿Cómo está el inventario por sede?"])


def _rol_nombrado(roles: list[Rol], frase: str) -> Rol | None:
    palabras = frase.split()
    for r in roles:
        distintivas = [t for t in L.limpio(r.nombre).split() if t not in L.PALABRAS_VACIAS]
        if distintivas and all(any(L.similitud(q, t) >= 0.8 for q in palabras) for t in distintivas):
            return r
    return None


@manejador("usuarios_info")
async def usuarios_info(p: Peticion) -> B.Resp:
    roles = list((await p.db.scalars(select(Rol).where(Rol.empresa_id == p.ctx.empresa_id))).all())
    cond = [Usuario.empresa_id == p.ctx.empresa_id]
    if p.sede_ids is not None:
        cond.append(Usuario.sede_id.in_(p.sede_ids))
    rol = _rol_nombrado(roles, p.frase)
    if rol:
        cond.append(Usuario.rol_id == rol.id)
    if re.search(r"\binactiv\w+|\binhabilitad\w+", p.frase):
        cond.append(Usuario.activo.is_(False))
    elif re.search(r"\bactiv\w+|\bhabilitad\w+", p.frase):
        cond.append(Usuario.activo.is_(True))
    total = int(await p.db.scalar(select(func.count()).select_from(Usuario).where(*cond)) or 0)
    if not total:
        return B.Resp("No encontré usuarios con ese criterio.", sugerencias=["¿Cuántos usuarios hay?"])
    nombres_rol = {r.id: r.nombre for r in roles}
    por_rol = dict((await p.db.execute(select(Usuario.rol_id, func.count()).where(*cond).group_by(Usuario.rol_id))).all())
    activos = int(await p.db.scalar(select(func.count()).select_from(Usuario).where(*cond, Usuario.activo.is_(True))) or 0)
    texto = f"Hay **{B.n_de(total, 'usuario')}**" + (f" con el rol **{rol.nombre}**" if rol else "") + f" ({activos} {'activo' if activos == 1 else 'activos'})."
    if not rol and len(por_rol) > 1:
        texto += " Por rol: " + ", ".join(f"{nombres_rol.get(i, '—')} ({n})" for i, n in sorted(por_rol.items(), key=lambda x: -x[1])) + "."
    nombres_sede = {s.id: s.nombre for s in p.d.sedes}
    filas = (await p.db.scalars(select(Usuario).where(*cond).order_by(Usuario.nombre).limit(p.limite(15)))).all()
    tabla = B.tabla(None, [B.col("nombre", "Nombre"), B.col("correo", "Correo"), B.col("rol", "Rol"), B.col("sede", "Sede"), B.col("estado", "Estado")],
                    [B.fila({"nombre": u.nombre, "correo": u.email, "rol": nombres_rol.get(u.rol_id, "—"), "sede": nombres_sede.get(u.sede_id, "Todas") if u.sede_id else "Todas", "estado": "Activo" if u.activo else "Inhabilitado"},
                            tonos={"estado": "success" if u.activo else "neutral"}, ruta="/usuarios") for u in filas], total=total)
    return B.Resp(texto, [tabla], enlaces_a(p, "/usuarios", "/roles"), ["¿Qué roles hay?", "¿Quién anuló ventas esta semana?"])


@manejador("roles_info")
async def roles_info(p: Peticion) -> B.Resp:
    roles = list((await p.db.scalars(select(Rol).where(Rol.empresa_id == p.ctx.empresa_id, Rol.activo.is_(True)).order_by(Rol.nombre))).all())
    if not roles:
        return B.Resp("No hay roles configurados.")
    rol = _rol_nombrado(roles, p.frase)
    usuarios = dict((await p.db.execute(select(Usuario.rol_id, func.count()).where(Usuario.empresa_id == p.ctx.empresa_id).group_by(Usuario.rol_id))).all())
    if rol:
        por_modulo: dict[str, list[str]] = {}
        for d in PERMISOS:
            if d.codigo in rol.codigos_permisos:
                por_modulo.setdefault(d.modulo, []).append(d.descripcion)
        todos = len(rol.codigos_permisos) >= len(CODIGOS_PERMISOS)
        texto = f"El rol **{rol.nombre}** {'ve toda la empresa' if rol.alcance == 'empresa' else 'trabaja solo en su sede'}. {rol.descripcion or ''}".strip()
        bloques = [B.lista("Qué puede hacer", ["Tiene todos los permisos del sistema."] if todos else [f"{m}: {'; '.join(x)}" for m, x in por_modulo.items()])]
        return B.Resp(texto, bloques, enlaces_a(p, "/roles"), ["¿Qué roles hay?", "¿Cuántos usuarios hay?"])
    texto = f"Hay **{len(roles)} roles**: {B.lista_natural([r.nombre for r in roles])}."
    tabla = B.tabla(None, [B.col("rol", "Rol"), B.col("alcance", "Alcance"), B.col("permisos", "Permisos", "entero"), B.col("usuarios", "Usuarios", "entero"), B.col("descripcion", "Para qué sirve")],
                    [B.fila({"rol": r.nombre, "alcance": "Toda la empresa" if r.alcance == "empresa" else "Una sede", "permisos": len(r.codigos_permisos), "usuarios": int(usuarios.get(r.id, 0)), "descripcion": r.descripcion or "—"}, ruta="/roles") for r in roles])
    return B.Resp(texto, [tabla], enlaces_a(p, "/roles"), ["¿Qué puede hacer el gerente?", "¿Cuántos usuarios hay?"])


# ---------------------------------------------------------------------------------------------- auditoría
_MODULOS_AUDITORIA = (
    (r"\bventas?\b", "ventas"), (r"\btraslad\w+", "traslados"), (r"\b(inventario|entradas?|salidas?|ajustes?|stock)\b", "inventario"),
    (r"\b(sesion|acceso|ingreso|login|contrasena)\w*", "auth"), (r"\busuarios?\b", "usuarios"), (r"\broles?\b|\bpermisos?\b", "roles"),
    (r"\bproductos?\b", "productos"), (r"\bcategorias?\b", "categorias"), (r"\bsedes?\b", "sedes"), (r"\brecomend\w+", "recomendaciones"),
    (r"\bpredic\w+", "prediccion"), (r"\bgarantias?|\bno ?conformidad\w*|\bcalidad\b", "calidad"),
)
_DE_QUIENES = re.compile(r"\b(actividad|acciones|registros|movimientos|historial|operaciones)( recientes?| reciente)? (de|del|de todos|por) (los |las |todos los |todas las )?(usuarios|personas|empleados|equipo|gente|trabajadores)\b")
_ACCIONES_AUDITORIA = (
    (r"\banul\w+", ("anular",)), (r"\belimin\w+|\bborr\w+", ("eliminar", "eliminar_actividad", "eliminar_adjunto")), (r"\baprob\w+", ("aprobar",)), (r"\brechaz\w+", ("rechazar",)),
    (r"\bconfirm\w+", ("confirmar",)), (r"\bajust\w+", ("ajuste",)), (r"\bregistr\w+", ("registrar", "entrada", "salida")), (r"\bcre[oóa]\w*|\bcrearon\b", ("crear",)),
    (r"\bcambi\w+|\bmodific\w+|\bedit\w+|\bactualiz\w+", ("actualizar", "editar_actividad", "cambiar_rol_o_sede", "actualizar_parametros")),
)


@manejador("auditoria")
async def auditoria(p: Peticion) -> B.Resp:
    cond = [Auditoria.empresa_id == p.ctx.empresa_id]
    ve_todo = p.tiene("auditoria.ver")
    if not ve_todo:
        cond.append(Auditoria.modulo != "auth")
        if p.limitado:
            cond.append(Auditoria.sede_id == p.ctx.sede_id)
    periodo = p.ultimos_dias(7)
    frase = _DE_QUIENES.sub("actividad", p.frase)
    modulo = next((m for patron, m in _MODULOS_AUDITORIA if re.search(patron, frase)), None)
    acciones = next((a for patron, a in _ACCIONES_AUDITORIA if re.search(patron, frase)), None)
    fallidos = bool(re.search(r"\bfallid\w+|\berror\w*|\bdenegad\w+|\brechazad\w+ (por|del) sistema\b|\bintentos\b", p.frase))
    if modulo == "auth" and not ve_todo:
        return B.Resp("Los accesos y los inicios de sesión solo los ve quien tiene el permiso de auditoría completa. Con tu rol puedes consultar las operaciones del negocio (ventas, traslados, inventario…).", sugerencias=["¿Quién anuló ventas esta semana?"])
    if modulo:
        cond.append(Auditoria.modulo == modulo)
    if acciones:
        cond.append(Auditoria.accion.in_(acciones))
    if fallidos:
        cond.append(Auditoria.resultado == "fallido")
    if p.sede_ids is not None and not p.limitado:
        cond.append(Auditoria.sede_id.in_(p.sede_ids))
    sin_fecha = list(cond)
    cond += [Auditoria.fecha >= inicio_de_dia_utc(periodo.desde), Auditoria.fecha < fin_de_dia_utc(periodo.hasta)]
    total = int(await p.db.scalar(select(func.count()).select_from(Auditoria).where(*cond)) or 0)
    nombre_modulo = {"auth": "inicio de sesión"}.get(modulo or "", modulo)
    if not total:
        texto = f"No hay registros de actividad{' de ' + nombre_modulo if nombre_modulo else ''}{' fallidos' if fallidos else ''} {p.en_periodo(periodo)}."
        ultimo = await p.db.scalar(select(func.max(Auditoria.fecha)).where(*sin_fecha))
        if ultimo:
            texto += f" Lo último registrado fue el {L.fecha_larga(a_fecha_local(ultimo))}."
        return B.Resp(texto, sugerencias=["Actividad reciente de los usuarios"], enlaces=enlaces_a(p, "/auditoria"))
    filas = (await p.db.scalars(select(Auditoria).where(*cond).order_by(Auditoria.fecha.desc(), Auditoria.id.desc()).limit(p.limite(10)))).all()
    por_usuario = (await p.db.execute(select(Auditoria.usuario_email, func.count()).where(*cond).group_by(Auditoria.usuario_email).order_by(func.count().desc()).limit(3))).all()
    texto = f"Hay **{B.n_de(total, 'registro')}** de actividad{' de ' + nombre_modulo if nombre_modulo else ''}{' fallidos' if fallidos else ''} {p.en_periodo(periodo)}."
    if por_usuario and por_usuario[0][0]:
        texto += " Quien más actividad tuvo: " + ", ".join(f"{e or 'sistema'} ({n})" for e, n in por_usuario) + "."
    tabla = B.tabla(None, [B.col("fecha", "Fecha", "fecha_hora"), B.col("persona", "Persona"), B.col("modulo", "Módulo"), B.col("accion", "Acción"), B.col("entidad", "Sobre"), B.col("resultado", "Resultado")],
                    [B.fila({"fecha": a.fecha, "persona": a.usuario_email or "Sistema", "modulo": a.modulo, "accion": a.accion.replace("_", " "), "entidad": f"{a.entidad or ''} {a.entidad_id or ''}".strip() or "—",
                             "resultado": "Exitoso" if a.resultado == "exitoso" else "Fallido"}, tonos={"resultado": "success" if a.resultado == "exitoso" else "danger"}, ruta="/auditoria") for a in filas],
                    total=total, nota=f"Mostrando {len(filas)} de {total}." if total > len(filas) else None)
    return B.Resp(texto, [tabla], enlaces_a(p, "/auditoria"), ["¿Quién anuló ventas esta semana?", "Intentos de acceso fallidos", "Ventas anuladas"])


# -------------------------------------------------------------------------------------------------- empresa
_PARAMETROS = {
    "plazo_entrega_dias": ("Plazo de entrega del proveedor", "días entre pedir y recibir la mercancía", r"plazo|entrega|lead"),
    "dias_seguridad": ("Días de seguridad", "colchón adicional sobre el plazo de entrega", r"seguridad"),
    "dias_cobertura_objetivo": ("Cobertura objetivo", "días de demanda que se busca cubrir al reabastecer", r"cobertura objetivo|objetivo"),
    "horizonte_dias": ("Horizonte de predicción", "días hacia adelante que se estiman por defecto", r"horizonte"),
    "umbral_cobertura_alerta_dias": ("Umbral de alerta por cobertura", "se alerta si el stock cubre menos días que estos", r"umbral|alerta"),
    "dias_sin_rotacion": ("Días sin rotación", "sin ventas en estos días y con existencias, el producto se marca para revisión", r"rotacion"),
    "dias_max_anulacion": ("Plazo para anular una venta", "días máximos para anular una venta", r"anul"),
}


@manejador("empresa_info")
async def empresa_info(p: Peticion) -> B.Resp:
    empresa = await p.db.scalar(select(Empresa).where(Empresa.id == p.ctx.empresa_id))
    if empresa is None:
        return B.Resp("No encontré los datos de la empresa.")
    parametros = empresa.parametros()
    pidio = next((k for k, (_, _, patron) in _PARAMETROS.items() if re.search(patron, p.frase)), None)
    if pidio:
        etiqueta, explicacion, _ = _PARAMETROS[pidio]
        return B.Resp(f"**{etiqueta}**: {parametros[pidio]} días ({explicacion}).", enlaces=enlaces_a(p, "/empresa"), sugerencias=["Parámetros de la empresa"])
    datos = [f"Nombre: {empresa.nombre}"]
    for rotulo, valor in (("NIT o identificación", empresa.identificacion), ("Ciudad", empresa.ciudad), ("Dirección", empresa.direccion), ("Teléfono", empresa.telefono), ("Correo", empresa.email)):
        if valor:
            datos.append(f"{rotulo}: {valor}")
    datos.append(f"Zona horaria: {settings.app_timezone}")
    texto = f"Tu empresa es **{empresa.nombre}**" + (f" (NIT {empresa.identificacion})" if empresa.identificacion else "") + f", con {len(p.d.sedes)} sedes y {len(p.d.productos)} productos en el catálogo."
    bloques = [B.lista("Datos", datos), B.tabla("Parámetros de inventario y predicción", [B.col("parametro", "Parámetro"), B.col("valor", "Valor", "entero"), B.col("significa", "Qué significa")],
                                                  [B.fila({"parametro": e, "valor": parametros.get(k, CONFIGURACION_POR_DEFECTO[k]), "significa": s}) for k, (e, s, _) in _PARAMETROS.items()])]
    return B.Resp(texto, bloques, enlaces_a(p, "/empresa"), ["¿Cuál es el plazo de entrega configurado?", "¿Qué sedes tenemos?"])


@manejador("agentes_ia")
async def agentes_ia(p: Peticion) -> B.Resp:
    activas = int(await p.db.scalar(select(func.count()).select_from(ApiKey).where(ApiKey.empresa_id == p.ctx.empresa_id, ApiKey.activa.is_(True))) or 0)
    texto = ("Inventia puede conectarse con agentes de IA externos (por ejemplo, Claude) usando **llaves de solo lectura**: cada llave tiene alcances (qué puede consultar) y, si quieres, queda limitada a una sede. "
             "Se crean y se revocan en Integraciones; la llave completa se muestra una sola vez, al crearla. ")
    texto += f"Ahora hay **{B.n_de(activas, 'llave activa', 'llaves activas')}**." if activas else "Ahora no hay llaves activas."
    return B.Resp(texto, enlaces=enlaces_a(p, "/integraciones"), sugerencias=["¿Qué puedes hacer?"])
