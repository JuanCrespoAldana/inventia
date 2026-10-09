#!/usr/bin/env bash
# Restaura un respaldo creado con respaldar.sh. REEMPLAZA los datos actuales de la base.
#   infra/scripts/restaurar.sh ruta/al/respaldo.dump
set -euo pipefail

[ $# -eq 1 ] && [ -f "$1" ] || { echo "Uso: $0 ruta/al/respaldo.dump" >&2; exit 1; }
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE=(docker compose -f "$RAIZ/infra/docker-compose.yml" --env-file "$RAIZ/infra/.env")

read -r -p "Esto reemplazará TODOS los datos actuales. Escriba RESTAURAR para continuar: " RESPUESTA
[ "$RESPUESTA" = "RESTAURAR" ] || { echo "Cancelado."; exit 1; }

echo "Deteniendo la API…"
"${COMPOSE[@]}" stop frontend backend
"${COMPOSE[@]}" cp "$1" db:/tmp/restaurar.dump
"${COMPOSE[@]}" exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner /tmp/restaurar.dump'
"${COMPOSE[@]}" exec -T db rm -f /tmp/restaurar.dump
echo "Iniciando la API (aplica las migraciones pendientes)…"
"${COMPOSE[@]}" start backend frontend
echo "Restauración terminada."
