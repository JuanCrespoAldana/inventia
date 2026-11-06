"""Entidades que aparecen en una pregunta: sedes, categorías, productos, periodos, cantidades y filtros.

Las sedes, categorías y productos se reconocen contra el directorio REAL de la empresa (nombres y códigos), tolerando
plurales, géneros y errores de escritura. Nada se inventa: si una palabra no corresponde a nada, se informa.
"""

import math
import re
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.catalogo import Categoria, Producto
from app.model.sede import Sede
from app.security.acceso import Contexto
from app.service.asistente.conocimiento_datos import GLOSARIO, VERBOS_TAREAS
from app.util import lenguaje as L

# Adjetivos que describen la pregunta («¿cuáles rotan más rápido?») y solos no identifican un producto, aunque aparezcan en algún nombre.
_ADJETIVOS_DEBILES = frozenset({"rapido", "rapida", "rapidos", "rapidas", "lento", "lenta", "lentos", "lentas", "nuevo", "nueva", "nuevos", "nuevas", "viejo", "vieja", "grande", "grandes", "pequeno", "pequena"})
_GENERICAS_SEDE = frozenset({"sede", "sucursal", "tienda", "bodega", "punto", "venta", "almacen", "local"})
_MAXIMO_CANDIDATOS = 40
_ENCABEZADO_SEGUIMIENTO = re.compile(r"^(y|ahora|tambien|pero|entonces|ademas|mejor (?:en|para|con|ahora|dime|muestrame|usa|mira)|igual|que tal|y que tal|y si|y como)\b")
_PRONOMBRE_PRODUCTO = re.compile(
    r"\b(ese|esa|esos|esas|eso|este producto|esta referencia|el mismo|la misma|los mismos|las mismas|dicho producto|ese articulo)\b"
)
_PRONOMBRE_SEDE = re.compile(r"\b(esa sede|esa tienda|esa bodega|alli|ahi|la misma sede|en esa)\b")
_TODAS_LAS_SEDES = re.compile(
    r"\b(todas las sedes|toda la empresa|en total|consolidado|global|de toda la empresa|entre todas|todas mis sedes|todas las tiendas)\b"
)
# Palabras corrientes que no son un producto aunque no estén en el catálogo (se suman a las del dominio).
_COMUNES = frozenset(
    """quiero quieres necesito necesitas puedes puedo podemos podria podrias dime dame muestrame muestra mostrar ver listar lista
    listame dar saber conocer decir revisar consultar buscar hacer hizo hice hemos hay haya hubo tenemos tienen tiene tengo
    frente respecto comparado comparando versus tuvimos tuve hoy ayer manana ahora luego despues antes siempre nunca mucho poco bastante todos todas todo toda cada otro otra
    otros otras mismo misma mismos mismas solo solamente favor porfa gracias hola total totales general generales actual actuales
    nuevo nueva nuevos nuevas ultimo ultima ultimos ultimas primer primero primera segun entre sobre bajo hasta desde durante
    cuando donde adonde quien quienes cual cuales cuanto cuanta cuantos cuantas porque pues entonces tambien ademas aunque mejor
    mejores peor peores mayor mayores menor menores bien mal grande grandes pequeno pequenos esta estan estaba estuvo estamos
    fue fueron fuimos sera seran seria serian puede pueden quedan queda quedo vendio vendieron vendimos vendemos venden vende
    rota rotan giran gira lento lenta lentos lentas rapido rapida rapidos rapidas despacio velocidad rapidez
    mijo mija parce parcero parcera bro hermano amigo mano viejo viejito chino china oiga oye mire ome ey
    esta semana mes anio ano dia dias semanas meses quincena trimestre hora horas fecha periodo rango van vamos voy vas ir iran ira iba
    ser soy eres somos son estoy estas estamos estan hacen haces hago haga hagan hacemos debo debes debemos deben deberia deberiamos
    tocaria toca tendria tendriamos tendran tendremos tendra tenga tengan podrian podriamos pueda puedan sale salen salio salieron entra
    entran entro entraron llega llegan llego llegaron quedara quedaran queden quedamos paso pasa pasan pasaron ocurrio ocurre sucede
    sucedio mira miren mire vea veo ven vemos busco busca buscan encontrar encuentro encuentra necesitamos necesita necesitan quisiera
    quisieramos gustaria sirve sirven sirvio funciona funcionan significa significan
    recibe recibes reciben recibio recibimos envia envian enviamos envio enviaron manda mandan mando despacha despachan despacho traslada trasladan
    trasladamos mueve mueven movio movieron movimos compramos compras compra comprado compradas ganamos ganancia gano""".split()
)
# Las palabras con que el glosario nombra sus términos («modelos», «intervalo», «cobertura») son palabras reales: no se corrigen hacia otra parecida («modelos» → «módulos»).
_PALABRAS_DEL_GLOSARIO = frozenset(t for g in GLOSARIO for t in L.limpio(g.nombre).split() if len(t) >= 5)
_COMUNES = _COMUNES | VERBOS_TAREAS | _PALABRAS_DEL_GLOSARIO | frozenset("clave contrasena password sesion sesiones modelos modelo algoritmo algoritmos".split())
_PARECE_VERBO = re.compile(r"(ar|er|ir|ando|iendo|yendo|arse|erse|irse)$")  # infinitivos y gerundios no son nombres de productos
# Abreviaturas y grafías de chat que se escriben mucho.
_ABREVIATURAS = {
    "q": "que", "k": "que", "xq": "porque", "pq": "porque", "porq": "porque", "tb": "tambien", "tmb": "tambien", "tambn": "tambien",
    "estock": "stock", "estok": "stock", "stok": "stock", "vtas": "ventas", "inv": "inventario", "prod": "producto", "prods": "productos", "qeu": "que",
}
_CODIGO = re.compile(r"\b([a-z]{2,6})[\s\-_.]?(\d{1,5})\b")


