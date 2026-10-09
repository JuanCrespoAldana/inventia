# Pruebas, limitaciones y trabajo pendiente

Este documento dice con precisión qué se probó y cómo, qué **no** se pudo probar y qué límites tiene el sistema.
Está escrito para que quien reciba el proyecto sepa en qué puede apoyarse y qué debe comprobar por su cuenta antes de
usarlo con datos reales.

## Resultado de las pruebas

Última ejecución completa: **9 de octubre de 2026**, sobre la versión 1.0.0.

Entorno: Linux, Python 3.13, Node.js 22, PostgreSQL 16.15 local, Chromium (Playwright).

| Comprobación | Resultado |
|---|---|
| Backend, 137 pruebas, contra **PostgreSQL 16** (`TEST_DATABASE_URL`) | **137 pasaron**, 0 omitidas, 0 fallidas |
| Backend, mismas pruebas contra **SQLite** (modo rápido, sin variable) | 125 pasaron, 12 omitidas (las que exigen PostgreSQL), 0 fallidas |
| Frontend, pruebas (vitest) | **79 pasaron** en 12 archivos |
| Frontend, tipos (`tsc -b`, modo estricto) | Sin errores |
| Frontend, lint (`oxlint --deny-warnings`) | Sin advertencias |
| Frontend, compilación de producción (`vite build`) | Correcta |
| Tipos de la API (`npm run tipos`) | `api.gen.ts` coincide con el OpenAPI actual del backend |
| Recorrido en navegador (Chromium): 21 pantallas × 4 roles | 0 errores de consola, 0 respuestas HTTP ≥ 400 inesperadas |
| Recorrido en navegador a 1440, 1280, 390 y 320 px | Sin desbordamiento horizontal |
| Flujos funcionales en navegador (9) | Todos correctos (ver más abajo) |

Las 12 pruebas omitidas en SQLite son las marcadas `postgres`: 6 de concurrencia, 4 de migraciones y disparadores, y 2
de simultaneidad en predicción y recomendaciones. SQLite no puede reproducirlas fielmente (no tiene bloqueos de fila
ni disparadores equivalentes), por eso **la ejecución que cuenta es la de PostgreSQL**.

### Qué cubren las 137 pruebas del backend

| Archivo | Pruebas | Qué demuestran |
|---|---|---|
| `test_setup_auth.py` | 20 | Configuración inicial única y con token, ingreso, mensajes genéricos, bloqueo temporal, límite de solicitudes por IP en el ingreso, recuperación de contraseña, cabeceras de seguridad |
| `test_administracion.py` | 25 | Empresa, sedes, usuarios, roles, **aislamiento entre empresas**, alcance por sede, auditoría |
| `test_catalogo_inventario.py` | 12 | Catálogo, entradas, salidas, ajustes, mínimos y máximos, alertas, consolidado sin duplicados |
| `test_ventas_traslados.py` | 12 | Ventas, anulaciones, traslados en tres pasos, invariantes de existencias |
| `test_ml.py` | 17 | Modelos de pronóstico, control de calidad de datos, validación temporal sin fuga de información, WAPE/MAE, regla de preferencia del modelo avanzado |
| `test_prediccion.py` | 9 | Ejecución completa, omisiones con motivo, permisos, aislamiento, una sola ejecución activa |
| `test_recomendaciones.py` | 11 | Reglas de reposición y traslado con valores conocidos, ciclo de vida, aprobación humana |
| `test_dashboard_reportes.py` | 7 | Panel, reportes JSON/CSV/Excel, visibilidad según permisos |
| `test_demo.py` | 4 | Carga de la demostración en la empresa de la configuración inicial: conserva al administrador, no se repite, exige una sola empresa |
| `test_agentes.py` | 9 | Llaves, alcances, sede, vencimiento, revocación, solo lectura, aislamiento |
| `test_flujo_integral.py` | 1 | Escenario de **17 pasos**: empresa y administrador inicial, ingreso, sedes, usuarios por rol y sede, catálogo, existencias iniciales, consolidado, entradas y salidas, ventas, traslado, movimientos y reportes, alertas, predicción y recomendaciones, aislamiento entre empresas y entre sedes, auditoría. Un paso (el historial de ventas de 60 días) se inserta directamente en la base, porque la API no permite fechar ventas en el pasado |
| `test_concurrencia.py` | 6 | Salidas, ventas, confirmaciones, anulaciones y alertas simultáneas; traslados cruzados sin interbloqueo (PostgreSQL) |
| `test_migraciones.py` | 4 | Migración desde base vacía y `alembic check`, hacia atrás y adelante, con datos de la versión anterior, y disparadores de solo inserción (PostgreSQL) |

### Flujos comprobados en el navegador

Con la demostración cargada y un navegador real (Chromium) se comprobó, como administrador: registrar y anular una
venta; solicitar, aprobar y confirmar un traslado; crear un usuario; ver las validaciones en español de un
formulario; crear un rol y asignarle permisos; crear, copiar y revocar la llave de un agente; rechazar una
recomendación con comentario; descargar un reporte en Excel y en CSV; y cerrar sesión. También se recorrieron las
21 pantallas con los roles Administrador, Gerente, Analista de compras y Usuario de inventario, confirmando que cada pantalla sin permiso
muestra «No tiene acceso a esta sección» en lugar de una pantalla rota.

