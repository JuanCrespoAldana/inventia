#!/usr/bin/env bash
# Copia de seguridad de la base de datos de Inventia (formato comprimido de pg_dump).
#   infra/scripts/respaldar.sh [carpeta_destino]
# Requiere que el servicio «db» de Docker Compose esté en ejecución.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DESTINO="${1:-$RAIZ/respaldos}"
COMPOSE=(docker compose -f "$RAIZ/infra/docker-compose.yml" --env-file "$RAIZ/infra/.env")

mkdir -p "$DESTINO"
ARCHIVO="$DESTINO/inventia_$(date +%Y%m%d_%H%M%S).dump"

# Se vuelca dentro del contenedor y se copia después: así el archivo binario no pasa por ninguna tubería del terminal.
"${COMPOSE[@]}" exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner -f /tmp/respaldo.dump'
"${COMPOSE[@]}" cp db:/tmp/respaldo.dump "$ARCHIVO"
"${COMPOSE[@]}" exec -T db rm -f /tmp/respaldo.dump

[ -s "$ARCHIVO" ] || { echo "El respaldo quedó vacío; se descarta." >&2; rm -f "$ARCHIVO"; exit 1; }
chmod 600 "$ARCHIVO"
echo "Respaldo creado: $ARCHIVO ($(du -h "$ARCHIVO" | cut -f1))"
echo "Guárdelo fuera de este servidor: contiene todos los datos de la empresa."
