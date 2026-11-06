"""Intenciones de conocimiento: glosario, cómo se hace, módulos del sistema, cómo funciona el asistente y versión.

Los patrones se arman a partir de los datos de ``conocimiento_datos`` (cada término del glosario y cada guía aporta el suyo),
así que agregar un término o una guía nuevos no exige tocar este archivo. Se escriben sobre el texto normalizado.
"""

from app.service.asistente.conocimiento_datos import GLOSARIO, GUIAS, VERBOS_TAREAS
from app.service.asistente.intencion import Intencion, _i

CATEGORIA = "Ayuda del sistema"

_TERMINOS = "|".join(f"(?:{t.patron.pattern})" for t in GLOSARIO)
# Para «diferencia entre X y Y» se excluyen los términos genéricos: «la diferencia entre la sede Norte y la Sur» es una comparación de datos, no una definición.
_GENERICOS = frozenset({"sede", "categoria", "existencias", "rol", "alerta", "permiso"})
_TERMINOS_DIF = "|".join(f"(?:{t.patron.pattern})" for t in GLOSARIO if t.clave not in _GENERICOS)
_TAREAS = "|".join(f"(?:{g.patron.pattern})" for g in GUIAS)

# Verbos que, justo después de «cómo», indican que se pregunta por un procedimiento.
_VERBOS = "|".join(sorted(VERBOS_TAREAS, key=len, reverse=True))
_VERBOS_SE = _VERBOS
_AUXILIARES = "hago|hacer|puedo|podria|podemos|debo|deberia|tengo que|se|le|lo|la|las|los|me|uno|procedo|realizo|ejecuto|seria|es que|hay que|puede|pueden|haria|lleva|llevo|se puede|se debe|se hace"
_COMO_SE_HACE = rf"\b(?:como\s+(?:(?:{_AUXILIARES})\s+){{1,3}}|como\s+(?:{_VERBOS})\b|como\s+se\s+(?:{_VERBOS_SE})\b|de que (?:forma|manera|modo)\b|pasos? para\b|paso a paso\b|procedimiento (?:para|de)\b|instrucciones (?:para|de)\b|guia (?:para|de)\b|tutorial (?:de|para)\b|que (?:tengo que|debo|hay que|toca) hacer para\b|explicame como\b|ensename (?:a|como)\b|gui[ao]me (?:para|a|en|con|como)\b|orientame (?:para|a|en|con|como)\b|ayudame a\b)"

_DEFINE = (
    r"(?:que (?:es|son|significa|significan|quiere decir|quieren decir|se entiende por|representa|representan|mide|indica|muestra|seria)|a que se refiere|a que se refieren|definicion de|define|defineme|"
    r"explicame (?:que (?:es|son)|lo que (?:es|son)|el|la|los|las)|significado de|en que consiste|en que consisten|para que (?:sirve|sirven|se usa|se usan)|"
    r"como se (?:calcula|calculan|mide|miden|obtiene|obtienen|determina|determinan|define|definen|interpreta|interpretan|saca|sacan|llama|clasifica|clasifican|decide|deciden)|"
    r"como (?:calcula|calculas|mide|obtiene|determina|define|saca|clasifica) (?:el sistema|inventia|la aplicacion)|de donde sale|de donde salen|como funciona|como funcionan|"
    r"que (?:es|son) eso de|que (?:es|son) lo de|a que llaman|a que le llaman)"
)
_RELLENO = r"(?:(?!lo que\b)\w+\s+){0,3}?"
_ARTICULO = r"(?:(?:el|la|los|las|un|una|unos|unas|mi|mis|tu|tus|este|esta|estos|estas)\s+)?"

# Términos que, escritos solos, son claramente una pregunta por su significado (los que no tienen otra consulta propia).
_SUELTOS = (
    r"wape|rmse|mape|mae|pareto|linea base|baseline|punto de reposicion|punto de reorden|nivel objetivo|plazo de entrega|lead ?time|dias de seguridad|stock de seguridad|"
    r"cobertura objetivo|umbral|horizonte|sku|intervalo de 80|intervalo de confianza|factor de emision"
)

