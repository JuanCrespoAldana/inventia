# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). El proyecto usa
[versionado semántico](https://semver.org/lang/es/).

## [Sin publicar]

### Agregado

- **RMSE y MAPE** en la evaluación de los modelos de predicción, además de WAPE, MAE y sesgo. Se guardan por serie, por
  modelo candidato y por ejecución (también para la línea base), se muestran en *Predicción de demanda* y en el reporte
  de predicciones. El MAPE se calcula solo sobre los días con ventas porque con venta cero no existe; la **elección del
  modelo sigue haciéndose con WAPE** (decisión D-34). No hay migración: las métricas viven en columnas JSON, y las
  ejecuciones anteriores muestran «—».
- **Reportes en PDF** (`GET /api/reportes/{tipo}?formato=pdf` y botón *PDF* en la pantalla Reportes): encabezado con
  empresa, usuario, fecha y filtros, resumen, tabla con encabezado repetido y «Página X de Y». Para leer e imprimir:
  hasta 1.000 filas (Excel y CSV siguen hasta 50.000) (decisión D-35). Nuevas dependencias: `reportlab` y `pillow`.
- `ml/evaluar_modelos.py` imprime WAPE, MAE, RMSE y MAPE por tipo de serie, acepta `--csv` y usa 180 días por defecto
  (con menos de 132 el gradient boosting no puede validarse).
- **Pruebas de carga y de volumen** (`infra/carga/`): escenario de Locust con usuarios virtuales que consultan, venden y
  registran entradas; `verificar_consistencia.py` (comprueba en la base que no hubo actualizaciones perdidas),
  `medir_latencias.py` (tiempo de cada consulta con un solo usuario) e `inflar_base.sh` (multiplica el historial de una
  base de pruebas ×10 o ×50). Resultados y límites en [`docs/RENDIMIENTO.md`](docs/RENDIMIENTO.md).
- **Verificación de seguridad** (`infra/seguridad/`): `sonda_seguridad.py` (16 comprobaciones contra una API en ejecución:
  acceso sin token, token alterado o con algoritmo `none`, rol limitado, aislamiento por sede, cabeceras y CORS,
  inyección y XSS, bloqueo por intentos, auditoría) y `fuzz_api.sh` (Schemathesis sobre el propio contrato OpenAPI).
  Mapeo completo a OWASP Top 10:2025 en [`docs/SEGURIDAD.md`](docs/SEGURIDAD.md).
- `ml/evaluar_fuera_de_muestra.py`: prueba «holdout» del módulo de predicción (oculta los últimos días de cada serie,
  pronostica y compara con lo que ocurrió; mide también la cobertura del intervalo de 80 %). Resultados en
  [`docs/PREDICCION.md`](docs/PREDICCION.md#11-resultados-con-datos-de-demostración-rnf-030).
- `ml/simular_recomendaciones.py`: simulación que compara, sobre las últimas 8 semanas de la base de demostración, no reponer,
  mínimos y máximos fijos, las reglas de Inventia con promedio de 28 días y Inventia completo. Las reglas de Inventia perdieron
  5,2 puntos menos de la demanda que los mínimos y máximos fijos (IC 95 % 3,4 a 7,0) con 30 % menos inventario; el pronóstico
  avanzado no mejoró las decisiones frente al promedio simple, y la ventaja desaparece si se aceptan pocas sugerencias.
  Datos sintéticos; supuestos y límites en [`docs/PREDICCION.md`](docs/PREDICCION.md) §12 (decisión D-38).
- Variable `DOCS_API_ACTIVA` (por defecto `true`): con `false` se retiran `/api/docs` y `/api/openapi.json`.
- CI: trabajo informativo de seguridad (`pip-audit`, `npm audit`, Bandit; no bloquea), cobertura de pruebas en la
  salida del backend y configuración de Dependabot (`.github/dependabot.yml`).

### Cambiado

- **Estructura del backend con los nombres de carpeta de Spring** (D-39): `api` → `controller`, `schemas` → `dto`,
  `models` → `model`, `services` → `service`, `core` repartido en `config`, `security`, `exception` y `util`. Se crearon
  `specification/` (filtros dinámicos de consulta) y `mapper/` (conversión de entidad a DTO) con funciones que ya existían, y
  `exception/` se dividió en `excepciones.py` y `manejadores.py`. Sin cambios de comportamiento: mismas rutas, mismo contrato
  OpenAPI y las 214 pruebas del backend pasan. Guía nueva: [`docs/GUIA_ESTRUCTURA.md`](docs/GUIA_ESTRUCTURA.md).
- Limpieza: eliminados importaciones y variables sin uso en el backend.
- **Paginado en todas las pantallas con listas largas.** La vista previa de *Reportes* (hasta 200 filas) se muestra de 15 en
  15; los módulos de permisos de *Roles y permisos* de 5 en 5 (son 19) y la lista de roles de 10 en 10; las llaves de
  *Agentes de IA*, las actividades y el cumplimiento por persona de SST, las categorías ambientales y las líneas de venta,
  traslado y entrada, de 10 en 10; las series omitidas de *Predicción de demanda* de 15 en 15 y los ejercicios de SST de 6 en 6.
  Se usa el mismo paginador de los demás listados. Como esas listas ya llegan completas del servidor, se pagina en el
  navegador con el hook `usePaginacionLocal` o con la propiedad `paginar` de `Tabla`; el contrato de la API no cambia.
  Pruebas del frontend: de 133 a 145.
- `npm run setup` ahora **busca solo un Python compatible** (3.13, luego 3.12 y 3.14) y crea con él `backend/.venv`,
  aunque el `python` que aparece por defecto en la terminal sea otro. Si no hay ninguno, se detiene con un mensaje claro
  (en Windows indica `py install 3.13`). Si `backend/.venv` ya existe con un Python no compatible, avisa cómo
  borrarlo y repetir el setup, en lugar de fallar a mitad de la instalación de dependencias con un error de `numpy`.
- Documentado el rango de Python admitido (3.12 a 3.14) en README, guía de desarrollo y despliegue.
- **Intervalo de predicción recalibrado** (D-36): la cobertura medida fuera de muestra era de 62 % y no de 80 %; con la
  fórmula `Z₈₀ · 0,8 · σ · h^0,75` queda entre 78 % y 83 %. Las predicciones ya guardadas conservan su intervalo anterior
  hasta la siguiente ejecución.
- El contrato OpenAPI declara el formato real de los errores 422 (D-37); los tipos del frontend se regeneraron.
- Documentación: `docs/PREDICCION.md` incluye ahora el análisis de la demanda, la validación interna, la prueba fuera de
  muestra y la cobertura del intervalo, con sus limitaciones; D-35 aclara el efecto de las exportaciones grandes.

### Corregido

- **Integración continua (GitHub Actions):** el generador de tipos del frontend (`backend/scripts/exportar_openapi.py`) usaba
  SQLite por defecto, que solo se instala con `requirements-dev.txt`; ahora usa el controlador de PostgreSQL, que va en
  `requirements.txt`, y corre solo con las dependencias de producción. Además, ocho pruebas de calidad
  (`tests/test_sig_calidad_entradas.py`) calculaban «hoy» con la hora del computador en vez de la zona de la empresa, por lo que
  fallaban cuando el servidor está en UTC y en Colombia ya son más de las 7 p. m.; ahora usan `hoy_local()`.
- **Reportes recortados:** cuando la vista previa (200 filas) o el PDF (1.000 filas) se recortan, el resumen suma solo las filas mostradas. Ahora la vista previa, el PDF y la hoja de resumen del Excel lo dicen, y el aviso de la vista previa ya no afirma «primeros 200 de 200 registros».
- **Un número enorme en la URL ya no produce error 500** (D-37): un identificador o filtro que no cabe en la base de
  datos (p. ej. `?numero=99999999999`) se responde con 422 en unas 30 rutas. Lo encontró el fuzzing con Schemathesis; el
  mensaje de error era genérico y no filtraba datos.

### Seguridad

- `PyJWT` 2.13.0 → 2.15.1 (15 avisos de seguridad de la versión anterior detectados por `pip-audit`) y actualización de
  dependencias de Node: `npm audit` queda sin vulnerabilidades.
- Bandit (análisis estático): se sustituyó un `assert` que no se ejecuta con `python -O` por una excepción explícita y se
  documentaron dos usos justificados (generador pseudoaleatorio solo para datos de demostración; escape de texto, no
  lectura de XML). Sin hallazgos pendientes.

## [1.1.0] · 2026-10-09

Agrega el **Sistema Integrado de Gestión (SIG)** pedido después de la primera entrega: PQRS y sugerencias, Seguridad y
Salud en el Trabajo (pausas activas), Calidad (no conformidades y garantías) y Gestión ambiental, además de las
observaciones por entrada de inventario. Las decisiones están en D-28 a D-33 de
[`docs/DECISIONES.md`](docs/DECISIONES.md) y la correspondencia con lo solicitado, en
[`docs/TRAZABILIDAD.md`](docs/TRAZABILIDAD.md#4-sistema-integrado-de-gestión-versión-11).

### Para quien actualiza una instalación existente

1. Copie los archivos nuevos sobre el proyecto y detenga la API.
2. Ejecute `npm run migrar` (aplica `0004_sig`; **solo agrega** tablas y una columna opcional, no modifica datos).
3. Inicie la API: al arrancar asigna **sola** los 9 permisos nuevos a los roles de fábrica de cada empresa (ver D-28).
   Los roles que la empresa creó por su cuenta no los reciben; el administrador los concede desde **Roles y permisos**.
4. No hay variables de entorno nuevas ni dependencias nuevas.
5. Para que la gestión ambiental calcule CO₂, el administrador debe configurarla (**SIG → Gestión ambiental →
   Configuración**). Mientras tanto cuenta los vehículos vendidos y muestra «pendiente de parametrización».

### Agregado

**Menú SIG** con cuatro apartados, cada uno con su pantalla y sus permisos (9 permisos nuevos: ahora son 61).

**PQRS y sugerencias**
- Cualquier rol envía petición, queja, reclamo o sugerencia con evidencias opcionales y consulta el estado de las suyas.
- El administrador ve todas, filtra por tipo, estado, persona y fecha, cambia el estado, responde y consulta el historial
  de cambios (de solo inserción). No se envían correos de aviso: no existe un sistema de notificaciones (D-29).

**Seguridad y Salud en el Trabajo**
- Pausas activas automáticas para quien no administra: mensaje, ejercicio, instrucciones, duración y recomendaciones.
  Intervalo configurable (60 minutos por defecto). El servidor decide cuándo toca y evita repeticiones o pausas
  simultáneas, aunque haya varias pestañas; la pausa espera si hay un formulario abierto o una venta a medio armar.
- Los administradores no las reciben, pero ven el contenido, una vista previa y el cumplimiento por persona y día. Pueden
  editar los ejercicios y la frecuencia (D-32).

**Calidad**
- Guía educativa, no conformidades (tipo, cantidad afectada, estados, evidencias, historial de observaciones) y
  garantías (documento de respaldo, fechas, proveedor, respuesta y solución, estados e historial).
- Una no conformidad puede nacer de una entrada de inventario sin volver a digitar sus datos. **Registrar o gestionar
  calidad nunca modifica las existencias** (D-30).

**Entradas de inventario**
- Cada entrada tiene ahora número propio y un historial de **observaciones acumulativas** (autor y fecha, de solo
  inserción). Nueva pestaña **Entradas de mercancía** en Movimientos y botón para reportar una no conformidad desde el detalle.

**Gestión ambiental**
- Cuenta los vehículos de las ventas confirmadas (solo categorías marcadas como vehículo; las anuladas dejan de
  sumar; cada línea de venta se cuenta una vez) y **estima el CO₂ evitado** con parámetros configurables y documentados.
  Sin parámetros no se inventan cifras (D-33).
- Panel con totales, acumulado mensual y anual, gráficos, historial con filtros, metodología y configuración.

**Evidencias adjuntas** (JPEG, PNG, WebP y PDF; 3 MB y 5 por registro) con validación por contenido (D-31).

**Operación y pruebas**
- Migración `0004_sig`: 15 tablas, la columna `movimientos.entrada_id` y disparadores de solo inserción.
- `npm run demo:sig` (y `--con-sig` en `npm run demo`) cargan datos de ejemplo del SIG.
- Pruebas nuevas de backend (PQRS, calidad, SST, ambiental, permisos al actualizar, demostración y migración) y de
  frontend (pausas, ambiental, reglas de calidad, adjuntos, navegación).

### Cambiado

- `inventario_service.registrar_entrada` crea la cabecera de la entrada y enlaza sus movimientos; `ventas_service`
  contabiliza o excluye los vehículos al registrar o anular una venta. El resultado de las operaciones existentes no
  cambia.
- `Modal` aplaza las pausas activas mientras está abierto (propiedad `bloqueaPausas`, activa por defecto).
- Los nuevos permisos se reparten solos a los roles de fábrica al arrancar la API (antes solo se agregaban al
  administrador).
- Versión 1.1.0 en `package.json`, `frontend/package.json` y la API.

### Conocido

Ver «Limitaciones del sistema → Sistema Integrado de Gestión» en [`docs/LIMITACIONES.md`](docs/LIMITACIONES.md).

## [1.0.0] · 2026-10-09

Primera versión completa. Reestructura el proyecto anterior para cumplir el documento de grado (RF-001 a RF-038,
RN-001 a RN-012, RNF-001 a RNF-050). La correspondencia requisito por requisito está en
[`docs/TRAZABILIDAD.md`](docs/TRAZABILIDAD.md) y lo que no se pudo verificar, en
[`docs/LIMITACIONES.md`](docs/LIMITACIONES.md).

### Cambios que rompen compatibilidad

- **Se eliminó el registro público.** El primer administrador se crea una sola vez con `SETUP_TOKEN` (obligatorio
  en producción) desde la pantalla de configuración inicial o con `python -m app.cli inicializar`. Ver D-01 en
  [`docs/DECISIONES.md`](docs/DECISIONES.md).
- **Nuevo modelo de datos y de permisos.** Los dos roles fijos anteriores se reemplazan por cinco roles de fábrica
  más roles personalizados, con 52 permisos y alcance por empresa o por sede. La migración `0003_inventia`
  convierte `ADMIN_GENERAL` en *Administrador* y `USUARIO_SEDE` en *Usuario de inventario*; un usuario de sede sin
  sede queda inhabilitado hasta que se le asigne una (D-06).
- **Todas las rutas de la API cambiaron** y los listados devuelven `{items, total, pagina, tamano, paginas}`.
  Los errores tienen la forma `{detail, codigo, request_id, errores[]}`. Ver [`docs/API.md`](docs/API.md).
- **Variables de entorno:** se conservan los nombres existentes (`DATABASE_URL`, `SECRET_KEY`, `FRONTEND_URL`, …).
  Se agregan `SETUP_TOKEN`, `APP_TIMEZONE`, `ENVIRONMENT` y las de límite de intentos. Ver `backend/.env.example`.

### Agregado

**Empresa, sedes y usuarios**
- Varias empresas aisladas entre sí (cada consulta se filtra por la empresa de la sesión) y varias sedes por empresa.
- Usuarios con bloqueo temporal tras intentos fallidos, cambio obligatorio de contraseña, cambio voluntario y
  recuperación por código de 6 dígitos de un solo uso.
- Roles personalizados: un administrador elige los permisos de cada rol desde la interfaz.

**Catálogo e inventario**
- Categorías y productos con código inmutable, costo, precio, unidad y estado.
- Existencias por sede y vista consolidada. Entradas, salidas y ajustes con motivo; historial de movimientos de solo
  inserción; mínimos y máximos por producto y sede; parámetros de empresa configurables (plazo de entrega, días de
  seguridad, cobertura).
- Descuento atómico de existencias (`UPDATE … WHERE cantidad + delta >= 0`): dos operaciones simultáneas no pueden
  dejar existencias negativas.

**Ventas y traslados**
- Ventas multiproducto con descuento atómico y anulación con motivo que reintegra las existencias.
- Traslados entre sedes con tres pasos (solicitud, aprobación de origen, confirmación de destino); las existencias se
  mueven solo al confirmar y la operación es atómica.

**Alertas y panel**
- Alertas de inventario bajo, excedente, riesgo de desabastecimiento y sin rotación, que se abren y cierran solas.
- Panel con inventario, ventas del periodo, existencias por sede, alertas, traslados y recomendaciones pendientes,
  estado de la predicción y últimos movimientos, todo calculado desde la base y filtrado por sede y permisos.

**Predicción de demanda y recomendaciones**
- Predicción por sede y producto con control de calidad de datos, seis modelos (línea base de promedio de 28 días,
  promedio de 7 días, estacional semanal, Croston-SBA, suavizado exponencial semanal y regresión con rezagos),
  validación temporal con hasta tres cortes, MAE y WAPE, intervalo de 80 % y nivel de confianza.
- Un modelo avanzado reemplaza a la línea base solo si reduce el error al menos 3 %. Las series sin datos
  suficientes se **omiten con su motivo**; no se inventan pronósticos.
- Recomendaciones de reposición y de traslado con explicación en español y aprobación humana obligatoria. Aprobar un
  traslado solo crea la solicitud.
- Ejecución en segundo plano (una por empresa) y comando `python -m app.cli predecir` para programarla.

**Reportes y auditoría**
- Siete reportes con vista previa, CSV y Excel, limitados a la sede y a los permisos de quien los pide.
- Auditoría de accesos y operaciones (de solo inserción), con filtros por módulo, acción, resultado y fecha.

**Agentes de IA**
- API de solo lectura en `/api/agentes/*` con llaves propias (`X-API-Key`), alcances, sede opcional, vencimiento,
  revocación, fecha de último uso y registro en la auditoría de cada acceso denegado. Ejemplo en [`agents/`](agents/).

**Interfaz**
- 21 pantallas en español, con estados de carga, vacío y error, filtros en la URL, diseño responsivo (probado a 1440,
  1280, 390 y 320 px) y navegación filtrada por permisos.
- Tipos de la API generados desde OpenAPI (`npm run tipos`).

**Operación**
- Docker Compose (PostgreSQL, API, interfaz con nginx), migraciones al arrancar, comprobaciones de salud
  (`/api/health`, `/api/health/ready`), scripts de respaldo y restauración para bash y PowerShell.
- Datos de demostración ficticios de un comercio de movilidad eléctrica (bicicletas, monopatines, motos, baterías,
  repuestos y accesorios; `npm run demo`) con credenciales aleatorias que se muestran una sola vez. Con
  `npm run demo -- --en-empresa-existente` se cargan en la empresa creada con la configuración inicial, conservando
  el correo y la contraseña de su administrador.
- Integración continua en GitHub Actions (backend con SQLite y PostgreSQL, frontend, y verificación de tipos).
- Scripts multiplataforma en la raíz (`npm run setup | dev | migrar | demo | test | lint | build | tipos`).
- Documentación completa en [`docs/`](docs/).

### Seguridad

- Contraseñas con Argon2; tokens JWT con vencimiento, identificador y versión de contraseña (cambiarla invalida los
  tokens anteriores).
- Límite de solicitudes por IP en ingreso, recuperación, configuración inicial y API de agentes.
- Cabeceras de seguridad (CSP, `X-Frame-Options`, `nosniff`, `Referrer-Policy`) en la API y en nginx; CORS restringido
  a los orígenes configurados.
- Mensajes de error que no revelan si un correo existe; registros sin secretos.
- Llaves de agentes: solo se guarda su huella SHA-256 y se muestran una sola vez.
- Ningún secreto ni credencial se incluye en el repositorio. Quien haya compartido valores de la versión anterior
  (cadena de conexión, `SECRET_KEY`, contraseñas de correo o de administrador) debe **rotarlos**.

### Corregido respecto de la versión anterior

- Cualquier persona podía registrarse y el primer usuario en llegar quedaba como administrador (D-01).
- Los datos de la versión anterior se conservan al migrar (`0003_inventia`), con las salvedades de D-06.

### Conocido

Hay elementos preparados pero **no verificados** en el entorno de desarrollo (imágenes de Docker, nginx, scripts de
PowerShell, envío real de correo, ejecución de la integración continua) y límites de alcance (sin doble factor,
predicción validada solo con datos sintéticos). El detalle completo está en
[`docs/LIMITACIONES.md`](docs/LIMITACIONES.md).
