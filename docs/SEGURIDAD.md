# Seguridad

Describe las medidas de seguridad implementadas, cómo comprobarlas y qué queda bajo responsabilidad de quien
despliega el sistema. Cubre RN-009 y RNF-022 a RNF-028.

## Resumen de controles

| Área | Control | Dónde |
|---|---|---|
| Contraseñas | Argon2id; política: 8 a 128 caracteres con mayúscula, minúscula, número y carácter especial | `core/security.py`, `schemas/comunes.py` |
| Sesión | JWT firmado (HS256) con vencimiento (60 min por defecto), identificador único y **versión de contraseña**: cambiar la contraseña invalida todos los tokens anteriores | `core/security.py`, `api/deps.py` |
| Fuerza bruta | Bloqueo temporal de la cuenta (5 intentos → 15 min, configurable) y límite de solicitudes por IP en login, recuperación, cambio de contraseña y configuración inicial | `auth_service.py`, `core/limiter.py` |
| Enumeración de usuarios | En el ingreso: mismo mensaje y mismo coste de cálculo si el correo no existe (hash de relleno). En la recuperación: la respuesta es idéntica exista o no la cuenta | `auth_service.py` |
| Recuperación | Código de 6 dígitos, solo se guarda su huella SHA-256, un solo uso, vence a los 15 min, máx. 5 intentos; el paso final exige un token de sesión de un solo uso | `auth_service.py`, `models/password_reset_token.py` |
| Primer administrador | No existe registro público. La configuración inicial solo funciona mientras no haya ninguna empresa, exige `SETUP_TOKEN` (obligatorio en producción) y está protegida contra ejecuciones simultáneas | `setup_service.py`, `config.py` |
| Autorización | 61 permisos; cada ruta exige permisos en el servidor; alcance de sede aplicado en cada consulta | `core/permisos.py`, `api/deps.py`, `core/acceso.py` |
| Aislamiento | `empresa_id` en todas las tablas de negocio; las consultas lo toman del contexto autenticado, nunca del cuerpo ni de la URL | `services/*` |
| Escalada de privilegios | No se puede conceder un permiso que uno no tiene, ni crear un rol más poderoso que el propio; no se puede quitar el rol ni inhabilitar al último administrador | `rol_service.py`, `usuario_service.py` |
| Auditoría | Accesos (exitosos y fallidos) y operaciones, con usuario, IP, resultado y `request_id`; tabla de solo inserción con disparador en PostgreSQL; nunca guarda contraseñas ni llaves | `auditoria_service.py`, `models/base.py` |
| Integridad | Restricciones en la base, transacciones atómicas, movimientos inmutables | `models/*`, `services/inventario_service.py` |
| Agentes de IA | Llaves de solo lectura: hash SHA-256, alcances, sede opcional, vencimiento, revocación; las denegaciones quedan en auditoría | `agentes_service.py` |
| Cabeceras HTTP | `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`, `Permissions-Policy`; en nginx además `Content-Security-Policy` restrictiva | `core/contexto.py`, `frontend/nginx.conf` |
| CORS | Solo `FRONTEND_URL` y `CORS_ORIGINS`; sin credenciales (el token va en la cabecera `Authorization`, no en cookies) | `main.py` |
| Errores | Los errores internos devuelven un mensaje genérico y un `request_id`; el detalle técnico solo queda en el registro del servidor | `core/exceptions.py` |
| Base de datos | SSL obligatorio para servidores remotos (`DATABASE_SSL=auto`); consultas parametrizadas (SQLAlchemy) | `core/database.py` |
| Evidencias adjuntas (SIG) | Solo JPEG, PNG, WebP y PDF, reconocidos por sus **primeros bytes** (no por extensión ni por el tipo que declara el navegador); 3 MB por archivo y 5 por registro; nombre limpiado y nunca usado como ruta; el contenido vive en la base de datos y se descarga siempre como adjunto con `nosniff`; solo lo ve quien puede ver el registro | `services/adjuntos_service.py`, `api/adjuntos.py` |
| Historiales del SIG | `pqrs_historial`, `no_conformidad_historial`, `garantia_historial` y `entrada_observaciones` son de solo inserción (disparador) | `alembic/versions/0004_sig.py` |
| Contenedores | Imagen del backend y de nginx sin privilegios de administrador; sin secretos en las imágenes; PostgreSQL publicado solo en `127.0.0.1` | `Dockerfile`, `docker-compose.yml` |
| Dependencias | Versiones fijadas y archivo de bloqueo; sin cargar scripts ni fuentes de terceros en el navegador | `requirements.txt`, `package-lock.json` |

## Roles de fábrica

