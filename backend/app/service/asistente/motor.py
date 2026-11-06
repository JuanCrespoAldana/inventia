"""Motor del asistente: entiende la pregunta, verifica permisos y alcance, y arma la respuesta.

Flujo: directorio de la empresa → entidades (sedes, categorías, productos, periodo…) → intención por puntaje →
(seguimiento de la conversación) → permisos → alcance de sedes → respuesta. Todo es determinista y de solo lectura.
"""

import logging
from datetime import date

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dto.asistente_dto import ContextoConversacion, RespuestaAsistente
from app.security.acceso import Contexto
from app.service.asistente import bloques as B
from app.service.asistente import compuestas
from app.service.asistente import (  # noqa: F401  (importarlos registra las respuestas)
    respuestas_analitica,
    respuestas_comparar,
    respuestas_conocimiento,
    respuestas_general,
    respuestas_inventario,
    respuestas_inventario_ext,
    respuestas_movimientos,
    respuestas_operacion_ext,
    respuestas_sig,
    respuestas_sig_ext,
    respuestas_ventas,
    respuestas_ventas_ext,
)
from app.service.asistente.catalogo import (
    INTENCION_POR_CLAVE,
    SOCIALES,
    Intencion,
    SenalesEntidades,
    alcanza_umbral,
    puntuar,
)
from app.service.asistente.catalogo_ext import SIN_ALCANCE_EXT
from app.service.asistente.entidades import Directorio, Entidades, cargar_directorio, resolver
from app.service.asistente.peticion import MANEJADORES, Peticion
from app.util import lenguaje as L
from app.util.tiempo import hoy_local

log = logging.getLogger(__name__)

# Intenciones cuya respuesta no depende de las sedes (no se muestra «alcance»).
_SIN_ALCANCE = SOCIALES | {"mi_perfil", "navegacion", "accion_no_soportada", "reportes_ayuda", "roles_info", "empresa_info", "agentes_ia", "gracias", "despedida"} | SIN_ALCANCE_EXT
# Intenciones que no cambian la memoria de la conversación (saludar o dar las gracias no borra de qué se hablaba).
_NEUTRAS = SOCIALES | {"mi_perfil", "navegacion", "accion_no_soportada", "reportes_ayuda"}

# Mensajes de una sola palabra que apuntan claramente a un tema.
_PALABRA_SUELTA = {
    "inventario": "resumen_inventario", "stock": "resumen_inventario", "existencias": "resumen_inventario", "bodega": "resumen_inventario",
    "ventas": "ventas_resumen", "venta": "ventas_resumen", "productos": "buscar_producto", "catalogo": "catalogo_conteo",
    "alertas": "alertas_resumen", "traslados": "traslados_lista", "recomendaciones": "recomendaciones", "predicciones": "prediccion_demanda",
    "prediccion": "prediccion_demanda", "sedes": "sedes_info", "usuarios": "usuarios_info", "roles": "roles_info", "reportes": "reportes_ayuda",
    "movimientos": "movimientos_inventario", "pqrs": "pqrs_resumen", "calidad": "calidad_resumen", "garantias": "garantias", "auditoria": "auditoria",
    "resumen": "resumen_general", "empresa": "empresa_info", "categorias": "inventario_categoria", "margen": "margen_productos", "agotados": "listar_agotados",
}


def _permitido(ctx: Contexto, intencion: Intencion) -> bool:
    return not intencion.permisos or ctx.tiene_alguno(*intencion.permisos)


def _ids_validos(d: Directorio, anterior: ContextoConversacion | None) -> ContextoConversacion:
    """Los identificadores que llegan del navegador se vuelven a validar contra el directorio de la empresa."""
    if anterior is None:
        return ContextoConversacion()
    sedes, categorias, productos = {s.id for s in d.sedes}, {c.id for c in d.categorias}, {x.id for x in d.productos}
    intencion = anterior.intencion if anterior.intencion in INTENCION_POR_CLAVE else None
    return ContextoConversacion(
        intencion=intencion, sede_ids=[i for i in anterior.sede_ids if i in sedes], categoria_ids=[i for i in anterior.categoria_ids if i in categorias],
        producto_ids=[i for i in anterior.producto_ids if i in productos], desde=anterior.desde, hasta=anterior.hasta,
    )


