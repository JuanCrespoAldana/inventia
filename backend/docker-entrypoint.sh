#!/bin/sh
# Aplica las migraciones pendientes antes de arrancar la API. Si la migración falla, el contenedor termina
# con error (no se sirve tráfico con un esquema a medias). Con RUN_MIGRATIONS=false se omite el paso, p. ej.
# cuando las migraciones se ejecutan como un trabajo aparte en un despliegue con varias réplicas.
set -eu

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Inventia: aplicando migraciones…"
    alembic upgrade head
fi

exec "$@"
