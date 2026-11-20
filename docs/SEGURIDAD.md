# Seguridad

Describe las medidas de seguridad implementadas, cómo comprobarlas y qué queda bajo responsabilidad de quien
despliega el sistema. Cubre RN-009 y RNF-022 a RNF-028.

## Resumen de controles

| Área | Control | Dónde |
|---|---|---|
| Contraseñas | Argon2id; política: 8 a 128 caracteres con mayúscula, minúscula, número y carácter especial | `security/autenticacion.py`, `dto/comunes_dto.py` |
| Sesión | JWT firmado (HS256) con vencimiento (60 min por defecto), identificador único y **versión de contraseña**: cambiar la contraseña invalida todos los tokens anteriores | `security/autenticacion.py`, `security/dependencias.py` |
| Fuerza bruta | Bloqueo temporal de la cuenta (5 intentos → 15 min, configurable) y límite de solicitudes por IP en login, recuperación, cambio de contraseña y configuración inicial | `auth_service.py`, `security/limiter.py` |
| Enumeración de usuarios | En el ingreso: mismo mensaje y mismo coste de cálculo si el correo no existe (hash de relleno). En la recuperación: la respuesta es idéntica exista o no la cuenta | `auth_service.py` |
| Recuperación | Código de 6 dígitos, solo se guarda su huella SHA-256, un solo uso, vence a los 15 min, máx. 5 intentos; el paso final exige un token de sesión de un solo uso | `auth_service.py`, `model/password_reset_token.py` |
| Primer administrador | No existe registro público. La configuración inicial solo funciona mientras no haya ninguna empresa, exige `SETUP_TOKEN` (obligatorio en producción) y está protegida contra ejecuciones simultáneas | `setup_service.py`, `config.py` |
| Autorización | 51 permisos; cada ruta exige permisos en el servidor; alcance de sede aplicado en cada consulta | `security/permisos.py`, `security/dependencias.py`, `security/acceso.py` |
| Aislamiento | `empresa_id` en todas las tablas de negocio; las consultas lo toman del contexto autenticado, nunca del cuerpo ni de la URL | `service/*` |
| Escalada de privilegios | No se puede conceder un permiso que uno no tiene, ni crear un rol más poderoso que el propio; no se puede quitar el rol ni inhabilitar al último administrador | `rol_service.py`, `usuario_service.py` |
| Auditoría | Accesos (exitosos y fallidos) y operaciones, con usuario, IP, resultado y `request_id`; tabla de solo inserción con disparador en PostgreSQL; nunca guarda contraseñas ni llaves | `auditoria_service.py`, `model/base.py` |
| Integridad | Restricciones en la base (incluidas las tres reglas del MER que impone el motor: alerta ↔ existencia por sede, un traslado por recomendación, ejecución obligatoria), transacciones atómicas, movimientos inmutables | `model/*`, `alembic/versions/0005_integridad_mer.py`, `service/inventario_service.py` |
| Cabeceras HTTP | `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`, `Permissions-Policy`; en nginx además `Content-Security-Policy` restrictiva | `security/contexto.py`, `frontend/nginx.conf` |
| CORS | Solo `FRONTEND_URL` y `CORS_ORIGINS`; sin credenciales (el token va en la cabecera `Authorization`, no en cookies) | `main.py` |
| Errores | Los errores internos devuelven un mensaje genérico y un `request_id`; el detalle técnico solo queda en el registro del servidor | `exception/excepciones.py` |
| Base de datos | SSL obligatorio para servidores remotos (`DATABASE_SSL=auto`); consultas parametrizadas (SQLAlchemy) | `config/database.py` |
| Contenedores | Imagen del backend y de nginx sin privilegios de administrador; sin secretos en las imágenes; PostgreSQL publicado solo en `127.0.0.1` | `Dockerfile`, `docker-compose.yml` |
| Dependencias | Versiones fijadas y archivo de bloqueo; `pip-audit`, `npm audit` y Bandit sin hallazgos al 27/10/2026; Dependabot semanal; sin cargar scripts ni fuentes de terceros en el navegador | `requirements.txt`, `package-lock.json`, `.github/` |