@dataclass(frozen=True, slots=True)
class SedeInfo:
    id: int
    nombre: str
    ciudad: str | None
    activa: bool
    distintivas: tuple[str, ...]
    ciudad_tokens: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CategoriaInfo:
    id: int
    nombre: str
    activa: bool
    tokens: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProductoInfo:
    id: int
    codigo: str
    nombre: str
    categoria_id: int
    activo: bool
    tokens: tuple[str, ...]


@dataclass
class Directorio:
    """Sedes, categorías y productos de la empresa, listos para comparar con el texto de la pregunta."""

    sedes: list[SedeInfo]
    categorias: list[CategoriaInfo]
    productos: list[ProductoInfo]
    indice: dict[str, set[int]] = field(default_factory=dict)  # palabra del nombre de producto -> posiciones en ``productos``
    por_codigo: dict[str, ProductoInfo] = field(default_factory=dict)
    vocabulario: set[str] = field(default_factory=set)

    def sede(self, sede_id: int) -> SedeInfo | None:
        return next((s for s in self.sedes if s.id == sede_id), None)

    def categoria(self, categoria_id: int) -> CategoriaInfo | None:
        return next((c for c in self.categorias if c.id == categoria_id), None)

    def producto(self, producto_id: int) -> ProductoInfo | None:
        return next((p for p in self.productos if p.id == producto_id), None)


def _tokens_nombre(texto: str) -> tuple[str, ...]:
    return tuple(t for t in L.limpio(texto).split() if t not in L.PALABRAS_VACIAS and (len(t) > 1 or t.isdigit()))


def armar_directorio(sedes: list[Sede], categorias: list[Categoria], productos: list[Producto]) -> Directorio:
    infos_sede = []
    for s in sedes:
        propios = _tokens_nombre(s.nombre)
        distintivas = tuple(t for t in propios if t not in _GENERICAS_SEDE) or propios
        infos_sede.append(SedeInfo(s.id, s.nombre, s.ciudad, s.activa, distintivas, _tokens_nombre(s.ciudad or "")))
    infos_cat = [CategoriaInfo(c.id, c.nombre, c.activa, _tokens_nombre(c.nombre)) for c in categorias]
    infos_prod = [ProductoInfo(p.id, p.codigo, p.nombre, p.categoria_id, p.activo, _tokens_nombre(p.nombre)) for p in productos]
    d = Directorio(infos_sede, infos_cat, infos_prod)
    for posicion, p in enumerate(infos_prod):
        d.por_codigo[L.compacto(p.codigo)] = p
        for t in p.tokens:
            d.indice.setdefault(t, set()).add(posicion)
    d.vocabulario = set(d.indice)
    for s in infos_sede:
        d.vocabulario.update(s.distintivas)
        d.vocabulario.update(s.ciudad_tokens)
    for c in infos_cat:
        d.vocabulario.update(c.tokens)
    return d


