"""Utilidades de lenguaje natural en español para el asistente de consultas.

Todo es puro (sin base de datos ni bibliotecas externas): normalizar texto, comparar palabras tolerando
plurales y errores de escritura, y extraer fechas, periodos, cantidades y números de documento de una frase.
Las funciones que dependen de «hoy» lo reciben como parámetro para poder probarlas con fechas fijas.
"""

import calendar
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, timedelta

MESES: dict[str, int] = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}
NOMBRES_MES = ("", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")
NOMBRES_DIA = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
_MES = "(" + "|".join(sorted(MESES, key=len, reverse=True)) + ")"

NUMEROS_EN_LETRAS: dict[str, int] = {
    "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8,
    "nueve": 9, "diez": 10, "once": 11, "doce": 12, "quince": 15, "veinte": 20, "treinta": 30,
}

PALABRAS_VACIAS = frozenset(
    """a al algo algun alguna algunas alguno algunos ante ahi alli aqui como con contra cual cuales cuando cuanto cuanta
    cuantos cuantas de del desde donde dos el ella ellas ellos en entre era eran es esa esas ese eso esos esta estan estar
    este esto estos fue fueron ha han hasta hay la las le les lo los me mi mis mucho muy nada ni no nos nuestra nuestras
    nuestro nuestros o os otra otro para pero por porque que quien quienes se sea segun ser si sin sobre su sus te tengo
    tiene tienen todo toda todos todas tu tus un una unas uno unos y ya yo mas menos favor porfa dime dame muestrame
    necesito quiero puedes podrias tambien ademas solo""".split()
)

_UNIDADES_TECNICAS = re.compile(r"(\d+)\s+(v|w|ah|kw|kwh|mm|cm|km|kg|ml|hz|mah|l)\b")


def sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def base(texto: str) -> str:
    """Minúsculas y sin acentos (la «ñ» queda como «n»); conserva la puntuación para poder leer fechas."""
    return sin_acentos(texto).lower().strip()


def limpio(texto: str) -> str:
    """Solo letras, números y espacios; las magnitudes se pegan («48 v» → «48v») como en los nombres de producto."""
    t = re.sub(r"[^a-z0-9]+", " ", base(texto))
    t = _UNIDADES_TECNICAS.sub(r"\1\2", t)
    return re.sub(r"\s+", " ", t).strip()


def tokens(texto_limpio: str) -> list[str]:
    return texto_limpio.split()


def compacto(texto: str) -> str:
    """Solo letras y números, sin separadores: sirve para comparar códigos («BAT-004» == «bat 004»)."""
    return re.sub(r"[^a-z0-9]", "", base(texto))


def raiz(palabra: str) -> str:
    """Quita plural: «baterías» → «bateria», «motores» → «motor», «luces» → «luz»."""
    if len(palabra) <= 3 or any(c.isdigit() for c in palabra):
        return palabra
    if palabra.endswith("ces"):
        return palabra[:-3] + "z"
    if palabra.endswith("ones"):
        return palabra[:-2]
    if palabra.endswith("es") and len(palabra) > 4 and palabra[-3] in "rlndzj":
        return palabra[:-2]
    if palabra.endswith("s") and not palabra.endswith("ss"):
        return palabra[:-1]
    return palabra


def raiz_fuerte(palabra: str) -> str:
    """Además del plural ignora la vocal final: «urbano» y «urbana», «eléctrica» y «eléctrico» coinciden."""
    r = raiz(palabra)
    if len(r) > 4 and r[-1] in "aeo" and not any(c.isdigit() for c in r):
        return r[:-1]
    return r


def distancia(a: str, b: str) -> int:
    """Distancia de edición (inserción, borrado, cambio y letras cruzadas): «bateira» a «bateria» = 1."""
    filas = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        filas[i][0] = i
    for j in range(len(b) + 1):
        filas[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            costo = 0 if a[i - 1] == b[j - 1] else 1
            filas[i][j] = min(filas[i - 1][j] + 1, filas[i][j - 1] + 1, filas[i - 1][j - 1] + costo)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                filas[i][j] = min(filas[i][j], filas[i - 2][j - 2] + 1)
    return filas[len(a)][len(b)]


def _tolerancia(longitud: int) -> int:
    return 1 if longitud < 9 else 2


def similitud(a: str, b: str) -> float:
    """0 = distintas; 1 = iguales. Tolera plural, género y errores de escritura en palabras de 5+ letras."""
    if a == b:
        return 1.0
    if any(c.isdigit() for c in a + b):
        return 0.0
    ra, rb = raiz_fuerte(a), raiz_fuerte(b)
    if ra == rb:
        return 0.95
    if min(len(ra), len(rb)) >= 4 and (ra.startswith(rb) or rb.startswith(ra)):
        return 0.85
    if min(len(a), len(b)) >= 5 and distancia(ra, rb) <= _tolerancia(min(len(ra), len(rb))):
        return 0.8
    return 0.0


_CONFUSION_INICIAL = {"b": "v", "v": "b", "c": "sz", "s": "cz", "z": "cs", "k": "c", "g": "j", "j": "g"}  # letras que se suelen confundir al escribir


def _misma_inicial(a: str, b: str) -> bool:
    return a == b or b in _CONFUSION_INICIAL.get(a, "")


def _otra_forma_de_la_palabra(palabra: str, candidata: str) -> bool:
    """«confirmar» y «confirmaron» son formas distintas de una misma palabra, no un error de digitación."""
    comun = 0
    for x, y in zip(palabra, candidata, strict=False):
        if x != y:
            break
        comun += 1
    if len(palabra) == len(candidata) and palabra[:-1] == candidata[:-1] and palabra[-1] in "aeios" and candidata[-1] in "aeios":
        return True  # «anula»/«anulo», «cambia»/«cambio»: cambia la conjugación, no hay error
    diferencia = abs(len(palabra) - len(candidata))
    if diferencia == 1:
        corta, larga = sorted((palabra, candidata), key=len)
        if larga.startswith(corta):
            return True  # una letra de más al final: plural o género («pedido»/«pedidos»)
        if any(larga[:i] + larga[i + 1 :] == corta for i in range(len(larga))):
            return False  # una letra de más o de menos en medio de la palabra: errata («inventaro»)
    return diferencia > 0 and comun >= min(len(palabra), len(candidata)) - 1


def corregir_palabra(palabra: str, vocabulario: set[str] | frozenset[str]) -> str:
    """Devuelve la palabra del vocabulario más parecida si la escrita parece un error de digitación."""
    if len(palabra) < 5 or palabra in vocabulario or any(c.isdigit() for c in palabra):
        return palabra
    limite = _tolerancia(len(palabra))
    mejor, mejor_distancia = palabra, limite + 1
    for candidata in sorted(vocabulario):
        if abs(len(candidata) - len(palabra)) > limite or not _misma_inicial(palabra[0], candidata[0]) or _otra_forma_de_la_palabra(palabra, candidata):
            continue
        d = distancia(palabra, candidata)
        if d < mejor_distancia:
            mejor, mejor_distancia = candidata, d
    return mejor


# --------------------------------------------------------------------------------------- fechas y periodos


@dataclass(frozen=True)
class Periodo:
    desde: date
    hasta: date
    etiqueta: str

    @property
    def dias(self) -> int:
        return (self.hasta - self.desde).days + 1


def fecha_larga(d: date) -> str:
    return f"{d.day} de {NOMBRES_MES[d.month]} de {d.year}"


def _fecha_corta(d: date, con_anio: bool) -> str:
    return f"{d.day} de {NOMBRES_MES[d.month]}" + (f" de {d.year}" if con_anio else "")


def describir_rango(desde: date, hasta: date) -> str:
    if desde == hasta:
        return fecha_larga(desde)
    if desde.year == hasta.year and desde.month == hasta.month:
        return f"del {desde.day} al {hasta.day} de {NOMBRES_MES[hasta.month]} de {hasta.year}"
    if desde.year == hasta.year:
        return f"del {_fecha_corta(desde, False)} al {_fecha_corta(hasta, True)}"
    return f"del {_fecha_corta(desde, True)} al {_fecha_corta(hasta, True)}"


def _mes_completo(anio: int, mes: int, hoy: date) -> Periodo:
    desde = date(anio, mes, 1)
    hasta = min(date(anio, mes, calendar.monthrange(anio, mes)[1]), hoy) if (anio, mes) == (hoy.year, hoy.month) else date(
        anio, mes, calendar.monthrange(anio, mes)[1]
    )
    return Periodo(desde, hasta, f"{NOMBRES_MES[mes]} de {anio}")


def _anio_para_mes(mes: int, anio: int | None, hoy: date) -> int:
    if anio:
        return anio
    return hoy.year if mes <= hoy.month else hoy.year - 1


def _periodo_dias(hoy: date, dias: int, etiqueta: str) -> Periodo:
    return Periodo(hoy - timedelta(days=dias - 1), hoy, etiqueta)


def _inicio_semana(d: date) -> date:
    return d - timedelta(days=d.weekday())  # la semana empieza el lunes


def _trimestre(hoy: date, atras: int) -> Periodo:
    indice = (hoy.month - 1) // 3 - atras
    anio = hoy.year + indice // 4
    q = indice % 4
    desde = date(anio, q * 3 + 1, 1)
    hasta = date(anio, q * 3 + 3, calendar.monthrange(anio, q * 3 + 3)[1])
    etiqueta = "este trimestre" if atras == 0 else "el trimestre pasado"
    return Periodo(desde, min(hasta, hoy) if atras == 0 else hasta, etiqueta)


def _entero_o_palabra(texto: str) -> int | None:
    if texto.isdigit():
        return int(texto)
    return NUMEROS_EN_LETRAS.get(texto)


def _p_rango_dias_mes(m: re.Match, hoy: date) -> Periodo:
    d1, d2, mes = int(m.group(1)), int(m.group(2)), MESES[m.group(3)]
    anio = _anio_para_mes(mes, int(m.group(4)) if m.group(4) else None, hoy)
    p = Periodo(date(anio, mes, d1), date(anio, mes, d2), "")
    if p.desde > p.hasta:
        raise ValueError
    return Periodo(p.desde, p.hasta, describir_rango(p.desde, p.hasta))


def _p_rango_completo(m: re.Match, hoy: date) -> Periodo:
    d1, mes1, d2, mes2 = int(m.group(1)), MESES[m.group(2)], int(m.group(4)), MESES[m.group(5)]
    a2 = _anio_para_mes(mes2, int(m.group(6)) if m.group(6) else None, hoy)
    a1 = int(m.group(3)) if m.group(3) else (a2 if mes1 <= mes2 else a2 - 1)
    desde, hasta = date(a1, mes1, d1), date(a2, mes2, d2)
    if desde > hasta:
        raise ValueError
    return Periodo(desde, hasta, describir_rango(desde, hasta))


def _p_iso(m: re.Match, hoy: date) -> Periodo:
    fechas = sorted(date.fromisoformat(f) for f in re.findall(r"\d{4}-\d{2}-\d{2}", m.group(0)))
    return Periodo(fechas[0], fechas[-1], describir_rango(fechas[0], fechas[-1]))


def _p_numerica(m: re.Match, hoy: date) -> Periodo:
    dia, mes = int(m.group(1)), int(m.group(2))
    anio = int(m.group(3)) if m.group(3) else None
    if anio is not None and anio < 100:
        anio += 2000
    d = date(_anio_para_mes(mes, anio, hoy) if anio is None and (mes, dia) > (hoy.month, hoy.day) else (anio or hoy.year), mes, dia)
    return Periodo(d, d, fecha_larga(d))


def _p_dia_mes(m: re.Match, hoy: date) -> Periodo:
    dia, mes = int(m.group(1)), MESES[m.group(2)]
    anio = int(m.group(3)) if m.group(3) else (hoy.year if (mes, dia) <= (hoy.month, hoy.day) else hoy.year - 1)
    d = date(anio, mes, dia)
    return Periodo(d, d, fecha_larga(d))


def _p_mes_anio(m: re.Match, hoy: date) -> Periodo:
    return _mes_completo(int(m.group(2)), MESES[m.group(1)], hoy)


def _p_mes(m: re.Match, hoy: date) -> Periodo:
    mes = MESES[m.group(m.lastindex or 1)]
    return _mes_completo(_anio_para_mes(mes, None, hoy), mes, hoy)


def _p_desde_dia_mes(m: re.Match, hoy: date) -> Periodo:
    dia, mes = int(m.group(1)), MESES[m.group(2)]
    d = date(_anio_para_mes(mes, None, hoy), mes, dia)
    return Periodo(d, hoy, f"desde el {fecha_larga(d)}")


def _p_ultimos(m: re.Match, hoy: date) -> Periodo:
    n = _entero_o_palabra(m.group(1)) or 1
    unidad = m.group(2)
    if unidad.startswith("hora"):
        return Periodo(hoy - timedelta(days=1), hoy, "las últimas horas")
    factor = {"d": 1, "s": 7, "m": 30, "a": 365}[unidad[0]]
    dias = max(1, min(n * factor, 730))
    nombre = {"d": "día", "s": "semana", "m": "mes", "a": "año"}[unidad[0]]
    sufijo = "" if n == 1 else ("es" if nombre == "mes" else "s")
    articulo = "las últimas" if nombre == "semana" else "los últimos"
    return _periodo_dias(hoy, dias, f"{articulo} {n} {nombre}{sufijo}")


def _p_ultimo_singular(m: re.Match, hoy: date) -> Periodo:
    unidad = m.group(1)
    dias = {"dia": 1, "semana": 7, "mes": 30, "trimestre": 90, "ano": 365}[unidad]
    nombre = {"dia": "el último día", "semana": "la última semana", "mes": "el último mes", "trimestre": "el último trimestre", "ano": "el último año"}[unidad]
    return _periodo_dias(hoy, dias, nombre)


def _p_anio(m: re.Match, hoy: date) -> Periodo:
    anio = int(m.group(1))
    return Periodo(date(anio, 1, 1), min(date(anio, 12, 31), hoy) if anio == hoy.year else date(anio, 12, 31), f"el año {anio}")


def _p_semana_pasada(m: re.Match, hoy: date) -> Periodo:
    lunes = _inicio_semana(hoy) - timedelta(days=7)
    return Periodo(lunes, lunes + timedelta(days=6), "la semana pasada")


def _p_mes_pasado(m: re.Match, hoy: date) -> Periodo:
    primero = hoy.replace(day=1) - timedelta(days=1)
    p = _mes_completo(primero.year, primero.month, hoy)
    return Periodo(p.desde, p.hasta, "el mes pasado")


def _p_quincena(m: re.Match, hoy: date) -> Periodo:
    pasada = bool(re.search(r"pasada|anterior", m.group(0)))
    if hoy.day > 15:
        actual = (hoy.replace(day=16), hoy)
        previa = (hoy.replace(day=1), hoy.replace(day=15))
    else:
        fin_mes_previo = hoy.replace(day=1) - timedelta(days=1)
        actual = (hoy.replace(day=1), hoy)
        previa = (fin_mes_previo.replace(day=16), fin_mes_previo)
    d, h = previa if pasada else actual
    return Periodo(d, h, "la quincena pasada" if pasada else "esta quincena")


_DIAS_SEMANA = {"lunes": 0, "martes": 1, "miercoles": 2, "jueves": 3, "viernes": 4, "sabado": 5, "domingo": 6}


def _p_dia_semana(m: re.Match, hoy: date) -> Periodo:
    """«el lunes» es el lunes más reciente (hoy, si hoy es lunes); «el lunes pasado», el de la semana anterior."""
    objetivo = _DIAS_SEMANA[m.group(1)]
    atras = (hoy.weekday() - objetivo) % 7
    pasado = bool(m.group(2))
    if pasado and atras == 0:
        atras = 7
    dia = hoy - timedelta(days=atras)
    return Periodo(dia, dia, f"el {NOMBRES_DIA[objetivo]}" + (" pasado" if pasado else ""))


def _p_hace(m: re.Match, hoy: date) -> Periodo:
    """«hace 3 días», «hace una semana»: ese día exacto."""
    n = _entero_o_palabra(m.group(1)) or 1
    dias = n * (7 if m.group(2).startswith("semana") else 1)
    if dias > 730:
        raise ValueError("demasiado atrás")
    dia = hoy - timedelta(days=dias)
    return Periodo(dia, dia, "")  # sin etiqueta: se muestra como «el 31 de octubre de 2026»


def _p_fin_de_semana(m: re.Match, hoy: date) -> Periodo:
    """El sábado y el domingo más recientes que ya empezaron; «pasado» (estando en fin de semana) es el anterior."""
    sabado = hoy - timedelta(days=(hoy.weekday() - 5) % 7)  # sábado más reciente (hoy, si hoy es sábado)
    if re.search(r"pasado|anterior", m.group(0)) and hoy.weekday() >= 5:
        sabado -= timedelta(days=7)
    domingo = sabado + timedelta(days=1)
    pasado = bool(re.search(r"pasado|anterior", m.group(0)))
    return Periodo(sabado, min(domingo, hoy), "el fin de semana pasado" if pasado else "el fin de semana")


def _semestre(hoy: date, atras: int) -> Periodo:
    indice = (hoy.year * 2 + (hoy.month - 1) // 6) - atras
    anio, mitad = divmod(indice, 2)
    desde = date(anio, mitad * 6 + 1, 1)
    hasta = date(anio, mitad * 6 + 6, calendar.monthrange(anio, mitad * 6 + 6)[1])
    return Periodo(desde, min(hasta, hoy) if atras == 0 else hasta, "este semestre" if atras == 0 else "el semestre pasado")


def _p_antepasado(m: re.Match, hoy: date) -> Periodo:
    unidad = m.group(1)
    if unidad == "mes":
        primero = (hoy.replace(day=1) - timedelta(days=1)).replace(day=1) - timedelta(days=1)
        return _mes_completo(primero.year, primero.month, hoy)
    if unidad == "semana":
        lunes = _inicio_semana(hoy) - timedelta(days=14)
        return Periodo(lunes, lunes + timedelta(days=6), "la semana antepasada")
    return Periodo(date(hoy.year - 2, 1, 1), date(hoy.year - 2, 12, 31), f"el año {hoy.year - 2}")


_ORD_RE = r"(primer|primero|primera|segundo|segunda|tercer|tercero|tercera|cuarto|cuarta|1er|1ro|1ra|2do|2da|3er|3ro|3ra|4to|4ta)"
_ORDINALES = {"primer": 1, "primero": 1, "primera": 1, "1er": 1, "1ro": 1, "1ra": 1, "segundo": 2, "segunda": 2, "2do": 2, "2da": 2, "tercer": 3, "tercero": 3, "tercera": 3, "3er": 3, "3ro": 3,
              "3ra": 3, "cuarto": 4, "cuarta": 4, "4to": 4, "4ta": 4}


def _p_trimestre_numero(m: re.Match, hoy: date) -> Periodo:
    """«el primer trimestre», «Q3», «el tercer trimestre de 2025»: sin año, el más reciente que ya empezó."""
    if m.group(1):
        numero, anio_dado = _ORDINALES[m.group(1)], m.group(2)
    elif m.group(3):
        numero, anio_dado = int(m.group(3)), m.group(4)
    else:
        numero, anio_dado = int(m.group(5)), m.group(6)
    anio = int(anio_dado) if anio_dado else (hoy.year if date(hoy.year, numero * 3 - 2, 1) <= hoy else hoy.year - 1)
    desde = date(anio, numero * 3 - 2, 1)
    hasta = date(anio, numero * 3, calendar.monthrange(anio, numero * 3)[1])
    if desde > hoy:
        raise ValueError("aún no empieza")
    nombre = ("primer", "segundo", "tercer", "cuarto")[numero - 1]
    return Periodo(desde, min(hasta, hoy), f"el {nombre} trimestre de {anio}")


def _p_semestre_numero(m: re.Match, hoy: date) -> Periodo:
    numero = _ORDINALES[m.group(1)]
    if numero not in (1, 2):
        raise ValueError("un año solo tiene dos semestres")
    anio = int(m.group(2)) if m.group(2) else (hoy.year if date(hoy.year, numero * 6 - 5, 1) <= hoy else hoy.year - 1)
    desde = date(anio, numero * 6 - 5, 1)
    hasta = date(anio, numero * 6, calendar.monthrange(anio, numero * 6)[1])
    if desde > hoy:
        raise ValueError("aún no empieza")
    return Periodo(desde, min(hasta, hoy), f"el {'primer' if numero == 1 else 'segundo'} semestre de {anio}")


def _p_quincena_mes(m: re.Match, hoy: date) -> Periodo:
    """«la primera quincena de octubre» (1 al 15) y «la segunda quincena de septiembre» (16 al fin de mes); sin mes, la del mes en curso."""
    numero = _ORDINALES[m.group(1)]
    if numero not in (1, 2):
        raise ValueError("un mes solo tiene dos quincenas")
    if m.group(2):
        mes = MESES[m.group(2)]
        anio = int(m.group(3)) if m.group(3) else _anio_para_mes(mes, None, hoy)
    else:
        mes, anio = hoy.month, hoy.year
        if numero == 2 and hoy.day <= 15:  # la segunda quincena de este mes aún no empieza: se toma la del mes anterior
            ultimo = hoy.replace(day=1) - timedelta(days=1)
            mes, anio = ultimo.month, ultimo.year
    fin_mes = calendar.monthrange(anio, mes)[1]
    desde, hasta = (date(anio, mes, 1), date(anio, mes, 15)) if numero == 1 else (date(anio, mes, 16), date(anio, mes, fin_mes))
    if desde > hoy:
        raise ValueError("aún no empieza")
    hasta = min(hasta, hoy)
    return Periodo(desde, hasta, describir_rango(desde, hasta))


def _p_rango_meses(m: re.Match, hoy: date) -> Periodo:
    """«de abril a junio», «desde enero hasta marzo de 2026», «entre abril y junio»: del primer día del primer mes al último del segundo."""
    mes1, anio1, union, mes2, anio2 = MESES[m.group(1)], m.group(2), m.group(3), MESES[m.group(4)], m.group(5)
    if union == "y" and re.search(r"compar|diferencia|versus|\bvs\b|variacion|crecimiento|cambio|contra\b|frente", m.string):
        raise ValueError("«entre A y B» en una comparación no es un rango")
    a2 = int(anio2) if anio2 else _anio_para_mes(mes2, None, hoy)
    a1 = int(anio1) if anio1 else (a2 if mes1 <= mes2 else a2 - 1)
    desde = date(a1, mes1, 1)
    hasta = date(a2, mes2, calendar.monthrange(a2, mes2)[1])
    if desde > hasta or desde > hoy:
        raise ValueError("rango al revés")
    hasta = min(hasta, hoy)
    return Periodo(desde, hasta, describir_rango(desde, hasta))


def _p_hace_meses(m: re.Match, hoy: date) -> Periodo:
    """«hace 3 meses» es el mes calendario de esa fecha; «hace 2 años», el año completo."""
    n = _entero_o_palabra(m.group(1)) or 1
    if m.group(2).startswith("ano"):
        anio = hoy.year - n
        if n > 5:
            raise ValueError("demasiado atrás")
        return Periodo(date(anio, 1, 1), date(anio, 12, 31), f"el año {anio}")
    if n > 60:
        raise ValueError("demasiado atrás")
    anio, mes0 = divmod(hoy.year * 12 + hoy.month - 1 - n, 12)
    return _mes_completo(anio, mes0 + 1, hoy)


_REGLAS: list[tuple[re.Pattern, object]] = [
    (re.compile(rf"\bdesde (?:el )?(\d{{1,2}}) de {_MES}(?: de (\d{{4}}))? hasta (?:el )?(\d{{1,2}}) de {_MES}(?: de (\d{{4}}))?"), _p_rango_completo),
    (re.compile(rf"\b(?:del|desde el) (\d{{1,2}}) (?:al|hasta el) (\d{{1,2}}) de {_MES}(?: de (\d{{4}}))?"), _p_rango_dias_mes),
    (re.compile(rf"\bentre el (\d{{1,2}}) y el (\d{{1,2}}) de {_MES}(?: de (\d{{4}}))?"), _p_rango_dias_mes),
    (re.compile(r"\d{4}-\d{2}-\d{2}(?:\D{1,14}\d{4}-\d{2}-\d{2})?"), _p_iso),
    (re.compile(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b(?![\d/-])"), _p_numerica),
    (re.compile(rf"\bdesde (?:el )?(\d{{1,2}}) de {_MES}\b"), _p_desde_dia_mes),
    (re.compile(rf"\b(\d{{1,2}}) de {_MES}(?: de (\d{{4}}))?"), _p_dia_mes),
    (re.compile(rf"\b(?:de|desde|entre)(?: el mes de)? {_MES}(?: de (20\d{{2}}))? (a|hasta|al mes de|y) {_MES}(?: de (20\d{{2}}))?\b"), _p_rango_meses),
    (re.compile(rf"\b{_MES}(?: de| del)? (20\d{{2}})\b"), _p_mes_anio),
    (re.compile(rf"\b{_ORD_RE} quincena(?: (?:de|del) {_MES}(?: de (20\d{{2}}))?)?\b"), _p_quincena_mes),
    (re.compile(rf"\b{_ORD_RE} trimestre(?: (?:de|del) (20\d{{2}}))?\b|\bq([1-4])\b(?: ?(?:de|del)? ?(20\d{{2}}))?|\btrimestre ([1-4])\b(?: (?:de|del) (20\d{{2}}))?"), _p_trimestre_numero),
    (re.compile(rf"\b{_ORD_RE} semestre(?: (?:de|del) (20\d{{2}}))?\b"), _p_semestre_numero),
    (re.compile(r"\bhace (\d{1,2}|un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce) (mes(?:es)?|anos?)\b"), _p_hace_meses),
    (re.compile(r"\bante(?:s de)? ?ayer\b|\bantier\b"), lambda m, h: Periodo(h - timedelta(days=2), h - timedelta(days=2), "anteayer")),
    (re.compile(r"\bayer\b"), lambda m, h: Periodo(h - timedelta(days=1), h - timedelta(days=1), "ayer")),
    (re.compile(r"\bhace (\d{1,3}|un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|quince|veinte|treinta) (dias?|semanas?)\b"), _p_hace),
    (re.compile(r"\b(?:el |este |del |de |en )?(?:fin(?:es)? de semana|finde)(?: (?:pasado|anterior))?\b"), _p_fin_de_semana),
    (re.compile(r"\b(?:el|este|del|de|en)\s+(lunes|martes|miercoles|jueves|viernes|sabado|domingo)(\s+(?:pasado|anterior))?\b(?!\s+(?:a|al|hasta|y|o)\s+(?:lunes|martes|miercoles|jueves|viernes|sabado|domingo))"), _p_dia_semana),
    (re.compile(r"\bhoy\b|\beste dia\b"), lambda m, h: Periodo(h, h, "hoy")),
    (re.compile(r"\bsemana (?:pasada|anterior)\b|\bla semana que paso\b"), _p_semana_pasada),
    (re.compile(r"\best[ea] semana\b|\bsemana (?:actual|en curso)\b|\blo que va de la semana\b"), lambda m, h: Periodo(_inicio_semana(h), h, "esta semana")),
    (re.compile(r"\bquincena (?:pasada|anterior)\b|\best[ea] quincena\b"), _p_quincena),
    (re.compile(r"\bmes (?:pasado|anterior)\b|\bel mes que paso\b"), _p_mes_pasado),
    (re.compile(r"\best[ea] mes\b|\bmes (?:actual|en curso)\b|\blo que va del mes\b"), lambda m, h: Periodo(h.replace(day=1), h, "este mes")),
    (re.compile(r"\btrimestre (?:pasado|anterior)\b"), lambda m, h: _trimestre(h, 1)),
    (re.compile(r"\best[ea] trimestre\b|\btrimestre actual\b"), lambda m, h: _trimestre(h, 0)),
    (re.compile(r"\bano (?:pasado|anterior)\b|\bel ano que paso\b"), lambda m, h: Periodo(date(h.year - 1, 1, 1), date(h.year - 1, 12, 31), "el año pasado")),
    (re.compile(r"\best[ea] ano\b|\bano (?:actual|en curso)\b|\blo (?:que va|corrido) del ano\b|\bacumulado del ano\b"), lambda m, h: Periodo(date(h.year, 1, 1), h, "este año")),
    (re.compile(r"\b(mes|semana|ano) antepasad[oa]\b"), _p_antepasado),
    (re.compile(r"\bsemestre (?:pasado|anterior)\b"), lambda m, h: _semestre(h, 1)),
    (re.compile(r"\best[ea] semestre\b|\bsemestre actual\b"), lambda m, h: _semestre(h, 0)),
    # «las ventas del año», «del trimestre», «de la semana»: lo que va del periodo en curso («día de la semana» no es una fecha)
    (re.compile(r"\b(?:del|en el|durante el|todo el) ano\b(?!\s+\d)"), lambda m, h: Periodo(date(h.year, 1, 1), h, "este año")),
    (re.compile(r"\b(?:del|en el|durante el) trimestre\b"), lambda m, h: _trimestre(h, 0)),
    (re.compile(r"\b(?:del|en el|durante el) semestre\b"), lambda m, h: _semestre(h, 0)),
    (re.compile(r"(?<!dia )(?<!dias )\b(?:de|en|durante) la semana\b"), lambda m, h: Periodo(_inicio_semana(h), h, "esta semana")),
    (re.compile(r"\b(?:de|en|durante) la quincena\b"), _p_quincena),
    (re.compile(r"\b(?:del|en el|durante el) dia\b(?!\s+(?:de|a dia|\d))"), lambda m, h: Periodo(h, h, "hoy")),
    (re.compile(r"\b(?:ano|en|del|de|durante)\s+(20\d{2})\b"), _p_anio),
    (re.compile(r"\bultim[oa]s? (\d{1,3}|un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|quince|veinte|treinta) (dias?|semanas?|meses|mes|anos?|horas?)\b"), _p_ultimos),
    (re.compile(r"\bultim[oa]s? (dia|semana|mes|trimestre|ano)\b"), _p_ultimo_singular),
    (re.compile(r"\bultimos dias\b|\bdias recientes\b"), lambda m, h: _periodo_dias(h, 7, "los últimos días")),
    (re.compile(rf"\b(?:en|de|durante|del|para|el mes de|mes de)\s+{_MES}\b"), _p_mes),
    (re.compile(rf"\b{_MES}\b"), _p_mes),
]


def extraer_periodo(texto: str, hoy: date) -> tuple[Periodo | None, str]:
    """Busca el primer periodo reconocible en ``texto`` (ya en minúsculas y sin acentos).
    Devuelve el periodo y el texto sin la parte que lo expresaba."""
    for patron, fabrica in _REGLAS:
        m = patron.search(texto)
        if not m:
            continue
        try:
            periodo = fabrica(m, hoy)  # type: ignore[operator]
        except (ValueError, OverflowError):
            continue  # fecha imposible (31 de febrero): se intenta con otra regla
        if periodo.desde > periodo.hasta:
            continue
        return periodo, f"{texto[: m.start()]} {texto[m.end():]}"
    return None, texto


def extraer_horizonte(texto: str) -> tuple[int | None, str]:
    """Días hacia el FUTURO que menciona la persona («próximas 2 semanas», «en 10 días», «mañana»)."""
    reglas = (
        (re.compile(r"\b(?:proxim[oa]s?|siguientes?|venideros?) (\d{1,3}|un|una|dos|tres|cuatro|cinco|seis|siete|diez|quince|veinte|treinta) (dias?|semanas?|meses|mes)\b"), None),
        (re.compile(r"\b(?:en|dentro de) (\d{1,3}|un|una|dos|tres|cuatro|cinco|seis|siete|diez|quince|veinte|treinta) (dias?|semanas?|meses|mes)\b"), None),
        (re.compile(r"\b(?:la |el |esta |este )?(?:proxim[oa]|siguiente) (semana|mes|quincena|dia)\b"), 1),
        (re.compile(r"\bmanana\b"), "manana"),
    )
    for patron, modo in reglas:
        m = patron.search(texto)
        if not m:
            continue
        if modo is None:
            n = _entero_o_palabra(m.group(1)) or 1
            dias = n * {"d": 1, "s": 7, "m": 30}[m.group(2)[0]]
        elif modo == 1:
            dias = {"semana": 7, "mes": 30, "quincena": 15, "dia": 1}[m.group(1)]
        else:
            dias = 1
        return max(1, min(dias, 90)), f"{texto[: m.start()]} {texto[m.end():]}"
    return None, texto


_SUSTANTIVOS_LIMITE = (
    r"productos?|articulos?|referencias?|items?|alertas?|ventas?|movimientos?|recomendaciones|traslados?|sedes|resultados|"
    r"mejores|peores|mas|menos|primeros|ultimos|ultimas|registros|usuarios|garantias|quejas|categorias"
)


def extraer_limite(texto: str) -> tuple[int | None, str]:
    """Cuántos resultados pide («top 5», «los 10 más vendidos», «tres productos»). Máximo 25."""
    reglas = (
        re.compile(r"\btop\s*(\d{1,3})\b"),
        re.compile(rf"\b(\d{{1,3}})\s+(?:{_SUSTANTIVOS_LIMITE})\b"),
        re.compile(r"\b(?:los|las|primeros|primeras|ultimos|ultimas)\s+(\d{1,3})\b(?!\s*(?:v|w|ah|kw|dias|semanas|meses))"),
        re.compile(rf"\b({'|'.join(NUMEROS_EN_LETRAS)})\s+(?:{_SUSTANTIVOS_LIMITE})\b"),
    )
    for patron in reglas:
        m = patron.search(texto)
        if m:
            n = _entero_o_palabra(m.group(1))
            if n and 1 <= n <= 100:
                return min(n, 25), f"{texto[: m.start()]} {texto[m.end():]}"
    return None, texto


def extraer_numero_documento(texto: str) -> tuple[int | None, str]:
    """Número de una venta, traslado, radicado… («venta 15», «traslado n.º 3», «factura #20»)."""
    m = re.search(
        r"\b(?:venta|factura|ticket|comprobante|remision|traslado|pqrs|radicado|entrada|recepcion|garantia|recomendacion)\s*"
        r"(?:numero|nro|num|no|n)?\.?\s*#?\s*(\d{1,9})\b",
        texto,
    )
    if not m:
        return None, texto
    return int(m.group(1)), f"{texto[: m.start()]} {texto[m.end():]}"


def plural(n: int, singular: str, plural_: str | None = None) -> str:
    return f"{n} {singular if n == 1 else (plural_ or singular + 's')}"
