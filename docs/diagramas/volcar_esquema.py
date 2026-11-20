"""Vuelca el esquema real de PostgreSQL (tablas, columnas, llaves primarias y foráneas) a un JSON para ``relacional.py``.

    DATABASE_URL=postgresql+asyncpg://usuario:clave@localhost:5432/base python volcar_esquema.py esquema.json

Úselo con una base que tenga ``alembic upgrade head`` aplicado. Imprime también los totales (tablas, columnas, llaves
foráneas e índices) que cita el Anexo K del documento de grado.
"""
import asyncio
import json
import os
import sys

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

COLUMNAS = text("""
    SELECT table_name, column_name, data_type, character_maximum_length, numeric_precision, numeric_scale, is_nullable
    FROM information_schema.columns WHERE table_schema = 'public' AND table_name <> 'alembic_version'
    ORDER BY table_name, ordinal_position
""")


def _volcar(conn, filas):
    insp = inspect(conn)
    esquema = {}
    for t in sorted(insp.get_table_names()):
        if t == "alembic_version":
            continue
        esquema[t] = {
            "columnas": [],
            "pk": insp.get_pk_constraint(t)["constrained_columns"],
            "fks": [{"columna": c, "tabla": f["referred_table"], "destino": d}
                    for f in insp.get_foreign_keys(t) for c, d in zip(f["constrained_columns"], f["referred_columns"])],
            "indices": len(insp.get_indexes(t)),
            "fks_n": len(insp.get_foreign_keys(t)),
        }
    for tabla, col, tipo, largo, prec, esc, nulo in filas:
        if tabla in esquema:
            esquema[tabla]["columnas"].append({"nombre": col, "tipo": tipo, "largo": largo, "precision": prec, "escala": esc, "nulo": nulo == "YES"})
    return esquema


async def main(salida: str) -> None:
    motor = create_async_engine(os.environ["DATABASE_URL"])
    async with motor.connect() as conn:
        filas = (await conn.execute(COLUMNAS)).all()
        esquema = await conn.run_sync(_volcar, filas)
    await motor.dispose()
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(esquema, f, ensure_ascii=False, indent=1)
    print(f"{len(esquema)} tablas · {sum(len(t['columnas']) for t in esquema.values())} columnas · "
          f"{sum(t['fks_n'] for t in esquema.values())} llaves foráneas · {sum(t['indices'] for t in esquema.values())} índices")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