async def cargar_directorio(db: AsyncSession, ctx: Contexto) -> Directorio:
    sedes = (await db.scalars(select(Sede).where(Sede.empresa_id == ctx.empresa_id).order_by(Sede.nombre))).all()
    categorias = (await db.scalars(select(Categoria).where(Categoria.empresa_id == ctx.empresa_id).order_by(Categoria.nombre))).all()
    productos = (await db.scalars(select(Producto).where(Producto.empresa_id == ctx.empresa_id).order_by(Producto.nombre))).all()
    return armar_directorio(list(sedes), list(categorias), list(productos))


@dataclass
class Entidades:
    sedes: list[SedeInfo] = field(default_factory=list)
    todas_las_sedes: bool = False
    categorias: list[CategoriaInfo] = field(default_factory=list)
    productos: list[ProductoInfo] = field(default_factory=list)
    producto_exacto: bool = False
    sin_resolver: list[str] = field(default_factory=list)  # palabras que parecen un producto pero no coinciden con ninguno
    periodo: L.Periodo | None = None
    periodo_b: L.Periodo | None = None  # segundo periodo cuando piden comparar («compara octubre con septiembre»)
    no_encontrado: list[tuple[str, str]] = field(default_factory=list)  # (tipo, texto) de lo que nombraron y no existe: sede, categoria, producto
    horizonte: int | None = None
    limite: int | None = None
    numero: int | None = None
    prioridad: str | None = None
    tipo_alerta: str | None = None
    estado_alerta: str | None = None  # "resuelta" cuando preguntan por las ya cerradas
    estado_traslado: str | None = None
    estado_recomendacion: str | None = None
    tipo_recomendacion: str | None = None
    orden: str | None = None  # "asc" (menos, peor) | "desc" (más, mejor)
    agrupar: str = "dia"  # dia | semana | mes | dia_semana
    pronombre_producto: bool = False
    pronombre_sede: bool = False
    seguimiento: bool = False
    frase: str = ""  # frase completa normalizada y corregida (con cifras y fechas)
    texto: str = ""  # frase normalizada sin las partes ya interpretadas (fechas, cantidades)

    @property
    def producto_unico(self) -> ProductoInfo | None:
        return self.productos[0] if len(self.productos) == 1 else None


# ------------------------------------------------------------------------------------------------- sedes y categorías


def _coincide(palabras: tuple[str, ...], consulta: list[str]) -> list[int] | None:
    """Posiciones de ``consulta`` que cubren TODAS las palabras; ``None`` si alguna falta."""
    usadas: list[int] = []
    for palabra in palabras:
        mejor = max(((L.similitud(q, palabra), i) for i, q in enumerate(consulta) if q == palabra or q not in _SEGURAS), default=(0.0, -1))
        if mejor[0] < 0.8:
            return None
        usadas.append(mejor[1])
    return usadas


def _buscar_sedes(d: Directorio, consulta: list[str]) -> tuple[list[SedeInfo], set[int]]:
    puntuadas: list[tuple[int, SedeInfo, list[int]]] = []
    for s in d.sedes:
        usadas = _coincide(s.distintivas, consulta) if s.distintivas else None
        if usadas is not None:
            puntuadas.append((len(s.distintivas), s, usadas))
    if not puntuadas:
        # Sin coincidir el nombre, la ciudad también identifica la sede («ventas en Medellín»).
        for s in d.sedes:
            usadas = _coincide(s.ciudad_tokens, consulta) if s.ciudad_tokens else None
            if usadas is not None:
                puntuadas.append((1, s, usadas))
    if not puntuadas:
        return [], set()
    mayor = max(p[0] for p in puntuadas)
    elegidas = [p for p in puntuadas if p[0] == mayor] if mayor > 1 or len(puntuadas) == 1 else puntuadas
    consumidas = {i for _, _, usadas in elegidas for i in usadas}
    elegidas.sort(key=lambda x: min(x[2]))  # en el orden en que la persona las nombró («de Norte a Sur»)
    return [s for _, s, _ in elegidas], consumidas


