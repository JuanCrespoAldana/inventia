# Decisiones de diseño

Registro de las decisiones técnicas y funcionales que no estaban resueltas por el documento de grado, o en las que
la implementación se aparta de él por una razón concreta. Cada una indica el motivo, la alternativa descartada y
dónde se refleja en el código. Los identificadores `D-03`, `D-04`, `D-05` y `D-28` coinciden con los citados en
`backend/app/core/permisos.py`.

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

**Código.** `setup_service.py`, `api/setup.py`, `core/config.py`. **Pruebas.** `test_no_existe_registro_publico`,
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

**Código.** `core/permisos.py`, `api/pqrs.py`, `api/calidad.py`, `api/sst.py`, `api/ambiental.py`, `bootstrap.py`.
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

**Código.** `models/pqrs.py`, `services/pqrs_service.py`. **Pruebas.** `test_sig_pqrs_adjuntos.py`.

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

**Código.** `models/inventario.py`, `services/entradas_service.py`, `services/calidad_service.py`.
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

**Código.** `models/adjunto.py`, `services/adjuntos_service.py`, `api/adjuntos.py`. **Pruebas.** `test_sig_pqrs_adjuntos.py`.

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

**Código.** `services/sst_service.py`, `models/sst.py`, `features/sig/sst/*`, `lib/bloqueoPausas.ts`.
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

**Código.** `models/ambiental.py`, `services/ambiental_service.py`, `services/ventas_service.py` (ganchos al registrar y
anular), `features/sig/ambiental/*`. **Pruebas.** `test_sig_ambiental.py`, `calculos.test.ts`, `AmbientalPage.test.tsx`.
