# Evidencias de la versión 1.2.0 (`datos_pruebas/v1.2.0/`)

Resultados tal como los produjo cada herramienta el **20 de noviembre de 2026**, sobre el código de la versión 1.2.0 (Línea
Base 1, aún sin etiquetar: el commit y la fecha se registran al etiquetarla). Se obtuvieron con los datos de demostración, que
son sintéticos. Las evidencias de la versión 1.1.0 (26 y 27 de octubre de 2026) siguen en la carpeta superior sin modificarse.

| Archivo o carpeta | Qué contiene | Herramienta |
|---|---|---|
| `junit_pg.xml` | 251 pruebas del backend contra PostgreSQL 16 (todas pasan) | pytest |
| `pytest_sqlite.txt` | Las mismas pruebas en modo SQLite (221 pasan, 30 marcadas `postgres` se omiten) | pytest |
| `cobertura.json`, `cobertura_reporte.txt` | Cobertura de líneas del backend (`backend/.coveragerc`): 84,6 % | coverage.py |
| `frontend/` | Pruebas (Vitest), tipos (`tsc -b`), lint (oxlint), compilación (Vite) y regeneración de los tipos de la API | Vitest, tsc, oxlint, Vite |
| `navegador/` | Recorrido de las 21 pantallas por rol y ancho, y los 8 flujos de extremo a extremo, en Chromium | `infra/navegador/` |
| `seguridad/` | Sonda de 16 comprobaciones, Bandit, pip-audit, npm audit y fuzzing de la API (`fuzz/`) | `infra/seguridad/` y herramientas citadas |
| `esquema_migrado_0006.json` | Catálogo de la base creada con las migraciones hasta la `0006` (tablas, columnas, llaves, índices, restricciones, disparadores): de aquí salen las cifras de la documentación y de los diagramas del modelo relacional | `docs/diagramas/volcar_esquema.py` |
| `esquema_ddl.sql` | Script DDL de las 22 tablas (Anexo K.5 del documento), ejecutado el 20 de noviembre de 2026 sobre una base PostgreSQL 16 vacía; el catálogo resultante coincide con `esquema_migrado_0006.json` | Anexo K.5 del documento |

Lo que **no** se repitió sobre la versión 1.2.0 y sigue siendo evidencia de la 1.1.0: la carga con 5, 20 y 50 usuarios, la
latencia con 10 y 50 veces el volumen de datos, la evaluación de los modelos de predicción y la simulación de las
recomendaciones (carpetas `carga/`, `escala/` y `modelos/` de la carpeta superior). El código de predicción (`backend/app/ml/` y
`ml/`) no cambió entre versiones, pero ninguna de esas mediciones se ha vuelto a ejecutar.

El archivo `ndjson` que genera Schemathesis (200 MB, con las cabeceras de cada petición) no se conserva; se guardan el resumen
(`seguridad/fuzz/corrida_1_2_0.log`) y el informe JUnit.
