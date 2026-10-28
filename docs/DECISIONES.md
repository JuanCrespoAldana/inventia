# Decisiones de diseño

Registro de las decisiones técnicas y funcionales que no estaban resueltas por el documento de grado, o en las que
la implementación se aparta de él por una razón concreta. Cada una indica el motivo, la alternativa descartada y
dónde se refleja en el código. Los identificadores `D-03`, `D-04`, `D-05` y `D-28` coinciden con los citados en
`backend/app/security/permisos.py`.

## Índice

| ID | Decisión |
|---|---|
| [D-01](#d-01) | Sin registro público: configuración inicial controlada |
| [D-02](#d-02) | Nombre del producto y compatibilidad de variables de entorno |
| [D-03](#d-03) | El Administrador recibe todos los permisos |
| [D-04](#d-04) | Lectura básica compartida por todos los roles que operan |
| [D-05](#d-05) | Anulación de ventas, niveles de stock y recálculo de alertas |
| [D-06](#d-06) | Conversión de los roles de la versión anterior |
| [D-07](#d-07) | Los roles de alcance «empresa» no tienen sede |
| [D-08](#d-08) | Quién aprueba y quién confirma un traslado |
| [D-09](#d-09) | Aprobar una recomendación de traslado no mueve existencias |
| [D-10](#d-10) | Las recomendaciones pendientes se reemplazan, no se borran |
| [D-11](#d-11) | Una sola fuente de existencias; el consolidado se calcula |
| [D-12](#d-12) | Movimientos y auditoría de solo inserción |
| [D-13](#d-13) | Las ventas se anulan, no se eliminan |
| [D-14](#d-14) | Predicción: línea base, margen mínimo y omisión honesta |
| [D-15](#d-15) | La predicción es de toda la empresa, no de una sede |
| [D-16](#d-16) | Predicción en segundo plano dentro de la API |
| [D-17](#d-17) | Agentes de IA con llaves propias de solo lectura |
| [D-18](#d-18) | Tiempo en UTC; el «día» es el de la empresa |
| [D-19](#d-19) | Estados como texto, sin tipos `ENUM` de PostgreSQL |
| [D-20](#d-20) | Migraciones al arrancar el contenedor |
| [D-21](#d-21) | SQLite solo para pruebas rápidas |
| [D-22](#d-22) | Tipos del frontend generados desde la API |
| [D-23](#d-23) | Gráficos propios en SVG |
| [D-24](#d-24) | nginx reemplaza `X-Forwarded-For` |
| [D-25](#d-25) | Reportes: CSV con coma y marca de orden de bytes |
| [D-26](#d-26) | Directorio de sedes para filtros |
| [D-27](#d-27) | Un solo color de acento y escala de radios fija |
| [D-28](#d-28) | Sistema Integrado de Gestión (SIG): alcance, roles y permisos |
| [D-29](#d-29) | PQRS: historial inmutable y sin avisos por correo |
| [D-30](#d-30) | Entradas de inventario con observaciones; las no conformidades no mueven existencias |
| [D-31](#d-31) | Evidencias adjuntas guardadas en la base de datos, con límites estrictos |
| [D-32](#d-32) | Pausas activas: el servidor decide, el navegador solo muestra |
| [D-33](#d-33) | Gestión ambiental: lo real se cuenta, lo estimado exige parámetros documentados |
| [D-34](#d-34) | Métricas de error: el WAPE decide; RMSE y MAPE acompañan |
| [D-35](#d-35) | Reportes en PDF con ReportLab, para leer e imprimir |
| [D-36](#d-36) | Intervalo de predicción calibrado con datos reales de la demostración |
| [D-37](#d-37) | Errores de entrada documentados y manejados de forma uniforme |
| [D-38](#d-38) | Las recomendaciones se validan por simulación, no solo con pruebas unitarias |
| [D-39](#d-39) | Estructura por capas con los nombres de carpeta de Spring y sin capa `repository` |

---

<a id="d-01"></a>
## D-01 · Sin registro público: configuración inicial controlada

**Contexto.** La versión anterior permitía que cualquier persona se registrara y que el primer usuario en llegar
quedara como administrador. En un sistema expuesto a Internet eso es un riesgo directo (RN-009, RNF-022).

**Decisión.** No existe registro público. La primera empresa y su administrador se crean una sola vez, con el
`SETUP_TOKEN` (obligatorio en producción, mínimo 16 caracteres) desde la pantalla **Configuración inicial**, o con
`python -m app.cli inicializar`. Desde ese momento la ruta responde con conflicto. Los demás usuarios los crea un
administrador.

**Descartado.** Registro abierto con aprobación posterior (deja una superficie de ataque permanente).

**Código.** `setup_service.py`, `controller/setup_controller.py`, `config/settings.py`. **Pruebas.** `test_no_existe_registro_publico`,
`test_setup_exige_token_si_esta_definido`, `test_setup_solo_una_vez`.

<a id="d-02"></a>
## D-02 · Nombre del producto y compatibilidad de variables de entorno

**Decisión.** El producto se llama **Inventia**, como en el documento de grado. Los nombres de las variables de
entorno que ya existían (`DATABASE_URL`, `SECRET_KEY`, `SMTP_*`, `FRONTEND_URL`, …) se conservaron, de modo que un
`.env` anterior sigue funcionando; las variables nuevas son opcionales y tienen valores por defecto seguros.

**Excepción.** `SECRET_KEY` ahora debe tener al menos 32 caracteres y no puede ser un valor de ejemplo conocido;
el arranque falla con un mensaje claro si no se cumple.

<a id="d-03"></a>
## D-03 · El Administrador recibe todos los permisos

**Contexto.** La matriz de casos de uso (tabla 19) atribuye «Generar predicción de demanda» y «Generar
recomendación» solo al analista de compras y a la IA.

**Decisión.** El Administrador tiene todos los permisos del catálogo (61), incluidos esos. Si no hubiera analista de compras, nadie
podría generar predicciones, y una PyME pequeña suele tener una sola persona con ese cometido.

**Código.** `permisos.py` (`ROLES_SISTEMA`).

<a id="d-04"></a>
## D-04 · Lectura básica compartida por todos los roles que operan

**Contexto.** La matriz no da a algunos roles permiso para consultar sedes, categorías o productos.

**Decisión.** Todo rol que consulta inventario también puede **leer** sedes, categorías y productos. Sin esos datos
las pantallas no podrían mostrar nombres ni ofrecer filtros. Es solo lectura; las altas y cambios siguen siendo del
administrador.

<a id="d-05"></a>
## D-05 · Anulación de ventas, niveles de stock y recálculo de alertas

**Contexto.** El documento no asigna estas funciones, pero son necesarias para operar (corregir un error de venta,
fijar mínimos y máximos, refrescar alertas).

**Decisión.** Se asignan al **Encargado de sede** (dentro de su sede) y al **Administrador**.

### Diferencias frente a la matriz de casos de uso

Todo lo que la tabla 19 concede está concedido. Lo siguiente es lo que la implementación **añade**:

| Rol | Permisos añadidos | Motivo |
|---|---|---|
| Administrador | Predicción y recomendaciones (D-03); reportes de traslados y alertas; llaves de agentes | Que nunca quede un proceso sin responsable |
| Encargado de sede | Anular ventas, configurar niveles, recalcular alertas (D-05); reportes de traslados, alertas y recomendaciones | Operación diaria de la sede |
| Usuario de inventario | Leer sedes (D-04); reporte de alertas | Mostrar nombres y filtros; ver qué reponer |
| Gerente | Leer categorías (D-04); reportes de traslados, alertas y recomendaciones | Seguimiento completo sin poder operar |
| Analista de compras | Leer sedes y categorías (D-04); reportes de alertas y recomendaciones | Compras necesita ver sedes y qué se recomienda |

Un administrador puede quitar cualquiera de estos permisos creando un rol personalizado.

<a id="d-06"></a>
## D-06 · Conversión de los roles de la versión anterior

**Contexto.** La versión anterior tenía dos roles fijos: `ADMIN_GENERAL` y `USUARIO_SEDE`.

**Decisión.** La migración 0003 convierte `ADMIN_GENERAL` en **Administrador** y `USUARIO_SEDE` en **Usuario de
inventario** (el de menor privilegio que equivale a su uso anterior). Un `USUARIO_SEDE` sin sede asignada queda
**inhabilitado** hasta que un administrador le asigne una, porque un rol de sede sin sede no podría operar. Un
administrador puede después reasignar a cada persona el rol que corresponda.

<a id="d-07"></a>
## D-07 · Los roles de alcance «empresa» no tienen sede

**Decisión.** Un usuario con un rol de alcance `empresa` ve todas las sedes y no se le asocia ninguna: si se
intenta asignarle una, se ignora. Un rol de alcance `sede` **exige** sede. Así no hay usuarios con una sede
«decorativa» que parezca limitar su acceso sin hacerlo.

**Código.** `usuario_service._resolver_sede`. **Prueba.** `test_rol_de_sede_exige_sede_y_rol_de_empresa_no_la_admite`.

<a id="d-08"></a>
## D-08 · Quién aprueba y quién confirma un traslado

**Contexto.** La matriz permite aprobar al administrador y al encargado, y confirmar también al usuario de
inventario, pero no dice de qué sede.

**Decisión.**

- **Solicitar:** cualquier usuario con permiso, para traslados que *salgan de su sede o lleguen a ella*.
- **Aprobar o rechazar:** quien administra la **sede de origen** (es quien se compromete a entregar).
- **Confirmar:** quien administra la **sede de destino** (es quien comprueba que la mercancía llegó).
- Las existencias cambian **solo al confirmar**, en una única transacción. Un rol de empresa (por ejemplo,
  administrador) puede actuar en cualquier sede.

**Descartado.** Mover existencias al aprobar (deja mercancía «en tránsito» invisible en ambas sedes).

**Pruebas.** `test_traslado_permisos_por_sede`, `test_traslado_flujo_completo_y_atomico`.

<a id="d-09"></a>
## D-09 · Aprobar una recomendación de traslado no mueve existencias

**Decisión.** Aprobar una recomendación de traslado crea una **solicitud** de traslado (en estado «solicitado»,
vinculada a la recomendación). Esa solicitud sigue el circuito normal de D-08. Así RNF-034 (validación humana) se
cumple dos veces: quien aprueba la sugerencia y quienes aprueban y reciben el traslado.

**Pruebas.** `test_aprobar_un_traslado_crea_la_solicitud_pero_no_mueve_existencias`,
`test_dos_aprobaciones_simultaneas_crean_un_solo_traslado`.

<a id="d-10"></a>
## D-10 · Las recomendaciones pendientes se reemplazan, no se borran

**Decisión.** Al generar de nuevo, las recomendaciones *pendientes* anteriores pasan al estado `reemplazada` y se
conservan. Las *aprobadas* no se duplican. Las rechazadas y ejecutadas no se tocan. Se puede reconstruir qué se
sugirió y cuándo.

<a id="d-11"></a>
## D-11 · Una sola fuente de existencias; el consolidado se calcula

**Decisión.** La cantidad vive solo en `inventario_sede`. El inventario consolidado (RNF-019) se calcula siempre
sumando esas filas; no existe una tabla de totales que pueda desincronizarse.

<a id="d-12"></a>
## D-12 · Movimientos y auditoría de solo inserción

**Decisión.** `movimientos` y `auditoria` no admiten `UPDATE` ni `DELETE`: un disparador de PostgreSQL lo impide
aunque alguien escriba SQL a mano. Los errores se corrigen con ajustes o movimientos compensatorios. Cada
movimiento guarda saldo anterior y posterior, de modo que el historial se puede auditar por sí solo.

**Consecuencia.** En SQLite (pruebas rápidas) el disparador no existe; la prueba que lo verifica solo corre en
PostgreSQL.

<a id="d-13"></a>
## D-13 · Las ventas se anulan, no se eliminan

**Decisión.** Una venta anulada se conserva con quién la anuló, cuándo y por qué; las existencias se reintegran con
movimientos de «anulación» (no se borra el movimiento original). Solo se puede anular una vez y dentro del plazo
`dias_max_anulacion` (30 por defecto, configurable por empresa). Las ventas anuladas no cuentan en reportes ni en la
demanda que usa la predicción.

<a id="d-14"></a>
## D-14 · Predicción: línea base, margen mínimo y omisión honesta

**Decisión.** Un modelo avanzado solo se usa si supera al mejor modelo simple por al menos un 3 % de error en
validación temporal, y una serie sin datos suficientes se omite con su motivo en vez de recibir un número inventado.
Detalle y justificación en [PREDICCION.md](PREDICCION.md).

**Descartado.** Elegir siempre el modelo de menor error en validación sin margen (premia el azar) y rellenar
series cortas con promedios globales (oculta la falta de datos).

<a id="d-15"></a>
## D-15 · La predicción es de toda la empresa, no de una sede

**Decisión.** Solo roles de alcance `empresa` pueden *solicitar* una predicción; un rol limitado a una sede
recibe un rechazo explícito. Las recomendaciones de traslado necesitan ver todas las sedes a la vez. Los roles de
sede sí **consultan** los resultados de su sede.

<a id="d-16"></a>
## D-16 · Predicción en segundo plano dentro de la API

**Decisión.** La predicción corre como tarea en segundo plano de FastAPI (responde `202` y la interfaz consulta
el avance), con tiempo máximo, tope de series y una sola ejecución activa por empresa.

**Descartado.** Una cola externa (Celery, Redis): añade servicios que operar para un volumen que una PyME no
necesita. **Límite asumido:** el cálculo comparte proceso con la API; para catálogos muy grandes se recomienda
programarlo con `python -m app.cli predecir` fuera de horario. Si el servicio se reinicia a mitad de una ejecución,
esta se cierra como fallida al arrancar.

<a id="d-17"></a>
## D-17 · Agentes de IA con llaves propias de solo lectura

**Contexto.** RNF-049 pide que los agentes consulten información autorizada.

**Decisión.** Los agentes usan **llaves de API** propias (`X-API-Key`), no cuentas de usuario: de solo lectura,
con alcances explícitos, sede opcional, vencimiento (90 días por defecto) y revocación inmediata. Solo se guarda su
huella SHA-256. Las llaves no sirven en la API normal ni los tokens de usuario en `/api/agentes`. Ninguna ruta de
agentes modifica datos.

<a id="d-18"></a>
## D-18 · Tiempo en UTC; el «día» es el de la empresa

**Decisión.** Todas las fechas se guardan en UTC. El «día» de una venta, de un reporte o de una serie de demanda se
calcula en la zona horaria de la empresa (`APP_TIMEZONE`, por defecto `America/Bogota`). Una venta a las 11 p. m.
cuenta para ese día aunque en UTC ya sea el siguiente.

<a id="d-19"></a>
## D-19 · Estados como texto, sin tipos `ENUM` de PostgreSQL

**Decisión.** Los estados y tipos se guardan como texto y se validan en la aplicación. Añadir un valor nuevo no
exige migrar tipos nativos (que en PostgreSQL son incómodos de modificar) y mantiene compatibles SQLite y
PostgreSQL.

<a id="d-20"></a>
## D-20 · Migraciones al arrancar el contenedor

**Decisión.** El contenedor del backend ejecuta `alembic upgrade head` antes de arrancar y, si falla, termina con
error: nunca sirve tráfico con un esquema a medias. Con `RUN_MIGRATIONS=false` se omite el paso (por ejemplo, si
varias réplicas ejecutan las migraciones en un trabajo aparte).

<a id="d-21"></a>
## D-21 · SQLite solo para pruebas rápidas

**Decisión.** SQLite permite ejecutar casi toda la batería sin instalar nada. Lo que depende de PostgreSQL
(concurrencia real, índices parciales, disparadores y migraciones) se marca con `@pytest.mark.postgres` y corre
cuando se define `TEST_DATABASE_URL`. **La aplicación está soportada solo sobre PostgreSQL.**

<a id="d-22"></a>
## D-22 · Tipos del frontend generados desde la API

**Decisión.** `frontend/src/types/api.gen.ts` se genera del esquema OpenAPI (`npm run tipos`) y la integración
continua verifica que esté al día. Un cambio de contrato que rompa la interfaz se detecta al compilar.

<a id="d-23"></a>
## D-23 · Gráficos propios en SVG

**Decisión.** Los gráficos (líneas con banda de incertidumbre, barras) están hechos a mano con SVG: pesan una
fracción de una librería, no cargan nada externo y permiten representar cosas específicas, como el tramo parcial
del día en curso o la banda del intervalo de predicción.

<a id="d-24"></a>
## D-24 · nginx reemplaza `X-Forwarded-For`

**Decisión.** nginx **reemplaza** la cabecera con la IP real del cliente en lugar de agregarla. Si la anexara, un
cliente podría enviar su propia cabecera y falsear la IP para evadir el límite de intentos. La API solo confía en
esa cabecera si `TRUST_PROXY_HEADERS=true`.

<a id="d-25"></a>
## D-25 · Reportes: CSV con coma y marca de orden de bytes

**Decisión.** Los CSV usan coma como separador y UTF-8 con BOM, para que Excel muestre bien las tildes y la «ñ».
Los Excel (`.xlsx`) incluyen una hoja «Resumen» con los criterios del reporte. Los reportes grandes se truncan con
un aviso en lugar de agotar la memoria.

<a id="d-26"></a>
## D-26 · Directorio de sedes para filtros

**Decisión.** `GET /api/sedes/directorio` devuelve solo id y nombre de las sedes que el usuario puede ver, sin
exigir permisos de administración. Permite a una interfaz mostrar filtros y etiquetas sin dar acceso a datos de
gestión.

<a id="d-27"></a>
## D-27 · Un solo color de acento y escala de radios fija

**Decisión.** La interfaz usa una única paleta con un solo color de acento y una escala fija de radios de esquina
y sombras, definida como variables de diseño. Fuentes (Plus Jakarta Sans y Space Grotesk) e iconos van empaquetados.
La coherencia visual (RNF-044) se obtiene reutilizando los mismos componentes en todas las pantallas.

<a id="d-28"></a>
## D-28 · Sistema Integrado de Gestión (SIG): alcance, roles y permisos

**Contexto.** La versión 1.1 añade un módulo SIG con cuatro apartados (PQRS y sugerencias, Seguridad y Salud en el
Trabajo, Calidad y Gestión ambiental). La matriz de casos de uso del documento de grado no lo contemplaba, así que
sus permisos no tienen una fila de origen.

**Decisión.** Se agregan 9 permisos (de 52 a 61), agrupados en módulos «SIG · …»:

| Permiso | Quién lo recibe de fábrica |
|---|---|
| `pqrs.crear`, `sst.ver`, `calidad.ver`, `ambiental.ver` | Todos los roles (lectura básica del SIG) |
| `calidad.reportar` | Encargado de sede y Usuario de inventario (son quienes reciben y venden mercancía) |
| `pqrs.gestionar`, `sst.gestionar`, `calidad.gestionar`, `ambiental.configurar` | Solo el Administrador (D-03) |

En una instalación que ya existía, la API asigna los permisos nuevos a los roles de fábrica de cada empresa la primera vez
que arranca con la versión 1.1 (`sincronizar_permisos`); los roles creados por la empresa no los reciben y su
administrador decide. Si una empresa le quita después un permiso a un rol de fábrica, no se le vuelve a poner.

Consecuencias: el Administrador **no recibe pausas activas automáticas** (ver D-32), porque se decide por permiso y no por
nombre de rol; si una empresa crea un rol personalizado con `sst.gestionar`, ese rol tampoco las recibe.
El menú lateral muestra el grupo **SIG** con sus cuatro apartados y cada pantalla oculta lo que el rol no puede
hacer, pero la autoridad real está en el servidor: todas las rutas `/api/sig/*` exigen el permiso.
Las PQRS propias son visibles para quien las envió aunque no tenga `pqrs.gestionar`; las de otras personas, no.

**Descartado.** Atar el SIG a un rol «Calidad» nuevo: añade un rol que cada empresa tendría que poblar y no resuelve
nada que los permisos por separado no resuelvan.

**Código.** `security/permisos.py`, `controller/pqrs_controller.py`, `controller/calidad_controller.py`, `controller/sst_controller.py`, `controller/ambiental_controller.py`, `bootstrap.py`.
**Pruebas.** `test_sig_*.py` (permisos, aislamiento por empresa y por sede) y `test_sig_permisos.py` (reparto de los permisos
nuevos en una instalación que ya existía).

<a id="d-29"></a>
## D-29 · PQRS: historial inmutable y sin avisos por correo

**Contexto.** El requisito pide notificar a la administración «solo si ya existe un sistema real de notificaciones».
En el proyecto solo existe el correo de recuperación de contraseña; no hay cola, bandeja ni notificaciones internas.

**Decisión.** No se simulan avisos ni se envían correos. La administración ve el conteo por estado en la propia
bandeja de PQRS y puede filtrar por estado `pendiente`. Cada cambio de estado y cada respuesta se guarda en
`pqrs_historial`, una tabla de **solo inserción** (disparador en PostgreSQL, igual que `movimientos` y `auditoria`,
D-12): se conserva quién, cuándo, de qué estado a cuál y con qué comentario. Para marcar una PQRS como `resuelta`
se exige una respuesta, y la persona que la envió ya no puede añadirle adjuntos.

**Descartado.** Enviar un correo por cada PQRS: exigiría un servicio SMTP siempre configurado y un manejo de reintentos
que el resto del sistema no necesita. Queda como mejora (ver `LIMITACIONES.md`).

**Código.** `model/pqrs.py`, `service/pqrs_service.py`. **Pruebas.** `test_sig_pqrs_adjuntos.py`.

<a id="d-30"></a>
## D-30 · Entradas de inventario con observaciones; las no conformidades no mueven existencias

**Contexto.** Antes, una entrada de mercancía era solo un movimiento por producto, sin un registro que la agrupara ni
un lugar donde anotar observaciones. El SIG necesita enlazar una no conformidad o una garantía con la recepción de origen
sin que la persona vuelva a escribir los datos.

**Decisión.**
- Cada entrada crea una cabecera `entradas_inventario` (con consecutivo por empresa) y sus movimientos apuntan a ella
  (`movimientos.entrada_id`, nulo para los movimientos anteriores a la versión 1.1). No cambia el cálculo de existencias:
  `inventario_sede` sigue siendo la única fuente (D-11).
- Las observaciones se guardan en `entrada_observaciones`, una por fila, con autor y fecha, y **no se editan ni se
  borran** (solo inserción). Agregar una no sobrescribe las anteriores ni toca existencias.
- Una no conformidad puede nacer de una entrada (o de una de sus observaciones) y conserva el vínculo.
- **Registrar o gestionar una no conformidad o una garantía nunca modifica el inventario.** Si hay que dar de baja la
  mercancía, se hace con una salida (`deterioro`, `devolucion_proveedor`), que es una operación aparte, con sus
  propios permisos y su movimiento. Así no hay descuentos por duplicado ni existencias que cambien por un reporte.

**Código.** `model/inventario.py`, `service/entradas_service.py`, `service/calidad_service.py`.
**Pruebas.** `test_sig_calidad_entradas.py` (la no conformidad no cambia existencias ni movimientos).

<a id="d-31"></a>
## D-31 · Evidencias adjuntas guardadas en la base de datos, con límites estrictos

**Decisión.** Las evidencias de PQRS, no conformidades y garantías se guardan en `sig_adjuntos` (columna binaria), no en
el disco ni en un servicio externo. Motivos: la aplicación se despliega en contenedores sin volumen compartido, y así
las copias de seguridad de la base de datos incluyen las evidencias y el aislamiento por empresa se resuelve con las
mismas consultas. Límites: 3 MB por archivo, 5 por registro, solo JPEG, PNG, WebP y PDF.

Seguridad: el tipo se determina por los **primeros bytes** del archivo (no por la extensión ni por lo que declara el
navegador); el nombre se limpia y nunca se usa como ruta; la descarga se entrega siempre como adjunto con
`X-Content-Type-Options: nosniff`; se guarda el SHA-256; cada adjunto pertenece a exactamente un registro (restricción
en la base de datos) y solo lo ve quien puede ver ese registro.

**Descartado.** Almacenamiento en disco (se pierde al recrear el contenedor) y objetos externos (S3 y similares:
credenciales, costos y una dependencia nueva para un volumen pequeño de archivos). Si el volumen creciera, el servicio
`adjuntos_service` es el único lugar que habría que cambiar.

**Código.** `model/adjunto.py`, `service/adjuntos_service.py`, `controller/adjuntos_controller.py`. **Pruebas.** `test_sig_pqrs_adjuntos.py`.

<a id="d-32"></a>
## D-32 · Pausas activas: el servidor decide, el navegador solo muestra

**Contexto.** Las pausas deben aparecer solas a las personas que no administran, con un intervalo configurable, sin
repetirse ni solaparse y sin interrumpir una operación crítica.

**Decisión.**
- **Intervalo.** `sst_configuracion` guarda si las pausas están activas y el intervalo en minutos (1 a 480). Por defecto,
  60 minutos y activas. Las actividades (`sst_actividades`: mensaje, instrucciones, duración, recomendaciones de postura,
  ojos, manos y asiento) son editables por la administración; la primera vez que se consulta la configuración de una
  empresa se siembran ejercicios iniciales (una sola vez, aunque lleguen dos peticiones a la vez).
- **El servidor decide.** `POST /api/sig/sst/pausa/iniciar` solo crea una pausa si pasó el intervalo desde la última
  mostrada (con una tolerancia del 90 % por diferencias de reloj). Un índice único parcial garantiza una sola pausa
  abierta por persona: dos pestañas, o recargar la página, reciben la **misma** pausa, no otra. Una pausa abierta que
  nadie cierra se da por omitida a los 30 minutos para no bloquear la siguiente.
- **El navegador solo muestra.** Un planificador puro (`programacion.ts`) calcula cuándo preguntar; un canal
  `BroadcastChannel` coordina las pestañas abiertas del mismo navegador.
- **No interrumpe operaciones críticas.** La pausa **se aplaza** y se muestra cuando se libera: mientras haya un diálogo
  abierto (todos los formularios de la aplicación son diálogos), una venta o un traslado a medio armar, un guardado en
  curso, la persona esté escribiendo (se espera 8 segundos tras la última tecla) o la pestaña no esté visible. Cada
  pantalla lo declara con `lib/bloqueoPausas.ts`; el componente `Modal` lo hace por defecto. Si la persona estuvo
  ausente y ya tocaba, se le da una cortesía de 2 minutos al volver en lugar de interrumpirla de inmediato.
- **Administración excluida.** Quien tiene `sst.gestionar` no recibe pausas automáticas, pero puede ver el contenido y una
  vista previa en la sección SST.
- **Registro.** Cada pausa guarda fecha, persona, actividad (con el título copiado, por si luego se edita o se elimina la
  actividad) y si fue completada u omitida; la administración ve el cumplimiento por persona y por día.

**Descartado.** Decidir solo en el navegador (con `setInterval`): se duplicaría entre pestañas, se perdería al recargar
y no habría registro confiable.

**Código.** `service/sst_service.py`, `model/sst.py`, `features/sig/sst/*`, `lib/bloqueoPausas.ts`.
**Pruebas.** `test_sig_sst.py`, `programacion.test.ts`, `PausasActivas.test.tsx`, `bloqueoPausas.test.tsx`.

<a id="d-33"></a>
## D-33 · Gestión ambiental: lo real se cuenta, lo estimado exige parámetros documentados

**Contexto.** El requisito pide mostrar CO₂ evitado sin inventar cifras, distinguir lo real de lo estimado, no contar
ventas anuladas ni contar dos veces, y contar solo las categorías configuradas como vehículos.

**Decisión.**
- **Real:** unidades vendidas en ventas confirmadas y no anuladas, solo de categorías que la administración marcó como
  vehículo (`amb_categorias`). Se cuentan **siempre**, haya o no parámetros.
- **Estimado:** el CO₂ evitado. Solo existe si se configuran el factor de emisión de la red (`amb_configuracion`) y, por
  categoría, el recorrido anual, el consumo eléctrico y la emisión del vehículo de combustión de referencia.
  Sin eso, el registro queda con el CO₂ en blanco y el panel muestra «Pendiente de parametrización»: nunca un cero ni
  un valor por defecto.
- **Fórmula** (por unidad): `CO₂ (kg) = recorrido_anual × horizonte_años × (emisión_ref / 1000 − consumo / 100 × FE_red)`.
  La calcula el servidor con `Decimal` y redondea a gramos. No se recorta a cero: si los parámetros hicieran que el
  eléctrico emitiera más que la referencia, el resultado se muestra tal cual y no se oculta.
- **Una vez por línea de venta:** `amb_registros` tiene un índice único sobre `venta_item_id`. Registrar la venta crea
  los registros en la misma transacción; anular la venta los marca `anulado` (dejan de sumar, quedan en el historial).
- **El historial no se reescribe:** cada registro guarda los parámetros con los que se calculó. Cambiar la configuración
  afecta a las ventas nuevas y a los registros que seguían pendientes (se calculan al guardar la configuración o con el
  botón «Incorporar ventas anteriores»), no a lo ya calculado.
- **Sin valores por defecto escondidos.** El sistema no trae factor ni parámetros. La pantalla de configuración ofrece
  como sugerencia, no vinculante, el factor de la red colombiana que publica la UPME (0,220 kg CO₂e/kWh, año 2024); la
  persona debe aceptarlo y documentar la fuente. Los parámetros de vehículo son siempre de ingreso manual.
- Los datos de demostración (`cargar-demo-sig`) usan valores marcados como «de demostración» en el campo fuente.

**Descartado.** Valores por defecto para el recorrido y el consumo (serían cifras inventadas con apariencia de dato) y
recalcular el historial al cambiar la configuración (cambiaría cifras ya reportadas).

**Código.** `model/ambiental.py`, `service/ambiental_service.py`, `service/ventas_service.py` (ganchos al registrar y
anular), `features/sig/ambiental/*`. **Pruebas.** `test_sig_ambiental.py`, `calculos.test.ts`, `AmbientalPage.test.tsx`.

<a id="d-34"></a>
## D-34 · Métricas de error: el WAPE decide; RMSE y MAPE acompañan

**Contexto.** La evaluación de modelos pedía las métricas habituales de la literatura de pronóstico (MAE, RMSE, MAPE) y
el sistema solo informaba WAPE, MAE y sesgo.

**Decisión.** Cada serie y cada ejecución guardan ahora WAPE, MAE, RMSE, MAPE y sesgo, del modelo elegido y de la
línea base. La **elección del modelo sigue haciéndose con WAPE** (sin cambios).

- **MAPE solo sobre los días con ventas.** Con venta cero el cociente |error| / real no existe, y en una sede con
  productos de baja rotación eso ocurre casi todos los días. Calcularlo sobre todos los días lo dejaría indefinido o
  lo inflaría con divisiones por cifras muy pequeñas. Si en la validación no hubo ningún día con ventas, el MAPE es
  `null` y la pantalla muestra «—», nunca un 0 %.
- **RMSE en unidades por día**, para ver si el error se concentra en pocos días grandes (RMSE mucho mayor que MAE).
- **Globales por acumulación de sumas**, igual que el WAPE global: Σ error² / Σ días y Σ error porcentual / Σ días con
  ventas, no el promedio de los promedios por serie.
- **Sin migración.** Las métricas viven en columnas JSON (`predicciones.metricas`, `ejecuciones_prediccion.resumen`).
  Las ejecuciones anteriores no tienen RMSE ni MAPE y la interfaz las muestra como «—».

**Descartado.** Elegir con MAPE (sesgado por los días de venta baja y no definido con ceros) y recalcular el historial
de ejecuciones anteriores (no se conservan las series de validación).

**Código.** `ml/evaluacion.py`, `ml/pipeline.py`, `service/reportes_service.py`, `features/prediccion/*`.
**Pruebas.** `test_ml.py`, `test_prediccion.py`, `DetalleSerieModal.test.tsx`.

<a id="d-35"></a>
## D-35 · Reportes en PDF con ReportLab, para leer e imprimir

**Decisión.** `GET /api/reportes/{tipo}?formato=pdf` genera el PDF en el servidor con ReportLab (Python puro, con las
fuentes estándar del formato, que cubren el español). Tiene encabezado con empresa, usuario, fecha y filtros, el resumen
del reporte, la tabla con el encabezado repetido en cada página y el pie «Página X de Y». Se pone en horizontal cuando
el reporte tiene más de seis columnas.

- **Es para leer e imprimir, no para analizar:** se limita a 1.000 filas y lo dice dentro del documento. Excel y CSV
  siguen entregando hasta 50.000 filas. El límite sale de una medición: armar el PDF cuesta unos 0,2 ms de CPU por cada
  fila de 11 columnas (≈ 2 s para 1.000 filas, ≈ 4 s para 2.000).
- **Se arman en un hilo aparte:** el PDF, el Excel y el CSV se generan con `asyncio.to_thread`; si se armaran dentro de
  la corrutina, el servidor dejaría de atender al resto durante todo ese tiempo (RNF-011). *Matiz medido después:* con
  20 usuarios consultando, una exportación de Excel de 50.000 filas (≈ 16 s) igualmente retrasó a los demás (p95 de 160 ms
  a 2,5 s; ver [RENDIMIENTO.md](RENDIMIENTO.md#6-hallazgo-las-exportaciones-grandes-frenan-a-los-demás-usuarios)), porque
  generar el archivo es código de Python puro que compite por el procesador. El hilo evita el bloqueo total, no el
  retraso.
- **Mismo permiso, mismo alcance por sede y misma auditoría** que las otras exportaciones (`formato: pdf` queda en el
  registro).
- **El texto de la base de datos nunca se interpreta como marcado** (se escapa), y los caracteres que la fuente
  estándar no puede dibujar se reemplazan por «?» en lugar de aparecer como recuadros.
- **Dependencias nuevas:** `reportlab` y `pillow` (que reportlab exige), ambas con versión fijada.

**Descartado.** Convertir HTML a PDF con un navegador sin cabeza (agrega cientos de MB y un proceso externo al
contenedor) y generar el PDF en el navegador (el reporte quedaría sin auditoría del lado del servidor).

**Código.** `service/reportes_pdf.py`, `controller/reportes_controller.py`, `features/reportes/ReportesPage.tsx`.
**Pruebas.** `test_dashboard_reportes.py` (7 pruebas de PDF), `ReportesPage.test.tsx`.

<a id="d-36"></a>
## D-36 · Intervalo de predicción calibrado con datos reales de la demostración

**Decisión.** El intervalo de 80 % que muestra la interfaz se calcula como `Z₈₀ · 0,8 · σ · h^0,75` (antes
`Z₈₀ · σ · √h`), donde σ es la desviación del error de validación diario y *h* los días del horizonte
(`ESCALA_INTERVALO` y `EXPONENTE_HORIZONTE_INTERVALO` en `ml/pipeline.py`).

**Por qué.** Al contar cuántas veces la demanda real cayó dentro del intervalo en la prueba fuera de muestra
(`ml/evaluar_fuera_de_muestra.py`) la cobertura fue de **62 %** y no de 80 %: la fórmula con √h suponía errores
independientes entre días y subestimaba la incertidumbre acumulada. Con los parámetros nuevos la cobertura quedó entre
**78 % y 83 %** según el horizonte (7, 14 y 28 días).

**Límites que se declaran.** Los parámetros se ajustaron con los mismos datos sintéticos con los que se verificó, de modo
que la cobertura medida es optimista como estimación de lo que ocurriría con datos reales; deben revisarse con cada
empresa cuando acumule historial propio. Fuera de muestra, el sistema redujo el error absoluto total frente a la línea base en solo 2 % a 4 % (relativo);
se documenta tal cual en [`docs/PREDICCION.md`](PREDICCION.md#11-resultados-con-datos-de-demostración-rnf-030).

**Código.** `ml/pipeline.py`. **Pruebas.** `test_ml.py::test_el_margen_del_intervalo_sigue_la_formula_calibrada`.

<a id="d-37"></a>
## D-37 · Errores de entrada documentados y manejados de forma uniforme

**Decisión.** (1) Un número que no cabe en la base de datos (un identificador o filtro de 30 dígitos) se responde con
**422** y el formato de error habitual, no con 500; se resuelve en un solo manejador (`exception/manejadores.py`) en lugar de
acotar cada parámetro de las ~30 rutas afectadas. (2) El contrato OpenAPI declara el formato real de los errores 422
(`detail` en texto, `codigo`, `errores` por campo, `request_id`), no el que FastAPI documenta por defecto.

**Por qué.** Ambos hallazgos salieron de la prueba de contrato y fuzzing con Schemathesis (sección «Verificación frente a
OWASP» de [SEGURIDAD.md](SEGURIDAD.md)): 31 operaciones respondían 500 ante enteros fuera de rango y 97 operaciones
declaraban un cuerpo 422 distinto del real. El 500 no filtraba información (el mensaje era genérico), pero un fallo del
servidor ante una entrada inválida es un mal manejo de condiciones excepcionales (OWASP A10:2025).

**Descartado.** Limitar cada parámetro con `le=2147483647`: es fácil olvidar uno y no cubre los cuerpos JSON.

**Código.** `exception/excepciones.py`; tipos del frontend regenerados (`api.gen.ts`).
**Pruebas.** `test_setup_auth.py::test_valores_que_la_base_no_admite_responden_422_y_no_500` (PostgreSQL),
`test_un_valor_que_no_cabe_en_la_base_se_reconoce_como_entrada_invalida`,
`test_el_contrato_describe_el_formato_real_de_los_errores_de_validacion`.

<a id="d-38"></a>
## D-38 · Las recomendaciones se validan por simulación, no solo con pruebas unitarias

**Decisión.** Además de las pruebas que comprueban que cada regla calcula lo que dice, el efecto de las recomendaciones sobre los
quiebres de stock se evalúa repitiendo un período reciente con la demanda real de la base (`ml/simular_recomendaciones.py`) y
comparando cuatro políticas: sin reposición, mínimos y máximos fijos, las reglas de Inventia con promedio simple y Inventia
completo. Se reporta también qué pasa si solo se acepta una parte de las sugerencias.

**Por qué.** Una prueba unitaria demuestra que la regla se aplica, no que sirva. La simulación permite medir, con un intervalo, si
las reglas pierden menos ventas que lo que haría una pyme con niveles fijos, y separar qué parte del beneficio viene de las
reglas y qué parte del modelo de pronóstico. Resultado con datos sintéticos (§12 de [PREDICCION.md](PREDICCION.md)): las reglas
superan a los mínimos y máximos fijos por 5,2 puntos de la demanda (IC 95 % 3,4 a 7,0) con 30 % menos inventario; el pronóstico del
sistema no mejora las decisiones frente al promedio de 28 días (0,0 puntos, IC −0,9 a 1,0); y con 40 % de aceptación las políticas
son indistinguibles.

**Consecuencias.** La memoria atribuye el beneficio a las reglas parametrizables y no al modelo de IA, y presenta la aceptación
de las recomendaciones como condición del beneficio. La simulación no sustituye la evaluación con una empresa real: usa datos
sintéticos y supuestos (plazo exacto, sin mínimos de compra ni límite de capital) declarados en el documento.

**Descartado.** Presentar solo el escenario con 100 % de aceptación, que es el más favorable.

**Código.** `ml/simular_recomendaciones.py`. **Resultados.** `ml/resultados/simulacion_resumen.json`.

<a id="d-39"></a>
## D-39 · Estructura por capas con los nombres de carpeta de Spring y sin capa `repository`

**Decisión.** El backend sigue siendo un monolito por capas (`controller` → `service` → `model`). Las carpetas se nombran como en un
proyecto Spring para que cualquiera que conozca ese esquema se oriente: `controller`, `dto`, `service`, `model`, `security`,
`exception`, `specification` y `mapper`, más `config` y `util`. Los filtros dinámicos de consulta se separaron de los servicios
(`specification/`) y las conversiones de entidad a DTO que no consultan la base se separaron también (`mapper/`). Las consultas a
la base siguen dentro de cada servicio: no hay carpeta `repository`.

**Por qué.** Los nombres anteriores (`api`, `schemas`, `models`, `services`, `core`) eran correctos pero propios del ecosistema
FastAPI y dificultaban la lectura a quien viene de Spring. Un monolito por capas es la arquitectura adecuada para una pyme de
pocas sedes y un equipo pequeño: una sola unidad de despliegue, transacciones simples y aislamiento por empresa en un solo lugar.
Microservicios o una arquitectura hexagonal completa añadirían complejidad operativa sin un problema real que resolver.

**Consecuencias.** El cambio fue solo de organización: no se modificó ninguna regla de negocio, ruta ni contrato (el contrato OpenAPI
conserva las mismas rutas y operaciones) y las 214 pruebas pasan sin cambios de comportamiento. Los módulos del paquete `ml` no se
movieron porque son cálculo puro sin base de datos.

**Descartado.** Crear una capa `repository` con una clase por tabla: los servicios ejecutan cerca de 270 consultas, muchas de ellas
uniones y agregaciones específicas de un caso de uso, y envolverlas en repositorios genéricos sería una indirección sin beneficio
(con SQLAlchemy, la sesión ya cumple el papel de repositorio y unidad de trabajo). Se podrá extraer si el volumen de consultas
repetidas lo justifica.

**Código.** Todo `backend/app/`. **Guía.** [GUIA_ESTRUCTURA.md](GUIA_ESTRUCTURA.md).
