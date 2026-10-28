"""Verifica la consistencia del inventario después de una prueba de carga (RNF-014).

Comprueba, con consultas de solo lectura, que las operaciones simultáneas no dejaron datos inconsistentes:

  1. Ninguna existencia negativa.
  2. Cada movimiento cumple  saldo_posterior = saldo_anterior + delta.
  3. La cadena de movimientos de cada producto en cada sede es continua: el saldo anterior de un movimiento
     es igual al saldo posterior del movimiento previo (si dos operaciones hubieran leído el mismo saldo y
     escrito a la vez, la cadena se rompería: «actualización perdida»).
  4. El último saldo registrado coincide con la existencia actual.
  5. Ningún consecutivo de venta repetido dentro de una misma empresa.

Uso (desde la carpeta backend, con el entorno virtual del proyecto):

    export DATABASE_URL=postgresql+asyncpg://usuario:clave@localhost:5432/base_de_pruebas
    python ../infra/carga/verificar_consistencia.py            # imprime un informe
    python ../infra/carga/verificar_consistencia.py --json     # salida para guardar como evidencia

Código de salida 0 si todo es consistente y 1 si encuentra alguna violación.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

VERIFICACIONES: list[tuple[str, str, str]] = [
    (
        "existencias_negativas",
        "Existencias con cantidad negativa",
        "SELECT count(*) FROM inventario_sede WHERE cantidad < 0",
    ),
    (
        "movimientos_aritmetica",
        "Movimientos donde saldo_posterior ≠ saldo_anterior + delta",
        "SELECT count(*) FROM movimientos WHERE saldo_posterior <> saldo_anterior + delta",
    ),
    (
        "cadenas_rotas",
        "Movimientos cuyo saldo anterior no es el saldo posterior del movimiento previo (actualización perdida)",
        """
        SELECT count(*) FROM (
            SELECT saldo_anterior,
                   lag(saldo_posterior) OVER (PARTITION BY sede_id, producto_id ORDER BY id) AS previo
            FROM movimientos
        ) t
        WHERE previo IS NOT NULL AND saldo_anterior <> previo
        """,
    ),
    (
        "saldo_final_distinto_de_existencia",
        "Productos cuya existencia actual no coincide con el último saldo registrado",
        """
        SELECT count(*) FROM inventario_sede i
        JOIN LATERAL (
            SELECT saldo_posterior FROM movimientos m
            WHERE m.sede_id = i.sede_id AND m.producto_id = i.producto_id
            ORDER BY m.id DESC LIMIT 1
        ) ult ON true
        WHERE ult.saldo_posterior <> i.cantidad
        """,
    ),
    (
        "consecutivos_repetidos",
        "Consecutivos de venta repetidos dentro de una empresa",
        "SELECT count(*) FROM (SELECT empresa_id, numero FROM ventas GROUP BY 1, 2 HAVING count(*) > 1) t",
    ),
]

TOTALES: list[tuple[str, str]] = [
    ("existencias", "SELECT count(*) FROM inventario_sede"),
    ("movimientos", "SELECT count(*) FROM movimientos"),
    ("ventas", "SELECT count(*) FROM ventas"),
    ("entradas", "SELECT count(*) FROM entradas_inventario"),
]


async def verificar(url: str) -> dict:
    motor = create_async_engine(url)
    try:
        async with motor.connect() as con:
            totales = {nombre: (await con.execute(text(sql))).scalar_one() for nombre, sql in TOTALES}
            resultados = []
            for clave, descripcion, sql in VERIFICACIONES:
                violaciones = (await con.execute(text(sql))).scalar_one()
                resultados.append({"verificacion": clave, "descripcion": descripcion, "violaciones": int(violaciones)})
    finally:
        await motor.dispose()
    return {"totales": totales, "resultados": resultados, "consistente": all(r["violaciones"] == 0 for r in resultados)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="imprime el resultado como JSON")
    args = parser.parse_args()
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("Defina DATABASE_URL (base de pruebas).", file=sys.stderr)
        return 2
    informe = asyncio.run(verificar(url))
    if args.json:
        print(json.dumps(informe, ensure_ascii=False, indent=2))
    else:
        t = informe["totales"]
        print(f"Registros revisados: {t['existencias']} existencias, {t['movimientos']} movimientos, "
              f"{t['ventas']} ventas, {t['entradas']} entradas")
        for r in informe["resultados"]:
            print(f"  [{'OK' if r['violaciones'] == 0 else 'FALLA'}] {r['descripcion']}: {r['violaciones']}")
        print("Resultado:", "consistente" if informe["consistente"] else "INCONSISTENTE")
    return 0 if informe["consistente"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