def _buscar_categorias(d: Directorio, consulta: list[str]) -> tuple[list[CategoriaInfo], set[int]]:
    """Categorías que la frase nombra. Basta una palabra propia de la categoría («bicicletas» → «Bicicletas eléctricas»);
    una palabra compartida por varias («eléctricos») solo cuenta si la frase la acompaña del resto del nombre."""
    por_palabra: dict[str, int] = {}  # en cuántas categorías aparece cada palabra (sin distinguir género ni plural)
    for c in d.categorias:
        for t in set(c.tokens):
            por_palabra[t] = sum(1 for o in d.categorias if any(L.similitud(t, u) >= 0.9 for u in o.tokens))
    completas: list[tuple[int, CategoriaInfo, set[int]]] = []
    parciales: list[tuple[int, CategoriaInfo, set[int]]] = []
    for c in d.categorias:
        if not c.tokens:
            continue
        cubiertas: set[int] = set()
        propias = 0
        for t in c.tokens:
            mejor = max(((L.similitud(q, t), i) for i, q in enumerate(consulta)), default=(0.0, -1))
            if mejor[0] >= 0.8:
                cubiertas.add(mejor[1])
                if por_palabra.get(t, 0) == 1 and len(t) >= 4:
                    propias += 1
        if not cubiertas:
            continue
        if len(cubiertas) >= len(set(c.tokens)):
            completas.append((len(c.tokens), c, cubiertas))
        elif propias:
            parciales.append((propias, c, cubiertas))
    elegidas = completas or parciales
    if not elegidas:
        return [], set()
    mayor = max(n for n, _, _ in elegidas)
    ganadoras = [(c, usadas) for n, c, usadas in elegidas if n == mayor]
    return [c for c, _ in ganadoras], {i for _, usadas in ganadoras for i in usadas}


# ------------------------------------------------------------------------------------------------------ productos


