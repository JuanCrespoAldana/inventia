"""Respuestas de conocimiento: glosario, guías «cómo se hace», módulos del sistema, cómo funciona el asistente, versión y temas que Inventia no registra."""

import re

from app.dto.asistente_dto import Enlace
from app.service.asistente import bloques as B
from app.service.asistente.catalogo import INTENCIONES, PERMISOS_DE_RUTA
from app.service.asistente.conocimiento_datos import GLOSARIO, GUIAS, NO_REGISTRA, VERSION_SISTEMA, Tarea, Termino
from app.service.asistente.datos import enlaces_a
from app.service.asistente.peticion import Peticion, manejador

_UNIDAD_PARAMETRO = "días"
_PERMISOS_EXTRA_RUTA: dict[str, tuple[str, ...]] = {"/ventas/nueva": ("ventas.registrar",), "/traslados/nuevo": ("traslados.solicitar",)}
_COMPARA = re.compile(r"\b(diferencia|diferencias|distingo|distinguir|distinto|distintos|diferente|diferentes|versus|vs|comparar|comparado con|se parece|igual a)\b")


# ================================================================================================== glosario
def _terminos_en(frase: str) -> list[Termino]:
    """Términos del glosario que aparecen en la frase, en el orden del glosario (los específicos primero).

    Cada término coincidente «consume» su texto para que uno general («existencias») no se vuelva a activar con las palabras de uno específico («stock mínimo»)."""
    restante = frase
    salida: list[tuple[int, int, Termino]] = []
    for orden, termino in enumerate(GLOSARIO):
        m = termino.patron.search(restante)
        if m and m.end() > m.start():
            salida.append((orden, m.start(), termino))
            restante = restante[: m.start()] + " " * (m.end() - m.start()) + restante[m.end():]
    return [t for _, _, t in salida]


def _por_posicion(frase: str, terminos: list[Termino]) -> list[Termino]:
    return sorted(terminos, key=lambda t: (m.start() if (m := t.patron.search(frase)) else 0))


async def _valor_parametro(p: Peticion, termino: Termino) -> B.BloqueMetricas | None:
    if not termino.parametro:
        return None
    parametros = await p.parametros()
    valor = parametros.get(termino.parametro)
    if valor is None:
        return None
    return B.metricas(None, ("Valor actual en tu empresa", f"{B.entero(valor)} {_UNIDAD_PARAMETRO}"))


@manejador("glosario")
async def glosario(p: Peticion) -> B.Resp:
    terminos = _terminos_en(p.frase)
    if not terminos:
        return _indice_glosario(p)
    if len(terminos) > 1 and _COMPARA.search(p.frase):
        elegidos = _por_posicion(p.frase, terminos[:3])
        bloques = [B.lista(t.nombre, [t.definicion, *t.detalle]) for t in elegidos]
        rutas = [t.ruta for t in elegidos if t.ruta]
        nombres = B.lista_natural([f"**{t.nombre}**" for t in elegidos])
        return B.Resp(f"Te explico {nombres} para que veas en qué se diferencian:", bloques, _enlaces_unicos(p, rutas), list(dict.fromkeys(s for t in elegidos for s in t.sugerencias))[:3])
    t = terminos[0]
    bloques: list = []
    if t.detalle:
        bloques.append(B.lista(None, list(t.detalle)))
    metrica = await _valor_parametro(p, t)
    if metrica is not None:
        bloques.append(metrica)
    sugerencias = list(t.sugerencias) or ["¿Qué más significa algo del sistema?", "Glosario"]
    return B.Resp(f"**{t.nombre}**: {t.definicion}", bloques, _enlaces_unicos(p, [t.ruta] if t.ruta else []), sugerencias)


def _enlaces_unicos(p: Peticion, rutas: list[str]) -> list[Enlace]:
    vistos: dict[str, Enlace] = {}
    for ruta in rutas:
        for e in enlaces_a(p, ruta):
            vistos.setdefault(e.ruta, e)
    return list(vistos.values())[:3]