def _senales(e: Entidades) -> SenalesEntidades:
    return SenalesEntidades(producto=bool(e.productos), sede=bool(e.sedes), categoria=bool(e.categorias), periodo=e.periodo is not None, horizonte=e.horizonte is not None)


def _hay_entidades(e: Entidades) -> bool:
    return bool(e.sedes or e.productos or e.categorias or e.periodo or e.horizonte or e.limite is not None or e.todas_las_sedes)


def _sin_otro_tema(e: Entidades) -> bool:
    """Falso cuando el mensaje solo trae una fecha y además palabras de otro tema («consumo de energía este año»): no es «¿y ayer?»."""
    if e.sedes or e.productos or e.categorias or e.horizonte or e.limite is not None or e.todas_las_sedes:
        return True
    return not [t for t in e.texto.split() if t not in L.PALABRAS_VACIAS]


def _sugerencias_de(ctx: Contexto, ranking: list[tuple[Intencion, float]], cuantas: int = 3) -> list[str]:
    salida: list[str] = []
    for intencion, _ in ranking:
        if intencion.clave in SOCIALES or not intencion.ejemplos or not _permitido(ctx, intencion):
            continue
        if intencion.ejemplos[0] not in salida:
            salida.append(intencion.ejemplos[0])
        if len(salida) >= cuantas:
            break
    return salida


def _por_entidad_sola(ctx: Contexto, e: Entidades) -> str | None:
    """Mensajes que solo nombran algo («BAT-004», «Sede Norte», «baterías»): se responde lo más probable."""
    candidatas: list[str] = []
    if e.productos:
        candidatas = ["producto_info", "stock_producto"]
    elif e.categorias:
        candidatas = ["inventario_categoria"]
    elif e.sedes:
        candidatas = ["inventario_por_sede", "sedes_info"]
    elif e.periodo and not [t for t in e.texto.split() if t not in L.PALABRAS_VACIAS]:
        # solo la fecha («ayer», «octubre»): si sobran palabras («consumo de energía este año») es otro tema y no se adivina
        candidatas = ["ventas_resumen"]
    for clave in candidatas:
        if _permitido(ctx, INTENCION_POR_CLAVE[clave]):
            return clave
    return None


def _no_entendida(ctx: Contexto, e: Entidades, ranking: list[tuple[Intencion, float]], iniciales: list[str]) -> B.Resp:
    texto = "No estoy seguro de haber entendido tu pregunta."
    if ranking and ranking[0][1] > 0 and ranking[0][0].requiere in ("producto", "sede", "categoria"):
        falta = {"producto": "de qué producto hablas (nombre o código)", "sede": "de qué sede hablas", "categoria": "de qué categoría hablas"}[ranking[0][0].requiere]
        texto = f"Creo que preguntas por «{ranking[0][0].titulo.lower()}», pero me falta saber {falta}."
    if e.sin_resolver:
        texto += f" No reconozco «{' '.join(e.sin_resolver[:3])}» como un producto, una sede ni una categoría de tu empresa."
    sugerencias = _sugerencias_de(ctx, ranking) or iniciales[:4]
    texto += " Prueba con otra forma, por ejemplo" + (":" if sugerencias else " «¿Qué puedes hacer?».")
    return B.Resp(texto, sugerencias=sugerencias + (["¿Qué puedes hacer?"] if sugerencias else []), entendida=False)


def _sin_permiso(ctx: Contexto, intencion: Intencion, iniciales: list[str]) -> B.Resp:
    return B.Resp(
        f"Con tu rol ({ctx.rol.nombre}) no puedes consultar {intencion.titulo.lower()}. Si lo necesitas, pídele acceso a quien administra el sistema.",
        sugerencias=iniciales[:4],
    )


def _limpiar(sugerencias: list[str], pregunta: str) -> list[str]:
    vistas: set[str] = set()
    salida = []
    clave_pregunta = L.limpio(pregunta)
    for s in sugerencias:
        clave = L.limpio(s)
        if clave in vistas or clave == clave_pregunta:
            continue
        vistas.add(clave)
        salida.append(s)
    return salida[:5]