INTENCIONES_CONOCIMIENTO: tuple[Intencion, ...] = (
    _i("glosario", CATEGORIA, "Qué significa un término del sistema", (),
       ("¿Qué es el stock mínimo?", "¿Cómo se calcula la cobertura?", "¿Qué significa WAPE?", "¿Qué diferencia hay entre alerta crítica y alta?", "Glosario"), [
        (rf"\b{_DEFINE}\s+{_ARTICULO}{_RELLENO}(?:{_TERMINOS})", 14.5),
        (rf"\bdiferencias? (?:\w+\s+){{0,2}}?entre\s+(?:\w+\s+){{0,6}}?(?:{_TERMINOS_DIF})", 14.5),
        (rf"^{_ARTICULO}(?:{_SUELTOS})$", 14.5),
        (r"\b(glosario|diccionario|vocabulario|terminologia)\b", 9),
        (r"\b(que|cuales) (terminos|palabras|conceptos|siglas|definiciones) (usa|usan|maneja|manejan|hay|tiene|tienen|conoces|sabes|explicas)\b", 10),
        (r"\b(explicame|ayudame a entender|no entiendo) (los |las )?(terminos|conceptos|palabras|siglas|indicadores|metricas)\b", 10),
    ]),
    _i("como_hacer", CATEGORIA, "Guía paso a paso de una tarea", (),
       ("¿Cómo registro una venta?", "¿Cómo solicito un traslado?", "¿Cómo ajusto el inventario?", "¿Cómo creo un usuario?", "¿Cómo cambio mi contraseña?"), [
        (rf"^(?=.*{_COMO_SE_HACE}).*(?:{_TAREAS})", 12),
        (r"^(?:pasos?|paso a paso|guia|tutorial|instrucciones|procedimiento)\b", 4),
    ], contras=[
        (r"\b(ver|veo|consultar|consulto|mirar|miro|revisar|reviso|saber|encontrar|encuentro|listar|mostrar|muestrame|dime|cuanto|cuantos|cuantas|cual|cuales)\b", -7),
        (r"\b(reporte|reportes|informe|informes|pdf|csv|descargar|exportar)\b", -9),
        (r"\b(vender|vendo|venta|ventas)\b.*\bmas\b|\bmas\b.*\b(ventas?|vender)\b", -8),
        (r"\b(mas|menos|mejor|aumentar|subir|incrementar|reducir|bajar|mejorar|optimizar|evitar|disminuir)\b", -5),
    ]),
    _i("modulos_sistema", CATEGORIA, "Qué módulos y pantallas tiene el sistema", (),
       ("¿Qué módulos tiene el sistema?", "¿Qué hace Inventia?"), [
        (r"\bque (modulos|pantallas|secciones|apartados|funciones|funcionalidades|opciones|herramientas|partes|areas|menus|paginas) (tiene|hay|incluye|trae|maneja|contiene|existen|ofrece|tienen)\b", 10),
        (r"\b(modulos|funcionalidades|funciones|pantallas|secciones|menu|caracteristicas) (del|de la|de) (sistema|inventia|aplicacion|programa|software|plataforma|app)\b", 10),
        (r"\bque (hace|puede hacer|sirve|ofrece|permite|incluye|trae|es capaz de hacer) (inventia|el sistema|la plataforma|la aplicacion|el programa|el software|esta app)\b", 10),
        (r"\b(lista|listado|resumen|mapa|recorrido|tour) (de )?(los |las )?(modulos|pantallas|secciones|funcionalidades|menus)\b|\bcuantos modulos\b|\btour\b", 10),
        (r"\bpara que (sirve|sirven) (inventia|el sistema|la plataforma|esta app|esta aplicacion)\b", 10),
    ]),
    _i("asistente_funciona", CATEGORIA, "Cómo funciona el asistente y sus límites", (),
       ("¿Cómo funciona el asistente?", "¿Qué no puedes hacer?", "¿De dónde sacas los datos?"), [
        (r"\bcomo (funcionas|trabajas|respondes|entiendes|aprendes|piensas|eres capaz|sabes (tanto|todo))\b|\bcomo funciona (el asistente|este chat|el chat|esto del asistente|el bot)\b", 10),
        (r"\b(usas|usa|funcionas con|funciona con|eres (un|una)|tienes|tiene|estas hecho con|estas basado en) (un )?(llm|gpt|chatgpt|modelo de lenguaje|ia generativa|inteligencia artificial generativa|openai|claude|gemini|ia)\b", 10),
        (r"\b(llm|gpt|chatgpt|modelo de lenguaje|openai|ia generativa)\b", 9),
        (r"\bque no (puedes|sabes|haces|entiendes|respondes)\b|\b(tus|sus) (limitaciones|limites)\b|\blimitaciones del asistente\b|\bhasta donde (llegas|puedes|sabes)\b", 10),
        (r"\bde donde (sacas|salen|vienen|obtienes|sale) (los |las |tus |la |el )?(datos|informacion|cifras|respuestas|numeros)\b|\b(son|estan) (datos )?(reales|actualizad\w+)\b|\ben tiempo real\b|\bque tan actualizad\w+\b|\bdatos (reales|en vivo|actualizados)\b|\bque (datos|informacion) (usa|usas|maneja|manejas|tienes|tiene|consultas|consulta|lees|lee|ves|ve|conoces|conoce)\b", 10),
        (r"\bno (me )?(entendiste|entiendes|entendio|respondiste|respondes|contestaste|contestas|sirves|ayudas)\b|\bno es lo que (te )?(pregunte|pedi|quise)\b|\b(respuesta|dato|informacion) (incorrect\w+|equivocad\w+|erronea|mala|falsa)\b|\bte equivocas\b|\bestas (mal|equivocad\w+)\b|\beso esta mal\b|\bno me sirve\b|\bno me ayuda\b|\bpor que no me (entiendes|respondes)\b", 10),
        (r"\bno (te )?(entiendo|comprendo|capto)\b|\bexplicalo\b|\bmas (simple|sencillo|claro|facil)\b|\bpuedes repetir\b", 9),
        (r"\bcuantas? (preguntas|consultas|cosas|tipos de preguntas) (entiendes|sabes|puedes|respondes|manejas|contestas)\b", 10),
        (r"\b(que tan|eres) (inteligente|confiable|preciso|exacto|bueno)\b|\bpuedo (confiar|fiarme)\b", 9),
        (r"\b(me )?(recuerdas|recuerdas lo|te acuerdas|tienes memoria|guardas (la )?conversacion|guardas mis preguntas)\b", 9),
    ]),
    _i("version_sistema", CATEGORIA, "Versión del sistema", (),
       ("¿Qué versión del sistema es?",), [
        (r"\bversion\b.*\b(sistema|inventia|aplicacion|app|programa|plataforma|software)\b|\b(sistema|inventia|aplicacion|app|programa|plataforma|software)\b.*\bversion\b", 11),
        (r"\b(que|cual es la|cual) version\b|\bversion actual\b|\bnumero de version\b|\bultima actualizacion\b|\bcuando se actualizo\b", 11),
    ]),
)