_GRUPOS_GLOSARIO: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Existencias", ("stock_minimo", "stock_maximo", "agotado", "excesivo", "estado_bajo", "consolidado", "valor_inventario", "existencias")),
    ("Movimientos", ("kardex", "entrada", "salida", "ajuste", "merma", "anulacion", "traslado")),
    ("Indicadores", ("cobertura", "dias_inventario", "rotacion", "abc", "margen", "ticket", "costo_precio", "codigo_producto")),
    ("Alertas", ("alerta", "prioridad_alerta", "riesgo_desabastecimiento", "requiere_revision")),
    ("Predicción y recomendaciones", ("prediccion", "horizonte", "confianza", "intervalo", "wape", "linea_base", "modelos", "recomendacion", "reabastecimiento", "punto_reposicion")),
    ("Parámetros de la empresa", ("parametros", "plazo_entrega", "dias_seguridad", "cobertura_objetivo", "umbral_alerta")),
    ("SIG", ("sig", "pqrs", "sst", "no_conformidad", "garantia", "evidencia", "co2")),
    ("Administración", ("rol", "permiso", "alcance_sede", "auditoria", "llave_agente", "sede", "categoria", "inteligencia_artificial")),
)


def _indice_glosario(p: Peticion) -> B.Resp:
    por_clave = {t.clave: t for t in GLOSARIO}
    bloques = [B.lista(grupo, [por_clave[c].nombre for c in claves if c in por_clave]) for grupo, claves in _GRUPOS_GLOSARIO]
    texto = ("Puedo explicarte los términos que usa el sistema: qué significan, cómo se calculan y dónde se ven. "
             "Pregúntame, por ejemplo, «¿qué es el stock mínimo?» o «¿cómo se calcula la cobertura?». Estos son los que conozco:")
    return B.Resp(texto, bloques, sugerencias=["¿Qué es el stock mínimo?", "¿Cómo se calcula la cobertura?", "¿Qué significa WAPE?", "¿Qué es una no conformidad?"])


# ============================================================================================ cómo se hace
def _permitida(p: Peticion, tarea: Tarea) -> bool:
    return not tarea.permisos or p.tiene(*tarea.permisos)


def _enlaces_tarea(p: Peticion, tarea: Tarea) -> list[Enlace]:
    salida = []
    for etiqueta, ruta in tarea.enlaces:
        permisos = _PERMISOS_EXTRA_RUTA.get(ruta) or PERMISOS_DE_RUTA.get(ruta, ())
        if not permisos or p.tiene(*permisos):
            salida.append(Enlace(etiqueta=f"Abrir {etiqueta}", ruta=ruta))
    return salida[:3]


def _ejemplo_tarea(tarea: Tarea) -> str:
    return f"¿Cómo hago para {tarea.nombre}?"