def _buscar_productos(d: Directorio, texto_base: str, consulta: list[str]) -> tuple[list[ProductoInfo], bool, list[str], list[str]]:
    """Productos que la frase nombra: por código exacto o por las palabras del nombre. Devuelve también las palabras que
    parecían un producto pero no coincidieron con ninguno y las palabras de la frase que sí coincidieron con algún nombre."""
    por_codigo: list[ProductoInfo] = []
    for m in _CODIGO.finditer(texto_base):
        producto = d.por_codigo.get(m.group(1) + m.group(2)) or d.por_codigo.get(m.group(1) + m.group(2).zfill(3))
        if producto and producto not in por_codigo:
            por_codigo.append(producto)
    if por_codigo:
        return por_codigo, True, [], []

    contenido = [q for q in consulta if q not in L.PALABRAS_VACIAS and (len(q) >= 3 or any(c.isdigit() for c in q))]
    if not contenido or not d.productos:
        return [], False, [], []

    # Para cada palabra de la frase: qué palabras de nombres de producto se le parecen.
    similares: dict[str, dict[str, float]] = {}
    for q in contenido:
        # Una palabra corriente del dominio («costo», «ventas») no se confunde con un nombre parecido («corte»): exige igualdad o misma raíz.
        minimo = 0.95 if q in _CONOCIDAS else 0.8
        for palabra in d.indice:
            s = L.similitud(q, palabra)
            if s >= minimo:
                similares.setdefault(q, {})[palabra] = s
    reconocidas = [q for q in contenido if q in similares]
    sin_resolver = [q for q in contenido if q not in similares]
    if not reconocidas or all(q in _ADJETIVOS_DEBILES for q in reconocidas):
        return [], False, sin_resolver, []

    total = len(d.productos)
    # Una palabra que está en el nombre de muchísimos productos («eléctrica») no basta para decir de cuál se habla.
    umbral_generica = max(5, total // 5)
    def alcance_de(q: str) -> int:  # a cuántos productos apunta la palabra, contando todas las variantes que se le parecen
        return len(set().union(*(d.indice[p] for p in similares[q])))

    if not any(alcance_de(q) <= umbral_generica for q in reconocidas):
        return [], False, sin_resolver, []
    peso = {q: math.log(1 + total / max(1, min(len(d.indice[p]) for p in similares[q]))) for q in reconocidas}
    suma_pesos = sum(peso.values())

    candidatos: set[int] = set()
    for q in reconocidas:
        for p in similares[q]:
            candidatos |= d.indice[p]

    puntuados: list[tuple[float, float, int]] = []
    for posicion in candidatos:
        producto = d.productos[posicion]
        propios = set(producto.tokens)
        cubierto = 0.0
        usadas_del_producto: set[str] = set()
        for q in reconocidas:
            coincidencias = [(s, p) for p, s in similares[q].items() if p in propios]
            if coincidencias:
                s, p = max(coincidencias)
                cubierto += peso[q] * s
                usadas_del_producto.add(p)
        cobertura = cubierto / suma_pesos
        precision = len(usadas_del_producto) / max(1, len(propios))
        puntuados.append((cobertura, precision, posicion))
    puntuados.sort(key=lambda t: (-t[0], -t[1], d.productos[t[2]].nombre))
    mejor_cobertura = puntuados[0][0]
    if mejor_cobertura < 0.5:
        return [], False, sin_resolver, []
    empatados = [t for t in puntuados if t[0] >= mejor_cobertura - 0.001]
    exactos = [t for t in empatados if t[1] >= 0.999 and t[0] >= 0.999]
    if exactos:
        return [d.productos[t[2]] for t in exactos], True, sin_resolver, reconocidas
    return [d.productos[t[2]] for t in empatados[:_MAXIMO_CANDIDATOS]], False, sin_resolver, reconocidas


# --------------------------------------------------------------------------------------------------- filtros simples


def _filtros(c: str, e: Entidades) -> None:
    if re.search(r"\bcritic\w+|\burgent\w+", c):
        e.prioridad = "critica"
    elif re.search(r"\bprioridad alta\b|\balertas? altas?\b|\bprioridad (media|baja)\b", c):
        e.prioridad = "alta" if "alta" in c else ("media" if "media" in c else "baja")
    if re.search(r"\balertas? (ya )?(resuelt\w+|cerrad\w+|solucionad\w+|atendid\w+)|\b(resuelt|cerrad|solucionad|atendid)[oa]s\b|\bhistorial de alertas\b", c):
        e.estado_alerta = "resuelta"
    if re.search(r"\brie?sgo\b|\bdesabastec\w+|\bagotamient\w+|\bquiebre\w*|\bfaltantes?\b", c):
        e.tipo_alerta = "riesgo_desabastecimiento"
    elif re.search(r"\bexces\w+|\bsobre ?stock\b", c):
        e.tipo_alerta = "inventario_excesivo"
    elif re.search(r"\binventario bajo\b|\bstock bajo\b|\bbajo stock\b|\bbajas?\b", c):
        e.tipo_alerta = "inventario_bajo"
    elif re.search(r"\brequiere\w* revision\b", c):
        e.tipo_alerta = "requiere_revision"
    for patron, estado in (
        (r"\bsolicitad\w+", "solicitado"), (r"\baprobad\w+", "aprobado"), (r"\bconfirmad\w+", "confirmado"),
        (r"\brechazad\w+", "rechazado"), (r"\bcancelad\w+", "cancelado"),
    ):
        if re.search(patron, c):
            e.estado_traslado = estado
            break
    for patron, estado in (
        (r"\bpendient\w+|\bpor (revisar|aprobar|atender)\b", "pendiente"), (r"\baprobad\w+", "aprobada"),
        (r"\brechazad\w+", "rechazada"), (r"\bejecutad\w+", "ejecutada"), (r"\breemplazad\w+", "reemplazada"),
    ):
        if re.search(patron, c):
            e.estado_recomendacion = estado
            break
    if re.search(r"\btraslad\w+|\bmover\b|\bmandar\b|\benviar\b|\bredistribu\w+|\bentre sedes\b|\bpasar de\b", c):
        e.tipo_recomendacion = "traslado"
    elif re.search(r"\bcompra\w*|\bcomprar\b|\bpedir\b|\bpedido\w*|\breponer\b|\breabastec\w+|\bsurtir\b|\bresurtir\b|\breposicion\b", c):
        e.tipo_recomendacion = "reabastecimiento"
    if re.search(r"\bmenos\b|\bmenor(es)?\b|\bpeor(es)?\b|\bpoco\b|\bmas bajos?\b", c):
        e.orden = "asc"
    elif re.search(r"\bmas\b|\bmayor(es)?\b|\bmejor(es)?\b|\btop\b|\bmucho\b", c):
        e.orden = "desc"
    if re.search(r"\bpor mes\b|\bmensual\w*|\bmes (con|que|se)\b|\bque mes\b|\bmejor mes\b|\bpeor mes\b|\bmeses\b", c):
        e.agrupar = "mes"
    elif re.search(r"\bpor semana\b|\bsemanal\w*|\bque semana\b|\bmejor semana\b|\bpeor semana\b", c):
        e.agrupar = "semana"
    elif re.search(r"\bque dia\b|\bmejor dia\b|\bpeor dia\b|\bdia (que )?(mas|menos)\b", c) and e.periodo and not re.search(r"\bdias? de la semana\b", c):
        e.agrupar = "dia"  # «¿qué día de octubre se vendió más?»: una fecha concreta, no el día de la semana
    elif re.search(r"\bdias? de la semana\b|\bque dia\b|\bmejor dia\b|\bpeor dia\b|\bdia (que )?(mas|menos)\b", c):
        e.agrupar = "dia_semana"


# --------------------------------------------------------------------------------------------------------- resolver


_PIDE_COMPARAR = re.compile(r"\bcompar\w+|\bversus\b|\bvs\b|\bcontra\b|\bfrente a\b|\brespecto (a|de)\b|\bdiferencia entre\b|\bcambio entre\b|\b(vendimos|vendio|vendieron|facturamos|crecimos|bajamos|subimos|ventas?)\b.*\b(mas|menos|mejor|peor)\b.*\bque\b")
_ANTES_DE_SEDE = frozenset({"de", "del", "la", "el", "en", "a", "al"})


def _no_encontrado(d: Directorio, e: Entidades, texto_base: str, consulta: list[str], sin_resolver: list[str]) -> list[tuple[str, str]]:
    """Lo que la persona nombró y no existe en su empresa: un código de producto («BAT-999») o una sede/categoría que no está entre las suyas.
    Sirve para decirlo, en vez de contestar con los datos de toda la empresa como si no hubieran dicho nada."""
    salida: list[tuple[str, str]] = []
    prefijos = {re.match(r"[a-z]+", k).group(0) for k in d.por_codigo if re.match(r"[a-z]+", k)}
    for m in _CODIGO.finditer(texto_base):
        if m.group(1) in prefijos and not (d.por_codigo.get(m.group(1) + m.group(2)) or d.por_codigo.get(m.group(1) + m.group(2).zfill(3))):
            salida.append(("producto", f"{m.group(1).upper()}-{m.group(2)}"))
    desconocidas = {q for q in sin_resolver if q not in _CONOCIDAS and q not in L.PALABRAS_VACIAS and not any(c.isdigit() for c in q) and len(q) >= 3}
    for i, q in enumerate(consulta[:-1]):
        j = i + 1
        while j < len(consulta) - 1 and consulta[j] in _ANTES_DE_SEDE:
            j += 1
        siguiente = consulta[j]
        if siguiente not in desconocidas:
            continue
        if q in _GENERICAS_SEDE - {"venta", "bodega", "local", "punto"} and not e.sedes:
            salida.append(("sede", siguiente))
        elif q in ("categoria", "categorias", "linea") and not e.categorias:
            salida.append(("categoria", siguiente))
    return list(dict.fromkeys(salida))


def resolver(d: Directorio, mensaje: str, hoy: date) -> tuple[Entidades, list[str]]:
    """Interpreta la pregunta. Devuelve las entidades y las palabras (ya corregidas) con las que se clasifica la intención."""
    e = Entidades()
    b = L.base(mensaje).lstrip(" ¿¡?!.,;:-—–\"'«»“”()[]")  # «¿Y en la Sede Norte?» empieza igual que «y en la sede norte»
    e.seguimiento = bool(_ENCABEZADO_SEGUIMIENTO.search(b))
    e.pronombre_producto = bool(_PRONOMBRE_PRODUCTO.search(b))
    e.pronombre_sede = bool(_PRONOMBRE_SEDE.search(b))
    e.todas_las_sedes = bool(_TODAS_LAS_SEDES.search(b))

    e.numero, b2 = L.extraer_numero_documento(b)
    e.periodo, b2 = L.extraer_periodo(b2, hoy)
    if e.periodo and _PIDE_COMPARAR.search(b):
        e.periodo_b, b2 = L.extraer_periodo(b2, hoy)
        if e.periodo_b and e.periodo_b.desde > e.periodo.desde:  # el más reciente va primero
            e.periodo, e.periodo_b = e.periodo_b, e.periodo
    e.horizonte, b2 = L.extraer_horizonte(b2)
    e.limite, b2 = L.extraer_limite(b2)

    cadena = L.limpio(b2)
    consulta = [_ABREVIATURAS.get(t, t) for t in cadena.split()]

    # Corrige errores de digitación solo en palabras que NO son nombres propios del negocio.
    protegidas = d.vocabulario
    consulta = [q if q in protegidas or q in _SEGURAS else L.corregir_palabra(q, VOCABULARIO_CORRECCION) for q in consulta]
    cadena = " ".join(consulta)

    e.sedes, usadas = _buscar_sedes(d, consulta)
    if e.sedes:
        e.todas_las_sedes = False
    restantes = [q for i, q in enumerate(consulta) if i not in usadas]
    e.categorias, usadas_cat = _buscar_categorias(d, restantes)
    palabras_categoria = {restantes[i] for i in usadas_cat}
    e.productos, e.producto_exacto, sin_resolver, reconocidas = _buscar_productos(d, b2, restantes)

    # Si todas las palabras que apuntan a productos son las de la categoría nombrada («bicicletas», «baterías»),
    # la persona habla de la categoría completa y no de productos concretos.
    if e.categorias and e.productos and not e.producto_exacto and set(reconocidas) <= palabras_categoria:
        e.productos = []
    if len(e.productos) == 1 and e.categorias and not e.producto_exacto:
        e.categorias = []  # un producto concreto pesa más que la categoría
    if e.productos:
        e.sin_resolver = []
    else:
        e.sin_resolver = [q for q in sin_resolver if q not in _CONOCIDAS and q not in palabras_categoria and not _PARECE_VERBO.search(q)][:4]

    e.no_encontrado = _no_encontrado(d, e, b2, consulta, sin_resolver)

    # Frase completa (con cifras y fechas intactas) y corregida: es la que se usa para identificar la intención.
    e.frase = " ".join(q if q in protegidas or q in _SEGURAS else L.corregir_palabra(q, VOCABULARIO_CORRECCION) for q in (_ABREVIATURAS.get(t, t) for t in L.limpio(b).split()))

    _filtros(cadena, e)
    e.texto = cadena
    return e, consulta


# Se construye una sola vez: palabras del dominio y de los ejemplos de pregunta.
def _vocabulario_correccion() -> frozenset[str]:
    from app.service.asistente.catalogo import INTENCIONES, VOCABULARIO_BASE

    palabras = set(VOCABULARIO_BASE)
    for i in INTENCIONES:
        for ejemplo in i.ejemplos:
            palabras.update(t for t in L.limpio(ejemplo).split() if len(t) >= 5 and not any(c.isdigit() for c in t))
    return frozenset(palabras)


VOCABULARIO_CORRECCION = _vocabulario_correccion()


_CONOCIDAS = VOCABULARIO_CORRECCION | _COMUNES
_SEGURAS = _COMUNES | L.PALABRAS_VACIAS  # palabras corrientes: nunca se «corrigen» hacia una del dominio
