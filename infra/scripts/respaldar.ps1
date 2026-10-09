# Copia de seguridad de la base de datos de Inventia en Windows (PowerShell).
#   .\infra\scripts\respaldar.ps1 [-Destino .\respaldos]
# Requiere Docker Desktop y que el servicio «db» esté en ejecución.
param([string]$Destino = "")
$ErrorActionPreference = "Stop"
$raiz = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if (-not $Destino) { $Destino = Join-Path $raiz "respaldos" }
New-Item -ItemType Directory -Force -Path $Destino | Out-Null
$archivo = Join-Path (Resolve-Path $Destino).Path ("inventia_{0}.dump" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
$base = @("compose", "-f", (Join-Path $raiz "infra\docker-compose.yml"), "--env-file", (Join-Path $raiz "infra\.env"))

function Compose { & docker @base @args; if ($LASTEXITCODE -ne 0) { throw "docker compose falló (código $LASTEXITCODE)" } }

Compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner -f /tmp/respaldo.dump'
Compose cp "db:/tmp/respaldo.dump" $archivo
Compose exec -T db rm -f /tmp/respaldo.dump

if (-not (Test-Path $archivo) -or (Get-Item $archivo).Length -eq 0) {
    Remove-Item -ErrorAction SilentlyContinue $archivo
    throw "El respaldo quedó vacío; se descartó."
}
Write-Host "Respaldo creado: $archivo"
Write-Host "Guárdelo fuera de este equipo: contiene todos los datos de la empresa."