def clasificar(ctx: Contexto, e: Entidades) -> str | None:
    """Intención de un mensaje suelto (sin conversación previa): es lo que usan las pruebas del corpus."""
    ranking = puntuar(e.frase, _senales(e))
    mejor, puntos = (ranking[0] if ranking else (None, 0.0))
    if mejor is not None and alcanza_umbral(puntos):
        return mejor.clave
    return _alternativa(ctx, e)


def _por_contexto(ranking: list[tuple[Intencion, float]], e: Entidades, previo: ContextoConversacion) -> str | None:
    """Intención que casi alcanzó el puntaje y solo le faltaba lo que la conversación ya había nombrado (el producto, la sede o la categoría)."""
    if not ranking or ranking[0][1] <= 0:
        return None
    intencion = ranking[0][0]
    tiene = {"producto": bool(e.productos), "sede": bool(e.sedes), "categoria": bool(e.categorias)}
    recordado = {"producto": bool(previo.producto_ids), "sede": bool(previo.sede_ids), "categoria": bool(previo.categoria_ids)}
    if intencion.requiere in tiene and not tiene[intencion.requiere] and recordado[intencion.requiere]:
        return intencion.clave
    return None


def _alternativa(ctx: Contexto, e: Entidades) -> str | None:
    """Cuando ninguna intención alcanza el umbral: una palabra suelta («alertas») o solo una entidad («BAT-004»)."""
    palabras = [t for t in e.frase.split() if t not in L.PALABRAS_VACIAS]
    if len(palabras) == 1 and palabras[0] in _PALABRA_SUELTA:
        return _PALABRA_SUELTA[palabras[0]]
    if _hay_entidades(e):
        return _por_entidad_sola(ctx, e)
    return None


def _no_encontrado(ctx: Contexto, d: Directorio, e: Entidades, iniciales: list[str]) -> B.Resp:
    """Nombraron algo que no existe en la empresa (una sede, una categoría o un código de producto): se dice, sin contestar con otra cosa."""
    frases: list[str] = []
    sugerencias: list[str] = []
    autorizadas = ctx.sedes_autorizadas()
    for tipo, texto in e.no_encontrado:
        if tipo == "producto":
            frases.append(f"No encontré ningún producto con el código **{texto}** en tu empresa.")
            sugerencias += ["¿Qué productos hay?", "Productos agotados"]
        elif tipo == "sede":
            visibles = [s.nombre for s in d.sedes if autorizadas is None or s.id in autorizadas]
            frases.append(f"No encontré una sede llamada «{texto}»." + (f" {'Tu sede es' if len(visibles) == 1 else 'Tus sedes son'} {B.lista_natural(visibles)}." if visibles else ""))
            sugerencias += [f"Inventario de {visibles[0]}"] if visibles else []
        else:
            nombres = [c.nombre for c in d.categorias][:8]
            frases.append(f"No encontré una categoría llamada «{texto}»." + (f" Las categorías son {B.lista_natural(nombres)}." if nombres else ""))
            sugerencias += ["¿Qué categorías hay?"]
    return B.Resp(" ".join(frases), sugerencias=list(dict.fromkeys(sugerencias)) or iniciales[:3])


def _parte_valida(d: Directorio, parte: str, hoy: date, hay_antes: bool) -> bool:
    """Una parte de una pregunta compuesta sirve si se entiende sola o, habiendo algo antes, es un seguimiento («¿y el máximo?», «las de septiembre»); un saludo o un agradecimiento no."""
    e, _ = resolver(d, parte, hoy)
    ranking = puntuar(e.frase, _senales(e))
    if ranking and alcanza_umbral(ranking[0][1]):
        return ranking[0][0].clave not in SOCIALES
    return hay_antes and bool(e.seguimiento or e.pronombre_producto or e.pronombre_sede or (_hay_entidades(e) and _sin_otro_tema(e)))


