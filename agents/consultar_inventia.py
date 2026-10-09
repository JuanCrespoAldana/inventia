"""Cliente de ejemplo para agentes de IA: consulta Inventia en modo solo lectura y arma un resumen.

    export INVENTIA_URL=http://localhost:8080        # o la URL donde corre el backend (por defecto http://localhost:8000)
    export INVENTIA_API_KEY=inv_...                  # llave creada en «Agentes de IA» (se muestra una sola vez)
    python agents/consultar_inventia.py

Solo usa la biblioteca estándar. La llave únicamente permite CONSULTAR (existencias, alertas, predicciones y
recomendaciones según los alcances concedidos): un agente no puede registrar movimientos ni aprobar nada. Las
recomendaciones siempre las decide una persona en la aplicación.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

URL = os.environ.get("INVENTIA_URL", "http://localhost:8000").rstrip("/")
LLAVE = os.environ.get("INVENTIA_API_KEY", "")


class ErrorInventia(Exception):
    pass


def consultar(ruta: str, **parametros) -> dict:
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
        raise ErrorInventia(f"{e.code} al consultar «{ruta}»: {detalle}") from e
    except urllib.error.URLError as e:
        raise ErrorInventia(f"No se pudo conectar con {URL}: {e.reason}") from e


def todas(ruta: str, tope: int = 500, **parametros) -> list[dict]:
    """Recorre todas las páginas de un listado (hasta `tope` filas)."""
    filas, pagina = [], 1
    while len(filas) < tope:
        datos = consultar(ruta, pagina=pagina, tamano=100, **parametros)
        filas += datos["items"]
        if pagina >= datos["paginas"]:
            break
        pagina += 1
    return filas[:tope]


def main() -> int:
    if not LLAVE:
        print("Defina la variable INVENTIA_API_KEY con la llave de acceso del agente.", file=sys.stderr)
        return 1
    try:
        yo = consultar("yo")
        print(f"Llave «{yo['nombre']}» · alcances: {', '.join(yo['alcances'])} · solo lectura: {yo['solo_lectura']}\n")

        if "alertas:leer" in yo["alcances"]:
            alertas = todas("alertas")
            criticas = [a for a in alertas if a["prioridad"] == "critica"]
            print(f"Alertas activas: {len(alertas)} ({len(criticas)} críticas)")
            for a in criticas[:5]:
                print(f"  - [{a['sede']}] {a['mensaje']}")

        if "inventario:leer" in yo["alcances"]:
            inventario = todas("inventario")
            agotados = [i for i in inventario if i["estado"] == "agotado"]
            print(f"\nExistencias: {len(inventario)} combinaciones producto-sede, {len(agotados)} agotadas")

        if "predicciones:leer" in yo["alcances"]:
            pred = consultar("predicciones", tamano=5)
            print(f"\nÚltima predicción: datos hasta {pred['fecha_corte']} (son estimaciones, no ventas)")
            for p in pred["items"]:
                print(f"  - {p['producto']} en {p['sede']}: {p['demanda_estimada']} u. entre {p['limite_inferior']} y {p['limite_superior']} (confianza {p['confianza']})")

        if "recomendaciones:leer" in yo["alcances"]:
            recs = todas("recomendaciones")
            print(f"\nRecomendaciones pendientes de aprobación humana: {len(recs)}")
            for r in recs[:5]:
                print(f"  - ({r['prioridad']}) {r['tipo']}: {r['cantidad_sugerida']} u. de {r['producto']} en {r['sede']}")
    except ErrorInventia as e:
        print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
