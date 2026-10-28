"""Mide el tiempo de respuesta de un usuario solo, endpoint por endpoint (RNF-011 y RNF-013).

Complementa a Locust: Locust mide muchos usuarios a la vez; este script mide cuánto tarda cada consulta cuando nadie
más usa el sistema, y cómo cambia ese tiempo al crecer el volumen de datos (ejecútelo antes y después de
``inflar_base.sh``).

    export INVENTIA_EMAIL=...  INVENTIA_PASSWORD=...        # administrador de una base de PRUEBA
    python medir_latencias.py http://127.0.0.1:8000 resultados/latencias_x1.json [--repeticiones 15]

Para cada consulta se hacen ``--repeticiones`` peticiones consecutivas (la primera se descarta como calentamiento) y se
informan mediana, percentil 95 y máximo en milisegundos. Las exportaciones pesadas (Excel/CSV de todo el historial) se
repiten solo 3 veces. Solo hace lecturas.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

import requests

DESDE_TODO = "2020-01-01"  # antes de cualquier dato: pide todo el historial disponible


def _percentil(valores: list[float], p: float) -> float:
    ordenados = sorted(valores)
    k = min(len(ordenados) - 1, max(0, round(p / 100 * (len(ordenados) - 1))))
    return ordenados[k]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("host")
    ap.add_argument("salida", type=Path)
    ap.add_argument("--repeticiones", type=int, default=15)
    a = ap.parse_args()
    host = a.host.rstrip("/")
    email, clave = os.environ.get("INVENTIA_EMAIL", ""), os.environ.get("INVENTIA_PASSWORD", "")
    if not email or not clave:
        print("Defina INVENTIA_EMAIL e INVENTIA_PASSWORD.", file=sys.stderr)
        return 2
    r = requests.post(f"{host}/api/auth/login", json={"email": email, "password": clave}, timeout=30)
    r.raise_for_status()
    cab = {"Authorization": f"Bearer {r.json()['access_token']}"}

    def obtener(ruta: str, **params):
        return requests.get(host + ruta, params=params or None, headers=cab, timeout=300)

    # páginas más profundas posibles: el costo de paginar crece con el desplazamiento
    ultimas = {}
    for ruta in ("/api/ventas", "/api/movimientos", "/api/auditoria"):
        ultimas[ruta] = obtener(ruta, tamano=50).json()["paginas"]

    ligeras = [
        ("Panel (30 días)", "/api/dashboard", {"dias": 30}),
        ("Panel (365 días)", "/api/dashboard", {"dias": 365}),
        ("Existencias consolidadas", "/api/inventario/consolidado", {"tamano": 50}),
        ("Alertas", "/api/alertas", {"tamano": 50}),
        ("Ventas, primera página", "/api/ventas", {"tamano": 50}),
        ("Ventas, última página", "/api/ventas", {"tamano": 50, "pagina": ultimas["/api/ventas"]}),
        ("Movimientos, primera página", "/api/movimientos", {"tamano": 50}),
        ("Movimientos, última página", "/api/movimientos", {"tamano": 50, "pagina": ultimas["/api/movimientos"]}),
        ("Movimientos, todo el historial", "/api/movimientos", {"tamano": 50, "desde": DESDE_TODO}),
        ("Auditoría, primera página", "/api/auditoria", {"tamano": 50}),
        ("Auditoría, última página", "/api/auditoria", {"tamano": 50, "pagina": ultimas["/api/auditoria"]}),
        ("Reporte de ventas en pantalla (todo el historial)", "/api/reportes/ventas", {"formato": "json", "desde": DESDE_TODO}),
        ("Reporte de movimientos en pantalla (todo el historial)", "/api/reportes/movimientos", {"formato": "json", "desde": DESDE_TODO}),
        ("Reporte de ventas en PDF (1.000 filas)", "/api/reportes/ventas", {"formato": "pdf", "desde": DESDE_TODO}),
    ]
    pesadas = [
        ("Reporte de ventas en CSV (todo el historial)", "/api/reportes/ventas", {"formato": "csv", "desde": DESDE_TODO}),
        ("Reporte de ventas en Excel (todo el historial)", "/api/reportes/ventas", {"formato": "xlsx", "desde": DESDE_TODO}),
    ]

    resultados = []
    for nombre, ruta, params in ligeras + pesadas:
        n = 3 if (nombre, ruta, params) in pesadas else a.repeticiones
        tiempos, bytes_, codigo = [], 0, None
        for i in range(n + 1):
            t0 = time.perf_counter()
            resp = obtener(ruta, **params)
            ms = (time.perf_counter() - t0) * 1000
            codigo, bytes_ = resp.status_code, len(resp.content)
            if i > 0:  # la primera petición calienta cachés y conexiones
                tiempos.append(ms)
        fila = {
            "consulta": nombre, "ruta": ruta, "parametros": params, "codigo": codigo, "repeticiones": n,
            "mediana_ms": round(statistics.median(tiempos), 1), "p95_ms": round(_percentil(tiempos, 95), 1),
            "maximo_ms": round(max(tiempos), 1), "bytes": bytes_,
        }
        resultados.append(fila)
        print(f"{nombre:<58} {codigo}  mediana {fila['mediana_ms']:>9.1f} ms   p95 {fila['p95_ms']:>9.1f} ms   {bytes_ / 1024:>9.1f} KiB")

    totales = {ruta: obtener(ruta, tamano=1).json()["total"] for ruta in ("/api/ventas", "/api/movimientos", "/api/auditoria")}
    informe = {"host": host, "filas": totales, "resultados": resultados}
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    a.salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