async def responder(db: AsyncSession, ctx: Contexto, mensaje: str, anterior: ContextoConversacion | None = None) -> RespuestaAsistente:
    """Responde el mensaje; si trae varias preguntas («… y además …», «¿…? ¿…?») contesta cada una, hasta ``MAX_PARTES``."""
    partes = compuestas.dividir(mensaje)
    d = await cargar_directorio(db, ctx)
    if len(partes) < 2:
        return await _responder_una(db, ctx, mensaje, anterior, d)
    hoy = hoy_local()
    omitidas = max(0, len(partes) - compuestas.MAX_PARTES)
    partes = partes[: compuestas.MAX_PARTES]
    if not all(_parte_valida(d, parte, hoy, i > 0 or anterior is not None) for i, parte in enumerate(partes)):
        return await _responder_una(db, ctx, mensaje, anterior, d)  # el corte no es claro: se responde el mensaje entero, como siempre
    respuestas: list[RespuestaAsistente] = []
    contexto = anterior
    for parte in partes:
        respuesta = await _responder_una(db, ctx, parte, contexto, d)
        respuestas.append(respuesta)
        contexto = respuesta.contexto
    if all(r.intencion == "no_entendida" for r in respuestas):
        return await _responder_una(db, ctx, mensaje, anterior, d)
    return compuestas.fusionar(partes, respuestas, omitidas, respuestas[-1].contexto)


async def _responder_una(db: AsyncSession, ctx: Contexto, mensaje: str, anterior: ContextoConversacion | None, d: Directorio) -> RespuestaAsistente:
    hoy: date = hoy_local()
    previo = _ids_validos(d, anterior)
    e, _ = resolver(d, mensaje, hoy)
    iniciales = respuestas_general.construir_ayuda(ctx).iniciales

    # ------------------------------------------------------------------------------------------ intención
    ranking = puntuar(e.frase, _senales(e))
    mejor, puntos = (ranking[0] if ranking else (None, 0.0))
    entendida = mejor is not None and alcanza_umbral(puntos)
    hay_pronombre = e.pronombre_producto or e.pronombre_sede
    clave: str | None = mejor.clave if entendida and mejor else None
    hereda = False  # toma sedes, productos y periodo de la conversación
    if previo.intencion and not (entendida and mejor is not None and mejor.clave in SOCIALES):  # «gracias, eso era todo» no repite la respuesta anterior
        marca = e.seguimiento or hay_pronombre
        if not entendida and marca and (por_contexto := _por_contexto(ranking, e, previo)):
            clave, hereda = por_contexto, True  # «¿y cuánto vale?» después de hablar de un producto: pide el precio de ese producto
        elif (not entendida and ((_hay_entidades(e) and _sin_otro_tema(e)) or marca)) or (marca and (not entendida or puntos < 5.0)):
            clave, hereda = previo.intencion, True
        elif marca:
            hereda = True
    if clave is None:
        clave = _alternativa(ctx, e)
    if clave is None:
        resp = _no_entendida(ctx, e, ranking, iniciales)
        return _armar(resp, "no_entendida", previo, None, [], [], None, ctx, None, [], pregunta=mensaje)
    intencion = INTENCION_POR_CLAVE[clave]
    if not _permitido(ctx, intencion):
        return _armar(_sin_permiso(ctx, intencion, iniciales), clave, previo, None, [], [], None, ctx, None, [], pregunta=mensaje)

    if e.no_encontrado and clave not in _SIN_ALCANCE:
        return _armar(_no_encontrado(ctx, d, e, iniciales), clave, previo, None, [], [], None, ctx, None, [], pregunta=mensaje)

    # ---------------------------------------------------------------------------------------- alcance
    avisos: list[str] = []
    nombradas = [s.id for s in e.sedes]
    autorizadas = ctx.sedes_autorizadas()
    if not nombradas and hereda and not e.todas_las_sedes:  # las sedes que vienen de la conversación se limitan, sin avisos, a las que la persona puede ver
        nombradas = [i for i in previo.sede_ids if autorizadas is None or i in autorizadas]
    if nombradas:
        if autorizadas is None:
            sede_ids: list[int] | None = nombradas
        else:
            permitidas = [i for i in nombradas if i in autorizadas]
            denegadas = [s.nombre for s in d.sedes if s.id in nombradas and s.id not in autorizadas]
            if not permitidas:
                nombre_propia = next((s.nombre for s in d.sedes if autorizadas and s.id == autorizadas[0]), "tu sede")
                texto = f"Con tu rol ({ctx.rol.nombre}) solo puedes consultar la información de tu sede ({nombre_propia}), no la de {B.lista_natural(denegadas)}."
                return _armar(B.Resp(texto, sugerencias=iniciales[:4]), clave, previo, None, [], [], None, ctx, None, [], pregunta=mensaje)
            if denegadas:
                avisos.append(f"No tienes acceso a {B.lista_natural(denegadas)}; la respuesta se limita a tu sede.")
            sede_ids = permitidas
    else:
        sede_ids = autorizadas
        if e.todas_las_sedes and autorizadas is not None:
            avisos.append("Tu rol solo permite consultar tu sede; la respuesta se limita a ella.")

    # -------------------------------------------------------------------- productos, categoría y periodo
    producto_ids = [x.id for x in e.productos][:60]
    categoria_ids = [c.id for c in e.categorias]
    if hereda:
        if not producto_ids and not categoria_ids:
            producto_ids, categoria_ids = list(previo.producto_ids), list(previo.categoria_ids)
        elif e.categorias and not e.productos:
            producto_ids = []
    periodo = e.periodo
    if periodo is None and hereda and previo.desde and previo.hasta:
        periodo = L.Periodo(previo.desde, previo.hasta, L.describir_rango(previo.desde, previo.hasta))
        e.periodo = periodo

    peticion = Peticion(db=db, ctx=ctx, d=d, e=e, hoy=hoy, frase=e.frase, clave=clave, sede_ids=sede_ids, sedes_nombradas=bool(nombradas), producto_ids=producto_ids,
                        categoria_ids=categoria_ids, periodo=periodo, avisos=avisos)
    manejador = MANEJADORES.get(clave)
    if manejador is None:  # no debería ocurrir: toda intención del catálogo tiene su respuesta
        log.error("Intención sin respuesta: %s", clave)
        return _armar(_no_entendida(ctx, e, ranking, iniciales), "no_entendida", previo, None, [], [], None, ctx, None, [], pregunta=mensaje)
    try:
        resp = await manejador(peticion)
    except SQLAlchemyError:
        log.exception("Error de base de datos en la intención %s", clave)
        await db.rollback()
        resp = B.Resp("No pude consultar esa información en este momento. Inténtalo de nuevo en unos segundos.", entendida=False)
    except Exception:  # el asistente nunca debe devolver un error 500 por una pregunta
        log.exception("Error inesperado en la intención %s", clave)
        resp = B.Resp("Tuve un problema armando esa respuesta. Prueba reformulando la pregunta.", entendida=False)
    return _armar(resp, clave, previo, sede_ids, nombradas, producto_ids, categoria_ids, ctx, periodo, avisos, peticion=peticion, pregunta=mensaje)