@manejador("como_hacer")
async def como_hacer(p: Peticion) -> B.Resp:
    tarea = next((t for t in GUIAS if t.patron.search(p.frase)), None)
    if tarea is None:
        disponibles = [t for t in GUIAS if _permitida(p, t)]
        ejemplos = [_ejemplo_tarea(t) for t in disponibles[:30]]
        elegidos = ejemplos[::max(1, len(ejemplos) // 10)][:10]
        texto = ("Puedo explicarte paso a paso cómo hacer las tareas del sistema. Dime cuál quieres hacer, por ejemplo «cómo registro una venta» o «cómo solicito un traslado». "
                 "Estas son algunas tareas que puedes hacer con tu rol:")
        return B.Resp(texto, [B.lista(None, elegidos)], sugerencias=elegidos[:4])
    puede = _permitida(p, tarea)
    pasos = [f"**Paso {i}.** {paso}" for i, paso in enumerate(tarea.pasos, 1)]
    if puede:
        texto = f"Para **{tarea.nombre}**:"
    else:
        texto = (f"Con tu rol (**{p.ctx.rol.nombre}**) no puedes {tarea.nombre} directamente: lo hace quien tenga ese permiso (por ejemplo, un administrador). "
                 "Así se hace, por si necesitas pedirlo:")
    bloques = [B.lista(None, pasos)]
    if tarea.notas:
        bloques.append(B.lista("Ten en cuenta", list(tarea.notas)))
    return B.Resp(texto, bloques, _enlaces_tarea(p, tarea) if puede else [], list(tarea.sugerencias) or ["¿Qué puedo hacer en el sistema?"])


# ============================================================================================ módulos
_MENU: tuple[tuple[str, tuple[tuple[str, str, str], ...]], ...] = (
    ("Inicio", (
        ("/", "Panel de control", "resumen de la operación: ventas por día, productos más vendidos, inventario por sede, alertas prioritarias, predicción y movimientos recientes."),
        ("/asistente", "Asistente", "este chat, para consultar tus datos escribiendo en lenguaje normal."),
    )),
    ("Inventario", (
        ("/inventario", "Existencias", "consultar las existencias por sede, registrar entradas y salidas, ajustar por conteo físico y definir mínimos y máximos."),
        ("/inventario/consolidado", "Inventario consolidado", "la suma de las existencias de todas las sedes y cómo se reparten."),
        ("/movimientos", "Movimientos", "el historial de cada cambio de existencias (entradas, salidas, ajustes, ventas, traslados)."),
        ("/productos", "Productos", "el catálogo: código, nombre, categoría, unidad, costo y precio."),
        ("/categorias", "Categorías", "los grupos de productos."),
    )),
    ("Operación", (
        ("/ventas", "Ventas", "registrar, consultar y anular ventas."),
        ("/traslados", "Traslados", "solicitar, aprobar y confirmar el movimiento de mercancía entre sedes."),
        ("/alertas", "Alertas", "lo que requiere atención, por prioridad: inventario bajo, excesivo, riesgo de desabastecimiento y productos sin movimiento."),
    )),
    ("Inteligencia", (
        ("/predicciones", "Predicción de demanda", "cuánto se espera vender de cada producto y sede, con su rango y confianza."),
        ("/recomendaciones", "Recomendaciones", "qué reponer o trasladar, para aprobar o rechazar."),
        ("/reportes", "Reportes", "informes de inventario, ventas, movimientos, traslados, alertas, predicciones y recomendaciones, en PDF, Excel o CSV."),
    )),
    ("SIG", (
        ("/sig/pqrs", "PQRS", "peticiones, quejas, reclamos y sugerencias, con su seguimiento."),
        ("/sig/sst", "Seguridad y Salud en el Trabajo", "las pausas activas y su cumplimiento."),
        ("/sig/calidad", "Calidad", "no conformidades y garantías."),
        ("/sig/ambiental", "Gestión ambiental", "vehículos eléctricos vendidos y CO₂ evitado (estimación)."),
    )),
    ("Administración", (
        ("/empresa", "Empresa", "datos de la empresa y parámetros de inventario y predicción."),
        ("/sedes", "Sedes", "las ubicaciones de la empresa."),
        ("/usuarios", "Usuarios", "las personas con acceso: altas, bajas, contraseñas y desbloqueos."),
        ("/roles", "Roles y permisos", "qué puede hacer cada rol."),
        ("/auditoria", "Auditoría", "quién hizo qué y cuándo."),
        ("/integraciones", "Agentes de IA", "llaves para que un asistente externo consulte (solo lectura)."),
    )),
)


def _disponible(p: Peticion, ruta: str) -> bool:
    permisos = PERMISOS_DE_RUTA.get(ruta, ())
    return not permisos or p.tiene(*permisos)


@manejador("modulos_sistema")
async def modulos_sistema(p: Peticion) -> B.Resp:
    bloques: list = []
    total = disponibles = 0
    no_disponibles: list[str] = []
    for seccion, items in _MENU:
        lineas = []
        for ruta, nombre, descripcion in items:
            total += 1
            if _disponible(p, ruta):
                disponibles += 1
                lineas.append(f"**{nombre}**: {descripcion}")
            else:
                no_disponibles.append(nombre)
        if lineas:
            bloques.append(B.lista(seccion, lineas))
    bloques.insert(0, B.metricas(None, ("Pantallas con tu rol", B.entero(disponibles)), ("Pantallas del sistema", B.entero(total))))
    if no_disponibles:
        bloques.append(B.lista("No disponibles con tu rol", [B.lista_natural(no_disponibles) + "."]))
    texto = ("Inventia es un sistema web de gestión inteligente de inventarios para PyMEs con varias sedes: controla existencias, ventas y traslados, avisa lo que requiere atención "
             "y usa la historia de ventas para predecir la demanda y sugerir qué reponer. Esto es lo que ves con tu rol:")
    return B.Resp(texto, bloques, sugerencias=["¿Qué puedes hacer?", "¿Qué puedo hacer en el sistema?", "¿Cómo funciona el asistente?"])


# ====================================================================================== el asistente
_QUEJA = re.compile(r"\bno (me )?(entendiste|entiendes|entendio|respondiste|respondes|contestaste|contestas|sirves|ayudas)\b|\bno es lo que (te )?(pregunte|pedi|quise)\b|\b(respuesta|dato|informacion) (incorrect\w+|equivocad\w+|erronea|mala|falsa)\b|\bte equivocas\b|\bestas (mal|equivocad\w+)\b|\beso esta mal\b|\bno me sirve\b|\bno me ayuda\b|\bpor que no me (entiendes|respondes)\b")
_NO_ENTIENDO = re.compile(r"\bno (te )?(entiendo|comprendo|capto)\b|\bexplicalo\b|\bmas (simple|sencillo|claro|facil)\b|\bpuedes repetir\b")
_DATOS = re.compile(r"\bde donde (sacas|salen|vienen|obtienes|sale)\b|\bdatos (reales|actualizad\w+|en vivo|verdaderos)\b|\btiempo real\b|\bque tan actualizad\w+\b|\bfuente\b|\bson reales\b")
_MODELO = re.compile(r"\b(llm|gpt|chatgpt|modelo de lenguaje|ia generativa|inteligencia artificial generativa|openai|claude|gemini|usas ia|funcionas con ia|tienes ia)\b")
_LIMITES = re.compile(r"\bque no (puedes|sabes|haces|entiendes|respondes)\b|\blimitaciones?\b|\bhasta donde\b|\bno puedes\b|\bcuales son tus limites\b")
_CUANTAS = re.compile(r"\bcuantas? (preguntas|consultas|cosas|tipos)\b")


@manejador("asistente_funciona")
async def asistente_funciona(p: Peticion) -> B.Resp:
    puedo = sum(1 for i in INTENCIONES if i.categoria != "General" and (not i.permisos or p.tiene(*i.permisos)))
    if _CUANTAS.search(p.frase):
        apertura = (f"Con tu rol reconozco **{B.entero(puedo)} tipos de consulta** distintos, y cada uno admite muchísimas formas de preguntarlo (con o sin tildes, con errores de escritura, "
                    "con sedes, productos y fechas). Aun así soy un asistente por reglas, no un modelo de lenguaje: una frase muy rebuscada puede no entenderse.")
    elif _QUEJA.search(p.frase):
        apertura = "Perdón si no te entendí bien o si la respuesta no era la que buscabas. Te cuento cómo trabajo para que la próxima salga mejor."
    elif _NO_ENTIENDO.search(p.frase):
        apertura = "Cuéntame qué parte no quedó clara y la explico de otra forma, o pregúntame con otras palabras. Mientras tanto, así funciono."
    elif _MODELO.search(p.frase):
        apertura = ("No soy un modelo de lenguaje generativo: soy un asistente que **reconoce tu pregunta con reglas** y la responde con los datos reales de tu empresa. "
                    "Por eso no invento cifras, pero tampoco entiendo cualquier frase.")
    elif _DATOS.search(p.frase):
        apertura = "Cada respuesta sale de una consulta en vivo a la base de datos de tu empresa en ese momento: no uso copias ni cifras de memoria."
    else:
        apertura = "Soy el asistente de consultas de Inventia: entiendo tu pregunta con reglas y la respondo con los datos reales de tu empresa."
    bloques = [
        B.metricas(None, ("Tipos de consulta con tu rol", B.entero(puedo)), ("Respeta tu rol y tu sede", "Sí"), ("Modifica datos", "No")),
        B.lista("Qué entiendo", [
            "Preguntas sobre existencias, ventas, movimientos, traslados, alertas, predicción, recomendaciones, calidad, PQRS, gestión ambiental y administración.",
            "Productos por nombre o código, sedes, categorías y fechas («hoy», «ayer», «el mes pasado», «del 1 al 15 de octubre», «el primer trimestre»).",
            "Errores de escritura frecuentes, mayúsculas y la falta de tildes.",
            "Preguntas de seguimiento: después de «ventas de la sede Norte» puedes decir «¿y la semana pasada?».",
            "Definiciones («¿qué es el stock mínimo?») y guías paso a paso («¿cómo registro una venta?»).",
        ]),
        B.lista("Cómo sacarme más provecho", [
            "Sé directo y nombra lo que buscas: «ventas de octubre por sede» funciona mejor que una frase muy larga.",
            "Si menciono algo que no entendí, te propongo preguntas parecidas: elige una.",
            "Puedes hacer hasta 3 preguntas en un mensaje («¿cuántos productos hay y cuáles están agotados?») y las respondo una por una.",
        ]),
        B.lista("Lo que no hago", [
            "No registro ni modifico nada: solo consulto (te dejo el enlace a la pantalla donde sí puedes actuar).",
            "No respondo sobre lo que Inventia no guarda: clientes, descuentos, metas, medios de pago, lotes o contabilidad.",
            "No sé de temas ajenos al inventario, y no soy un modelo de lenguaje: una frase muy rebuscada puede no entenderse.",
            "Las predicciones son estimaciones, no promesas.",
        ]),
    ]
    return B.Resp(apertura, bloques, sugerencias=["¿Qué puedes hacer?", "¿Qué módulos tiene el sistema?", "Dame un resumen general"])


# ======================================================================================= la versión
@manejador("version_sistema")
async def version_sistema(p: Peticion) -> B.Resp:
    empresa = await p.nombre_empresa()
    bloques = [B.metricas(None, ("Versión", VERSION_SISTEMA), ("Empresa", empresa), ("Zona horaria", "Bogotá (UTC−5)")),
               B.lista("Cómo está construido", ["Interfaz web que funciona en computador y celular.", "Servicio de datos con base de datos PostgreSQL.",
                                                "Permisos y alcance por sede validados en el servidor, en cada operación.", "Predicción de demanda con varios modelos y reglas explícitas."])]
    return B.Resp(f"Estás usando **Inventia, versión {VERSION_SISTEMA}**: un sistema web de gestión inteligente de inventarios multisede para PyMEs.", bloques,
                  sugerencias=["¿Qué módulos tiene el sistema?", "¿Cómo funciona el asistente?"])


# ============================================================================== lo que no se registra
def respuesta_sin_registro(p: Peticion) -> B.Resp | None:
    """Explica con honestidad que Inventia no guarda ese dato y qué sí se puede preguntar; ``None`` si el tema no está en la lista."""
    for n in NO_REGISTRA:
        if n.patron.search(p.frase):
            return B.Resp(f"Sobre **{n.tema}**: {n.texto}", [B.lista("En su lugar, puedes preguntarme", list(n.alternativas))],
                          enlaces_a(p, n.ruta) if n.ruta else [], list(n.alternativas)[:3])
    return None