Cada empresa recibe cinco roles al crearse. Los administradores pueden crear roles adicionales y ajustar sus
permisos desde la pantalla **Roles y permisos**; los cinco del sistema no se pueden eliminar ni cambiar de permisos.

| Rol | Alcance | Puede | No puede |
|---|---|---|---|
| Administrador | Empresa | Todo: empresa, sedes, usuarios, roles, catálogo, operaciones, reportes, auditoría completa, llaves de agentes | — |
| Gerente | Empresa | Consultar inventario consolidado, ventas, traslados, alertas, predicciones; aprobar recomendaciones; reportes; historial de operaciones | Registrar operaciones, administrar usuarios o roles, ver accesos de otros usuarios |
| Encargado de sede | Sede | Operar su sede (entradas, salidas, ajustes, ventas, anulaciones); solicitar, aprobar y confirmar traslados; configurar mínimos y máximos; ver y aprobar recomendaciones | Ver otras sedes, administrar usuarios, ver el consolidado |
| Usuario de inventario | Sede | Entradas, salidas, ajustes y ventas de su sede; solicitar y confirmar traslados; consultar existencias y alertas | Anular ventas, aprobar traslados, configurar niveles, ver predicciones |
| Analista de compras | Empresa | Consultar el consolidado, ventas y alertas; generar predicciones y recomendaciones; aprobar recomendaciones; reportes de compras | Registrar operaciones de inventario, administrar usuarios |

**Sistema Integrado de Gestión (SIG).** Los nueve permisos nuevos se reparten así (D-28): todos los roles pueden enviar
PQRS y consultar los apartados de SST, calidad y gestión ambiental; el Encargado de sede y el Usuario de inventario además
reportan no conformidades y garantías de su sede; solo el Administrador gestiona PQRS, pausas activas, el estado de
calidad y los parámetros ambientales. El Gerente y el Analista de compras consultan pero no reportan.
Quien tenga `sst.gestionar` no recibe pausas activas automáticas.

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
| Un usuario de sede no opera ni ve otra sede | `test_encargado_de_sede_solo_ve_su_sede`, `test_usuario_de_sede_no_opera_en_otra_sede` |
| No se puede escalar privilegios | `test_no_se_puede_escalar_privilegios_creando_roles` |
| Protección del último administrador | `test_no_se_puede_inhabilitar_al_ultimo_administrador`, `test_no_se_puede_quitar_el_rol_al_ultimo_administrador` |
| La auditoría no guarda secretos y no se puede alterar | `test_auditoria_registra_altas_y_cambios_sin_secretos`, `test_auditoria_y_movimientos_son_de_solo_insercion` |
| Una persona solo ve sus PQRS; solo quien gestiona ve las de todos | `test_pqrs_flujo_completo`, `test_pqrs_aisladas_entre_empresas` (SIG) |
| Las evidencias rechazan archivos peligrosos, falsos o excesivos y respetan la visibilidad del registro | `test_adjuntos_rechaza_archivos_peligrosos_o_excesivos`, `test_adjuntos_pqrs_subir_descargar_eliminar` (SIG) |
| Los historiales del SIG no se pueden alterar, aunque se use SQL directo | `test_migracion_del_sig_conserva_datos_se_revierte_y_protege_historiales` (PostgreSQL) |
| Las llaves de agentes se guardan como huella, son de solo lectura y respetan alcance y sede | `test_la_llave_se_muestra_una_vez_y_solo_se_guarda_su_huella`, `test_los_agentes_son_de_solo_lectura_y_la_llave_no_sirve_en_la_api_normal`, `test_una_llave_limitada_a_una_sede_no_ve_las_demas` |

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
- **No se realizó una prueba de penetración independiente.** Los controles se verificaron con pruebas
  automatizadas propias, no con una auditoría externa.
- **Recuperación de contraseña:** la respuesta es idéntica exista o no el correo, pero cuando existe el servidor
  además guarda el código y envía un correo, así que un atacante paciente podría distinguir ambos casos por el
  tiempo de respuesta. El espacio de 6 dígitos es pequeño: la protección real son los 5 intentos y los 15 minutos
  de vigencia, y el límite de solicitudes por IP.
- **La política de contraseñas no consulta listas de contraseñas filtradas.**
- **Las evidencias del SIG no se analizan en busca de virus.** Solo se limita su tipo (por contenido), tamaño y cantidad,
  y se entregan como descarga. Si la empresa recibe archivos de personas externas, debe añadir un análisis antivirus.

## Cómo informar una vulnerabilidad

Este proyecto es académico. Si encuentra una vulnerabilidad, repórtela de forma privada al autor del proyecto en
lugar de publicarla.