def _armar(
    resp: B.Resp, clave: str, previo: ContextoConversacion, sede_ids: list[int] | None, nombradas: list[int], producto_ids: list[int], categoria_ids: list[int] | None,
    ctx: Contexto, periodo: L.Periodo | None, avisos: list[str], peticion: Peticion | None = None, pregunta: str = "",
) -> RespuestaAsistente:
    # Qué recordar para la siguiente pregunta: lo que esta respuesta usó (si salió bien); si no, lo anterior.
    if clave in _NEUTRAS or clave == "no_entendida" or not resp.entendida:
        contexto = previo
    else:
        contexto = ContextoConversacion(
            intencion=clave, sede_ids=list(nombradas), categoria_ids=list(categoria_ids or []), producto_ids=list(producto_ids),
            desde=periodo.desde if periodo else None, hasta=periodo.hasta if periodo else None,
        )
    alcance = None
    if peticion is not None and clave not in _SIN_ALCANCE:
        alcance = peticion.alcance
    texto_periodo = None
    if peticion is not None and periodo is not None and clave not in _SIN_ALCANCE:
        texto_periodo = peticion.periodo_texto(periodo)
    todos_avisos = [*avisos, *resp.avisos]
    return RespuestaAsistente(
        intencion=clave, entendida=resp.entendida, texto=resp.texto, bloques=resp.bloques, enlaces=resp.enlaces, sugerencias=_limpiar(resp.sugerencias, pregunta),
        avisos=list(dict.fromkeys(todos_avisos)), alcance=alcance, periodo=texto_periodo, contexto=contexto,
    )