Estos recorridos se hicieron con guiones de Playwright escritos para la verificación; **no forman parte del
repositorio ni de la integración continua**. Si el equipo quiere pruebas de extremo a extremo permanentes, es el
siguiente paso natural (ver «Mejoras recomendadas»).

### Cómo repetir estas pruebas

```bash
npm run lint && npm run typecheck && npm run build && npm run test:frontend
npm run test:backend                       # SQLite
# PostgreSQL (base descartable: las pruebas la borran y recrean)
TEST_DATABASE_URL=postgresql+asyncpg://USUARIO:CLAVE@localhost:5432/inventia_test npm run test:backend
```

Más detalle en [`DESARROLLO.md`](DESARROLLO.md#pruebas).

## Lo que no se pudo verificar

Estos elementos **existen en el repositorio pero no se ejecutaron** en el entorno donde se desarrolló el sistema. Pueden
funcionar a la primera o pedir ajustes menores; no se debe asumir ninguna de las dos cosas.

| Elemento | Qué se hizo | Qué falta |
|---|---|---|
| **Imágenes de Docker** (`backend/Dockerfile`, `frontend/Dockerfile`) | Se revisaron y se validó la sintaxis de `docker-compose.yml` con `docker compose config` | Construirlas: el registro de imágenes estaba bloqueado en el entorno |
| **Ejecución con Docker Compose** (red, volúmenes, `healthcheck`, orden de arranque) | El script de arranque del contenedor se ejecutó fuera de Docker sobre PostgreSQL vacío y la API arrancó en modo producción | Ejecutar `docker compose up` completo |
| **nginx** (`frontend/nginx.conf`) | Revisión manual | Validar con `nginx -t` y servir la interfaz con él |
| **Scripts de PowerShell** (`infra/scripts/*.ps1`) | Se escribieron como equivalentes de los `.sh` | Ejecutarlos en Windows. (Los comandos `npm run …` de la raíz usan Node.js y no dependen de PowerShell ni de bash, pero tampoco se ejecutaron en Windows) |
| **Scripts `.sh` de respaldo y restauración contra Docker** | El volcado y la restauración con `pg_dump`/`pg_restore` se probaron contra PostgreSQL local | Probarlos contra el contenedor |
| **Envío real de correo** (recuperación de contraseña) | Probado con un envío simulado: el flujo completo funciona y el código llega a la capa de envío | Probar con el servidor SMTP real de la empresa |
| **Integración continua** (`.github/workflows/ci.yml`) | Cada paso del flujo se ejecutó por separado en local | Ver el flujo correr en GitHub Actions |
| **Navegadores distintos de Chromium** | — | Firefox, Safari y Edge |
| **Carga y volumen** | Medición informal sobre la demostración (4 403 ventas, 11 550 movimientos): las consultas principales respondieron en 8 a 40 ms | Prueba de carga con muchos usuarios y millones de filas |
| **Accesibilidad (WCAG)** | Etiquetas asociadas a cada campo, foco visible, diálogos con foco atrapado y cierre con Escape, un `h1` por pantalla | Medir el contraste con una herramienta, auditoría formal y prueba con lector de pantalla |

**Recomendación:** antes de usar datos reales, haga un primer despliegue de ensayo y siga la lista de
[«Primera prueba del despliegue»](DESPLIEGUE.md#primera-prueba-del-despliegue).

## Limitaciones del sistema

### Predicción y recomendaciones

- **La calidad de la predicción depende de los datos de la empresa.** La validación del método se hizo con series
  sintéticas y con la demostración (ventas generadas por el propio sistema). Eso demuestra que el método funciona
  como se describe, **no** cuánto acertará en una empresa real. Ese número lo da el sistema mismo, producto por
  producto, con el WAPE de cada ejecución; hasta contar con varios meses de ventas reales, trate las predicciones
  como una guía y no como un compromiso.
- **Exige historia.** Una serie con menos de 28 días, menos de 5 días con ventas o más de 50 % de días sin
  existencias se **omite** y se explica por qué. No se rellena con suposiciones.
- **No modela eventos externos** (promociones, festivos, cambios de precio, clima) ni la relación entre productos.
  Si una promoción distorsiona las ventas, la predicción lo reflejará como parte de la historia.
- **Los plazos de entrega son un parámetro de la empresa** (no por proveedor ni por producto). El cálculo de
  reposición es tan bueno como ese valor.
- **No hay órdenes de compra.** Una recomendación de compra indica cuánto y por qué; registrar el pedido al proveedor
  y recibirlo sigue siendo un proceso externo (la recepción se registra como una entrada de inventario).
- **La predicción se ejecuta bajo demanda o programada con el CLI.** No hay un planificador interno: use `cron` o el
  programador de tareas de su sistema (ver [`DESPLIEGUE.md`](DESPLIEGUE.md#predicción-programada)).

### Seguridad

Los controles implementados y las responsabilidades de quien despliega están en [`SEGURIDAD.md`](SEGURIDAD.md). Los
límites conocidos son:

- **No hay doble factor de autenticación.**
- **El token de sesión no se puede revocar de forma individual**: vence (60 minutos por defecto) o se invalida al
  cambiar la contraseña. Un token copiado seguiría valiendo hasta vencer.
- **El token se guarda en el almacenamiento del navegador**, no en una cookie `HttpOnly`. Evita ataques CSRF, pero un
  fallo XSS permitiría leerlo; se mitiga con una política CSP estricta y sin `dangerouslySetInnerHTML`.
- **La política CSP permite estilos en línea** (`style-src 'unsafe-inline'`) porque los gráficos y la librería de
  animación aplican estilos dinámicos. No permite scripts en línea ni de otros orígenes.
- **El límite de solicitudes está en memoria del proceso** y es por IP: con varias réplicas de la API cada una cuenta
  por separado. Para un límite global use un proxy o un almacén compartido.
- **La aplicación no termina HTTPS.** Debe publicarse detrás de un proxy o plataforma con certificado.
- **La recuperación de contraseña depende de que el correo esté configurado** (SMTP). Sin él, un administrador debe
  restablecer la contraseña de la persona.
- **Enumeración de correos.** El ingreso iguala el tiempo de respuesta entre un correo inexistente y uno real, y la
  recuperación responde igual en ambos casos; pero en la recuperación un atacante paciente podría distinguirlos por
  el tiempo de respuesta, y el aviso de «cuenta bloqueada» confirma que un correo existe tras varios intentos
  fallidos.
- **No se hizo una prueba de penetración independiente** y la política de contraseñas no consulta listas de
  contraseñas filtradas.

### Funcionalidad

- **Una sola moneda por instalación** (`VITE_MONEDA`, al compilar la interfaz) y sin impuestos ni descuentos: los
  precios y costos son valores simples. No sustituye a un sistema contable ni a facturación electrónica.
- **Sin lectores de código de barras ni integración con puntos de venta**; las ventas se registran en la aplicación o
  por la API. No hay importación masiva de productos ni de ventas desde Excel/CSV.
- **Productos sin lotes, series ni fechas de vencimiento.** El inventario es por cantidad, no por lote.
- **Los traslados entre sedes no contemplan recepciones parciales:** se confirman completos o se cancelan.
- **Sin notificaciones por correo ni móviles**: las alertas se ven en la aplicación.
- **Idioma único** (español). Los números y fechas se pueden cambiar con `VITE_LOCALE` y `VITE_MONEDA`, pero los textos
  no están preparados para traducirse.
- **Los reportes no tienen programación ni envío automático**; se generan a pedido.
- **El respaldo es manual o por tarea programada del cliente**; la aplicación no lo ejecuta ni lo guarda fuera del
  servidor.

### Operación

- **Una sola base de datos por despliegue.** Varias empresas comparten las mismas tablas y están aisladas por
  consulta, no por esquema o base; un fallo grave en el filtrado afectaría a todas, y por eso el aislamiento tiene
  pruebas específicas. Si el cliente exige separación física, debe desplegar una instancia por empresa.
- **Escalado horizontal limitado:** la ejecución de predicciones usa el proceso de la API (con una sola activa por
  empresa) y el límite de solicitudes está en memoria. Para cargas altas conviene separar un proceso de tareas.
- **La carga de datos de demostración es lenta contra una base remota.** Hace unas 50 mil consultas (25 mil con
  60 días): 1,5 minutos con la base en el mismo equipo, pero cada consulta paga la latencia de red con servicios como
  Neon. No se midió contra Neon; cuente de 20 a 60 minutos. Es una carga única, no se puede reanudar si se
  interrumpe (ver [`DESARROLLO.md`](DESARROLLO.md#solución-de-problemas)).
- **Las migraciones destructivas hacia atrás (`downgrade`) pueden perder datos** de las tablas nuevas. Haga respaldo
  antes de actualizar.

## Mejoras recomendadas

En orden aproximado de valor:

1. Ejecutar el despliegue de ensayo con Docker y corregir lo que aparezca; después activar la integración continua en
   GitHub.
2. Incorporar los guiones de navegador como pruebas de extremo a extremo permanentes (Playwright) en la integración
   continua.
3. Medir la precisión de la predicción con las ventas reales de la primera empresa y ajustar, si hace falta, los
   umbrales de calidad de datos y de confianza (están en `backend/app/ml/` y se explican en
   [`PREDICCION.md`](PREDICCION.md)).
4. Doble factor de autenticación y revocación de sesiones individuales.
5. Importación masiva de productos y ventas desde CSV/Excel.
6. Notificaciones por correo para las alertas críticas.
7. Planificador de tareas propio (predicción nocturna) y límite de solicitudes compartido entre réplicas (por
   ejemplo con Redis).
8. Auditoría de accesibilidad y pruebas con lector de pantalla.
9. Lotes y fechas de vencimiento para empresas con productos perecederos.
