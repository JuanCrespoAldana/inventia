# Registro de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). El proyecto usa
[versionado semántico](https://semver.org/lang/es/).

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
