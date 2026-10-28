#!/usr/bin/env bash
# Prueba de fuzzing de la API con Schemathesis a partir de su propio esquema OpenAPI (OWASP A05 y A10).
# Genera entradas válidas e inválidas para cada ruta y verifica que la API NUNCA responda con un error 5xx y que las
# respuestas cumplan el esquema documentado.
#
# Uso:  ./fuzz_api.sh <url_api> <archivo_con_token> [semilla]
#   <url_api>            API de una base de PRUEBA, p. ej. http://127.0.0.1:8002
#   <archivo_con_token>  archivo de texto con un JWT de administrador (el token no se escribe en la línea de comandos
#                        del historial ni se imprime)
#
# ADVERTENCIA: envía peticiones POST/PUT/PATCH/DELETE con datos aleatorios. Usarlo SOLO contra una copia desechable.
# Se excluyen las rutas de autenticación, la configuración inicial, la ejecución de predicciones (trabajo pesado), las
# rutas de agentes (usan otra llave), el restablecimiento de contraseñas y la edición o inhabilitación de usuarios: con
# datos aleatorios el fuzzer termina cambiando la contraseña o el rol del propio administrador (el sistema reacciona bien
# e invalida su sesión) y el resto de la corrida quedaría sin permisos, con lo que ya no probaría nada.
# Requiere: pip install schemathesis
set -euo pipefail
URL="${1:?Indique la URL de la API de pruebas}"
TOKEN_FILE="${2:?Indique el archivo con el token}"
SEMILLA="${3:-20261026}"
case "$URL" in
  *127.0.0.1*|*localhost*) ;;
  *) echo "Por seguridad solo se ejecuta contra localhost: $URL" >&2; exit 2 ;;
esac
SALIDA="${SALIDA:-resultados_fuzz}"
# Las exclusiones se combinan en UNA sola expresión sobre «MÉTODO /ruta» (Schemathesis exige que se cumplan todos los
# filtros de exclusión a la vez, así que varios filtros no sumarían exclusiones).
EXCLUIR='^(\w+ /api/(auth|setup|agentes)|\w+ /api/predicciones/ejecutar|\w+ /api/usuarios/\{[^}]+\}/restablecer-password|(PUT|PATCH|DELETE) /api/usuarios/)'
mkdir -p "$SALIDA"
st run "$URL/api/openapi.json" \
  --header "Authorization: Bearer $(cat "$TOKEN_FILE")" \
  --checks not_a_server_error,response_schema_conformance \
  --exclude-name-regex "$EXCLUIR" \
  --max-examples "${MAX_EJEMPLOS:-25}" --workers 2 --max-time "${MAX_SEGUNDOS:-900}" \
  --seed "$SEMILLA" --request-timeout 60 \
  --report ndjson,junit --report-dir "$SALIDA" --no-color