## Roles de fábrica

Cada empresa recibe cinco roles al crearse. Los administradores pueden crear roles adicionales y ajustar sus
permisos desde la pantalla **Roles y permisos**; los cinco del sistema no se pueden eliminar ni cambiar de permisos.

| Rol | Alcance | Puede | No puede |
|---|---|---|---|
| Administrador | Empresa | Todo: empresa, sedes, usuarios, roles, catálogo, operaciones, reportes, auditoría completa | — |
| Gerente | Empresa | Consultar inventario consolidado, ventas, traslados, alertas, predicciones; aprobar recomendaciones; reportes; historial de operaciones | Registrar operaciones, administrar usuarios o roles, ver accesos de otros usuarios |
| Encargado de sede | Sede | Operar su sede (entradas, salidas, ajustes, ventas, anulaciones); solicitar, aprobar y confirmar traslados; configurar mínimos y máximos; ver y aprobar recomendaciones | Ver otras sedes, administrar usuarios, ver el consolidado |
| Usuario de inventario | Sede | Entradas, salidas, ajustes y ventas de su sede; solicitar y confirmar traslados; consultar existencias y alertas | Anular ventas, aprobar traslados, configurar niveles, ver predicciones |
| Analista de compras | Empresa | Consultar el consolidado, ventas y alertas; generar predicciones y recomendaciones; aprobar recomendaciones; reportes de compras | Registrar operaciones de inventario, administrar usuarios |

Las diferencias frente a la matriz de casos de uso del documento de grado están justificadas en
[DECISIONES.md](DECISIONES.md).

## Cómo se comprobó

Cada afirmación de la tabla tiene una prueba automatizada (ver [TRAZABILIDAD.md](TRAZABILIDAD.md)). Las más
relevantes para seguridad:

| Comportamiento | Prueba |
|---|---|
| No hay registro público; la configuración inicial exige token y solo ocurre una vez | `test_no_existe_registro_publico`, `test_setup_exige_token_si_esta_definido`, `test_setup_solo_una_vez` |
| Mensaje genérico y auditoría en credenciales incorrectas | `test_login_incorrecto_mensaje_generico_y_auditado` |
| Bloqueo por intentos fallidos | `test_bloqueo_tras_intentos_fallidos` |
| Límite de solicitudes por IP en el ingreso (el 11.º intento en un minuto recibe 429) | `test_limite_de_solicitudes_por_ip_en_el_ingreso` |
| Cambiar la contraseña invalida los tokens anteriores | `test_cambiar_password_invalida_tokens_anteriores` |
| Ninguna respuesta expone hashes ni secretos | `test_ninguna_respuesta_expone_hash_ni_secretos` |
| Los errores internos no filtran detalles | `test_error_interno_no_filtra_detalles` |
| Cabeceras de seguridad y `X-Request-ID` | `test_cabeceras_de_seguridad_y_request_id` |
| Una empresa no ve datos de otra | `test_empresas_no_ven_datos_de_otras`, `test_aislamiento_de_inventario_entre_empresas`, `test_una_llave_nunca_ve_datos_de_otra_empresa` |
| La base de datos impone las reglas del MER (CRF-MER-01) | `test_una_alerta_solo_puede_pertenecer_a_una_existencia_por_sede`, `test_una_recomendacion_da_lugar_a_lo_sumo_a_un_traslado`, `test_toda_recomendacion_nace_de_una_ejecucion_de_prediccion` |
| El MER publicado coincide con los modelos | `tests/test_mer_consistente.py` |
| Un usuario de sede no opera ni ve otra sede | `test_encargado_de_sede_solo_ve_su_sede`, `test_usuario_de_sede_no_opera_en_otra_sede` |
| No se puede escalar privilegios | `test_no_se_puede_escalar_privilegios_creando_roles` |
| Protección del último administrador | `test_no_se_puede_inhabilitar_al_ultimo_administrador`, `test_no_se_puede_quitar_el_rol_al_ultimo_administrador` |
| La auditoría no guarda secretos y no se puede alterar | `test_auditoria_registra_altas_y_cambios_sin_secretos`, `test_auditoria_y_movimientos_son_de_solo_insercion` |

