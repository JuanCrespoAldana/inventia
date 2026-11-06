"""Preguntas compuestas: «¿cuántos productos hay y cuáles están agotados?» se contesta como dos preguntas y se une el resultado.

Aquí solo hay texto: cortar el mensaje en preguntas y fusionar las respuestas. El motor decide si el corte es válido (cada parte debe
entenderse sola o ser un seguimiento como «¿y el máximo?»); si no lo es, el mensaje se responde entero, como siempre.
"""

import re

from app.dto.asistente_dto import ContextoConversacion, Enlace, RespuestaAsistente

MAX_PARTES = 3
INTENCION_COMPUESTA = "compuesta"

_PEDIR = r"(?:dime|dame|muestrame|muéstrame|cuentame|cuéntame|indicame|indícame|enseñame|enséñame|listame|lístame|explicame|explícame|damelo|dímelo|dimelo)"
# Solo se acepta «qué» y «cómo» con tilde: sin ella «y que…» / «y como…» suelen ser parte de la misma frase («lo que», «tanto como»).
_INTERROGATIVO_SEGURO = r"(?:cu[aá]nt[oa]s?|cu[aá]l(?:es)?|qui[eé]n(?:es)?|d[oó]nde|c[oó]mo|qué)"

_CORTE = re.compile(
    "|".join(
        [
            r"\s*;\s*",  # «…; …»
            r"(?<=[?!])\s+",  # «¿…? ¿…?»
            r"(?-i:(?<=\w\w\w\.)\s+(?=[¿¡A-ZÁÉÍÓÚÑ]))",  # «… . Otra frase» (no corta abreviaturas de una o dos letras)
            r"(?:\s*,\s*|\s+y\s+)(?:ademas|además|tambien|también|aparte)\b[\s,]*",  # «, además …» / «y también …»
            rf"\s+(?:ademas|además)\s+(?=(?:{_PEDIR}|{_INTERROGATIVO_SEGURO})\b)",
            rf"\s*,?\s+y\s+(?={_PEDIR}\b)",  # «… y dime …»
            rf"\s*,?\s+y\s+(?={_INTERROGATIVO_SEGURO}\b)",  # «… y cuántos …»
            r"\s*,?\s+y\s+(?=(?:cu[aá]nt[oa]s?|cu[aá]l(?:es)?|qui[eé]n(?:es)?|d[oó]nde)\b)",  # lo mismo sin tilde cuando no hay ambigüedad
        ]
    ),
    re.IGNORECASE,
)
_BORDES = " \t\r\n,;:.-–—"


def _palabras(texto: str) -> int:
    return len(re.findall(r"\w+", texto))


def dividir(mensaje: str) -> list[str]:
    """Las preguntas que trae el mensaje, en orden. Si no hay un corte claro devuelve el mensaje entero (una sola parte)."""
    texto = mensaje.strip()
    if len(texto) < 14:
        return [texto]
    partes = [p.strip(_BORDES) for p in _CORTE.split(texto) if p and p.strip(_BORDES)]
    if len(partes) < 2 or any(_palabras(p) < 2 for p in partes):
        return [texto]
    return partes


def etiqueta(parte: str) -> str:
    """La pregunta sin signos, para titular su respuesta."""
    limpia = parte.strip(" ¿?¡!.,;:").strip()
    limpia = re.sub(r"^(?:y|e)\s+", "", limpia, flags=re.IGNORECASE)
    return (limpia[:1].upper() + limpia[1:]) if limpia else parte


def _numerar(bloque, numero: int, primero: bool, titulo: str):
    """El bloque con el número de su pregunta en el título (el primero de cada parte, si no tenía título, lleva el de la pregunta)."""
    if bloque.titulo:
        return bloque.model_copy(update={"titulo": f"{numero}. {bloque.titulo}"})
    if primero:
        return bloque.model_copy(update={"titulo": f"{numero}. {titulo}"})
    return bloque


def fusionar(partes: list[str], respuestas: list[RespuestaAsistente], omitidas: int, contexto: ContextoConversacion) -> RespuestaAsistente:
    """Una sola respuesta con el texto, los bloques, los enlaces y los avisos de cada pregunta, numerados."""
    textos: list[str] = []
    bloques: list = []
    enlaces: dict[str, Enlace] = {}
    sugerencias: list[str] = []
    avisos: list[str] = []
    for n, (parte, r) in enumerate(zip(partes, respuestas, strict=True), start=1):
        titulo = etiqueta(parte)
        textos.append(f"**{n}. {titulo}**\n{r.texto}")
        bloques += [_numerar(b, n, i == 0, titulo) for i, b in enumerate(r.bloques)]
        for e in r.enlaces:
            enlaces.setdefault(e.ruta, e)
        sugerencias += r.sugerencias
        avisos += r.avisos
    if omitidas:
        resto = "la otra" if omitidas == 1 else f"las otras {omitidas}"
        avisos.append(f"Respondí las primeras {len(partes)} preguntas; envía {resto} en un mensaje aparte.")
    alcances = {r.alcance for r in respuestas if r.alcance}
    periodos = {r.periodo for r in respuestas if r.periodo}
    vistas: set[str] = set()
    unicas = [s for s in sugerencias if not (s in vistas or vistas.add(s))]
    return RespuestaAsistente(
        intencion=INTENCION_COMPUESTA, entendida=all(r.entendida for r in respuestas), texto="\n\n".join(textos), bloques=bloques,
        enlaces=list(enlaces.values())[:5], sugerencias=unicas[:5], avisos=list(dict.fromkeys(avisos)),
        alcance=alcances.pop() if len(alcances) == 1 else None, periodo=periodos.pop() if len(periodos) == 1 else None, contexto=contexto,
    )
