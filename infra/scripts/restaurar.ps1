# Restaura un respaldo creado con respaldar.ps1. REEMPLAZA los datos actuales de la base.
#   .\infra\scripts\restaurar.ps1 -Archivo .\respaldos\inventia_20261008_101500.dump
param([Parameter(Mandatory = $true)][string]$Archivo)
$ErrorActionPreference = "Stop"
if (-not (Test-Path $Archivo)) { throw "No existe el archivo $Archivo" }
$archivo = (Resolve-Path $Archivo).Path
$raiz = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$base = @("compose", "-f", (Join-Path $raiz "infra\docker-compose.yml"), "--env-file", (Join-Path $raiz "infra\.env"))

function Compose { & docker @base @args; if ($LASTEXITCODE -ne 0) { throw "docker compose falló (código $LASTEXITCODE)" } }

$respuesta = Read-Host "Esto reemplazará TODOS los datos actuales. Escriba RESTAURAR para continuar"
if ($respuesta -ne "RESTAURAR") { Write-Host "Cancelado."; exit 1 }

Write-Host "Deteniendo la API…"
Compose stop frontend backend
Compose cp $archivo "db:/tmp/restaurar.dump"
Compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner /tmp/restaurar.dump'
Compose exec -T db rm -f /tmp/restaurar.dump
Write-Host "Iniciando la API (aplica las migraciones pendientes)…"
Compose start backend frontend
Write-Host "Restauración terminada."
