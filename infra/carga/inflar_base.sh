#!/usr/bin/env bash
# Multiplica el volumen de ventas, movimientos y auditoría de una base de PRUEBAS para medir cómo responde el
# sistema con más datos (RNF-013). Cada copia repite el historial original desplazado hacia atrás en el tiempo
# (210 días por copia), de modo que lo reciente (lo que muestra el panel) no cambia y el historial crece.
#
# Uso:   ./inflar_base.sh <base_de_datos> <copias>        p. ej.  ./inflar_base.sh inventia_escala 9   (≈ ×10)
# Requiere psql y las variables PGHOST, PGPORT, PGUSER y PGPASSWORD (o ~/.pgpass) apuntando al servidor de pruebas.
#
# ADVERTENCIA: SOLO para una base desechable (copia de la de demostración). Las ventas copiadas llevan consecutivos
# NEGATIVOS para no chocar con los reales; los registros copiados no son consistentes con las existencias actuales
# (sirven para medir tiempos, no para verificar el inventario). Nunca lo ejecute sobre datos reales.
set -euo pipefail

BASE="${1:?Indique la base de datos de pruebas}"
COPIAS="${2:?Indique cuántas copias (1 = ×2, 9 = ×10, 49 = ×50)}"
PSQL=(psql -v ON_ERROR_STOP=1 -X -q -d "$BASE" -At)

case "$BASE" in
  *prod*|*real*) echo "Se niega a trabajar sobre una base cuyo nombre sugiere datos reales: $BASE" >&2; exit 2 ;;
esac

# Los tamaños originales se guardan la primera vez, para que ejecuciones posteriores sigan copiando solo lo original.
"${PSQL[@]}" -c "create table if not exists _inflado_base (bv int, bm bigint, nm int, ba bigint, copias int)" >/dev/null
if [ "$("${PSQL[@]}" -c "select count(*) from _inflado_base")" = "0" ]; then
  "${PSQL[@]}" -c "insert into _inflado_base select (select max(id) from ventas), (select max(id) from movimientos),
                   (select max(numero) from ventas), (select coalesce(max(id), 0) from auditoria), 0" >/dev/null
fi
IFS='|' read -r BV BM NM BA YA < <("${PSQL[@]}" -c "select bv, bm, nm, ba, copias from _inflado_base")
echo "Base $BASE: ventas hasta id $BV, movimientos hasta id $BM, auditoría hasta id $BA. Copias ya aplicadas: $YA"

for ((k = YA + 1; k <= YA + COPIAS; k++)); do
  "${PSQL[@]}" <<SQL
BEGIN;
INSERT INTO ventas (id, empresa_id, sede_id, numero, usuario_id, fecha, fecha_dia, total, estado, observacion,
                    anulada_por, anulada_en, motivo_anulacion, created_at, updated_at)
SELECT id + $k * $BV, empresa_id, sede_id, -(numero + $k * ($NM + 1)), usuario_id, fecha - ($k * 210) * interval '1 day',
       fecha_dia - $k * 210, total, estado, observacion, anulada_por, anulada_en, motivo_anulacion, created_at, updated_at
FROM ventas WHERE id <= $BV AND numero > 0;

INSERT INTO venta_items (venta_id, producto_id, cantidad, precio_unitario, subtotal)
SELECT venta_id + $k * $BV, producto_id, cantidad, precio_unitario, subtotal
FROM venta_items WHERE venta_id <= $BV;

INSERT INTO movimientos (id, empresa_id, sede_id, producto_id, tipo, motivo, delta, saldo_anterior, saldo_posterior,
                         sede_contraparte_id, usuario_id, fecha, observacion, venta_id, traslado_id, entrada_id, created_at)
SELECT id + $k * $BM, empresa_id, sede_id, producto_id, tipo, motivo, delta, saldo_anterior, saldo_posterior,
       sede_contraparte_id, usuario_id, fecha - ($k * 210) * interval '1 day', observacion,
       CASE WHEN venta_id IS NULL THEN NULL ELSE venta_id + $k * $BV END, NULL, NULL, created_at
FROM movimientos WHERE id <= $BM;

INSERT INTO auditoria (empresa_id, usuario_id, usuario_email, sede_id, fecha, modulo, accion, entidad, entidad_id,
                       resultado, detalle, ip, request_id)
SELECT empresa_id, usuario_id, usuario_email, sede_id, fecha - ($k * 210) * interval '1 day', modulo, accion, entidad,
       entidad_id, resultado, detalle, ip, request_id
FROM auditoria WHERE id <= $BA;
COMMIT;
SQL
  "${PSQL[@]}" -c "update _inflado_base set copias = $k" >/dev/null
  echo "  copia $k aplicada"
done

"${PSQL[@]}" -c "select setval('ventas_id_seq', (select max(id) from ventas)); select setval('movimientos_id_seq', (select max(id) from movimientos));" >/dev/null
"${PSQL[@]}" -c "analyze ventas; analyze venta_items; analyze movimientos; analyze auditoria;"
"${PSQL[@]}" -F ' · ' -c "select 'ventas', count(*) from ventas union all select 'venta_items', count(*) from venta_items union all select 'movimientos', count(*) from movimientos union all select 'auditoria', count(*) from auditoria"
