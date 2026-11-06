"""Conector MCP de Inventia: deja que Claude (u otro asistente compatible con MCP) consulte el inventario.

El asistente habla con este programa por la entrada y la salida estándar (protocolo MCP, JSON-RPC por líneas) y este
programa consulta la API de Inventia (`/api/agentes/*`) con la llave del agente. Es de SOLO LECTURA: no existe ninguna
herramienta que registre, apruebe o cambie algo, y la llave tampoco lo permite.

    INVENTIA_URL=http://localhost:8000            (por defecto)
    INVENTIA_API_KEY=inv_...                      (llave creada en Administración → Agentes de IA)
    python agents/servidor_mcp.py

Normalmente no se ejecuta a mano: Claude Desktop lo inicia según `claude_desktop_config.json` (ver agents/README.md).
Solo usa la biblioteca estándar de Python (la misma versión que el backend).
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

VERSION = "1.0.0"
VERSIONES_PROTOCOLO = ("2025-06-18", "2025-03-26", "2024-11-05")
URL = os.environ.get("INVENTIA_URL", "http://localhost:8000").rstrip("/")
LLAVE = os.environ.get("INVENTIA_API_KEY", "")
PAGINAS_MAXIMAS_CON_ESTADO = 10

INSTRUCCIONES = (
    "Inventia es un sistema de inventario multisede. Estas herramientas solo CONSULTAN: no pueden registrar movimientos, "
    "aprobar recomendaciones ni cambiar nada. Responda con lo que devuelvan las herramientas y no invente cifras. "
    "Las predicciones son estimaciones con margen de error: mencione su confianza y sus advertencias. Las recomendaciones "
    "están pendientes de aprobación humana: preséntelas como sugerencias, nunca como decisiones tomadas."
)


class ErrorInventia(Exception):
    pass


def consultar(ruta: str, **parametros) -> dict:
    if not LLAVE:
        raise ErrorInventia("Falta la llave: defina INVENTIA_API_KEY en la configuración del conector.")
    consulta = urllib.parse.urlencode({k: v for k, v in parametros.items() if v is not None})
    peticion = urllib.request.Request(f"{URL}/api/agentes/{ruta}" + (f"?{consulta}" if consulta else ""), headers={"X-API-Key": LLAVE})
    try:
        with urllib.request.urlopen(peticion, timeout=30) as respuesta:
            return json.load(respuesta)
    except urllib.error.HTTPError as e:
        try:
            detalle = json.load(e).get("detail", "")
        except Exception:  # noqa: BLE001
            detalle = ""
        if e.code == 401:
            detalle = detalle or "La llave no es válida, venció o fue revocada."
        elif e.code == 403:
            detalle = detalle or "La llave no tiene permiso para consultar eso."
        raise ErrorInventia(f"Inventia respondió {e.code} en «{ruta}»: {detalle}") from e
    except urllib.error.URLError as e:
        raise ErrorInventia(f"No se pudo conectar con Inventia en {URL}: {e.reason}. ¿Está encendido el programa?") from e


def _entero(argumentos: dict, nombre: str, defecto: int | None, minimo: int, maximo: int) -> int | None:
    valor = argumentos.get(nombre)
    if valor is None:
        return defecto
    if isinstance(valor, bool) or not isinstance(valor, int | float) or int(valor) != valor:
        raise TypeError(f"«{nombre}» debe ser un número entero.")
    if not minimo <= valor <= maximo:
        raise ValueError(f"«{nombre}» debe estar entre {minimo} y {maximo}.")
    return int(valor)


def _texto(argumentos: dict, nombre: str, maximo: int) -> str | None:
    valor = argumentos.get(nombre)
    if valor is None or valor == "":
        return None
    if not isinstance(valor, str):
        raise TypeError(f"«{nombre}» debe ser texto.")
    return valor.strip()[:maximo] or None


def _filtros_comunes(argumentos: dict) -> dict:
    return {"sede_id": _entero(argumentos, "sede_id", None, 1, 2_147_483_647)}


def _pagina(argumentos: dict) -> dict:
    return {"pagina": _entero(argumentos, "pagina", 1, 1, 100_000), "tamano": _entero(argumentos, "tamano", 20, 1, 50)}


def herramienta_yo(_argumentos: dict) -> dict:
    return consultar("yo")


def herramienta_inventario(argumentos: dict) -> dict:
    filtros = {**_filtros_comunes(argumentos), "q": _texto(argumentos, "q", 100)}
    estado = _texto(argumentos, "estado", 20)
    if estado is not None and estado not in ("agotado", "bajo", "excesivo", "normal"):
        raise ValueError("«estado» debe ser agotado, bajo, excesivo o normal.")
    paginado = _pagina(argumentos)
    if estado is None:
        return consultar("inventario", **filtros, **paginado)

    coincidencias, revisadas, pagina, hay_mas = [], 0, 1, False
    while pagina <= PAGINAS_MAXIMAS_CON_ESTADO:
        datos = consultar("inventario", **filtros, pagina=pagina, tamano=100)
        revisadas += len(datos["items"])
        coincidencias += [fila for fila in datos["items"] if fila["estado"] == estado]
        if pagina >= datos["paginas"]:
            break
        pagina += 1
    else:
        hay_mas = True
    resultado = {"estado": estado, "total_coincidencias": len(coincidencias), "filas_revisadas": revisadas,
                 "items": coincidencias[: paginado["tamano"]]}
    if len(coincidencias) > paginado["tamano"]:
        resultado["aviso"] = f"Se muestran {paginado['tamano']} de {len(coincidencias)} coincidencias; pida un «tamano» mayor o filtre por sede o producto."
    if hay_mas:
        resultado["aviso_parcial"] = f"Solo se revisaron las primeras {revisadas} existencias; filtre por sede o producto para revisar el resto."
    return resultado


def herramienta_alertas(argumentos: dict) -> dict:
    tipo = _texto(argumentos, "tipo", 30)
    return consultar("alertas", **_filtros_comunes(argumentos), tipo=tipo, **_pagina(argumentos))


def herramienta_predicciones(argumentos: dict) -> dict:
    return consultar("predicciones", **_filtros_comunes(argumentos), q=_texto(argumentos, "q", 100), **_pagina(argumentos))


def herramienta_recomendaciones(argumentos: dict) -> dict:
    return consultar("recomendaciones", **_filtros_comunes(argumentos), **_pagina(argumentos))


_SEDE = {"type": "integer", "minimum": 1, "description": "Identificador de la sede (sede_id) para limitar la consulta. Si se omite, se consultan todas las que la llave permite."}
_BUSQUEDA = {"type": "string", "maxLength": 100, "description": "Texto a buscar en el nombre o el código del producto."}
_PAGINA = {"type": "integer", "minimum": 1, "default": 1, "description": "Número de página (empieza en 1)."}
_TAMANO = {"type": "integer", "minimum": 1, "maximum": 50, "default": 20, "description": "Filas por página (máximo 50)."}
_SOLO_LECTURA = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}

HERRAMIENTAS = {
    "quien_soy": {
        "titulo": "Permisos de la llave",
        "descripcion": "Muestra con qué nombre está registrada la llave, qué puede consultar (alcances) y si está limitada a una sede.",
        "esquema": {"type": "object", "properties": {}},
        "funcion": herramienta_yo,
    },
    "consultar_inventario": {
        "titulo": "Existencias por sede y producto",
        "descripcion": (
            "Lista las existencias (cantidad, stock mínimo y máximo) de cada producto en cada sede, con su estado: agotado, bajo "
            "(en o por debajo del mínimo), excesivo (sobre el máximo) o normal. Use «estado» para ver solo los agotados, los bajos, etc. "
            "Requiere el alcance inventario:leer."
        ),
        "esquema": {"type": "object", "properties": {
            "sede_id": _SEDE, "q": _BUSQUEDA,
            "estado": {"type": "string", "enum": ["agotado", "bajo", "excesivo", "normal"], "description": "Devuelve solo las existencias en ese estado."},
            "pagina": _PAGINA, "tamano": _TAMANO}},
        "funcion": herramienta_inventario,
    },
    "consultar_alertas": {
        "titulo": "Alertas de inventario activas",
        "descripcion": (
            "Lista las alertas activas con su prioridad (critica, alta, media o baja), el producto y la sede. Tipos: inventario_bajo, "
            "inventario_excesivo, riesgo_desabastecimiento y requiere_revision. Requiere el alcance alertas:leer."
        ),
        "esquema": {"type": "object", "properties": {
            "sede_id": _SEDE,
            "tipo": {"type": "string", "enum": ["inventario_bajo", "inventario_excesivo", "riesgo_desabastecimiento", "requiere_revision"], "description": "Filtra por tipo de alerta."},
            "pagina": _PAGINA, "tamano": _TAMANO}},
        "funcion": herramienta_alertas,
    },
    "consultar_predicciones": {
        "titulo": "Predicción de demanda",
        "descripcion": (
            "Devuelve la última predicción de demanda por producto y sede: demanda estimada, límites inferior y superior, confianza y "
            "advertencias. Son ESTIMACIONES, no ventas reales. Requiere el alcance predicciones:leer."
        ),
        "esquema": {"type": "object", "properties": {"sede_id": _SEDE, "q": _BUSQUEDA, "pagina": _PAGINA, "tamano": _TAMANO}},
        "funcion": herramienta_predicciones,
    },
    "consultar_recomendaciones": {
        "titulo": "Recomendaciones pendientes",
        "descripcion": (
            "Lista las recomendaciones de reposición o traslado que siguen pendientes de aprobación humana. Son sugerencias: ninguna se "
            "ha ejecutado. Requiere el alcance recomendaciones:leer."
        ),
        "esquema": {"type": "object", "properties": {"sede_id": _SEDE, "pagina": _PAGINA, "tamano": _TAMANO}},
        "funcion": herramienta_recomendaciones,
    },
}


def listar_herramientas() -> list[dict]:
    return [
        {"name": nombre, "title": h["titulo"], "description": h["descripcion"], "inputSchema": h["esquema"], "annotations": {"title": h["titulo"], **_SOLO_LECTURA}}
        for nombre, h in HERRAMIENTAS.items()
    ]


def llamar_herramienta(nombre: str, argumentos: dict) -> dict:
    try:
        datos = HERRAMIENTAS[nombre]["funcion"](argumentos)
        texto, con_error = json.dumps(datos, ensure_ascii=False, separators=(",", ":")), False
    except (ErrorInventia, ValueError, TypeError) as e:
        texto, con_error = str(e), True
    return {"content": [{"type": "text", "text": texto}], "isError": con_error}


class ErrorProtocolo(Exception):
    def __init__(self, codigo: int, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo


def atender(metodo: str, parametros: dict) -> dict:
    if metodo == "initialize":
        pedida = parametros.get("protocolVersion")
        return {
            "protocolVersion": pedida if pedida in VERSIONES_PROTOCOLO else VERSIONES_PROTOCOLO[0],
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "inventia", "title": "Inventia", "version": VERSION},
            "instructions": INSTRUCCIONES,
        }
    if metodo == "ping":
        return {}
    if metodo == "tools/list":
        return {"tools": listar_herramientas()}
    if metodo == "tools/call":
        nombre = parametros.get("name")
        if nombre not in HERRAMIENTAS:
            raise ErrorProtocolo(-32602, f"Herramienta desconocida: {nombre}")
        argumentos = parametros.get("arguments") or {}
        if not isinstance(argumentos, dict):
            raise ErrorProtocolo(-32602, "«arguments» debe ser un objeto.")
        return llamar_herramienta(nombre, argumentos)
    raise ErrorProtocolo(-32601, f"Método no soportado: {metodo}")


def responder(mensaje: dict) -> dict | None:
    if not isinstance(mensaje, dict) or "method" not in mensaje:
        return None
    identificador = mensaje.get("id")
    if identificador is None:
        return None  # notificación (p. ej. notifications/initialized): no se responde
    try:
        resultado = atender(mensaje["method"], mensaje.get("params") or {})
        return {"jsonrpc": "2.0", "id": identificador, "result": resultado}
    except ErrorProtocolo as e:
        return {"jsonrpc": "2.0", "id": identificador, "error": {"code": e.codigo, "message": str(e)}}


def escribir(mensaje: dict) -> None:
    sys.stdout.write(json.dumps(mensaje, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def main() -> int:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    if not LLAVE:
        print("Aviso: INVENTIA_API_KEY no está definida; las herramientas responderán con un error.", file=sys.stderr)
    for linea in sys.stdin:
        linea = linea.strip()
        if not linea:
            continue
        try:
            recibido = json.loads(linea)
        except json.JSONDecodeError:
            escribir({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "JSON no válido"}})
            continue
        for mensaje in recibido if isinstance(recibido, list) else [recibido]:
            respuesta = responder(mensaje)
            if respuesta is not None:
                escribir(respuesta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
