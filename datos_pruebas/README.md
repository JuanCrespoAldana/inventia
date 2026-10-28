# Evidencias de la validación (`datos_pruebas/`)

Resultados tal como los produjo cada herramienta durante la validación de la versión 1.1.0 (27 de octubre de 2026). La memoria del proyecto de grado
(capítulo de pruebas y Anexo J) cita estas cifras y las lee directamente de estos archivos; el Anexo J incluye además una huella SHA-256 de cada uno para comprobar que no se alteraron.

**Todo se obtuvo con los datos de demostración, que son sintéticos** (tres sedes de una empresa ficticia de movilidad eléctrica). Ninguna de estas cifras proviene de una empresa real.

| Carpeta o archivo | Qué contiene | Herramienta |
|---|---|---|
| `junit_pg.xml` | 214 pruebas del backend contra PostgreSQL 16 | pytest |
| `cobertura.json` | Cobertura de líneas del backend (regenerada tras reorganizar las carpetas del backend, D-39) | coverage.py |
| `frontend/` | Compilación, comprobación de tipos, lint y 133 pruebas del frontend | Vite, tsc, oxlint, Vitest |
| `carga/` | Carga con 5, 20 y 50 usuarios virtuales, verificador de consistencia posterior y medición con predicción en ejecución (RNF-012) | Locust |
| `escala/` | Latencia con 1, 10 y 50 veces el volumen de datos de demostración | Locust y medidor propio |
| `modelos/` | Evaluación de los modelos de predicción (cortes de 7, 14 y 28 días), intervalo bootstrap y simulación de políticas | `ml/` y `backend/app/ml/` |
| `seguridad/` | Sonda de 16 comprobaciones (OWASP Top 10:2025), fuzzing de la API (Schemathesis), Bandit, pip-audit y npm audit (antes y después de las correcciones) | `infra/seguridad/` y herramientas citadas |
| `navegador/` | Registros de los recorridos de pantallas por rol y de los flujos de extremo a extremo en Chromium | `infra/navegador/` |

Para repetir una medición, ver `docs/DESARROLLO.md` (pruebas) y `docs/RENDIMIENTO.md` (carga y escala). Los resultados cambian con el equipo en que se ejecuten; la columna de tiempos es indicativa, no un contrato.