## Verificación frente a OWASP Top 10:2025

La lista [OWASP Top 10:2025](https://owasp.org/Top10/) resume los diez riesgos más frecuentes en aplicaciones web. Esta sección
compara cada uno con lo que hace el sistema y con lo que **se comprobó** (herramientas y resultados), y dice qué queda
pendiente. Es una autoevaluación hecha por el equipo con herramientas automáticas; **no sustituye** una auditoría ni una
prueba de penetración independiente.

### Qué se ejecutó y qué resultó

| Herramienta | Qué revisa | Resultado (20 de noviembre de 2026, versión 1.2.0) |
|---|---|---|
| Pruebas automatizadas del proyecto (pytest, SQLite y PostgreSQL) | Los controles de las tablas anteriores | 251 pruebas, todas pasan; cobertura de líneas del backend: **84,6 %** (8.144 de 9.625 instrucciones; no se mide cobertura de ramas). Se mide con `concurrency = greenlet,thread` para contar el código asíncrono; en la 1.1.0 una medición sin esa opción dio 77 % y subestimaba lo ejecutado. Sin el asistente de consultas la cobertura es de 90,7 % (5.258 de 5.798); el asistente, que se agregó después de las mediciones de octubre, llega a 75,4 %. Las líneas menos cubiertas son la línea de comandos (`cli.py`, 30 %) y el envío de correo (`email_service.py`, 32 %), que no se prueban contra servicios reales, y varios módulos de respuestas del asistente (de 17 % a 57 %) |
| Bandit 1.9.4 | Análisis estático del código de la API (14.624 líneas) | **0 hallazgos**. Queda una prueba omitida con `# nosec B406` y su motivo (escape de texto para el PDF, no lectura de XML). En la 1.1.0 se habían atendido 3 hallazgos: el `assert` que no se ejecuta con `python -O` (se cambió por una excepción explícita) y dos usos justificados; la marca del generador pseudoaleatorio salió con los datos de demostración del SIG |
| pip-audit 2.10.1 | Vulnerabilidades conocidas en las 54 dependencias de Python | **0** (en la 1.1.0, tras subir PyJWT de 2.13.0 a 2.15.1, que tenía 15 avisos de seguridad) |
| npm audit | Vulnerabilidades conocidas en el frontend (232 paquetes; 78 de producción) | **0** (en la 1.1.0, tras actualizar dependencias) |
| Sonda propia [`infra/seguridad/sonda_seguridad.py`](../infra/seguridad/sonda_seguridad.py) | 16 comprobaciones contra una API en ejecución de 86 operaciones (ver abajo) | **16 de 16** |
| Schemathesis 4.33.4 · [`infra/seguridad/fuzz_api.sh`](../infra/seguridad/fuzz_api.sh) | Genera entradas válidas e inválidas para cada operación a partir del contrato OpenAPI y exige que ninguna produzca error 5xx ni una respuesta distinta de la documentada | **Versión 1.2.0:** 73 de 86 operaciones; con sesión de administrador, semilla 20261026 y tope de 900 s: **60.585 casos generados, 0 fallos**; pasaron las fases de cobertura, fuzzing y la prueba con estado (1.038 escenarios encadenados). **Versión 1.1.0** (26 de octubre, 113 de 131 operaciones): 1.ª corrida con 31 operaciones con error 500 y 97 con respuesta distinta del contrato; 2.ª corrida con 2 operaciones con error 500; corrida final con 47.959 casos y 0 fallos |
| OWASP ZAP (escáner dinámico) | Rastreo y ataque automático de la aplicación | **No se ejecutó**: no se pudo descargar en el entorno de pruebas |

**Lo que el fuzzing encontró y se corrigió** (decisión [D-37](DECISIONES.md#d-37)): un número que no cabe en la base de
datos (un identificador o filtro de 30 dígitos) o un byte nulo en un texto de búsqueda hacían que la API respondiera 500 en
unas 30 rutas, y el contrato OpenAPI describía el error 422 con un formato distinto del real. Ninguno exponía datos (el
mensaje de error era genérico), pero eran fallos del servidor ante entradas inválidas. Ahora responden 422 con el formato
habitual y hay pruebas automatizadas que lo garantizan.

**Límites del fuzzing.** En la 1.2.0 se excluyeron 13 de las 86 operaciones: las rutas de autenticación (inicio de sesión y
recuperación de contraseña limitan por IP), la configuración inicial, la ejecución de predicciones (trabajo pesado), y las rutas que
cambian o borran usuarios y que restablecen contraseñas (el fuzzing se habría bloqueado a sí mismo la sesión).
Además, la herramienta avisó de que una operación (`POST /api/productos`) respondió 404 una y otra vez (necesita una categoría que
ninguna otra operación del contrato crea con los datos generados) y de que 29 operaciones rechazaron la mayoría de las entradas
generadas porque las reglas de negocio son más estrictas que el contrato; esas operaciones se ejercitaron menos a fondo. La fase de
fuzzing agotó el tope de tiempo (900 s), de modo que no se agotó el espacio de casos. Se corrió con una sola semilla.

**Qué comprueba la sonda.** (1) 78 de las 86 operaciones exigen token; las 8 públicas lo son por diseño (estado y
ejecución de la configuración inicial, inicio de sesión, los tres pasos de recuperación de contraseña y dos de salud).
(2) Un token con la firma alterada y otro con algoritmo `none` reciben 401. (3) Un encargado de sede recibe 403 al consultar usuarios y
datos de la empresa y al crear usuarios o roles o ejecutar predicciones; no ve las existencias de otra sede ni los accesos de
otras personas en la auditoría.
(4) Un origen no autorizado no recibe cabeceras CORS y las cabeceras de seguridad están presentes. (5) Cinco cargas
maliciosas (comillas y `OR` lógico, `DROP TABLE`, HTML con `<script>`, byte nulo, recorrido de rutas) enviadas a cuatro
listados no producen error 5xx ni se reflejan en la respuesta. (6) Cuerpos malformados
(`{no es json`, `[]`, `null`, tipos equivocados) y rutas inexistentes dan 4xx controlado sin trazas. (7) Tras cinco intentos
fallidos el sexto recibe 423 (cuenta bloqueada) y la clave correcta también queda rechazada; un correo inexistente recibe
el mismo mensaje que uno existente. (8) Los intentos fallidos quedan en la auditoría. La sonda toma muestras representativas; no
recorre la matriz completa de cinco roles por 86 operaciones.

### Correspondencia con cada categoría

| Categoría (2025) | Qué hace el sistema | Cómo se verificó | Pendiente o fuera de alcance |
|---|---|---|---|
| **A01** Control de acceso roto | 51 permisos exigidos en el servidor en cada ruta; alcance por sede aplicado en cada consulta; `empresa_id` tomado siempre del contexto autenticado; no se puede escalar privilegios ni dejar la empresa sin administrador | Sonda (puntos 1 y 3); pruebas de aislamiento entre empresas y entre sedes; fuzzing con rol administrador | La sonda no prueba cada rol contra cada ruta; esa cobertura la dan las pruebas por módulo |
| **A02** Configuración de seguridad incorrecta | Cabeceras de seguridad y política de contenido en nginx; CORS restringido a los orígenes configurados; `DOCS_API_ACTIVA=false` oculta la documentación; `SECRET_KEY` de 32 caracteres mínimo y `SETUP_TOKEN` obligatorio en producción; contenedores sin privilegios | Sonda (punto 4); prueba del interruptor de documentación | HTTPS y HSTS dependen del proxy de quien despliega; las imágenes de Docker no se construyeron ni se escanearon en el entorno de pruebas (solo las construye el CI); la política de contenido admite estilos en línea; sin ZAP |
| **A03** Fallas en la cadena de suministro | Versiones fijadas y archivos de bloqueo; sin scripts ni fuentes de terceros en el navegador; trabajo informativo de seguridad en el CI (`pip-audit`, `npm audit`, Bandit) y Dependabot semanal | pip-audit y npm audit sin vulnerabilidades; PyJWT actualizado | Sin lista de materiales de software (SBOM); sin firma de imágenes ni de artefactos; las acciones del CI y las imágenes base se referencian por etiqueta, no por huella |
| **A04** Fallas criptográficas | Contraseñas con Argon2id; tokens firmados (HS256) con vencimiento; códigos de recuperación guardados solo como huella SHA-256; SSL obligatorio hacia bases remotas | Sonda (punto 2); pruebas de que ninguna respuesta expone hashes ni secretos | HS256 es simétrico y no hay rotación de claves; los códigos de 6 dígitos con SHA-256 sin sal dependen del límite de intentos y de la vigencia de 15 min, no del hash; el cifrado de datos en reposo depende del proveedor de la base |
| **A05** Inyección | Consultas parametrizadas con SQLAlchemy; validación con Pydantic; el frontend no inserta HTML sin escapar (sin `innerHTML` ni `dangerouslySetInnerHTML` en el código); los CSV neutralizan fórmulas; el PDF escapa el texto | Bandit sin hallazgos; sonda (punto 5); ≈48.000 casos de fuzzing en la corrida final | Sin revisión manual de cada pantalla ni escáner dinámico de XSS |
| **A06** Diseño inseguro | Movimientos y auditoría de solo inserción (disparadores); bloqueos consultivos y actualizaciones atómicas; ninguna recomendación se ejecuta sin aprobación humana | Pruebas de concurrencia sobre PostgreSQL; tras 50 usuarios escribiendo a la vez, 5 comprobaciones de consistencia con 0 violaciones ([RENDIMIENTO.md](RENDIMIENTO.md)) | Hay análisis de riesgos del proyecto, pero no un modelo de amenazas formal por componente |
| **A07** Fallas de autenticación | Sin registro público; política de contraseñas; bloqueo tras 5 intentos durante 15 min; límite por IP; mensaje idéntico exista o no la cuenta; recuperación con código de un solo uso; cambiar la contraseña invalida los tokens anteriores | Sonda (punto 7); pruebas de bloqueo, límite y recuperación | Sin autenticación de dos factores; sin consulta de contraseñas filtradas; el token no se puede revocar individualmente; el límite por IP vive en la memoria de cada proceso |
| **A08** Fallas de integridad de software o datos | Dependencias fijadas; migraciones versionadas; historiales y auditoría inmutables aun con SQL directo; el código no deserializa datos no confiables (sin `pickle`, `yaml.load`, `eval` ni modelos guardados: la predicción se recalcula) | Revisión del código; pruebas de inmutabilidad y de migración | Sin firma de imágenes ni de respaldos |
| **A09** Fallas de registro y alertas | Auditoría de accesos exitosos y fallidos, operaciones y exportaciones, con usuario, IP, resultado y `request_id`; nunca guarda secretos; `/api/health/ready` para monitoreo externo | Sonda (punto 8); pruebas de auditoría | No hay alertas automáticas (correo, SIEM) ante patrones sospechosos más allá del bloqueo de cuenta; sin política de retención de la auditoría |
| **A10** Mal manejo de condiciones excepcionales | Manejadores globales: error genérico con `request_id` (sin trazas), formato único de errores 4xx, transacciones con reversión, tiempo máximo de la predicción y cierre de ejecuciones colgadas al arrancar | Sonda (punto 6); el fuzzing encontró dos defectos reales (enteros fuera de rango y byte nulo) y quedaron corregidos (D-37) | Un error inesperado de la base (p. ej. un interbloqueo) sigue respondiendo 500 genérico, por diseño |

## Responsabilidades de quien despliega

Estas medidas **no** las puede resolver el código; la guía paso a paso está en [DESPLIEGUE.md](DESPLIEGUE.md).

1. **HTTPS.** La aplicación no termina TLS. Debe publicarse detrás de un proxy o plataforma que ofrezca HTTPS
   (RNF-027). Sin HTTPS, el token viajaría sin cifrar. Una vez con HTTPS, se recomienda añadir
   `Strict-Transport-Security` en ese proxy.
2. **Secretos.** Generar valores propios y únicos para `SECRET_KEY`, `SETUP_TOKEN`, la contraseña de PostgreSQL y
   las credenciales de correo. No subirlos a Git ni compartirlos. Rotarlos si alguna vez se expusieron.
3. **`TRUST_PROXY_HEADERS`.** Activarlo solo detrás de un proxy de confianza que reescriba `X-Forwarded-For`
   (el nginx incluido lo hace). Si se activa sin proxy, cualquier cliente podría falsear su IP y evadir el
   límite de intentos.
4. **Base de datos.** No exponer el puerto de PostgreSQL a Internet. Usar un usuario con permisos acotados.
5. **Respaldos.** Programar respaldos y guardarlos fuera del servidor (ver `infra/scripts/`).
6. **Correo.** Para que la recuperación de contraseña funcione hay que configurar SMTP. Con Gmail se necesita una
   «contraseña de aplicación», no la contraseña de la cuenta.
7. **Actualizaciones.** Revisar periódicamente las dependencias (`pip list --outdated`, `npm outdated`) y los
   avisos de seguridad de sus autores.

## Limitaciones conocidas

- **No hay autenticación de dos factores.** Es una mejora razonable para una siguiente versión.
- **El token de sesión no se puede revocar individualmente** (solo vence o se invalida al cambiar la contraseña).
  «Cerrar sesión» elimina el token del navegador y registra el evento, pero un token copiado seguiría valiendo
  hasta que venza. Reducir `ACCESS_TOKEN_EXPIRE_MINUTES` acota ese riesgo.
- **El token se guarda en el navegador** (no en una cookie `HttpOnly`). Esto evita ataques CSRF, pero un fallo de
  tipo XSS podría robarlo; por eso la política de contenido de nginx bloquea scripts de otros orígenes y la
  aplicación no inserta HTML sin escapar.
- **La política de contenido permite estilos en línea** (`style-src 'unsafe-inline'`) porque los gráficos y la
  librería de animación aplican estilos dinámicos. No permite scripts en línea.
- **El límite de solicitudes está en memoria del proceso.** Con varias réplicas de la API cada una cuenta por
  separado. El bloqueo por cuenta sí es global porque vive en la base de datos.
- **No se realizó una prueba de penetración independiente ni un escaneo dinámico con OWASP ZAP.** Los controles se
  verificaron con pruebas automatizadas propias, análisis estático, auditoría de dependencias y fuzzing del contrato
  (ver «Verificación frente a OWASP Top 10:2025»), no con una auditoría externa.
- **Recuperación de contraseña:** la respuesta es idéntica exista o no el correo, pero cuando existe el servidor
  además guarda el código y envía un correo, así que un atacante paciente podría distinguir ambos casos por el
  tiempo de respuesta. El espacio de 6 dígitos es pequeño: la protección real son los 5 intentos y los 15 minutos
  de vigencia, y el límite de solicitudes por IP.
- **La política de contraseñas no consulta listas de contraseñas filtradas.**

## Cómo informar una vulnerabilidad

Este proyecto es académico. Si encuentra una vulnerabilidad, repórtela de forma privada al autor del proyecto en
lugar de publicarla.
