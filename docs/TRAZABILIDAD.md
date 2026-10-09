# Matriz de trazabilidad de requisitos

Relaciona cada requisito del documento de grado (RF-001 a RF-038, RN-001 a RN-012 y RNF-001 a RNF-050) con
la parte del sistema que lo implementa y con la evidencia que lo respalda. Los nombres de los requisitos son
los del documento «Proyecto de Grado» (tablas 8 a 18).

## Cómo leer la matriz

**Estado**

| Estado | Significado |
|---|---|
| **Cumplido** | Implementado y respaldado por pruebas automatizadas que se ejecutaron y pasaron. |
| **Cumplido (navegador)** | Implementado y comprobado de forma manual en un navegador real, sin prueba automatizada específica. |
| **Parcial** | Implementado en parte; la columna de evidencia dice qué falta. |
| **Preparado, sin verificar** | Los archivos existen, pero no se pudieron ejecutar en el entorno de desarrollo (por ejemplo, Docker). |
| **Fuera del software** | Depende de una actividad organizacional o de la infraestructura del cliente. El sistema solo lo facilita. |

**Evidencia.** Las pruebas del backend viven en `backend/tests/` y se citan como `archivo::prueba` (sin el prefijo
`test_`). Las del frontend viven junto al código en `frontend/src/` y se citan por nombre de archivo. Las pruebas
marcadas con (PG) solo se ejecutan contra PostgreSQL real (`TEST_DATABASE_URL`); con SQLite se omiten.

**Resultado de la última ejecución completa:** ver [LIMITACIONES.md](LIMITACIONES.md#resultado-de-las-pruebas).

**Abreviaturas de archivos de prueba:** `admin` = `test_administracion.py` · `agentes` = `test_agentes.py` ·
`catinv` = `test_catalogo_inventario.py` · `conc` = `test_concurrencia.py` (PG) · `dash` = `test_dashboard_reportes.py` ·
`flujo` = `test_flujo_integral.py` · `migr` = `test_migraciones.py` (PG) · `ml` = `test_ml.py` ·
`pred` = `test_prediccion.py` · `reco` = `test_recomendaciones.py` · `auth` = `test_setup_auth.py` ·
`vt` = `test_ventas_traslados.py` · `sigpq` = `test_sig_pqrs_adjuntos.py` · `sigcal` = `test_sig_calidad_entradas.py` ·
`sigsst` = `test_sig_sst.py` · `sigamb` = `test_sig_ambiental.py` · `sigperm` = `test_sig_permisos.py` ·
`demo` = `test_demo.py`.

`flujo::test_flujo_completo_de_una_empresa` recorre de principio a fin el escenario de integración de 17 pasos
(configuración inicial → sedes → usuarios → productos → entradas → ventas → traslado → predicción →
recomendación → reportes → auditoría) y respalda de forma transversal a casi todos los requisitos funcionales.

---

## 1. Requisitos funcionales

| ID | Requisito | Dónde está implementado | Evidencia | Estado |
|---|---|---|---|---|
| RF-001 | Registrar usuario | `POST /api/usuarios` · `usuario_service` · pantalla **Usuarios** (modal «Nuevo usuario», contraseña temporal con cambio obligatorio) | `admin::crud_usuarios_y_roles_de_sede`, `admin::correo_de_usuario_unico`, `admin::rol_de_sede_exige_sede_y_rol_de_empresa_no_la_admite`, `auth::setup_crea_empresa_roles_y_admin`; `UsuariosPage.test.tsx` | Cumplido |
| RF-002 | Consultar usuario | `GET /api/usuarios` (filtros por texto, rol, sede y estado, paginado) · pantalla **Usuarios** | `admin::crud_usuarios_y_roles_de_sede`, `admin::empresas_no_ven_datos_de_otras`; `UsuariosPage.test.tsx` | Cumplido |
| RF-003 | Modificar usuario | `PUT /api/usuarios/{id}` (datos, rol y sede) · `usuario_service` | `admin::crud_usuarios_y_roles_de_sede`, `admin::no_se_puede_quitar_el_rol_al_ultimo_administrador`, `admin::no_se_puede_escalar_privilegios_creando_roles` | Cumplido |
| RF-004 | Inhabilitar usuario | `PATCH /api/usuarios/{id}/estado` · diálogo de confirmación en la interfaz · protección del último administrador | `admin::no_se_puede_inhabilitar_al_ultimo_administrador`, `admin::usuario_inhabilitado_pierde_acceso`; `UsuariosPage.test.tsx` | Cumplido |
| RF-005 | Iniciar sesión | `POST /api/auth/login` · JWT con versión de contraseña · `LoginPage` · ruta protegida | `auth::login_correcto_y_me`, `auth::login_incorrecto_mensaje_generico_y_auditado`, `auth::bloqueo_tras_intentos_fallidos`, `auth::rutas_protegidas_sin_token`, `auth::token_invalido`; `LoginPage.test.tsx`, `Rutas.test.tsx` | Cumplido |
| RF-006 | Recuperar contraseña | `POST /api/auth/forgot-password`, `verify-reset-code`, `reset-password` · código de 6 dígitos, un solo uso, vence, máx. 5 intentos · `RecuperarPage` | `auth::recuperacion_de_contraseña_flujo_completo`, `auth::codigo_se_invalida_tras_demasiados_intentos`. El **envío real del correo** depende de las credenciales SMTP del cliente y no se probó contra un servidor de correo real (ver LIMITACIONES) | Cumplido (envío SMTP sin verificar) |
| RF-007 | Registrar empresa | Configuración inicial protegida (`POST /api/setup`, `SETUP_TOKEN`, una sola vez) o `python -m app.cli inicializar` · `GET/PUT /api/empresa` · pantallas **Configuración inicial** y **Empresa** | `auth::setup_crea_empresa_roles_y_admin`, `auth::setup_solo_una_vez`, `auth::setup_exige_token_si_esta_definido`, `auth::no_existe_registro_publico`, `admin::empresa_consultar_y_modificar`, `admin::dos_empresas_no_pueden_repetir_identificacion` | Cumplido |
| RF-008 | Registrar sede | `POST /api/sedes` (nombre único por empresa sin distinguir mayúsculas) · pantalla **Sedes** | `admin::crud_sedes`, `admin::nombre_de_sede_unico_sin_importar_mayusculas`, `admin::validaciones_de_sede_en_espanol` | Cumplido |
| RF-009 | Consultar sedes | `GET /api/sedes`, `GET /api/sedes/directorio` (nombres para filtros, limitado a la sede del usuario si aplica) | `admin::crud_sedes`, `admin::directorio_de_sedes_para_usuario_limitado_a_su_sede` | Cumplido |
| RF-010 | Modificar sede | `PUT /api/sedes/{id}`, `PATCH /api/sedes/{id}/estado` (no se inhabilita una sede con traslados pendientes) | `admin::crud_sedes`, `admin::sede_inhabilitar_y_reactivar`, `vt::no_se_inhabilita_sede_ni_producto_con_traslado_pendiente` | Cumplido |
| RF-011 | Registrar producto | `POST /api/productos` (código único por empresa, categoría obligatoria) · `POST /api/categorias` · pantallas **Productos** y **Categorías** | `catinv::productos_crud_codigo_inmutable_y_unico`, `catinv::categorias_crud_y_reglas` | Cumplido |
| RF-012 | Consultar producto | `GET /api/productos` (búsqueda por código o nombre; filtros por categoría y estado) | `catinv::productos_crud_codigo_inmutable_y_unico`, `catinv::aislamiento_de_inventario_entre_empresas` | Cumplido |
| RF-013 | Modificar producto | `PUT /api/productos/{id}`; el código no se puede cambiar (identificación histórica) | `catinv::productos_crud_codigo_inmutable_y_unico` | Cumplido |
| RF-014 | Inhabilitar producto | `PATCH /api/productos/{id}/estado` con confirmación en la interfaz; un producto inhabilitado no recibe entradas | `catinv::producto_inhabilitado_no_recibe_entradas`, `vt::no_se_inhabilita_sede_ni_producto_con_traslado_pendiente` | Cumplido |
| RF-015 | Consultar inventario por sede | `GET /api/inventario` · pantalla **Existencias** (estado: agotado, bajo, normal, excesivo) | `catinv::inventario_lista_productos_sin_existencias`, `catinv::usuario_de_sede_no_opera_en_otra_sede`, `admin::encargado_de_sede_solo_ve_su_sede` | Cumplido |
| RF-016 | Consultar inventario consolidado | `GET /api/inventario/consolidado` (suma de las filas por sede; nunca se almacena aparte) · pantalla **Consolidado** | `catinv::consolidado_suma_las_sedes_sin_duplicar`, `vt::invariantes_de_inventario_tras_operar` | Cumplido |
| RF-017 | Registrar entrada | `POST /api/inventario/entradas` · pantalla **Existencias** (formulario multilínea) | `catinv::entrada_salida_ajuste_y_movimientos`, `catinv::cantidades_invalidas_y_lineas_repetidas`; `EditorLineas.test.tsx` | Cumplido |
| RF-018 | Registrar salida | `POST /api/inventario/salidas` y `POST /api/inventario/ajustes` (conteo físico, corrección) | `catinv::entrada_salida_ajuste_y_movimientos`, `catinv::salida_con_existencias_insuficientes_no_modifica_nada` | Cumplido |
| RF-019 | Validar existencias | `UPDATE … WHERE cantidad + delta >= 0 RETURNING` (atómico) + restricción `cantidad >= 0` en la base | `catinv::salida_con_existencias_insuficientes_no_modifica_nada`, `vt::venta_sin_precio_ni_stock_se_rechaza_completa`, `vt::traslado_sin_stock_suficiente_no_mueve_nada`, `conc::salidas_simultaneas_nunca_dejan_stock_negativo` (PG) | Cumplido |
| RF-020 | Registrar venta | `POST /api/ventas` (varios productos, descuenta existencias, consecutivo por empresa, anulación con motivo y plazo) · pantallas **Ventas**, **Nueva venta**, **Detalle de venta** | `vt::venta_descuenta_existencias_y_calcula_totales`, `vt::anular_venta_reintegra_y_no_se_repite`, `vt::plazo_de_anulacion`, `vt::usuario_de_sede_solo_vende_y_ve_su_sede`, `conc::ventas_simultaneas_consecutivos_unicos_y_sin_sobreventa` (PG), `conc::anulacion_simultanea_reintegra_una_sola_vez` (PG) | Cumplido |
| RF-021 | Consultar ventas | `GET /api/ventas` (filtros por sede, estado, periodo, número) · `GET /api/reportes/ventas` (por producto, sede y periodo) | `vt::usuario_de_sede_solo_vende_y_ve_su_sede`, `dash::reporte_de_ventas_excluye_anuladas_del_total` | Cumplido |
| RF-022 | Registrar traslado | `POST /api/traslados` (solicitud entre dos sedes de la misma empresa) · pantallas **Traslados**, **Nuevo traslado**, **Detalle de traslado** | `vt::traslado_flujo_completo_y_atomico`, `vt::traslado_rechazar_cancelar_y_validaciones`, `vt::traslado_permisos_por_sede` | Cumplido |
| RF-023 | Actualizar traslado | `POST /api/traslados/{id}/confirmar`: una sola transacción descuenta del origen y suma al destino; el cambio de estado actúa como «llave» | `vt::traslado_flujo_completo_y_atomico`, `conc::confirmacion_simultanea_de_un_traslado_mueve_una_sola_vez` (PG), `conc::traslados_cruzados_no_generan_interbloqueo` (PG) | Cumplido |
| RF-024 | Generar historial de movimientos | Tabla `movimientos` de solo inserción (trigger en PostgreSQL) con saldo anterior y posterior · `GET /api/movimientos` · pantalla **Movimientos** · reporte de movimientos | `catinv::entrada_salida_ajuste_y_movimientos`, `vt::invariantes_de_inventario_tras_operar`, `migr::auditoria_y_movimientos_son_de_solo_insercion` (PG) | Cumplido |
| RF-025 | Preparar datos de predicción | `app/ml/datos.py` (serie diaria sin huecos por sede y producto, ventas netas de anulaciones, marca de días sin existencias) y `app/ml/pipeline.py` (calidad, imputación, límite de picos) | `ml::historia_insuficiente_se_omite_con_motivo`, `ml::pocas_ventas_se_omite_aunque_haya_historia`, `ml::dias_sin_existencias_se_imputan_y_se_advierte`, `ml::picos_extremos_se_limitan`, `pred::la_ejecucion_guarda_predicciones_metricas_y_explica_lo_omitido` | Cumplido |
| RF-026 | Predecir demanda | `POST /api/predicciones/ejecutar` (en segundo plano) · 6 modelos candidatos, validación temporal, intervalo de 80 % · ver [PREDICCION.md](PREDICCION.md) | `ml::*` (16 pruebas), `pred::la_ejecucion_guarda_predicciones_metricas_y_explica_lo_omitido`, `pred::una_sola_ejecucion_activa_y_las_colgadas_se_cierran`, `pred::dos_solicitudes_simultaneas_crean_una_sola_ejecucion` | Cumplido |
| RF-027 | Consultar predicción | `GET /api/predicciones`, `/serie`, `/ejecuciones`, `/modelos` · pantalla **Predicciones** (historial + pronóstico con banda de incertidumbre, siempre rotulado «estimación») | `pred::catalogo_de_modelos_es_transparente`, `pred::permisos_de_prediccion_por_rol`, `pred::las_predicciones_estan_aisladas_entre_empresas`; `GraficoLineas.test.tsx` | Cumplido |
| RF-028 | Generar recomendación de reabastecimiento | `POST /api/recomendaciones/generar` · reglas explícitas (punto de reposición, nivel objetivo, plazo de entrega) · pantalla **Recomendaciones** | `reco::reglas_de_calculo_con_valores_conocidos`, `reco::reabastecimiento_aprobada_ejecutada_y_estados_finales`, `reco::el_stock_maximo_limita_la_cantidad_sugerida`, `reco::no_se_generan_recomendaciones_sin_una_prediccion_vigente` | Cumplido |
| RF-029 | Generar recomendación de traslado | Se sugiere traslado antes que compra cuando otra sede tiene excedente; al aprobarla se crea una **solicitud** de traslado (no mueve existencias) | `reco::la_sede_sin_stock_recibe_un_traslado_de_la_que_tiene_excedente`, `reco::aprobar_un_traslado_crea_la_solicitud_pero_no_mueve_existencias`, `reco::dos_aprobaciones_simultaneas_crean_un_solo_traslado` | Cumplido |
| RF-030 | Consultar recomendaciones | `GET /api/recomendaciones` (producto, sedes, cantidad, prioridad, explicación y datos que la originan) | `reco::roles_y_alcance_de_las_recomendaciones`, `reco::las_recomendaciones_no_cruzan_empresas`, `reco::rechazar_y_regenerar_conserva_historial` | Cumplido |
| RF-031 | Alerta de inventario bajo | `alertas_service`: se abre y se resuelve sola al cambiar las existencias; una única alerta activa por sede, producto y tipo (índice parcial único); prioridad crítica si está agotado | `catinv::niveles_generan_y_resuelven_alertas`, `catinv::alertas_sin_duplicados_y_recalculo`, `conc::alertas_no_se_duplican_con_movimientos_simultaneos` (PG) | Cumplido |
| RF-032 | Alerta de inventario excesivo | Ídem, con el stock máximo configurado por sede y producto | `catinv::niveles_generan_y_resuelven_alertas`; además, la predicción abre alertas de riesgo de desabastecimiento: `pred::la_prediccion_abre_alertas_de_riesgo_de_desabastecimiento` | Cumplido |
| RF-033 | Reporte de inventario | `GET /api/reportes/inventario` en JSON, CSV y Excel (con resumen) · pantalla **Reportes** | `dash::reporte_inventario_json_csv_y_excel`, `dash::reportes_exigen_permiso_y_quedan_auditados` | Cumplido |
| RF-034 | Reporte de ventas | `GET /api/reportes/ventas` (excluye anuladas del total) | `dash::reporte_de_ventas_excluye_anuladas_del_total` | Cumplido |
| RF-035 | Reporte de predicciones | `GET /api/reportes/predicciones` (valores estimados, modelo, error y confianza) | `dash::reportes_exigen_permiso_y_quedan_auditados`, `flujo::test_flujo_completo_de_una_empresa` | Cumplido |
| RF-036 | Registrar actividad | `auditoria_service.registrar` en cada operación relevante; tabla de solo inserción; IP, identificador de petición y resultado; nunca guarda secretos | `admin::auditoria_registra_altas_y_cambios_sin_secretos`, `auth::login_incorrecto_mensaje_generico_y_auditado`, `migr::auditoria_y_movimientos_son_de_solo_insercion` (PG) | Cumplido |
| RF-037 | Consultar auditoría | `GET /api/auditoria` (filtros por módulo, acción, usuario, resultado y fechas) · pantalla **Auditoría**; el gerente solo ve operaciones, no accesos | `dash::auditoria_visibilidad_por_permiso`, `admin::auditoria_registra_altas_y_cambios_sin_secretos` | Cumplido |
| RF-038 | Controlar permisos | 52 permisos; `requiere(*permisos)` en cada ruta; alcance de sede aplicado en el servidor; la interfaz oculta lo que no se puede usar, pero el servidor decide | `admin::catalogo_de_permisos_y_roles_del_sistema`, `admin::rol_personalizado_ciclo_completo`, `admin::roles_del_sistema_no_se_eliminan_ni_cambian_permisos`, `admin::gerente_no_gestiona_usuarios_ni_roles`, `admin::no_se_puede_escalar_privilegios_creando_roles`, `admin::encargado_de_sede_solo_ve_su_sede`; `Rutas.test.tsx`, `permisos.test.ts`, `navegacion.test.ts`, `RolesPage.test.tsx` | Cumplido |

---

## 2. Requisitos de negocio

| ID | Requisito de negocio | Cómo lo resuelve el sistema | Evidencia | Estado |
|---|---|---|---|---|
| RN-001 | Centralizar la información | Una sola base de datos por empresa con todas las sedes; los datos de cada empresa están aislados de las demás | `admin::empresas_no_ven_datos_de_otras`, `catinv::aislamiento_de_inventario_entre_empresas`, `agentes::una_llave_nunca_ve_datos_de_otra_empresa` | Cumplido |
| RN-002 | Controlar el inventario multi-sede | Existencias por sede y vista consolidada calculada a partir de ellas; traslados entre sedes | `catinv::consolidado_suma_las_sedes_sin_duplicar`, `vt::traslado_flujo_completo_y_atomico` | Cumplido |
| RN-003 | Mejorar la visibilidad operativa | Panel de control con cifras reales (nunca inventa datos si no los hay), historial de movimientos, alertas | `dash::dashboard_sin_datos_no_inventa_cifras`, `dash::dashboard_cifras_reales`, `dash::dashboard_respeta_permisos_y_sede` | Cumplido |
| RN-004 | Reducir el riesgo de desabastecimiento | Alertas de inventario bajo y de riesgo por cobertura (días de stock frente a demanda prevista) + recomendaciones de reposición | `catinv::niveles_generan_y_resuelven_alertas`, `pred::la_prediccion_abre_alertas_de_riesgo_de_desabastecimiento`, `reco::reglas_de_calculo_con_valores_conocidos` | Cumplido |
| RN-005 | Disminuir el exceso de inventario | Alerta de exceso sobre el stock máximo, alerta de «sin rotación» y traslado desde sedes con excedente antes de comprar | `catinv::niveles_generan_y_resuelven_alertas`, `reco::la_sede_sin_stock_recibe_un_traslado_de_la_que_tiene_excedente` | Cumplido |
| RN-006 | Utilizar inteligencia artificial | Pronóstico por sede y producto con comparación de modelos y validación temporal | `ml::*`, `pred::*` | Cumplido |
| RN-007 | Apoyar el reabastecimiento | Recomendaciones con cantidad, prioridad y explicación; requieren aprobación humana | `reco::*` | Cumplido |
| RN-008 | Optimizar la distribución entre sedes | Recomendaciones de traslado interno | `reco::la_sede_sin_stock_recibe_un_traslado_de_la_que_tiene_excedente`, `reco::aprobar_un_traslado_crea_la_solicitud_pero_no_mueve_existencias` | Cumplido |
| RN-009 | Proteger la información empresarial | Autenticación, permisos por rol y sede, auditoría, cabeceras de seguridad. Ver [SEGURIDAD.md](SEGURIDAD.md) | `auth::*`, `admin::gerente_no_gestiona_usuarios_ni_roles`, `auth::cabeceras_de_seguridad_y_request_id` | Cumplido |
| RN-010 | Facilitar la toma de decisiones | Reportes (JSON, CSV, Excel), panel, predicciones y recomendaciones | `dash::*`, `flujo::test_flujo_completo_de_una_empresa` | Cumplido |
| RN-011 | Permitir el crecimiento de la empresa | Sedes, usuarios, productos y roles ilimitados y configurables desde la interfaz; consultas paginadas con índices; migraciones versionadas | `admin::crud_sedes`, `admin::rol_personalizado_ciclo_completo`. La capacidad bajo carga elevada **no se midió** (ver RNF-011 y RNF-013) | Parcial |
| RN-012 | Mantener la continuidad operativa | Transacciones atómicas, respaldo y restauración, comprobaciones de salud, reinicio automático de contenedores | `migr::*` (PG), `conc::*` (PG); scripts `infra/scripts/respaldar|restaurar`: probados contra PostgreSQL local; el despliegue con Docker **no se pudo probar** | Parcial |

---

## 3. Requisitos no funcionales

### 3.1 Facilidad de uso

| ID | Requisito | Implementación | Evidencia | Estado |
|---|---|---|---|---|
| RNF-001 | Interfaz intuitiva | Navegación agrupada por módulos y filtrada por permisos, buscadores, atajos de acción en cada lista, estados vacíos que indican qué hacer | Recorrido de las 21 pantallas con 3 roles en navegador (1440, 1280, 390 y 320 px) | Cumplido (navegador) |
| RNF-002 | Capacitación de usuarios | El sistema no puede capacitar por sí mismo; se entrega un manual por rol y datos de demostración para practicar | [MANUAL_USUARIO.md](MANUAL_USUARIO.md); `python -m app.cli cargar-demo` | Fuera del software |
| RNF-003 | Manual de usuario | [MANUAL_USUARIO.md](MANUAL_USUARIO.md) | — | Cumplido |
| RNF-004 | Validación de datos | Validación en el cliente (zod) y en el servidor (pydantic); los errores del servidor se muestran junto al campo correspondiente, en español | `auth::setup_rechaza_password_debil_en_espanol`, `admin::validaciones_de_sede_en_espanol`, `vt::campos_opcionales_aceptan_null_explicito`; `formularios.test.ts`, `errors.test.ts` | Cumplido |
| RNF-005 | Navegación consistente | Mismos componentes para listas (`Tabla`, `BarraFiltros`, `Paginacion`), formularios (`Modal`) y confirmaciones (`ConfirmDialog`); filtros guardados en la URL | `useFiltros.test.tsx`, `navegacion.test.ts` | Cumplido |

### 3.2 Confiabilidad

| ID | Requisito | Implementación | Evidencia | Estado |
|---|---|---|---|---|
| RNF-006 | Disponibilidad | `/api/health` y `/api/health/ready`, `restart: unless-stopped`, comprobaciones de salud en Compose. La disponibilidad real depende de dónde se despliegue | Los puntos de salud de la API se probaron (`/api/health/ready` responde con la base conectada). Los contenedores y sus comprobaciones **no se ejecutaron** (ver [DESPLIEGUE.md](DESPLIEGUE.md)) | Preparado, sin verificar |
| RNF-007 | Integridad de la información | Restricciones en la base (`cantidad >= 0`, claves únicas, sedes distintas), transacciones, tablas de solo inserción para movimientos y auditoría | `vt::invariantes_de_inventario_tras_operar`, `catinv::salida_con_existencias_insuficientes_no_modifica_nada`, `migr::auditoria_y_movimientos_son_de_solo_insercion` (PG) | Cumplido |
| RNF-008 | Actualización de existencias | Cada movimiento actualiza la existencia y registra el saldo en la misma transacción; el traslado solo cambia existencias al confirmarse | `catinv::entrada_salida_ajuste_y_movimientos`, `vt::traslado_flujo_completo_y_atomico` | Cumplido |
| RNF-009 | Recuperación ante fallos | `infra/scripts/respaldar.sh|.ps1` y `restaurar.sh|.ps1` (volcado de PostgreSQL con verificación); guía en [DESPLIEGUE.md](DESPLIEGUE.md) | Volcado y restauración probados contra PostgreSQL local; las tareas programadas de respaldo y su almacenamiento fuera del servidor son responsabilidad del cliente | Parcial |
| RNF-010 | Control de errores | Respuestas de error uniformes (`detail`, `codigo`, `request_id`); los errores internos no filtran detalles; la interfaz muestra pantallas de error y reintento sin perder la sesión | `auth::error_interno_no_filtra_detalles`, `pred::un_error_de_calculo_deja_la_ejecucion_fallida_sin_detalles_tecnicos`; `errors.test.ts` | Cumplido |

### 3.3 Rendimiento y ambiente de trabajo

| ID | Requisito | Implementación | Evidencia | Estado |
|---|---|---|---|---|
| RNF-011 | Tiempo de respuesta ≤ 3 s | Paginación en todos los listados, índices por empresa, sede y fecha, agregados calculados en la base | Medición informal sobre la demostración (3 103 ventas, 8 239 movimientos, 36 productos, 3 sedes): las consultas principales respondieron en 6 a 160 ms (la más lenta, la primera carga del panel). **No es una prueba de carga**; con volúmenes mucho mayores o muchos usuarios simultáneos hay que volver a medir | Parcial |
| RNF-012 | Procesamiento de datos sin afectar la operación | La predicción corre en segundo plano, con tiempo máximo (`ML_TIEMPO_MAXIMO_SEGUNDOS`), tope de series y una sola ejecución activa por empresa; la interfaz consulta el avance | `pred::una_sola_ejecucion_activa_y_las_colgadas_se_cierran`, `pred::dos_solicitudes_simultaneas_crean_una_sola_ejecucion`, `ml::sin_tiempo_solo_se_comparan_modelos_simples_y_se_advierte`. El cálculo comparte proceso con la API: con catálogos muy grandes conviene programarlo fuera de horas pico (`python -m app.cli predecir`) | Cumplido |
| RNF-013 | Capacidad de almacenamiento | PostgreSQL, claves `BIGINT` en las tablas de mayor crecimiento (movimientos, auditoría, alertas, predicciones), índices compuestos | Diseño. No se probó con millones de filas | Parcial |
| RNF-014 | Operaciones simultáneas | Actualizaciones atómicas, bloqueos consultivos para consecutivos y configuración inicial, orden determinista de bloqueo para evitar interbloqueos | `conc::*` (6 pruebas, PG), `pred::dos_solicitudes_simultaneas_crean_una_sola_ejecucion`, `reco::dos_aprobaciones_simultaneas_crean_un_solo_traslado` | Cumplido |
| RNF-015 | Requisitos del equipo | Aplicación web moderna: navegador actual (Chrome/Edge/Firefox/Safari recientes) | Solo se probó con Chromium. Los demás navegadores no se probaron | Parcial |

### 3.4 Restricciones de diseño

| ID | Requisito | Implementación | Evidencia | Estado |
|---|---|---|---|---|
| RNF-016 | Python y FastAPI | Python 3.13, FastAPI, SQLAlchemy 2 asíncrono | `backend/` | Cumplido |
| RNF-017 | React y TypeScript | React 19, TypeScript estricto, Vite | `tsc -b` sin errores; `frontend/` | Cumplido |
| RNF-018 | PostgreSQL | PostgreSQL 16 (probado con 16); SQLite solo para pruebas rápidas | `migr::*`, `conc::*` (PG) | Cumplido |
| RNF-019 | Arquitectura centralizada | El consolidado se calcula siempre sumando `inventario_sede`; no existe una tabla de totales que pueda desincronizarse | `catinv::consolidado_suma_las_sedes_sin_duplicar` | Cumplido |
| RNF-020 | Docker y Docker Compose | `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`, `infra/docker-compose.yml` (PostgreSQL, API, interfaz, healthchecks, migraciones al arrancar, perfil `demo`) | `docker compose config` valida el archivo; el script de arranque y la API en modo producción se probaron sobre PostgreSQL. **No se construyeron las imágenes ni se ejecutaron los contenedores** (el registro de imágenes estaba bloqueado); el primer `docker compose up` puede requerir ajustes | Preparado, sin verificar |
| RNF-021 | Modelos de predicción | Series de tiempo (Holt-Winters, Croston-SBA) y aprendizaje automático (gradient boosting) frente a una línea base | `ml::*` | Cumplido |

### 3.5 Seguridad

| ID | Requisito | Implementación | Evidencia | Estado |
|---|---|---|---|---|
| RNF-022 | Autenticación | JWT firmado con vencimiento; el token deja de valer si cambia la contraseña; usuario inhabilitado pierde acceso | `auth::login_correcto_y_me`, `auth::token_invalido`, `auth::cambiar_password_invalida_tokens_anteriores`, `admin::usuario_inhabilitado_pierde_acceso` | Cumplido |
| RNF-023 | Protección de contraseñas | Argon2id, política de contraseña robusta, comparación en tiempo constante con relleno para no revelar si el correo existe | `auth::setup_rechaza_password_debil_en_espanol`, `auth::ninguna_respuesta_expone_hash_ni_secretos`, `auth::login_incorrecto_mensaje_generico_y_auditado` | Cumplido |
| RNF-024 | Control de acceso | Permisos por rol y alcance de sede, aplicados en el servidor en cada consulta | `admin::encargado_de_sede_solo_ve_su_sede`, `catinv::usuario_de_sede_no_opera_en_otra_sede`, `vt::traslado_permisos_por_sede`, `reco::roles_y_alcance_de_las_recomendaciones` | Cumplido |
| RNF-025 | Recuperación segura | Código de 6 dígitos guardado con hash, un solo uso, vence a los 15 minutos (configurable), 5 intentos, respuesta idéntica exista o no el correo | `auth::recuperacion_de_contraseña_flujo_completo`, `auth::codigo_se_invalida_tras_demasiados_intentos` | Cumplido |
| RNF-026 | Límite de intentos | Bloqueo temporal de la cuenta tras 5 intentos fallidos y límite de solicitudes por IP (slowapi) en login, recuperación, cambio de contraseña y configuración inicial | `auth::bloqueo_tras_intentos_fallidos`, `auth::limite_de_solicitudes_por_ip_en_el_ingreso`, `admin::desbloquear_cuenta` | Cumplido |
| RNF-027 | Comunicación segura | La aplicación no termina TLS: el HTTPS debe ofrecerlo el proxy o la plataforma de despliegue (ver [DESPLIEGUE.md](DESPLIEGUE.md)). La conexión a bases remotas exige SSL. No se emite HSTS desde la aplicación porque depende del dominio del cliente | Sin prueba automatizada | Parcial |
| RNF-028 | Auditoría | Accesos (exitosos y fallidos) y operaciones, con usuario, sede, IP, resultado e identificador de petición | `auth::login_incorrecto_mensaje_generico_y_auditado`, `admin::auditoria_registra_altas_y_cambios_sin_secretos`, `dash::reportes_exigen_permiso_y_quedan_auditados` | Cumplido |

### 3.6 Inteligencia artificial y calidad de las predicciones

| ID | Requisito | Implementación | Evidencia | Estado |
|---|---|---|---|---|
| RNF-029 | Calidad de los datos | Mínimo de 28 días de historia y 5 días con ventas; exclusión si más de la mitad del historial estuvo sin existencias; imputación de días sin stock; límite de picos. Lo omitido se informa con su motivo | `ml::historia_insuficiente_se_omite_con_motivo`, `ml::pocas_ventas_se_omite_aunque_haya_historia`, `ml::mas_de_la_mitad_sin_existencias_se_omite`, `pred::sin_ventas_suficientes_la_ejecucion_termina_con_aviso_honesto` | Cumplido |
| RNF-030 | Evaluación del modelo | Validación temporal con hasta 3 cortes; MAE, WAPE y sesgo por serie y global frente a la línea base; script `ml/evaluar_modelos.py` para repetir la evaluación | `ml::la_validacion_nunca_entrena_con_datos_del_futuro`, `ml::wape_y_mae_se_calculan_sobre_el_total`, `ml::el_modelo_avanzado_solo_gana_si_supera_a_los_simples_por_el_margen`, `ml::resumen_global_pondera_por_volumen_y_cuenta_omitidas` | Cumplido |
| RNF-031 | Trazabilidad de resultados | Cada predicción guarda ejecución, producto, sede, periodo, modelo, métricas y advertencias | `pred::la_ejecucion_guarda_predicciones_metricas_y_explica_lo_omitido` | Cumplido |
| RNF-032 | Actualización del modelo | Cada ejecución reentrena con el historial vigente; se puede lanzar desde la interfaz o programar con el CLI | `pred::la_ejecucion_guarda_predicciones_metricas_y_explica_lo_omitido` | Cumplido |
| RNF-033 | Interpretación de recomendaciones | Cada recomendación explica en español la situación, la demanda prevista, la cobertura, el plazo de entrega y el modelo usado | `reco::reglas_de_calculo_con_valores_conocidos`; revisión del texto en navegador | Cumplido |
| RNF-034 | Validación humana | Una recomendación no ejecuta nada: aprobar un traslado solo crea una solicitud, que aún debe aprobarse y confirmarse por separado; los agentes de IA son de solo lectura | `reco::aprobar_un_traslado_crea_la_solicitud_pero_no_mueve_existencias`, `agentes::los_agentes_son_de_solo_lectura_y_la_llave_no_sirve_en_la_api_normal` | Cumplido |

### 3.7 Mantenibilidad

| ID | Requisito | Implementación | Evidencia | Estado |
|---|---|---|---|---|
| RNF-035 | Arquitectura modular | Capas `api` → `services` → `models`, módulo `ml` puro (sin base de datos), frontend por funcionalidades. Ver [ARQUITECTURA.md](ARQUITECTURA.md) | `ml::*` prueba el módulo sin base de datos | Cumplido |
| RNF-036 | Código documentado | Documentación técnica en `docs/`, docstrings en los módulos principales, esquema OpenAPI en `/api/docs` | Este directorio | Cumplido |
| RNF-037 | Pruebas automatizadas | 137 pruebas de backend, 79 de frontend, integración de 17 pasos, concurrencia y migraciones sobre PostgreSQL real; integración continua definida en `.github/workflows/ci.yml` | Ver [LIMITACIONES.md](LIMITACIONES.md#resultado-de-las-pruebas). La ejecución de la integración continua en GitHub **no se verificó** | Cumplido (CI sin verificar) |
| RNF-038 | Migraciones controladas | Alembic con tres revisiones; la migración 0003 conserva los datos de la versión anterior | `migr::migracion_desde_base_vacia_y_alembic_check`, `migr::migracion_hacia_atras_y_adelante`, `migr::migracion_conserva_datos_de_la_version_anterior` (todas PG) | Cumplido |
| RNF-039 | Actualización de dependencias | Versiones fijadas (`requirements.txt`, `package-lock.json`); procedimiento de actualización en [DESARROLLO.md](DESARROLLO.md) | Revisión periódica: responsabilidad del equipo | Fuera del software |
| RNF-040 | Registro de cambios | [CHANGELOG.md](../CHANGELOG.md) | — | Cumplido |

### 3.8 Interfaz de usuario

| ID | Requisito | Implementación | Evidencia | Estado |
|---|---|---|---|---|
| RNF-041 | Diseño visual | Una sola paleta con un único color de acento, tipografías empaquetadas (sin cargar nada de Internet), escala de radios y espaciados fija | Revisión visual en navegador | Cumplido (navegador) |
| RNF-042 | Diseño responsivo | Se revisaron 1440, 1280, 390 y 320 px: sin desbordamiento horizontal en ninguna de las 21 pantallas; menú lateral colapsable en móvil | Recorrido automatizado con Playwright (medición de desbordamiento) | Cumplido (navegador) |
| RNF-043 | Legibilidad | Tamaños de texto, contraste y estados de enfoque visibles; etiquetas asociadas a sus campos; tablas con encabezados | Revisión en navegador y uso de etiquetas asociadas a cada campo. **No se hizo una auditoría de accesibilidad completa (WCAG)** | Parcial |
| RNF-044 | Consistencia visual | Biblioteca interna de componentes (`components/ui`) y *tokens* de diseño | Revisión visual | Cumplido (navegador) |
| RNF-045 | Retroalimentación | Avisos de éxito y error, estados de carga con esqueletos, estados vacíos, confirmaciones antes de acciones delicadas, validación en línea | `UsuariosPage.test.tsx`, `RolesPage.test.tsx`; flujos recorridos en navegador | Cumplido |

### 3.9 Interfaces de comunicación

| ID | Requisito | Implementación | Evidencia | Estado |
|---|---|---|---|---|
| RNF-046 | Acceso web | Aplicación de una página servida por nginx (o Vite en desarrollo) | Compilación (`vite build`) correcta; servida con Vite | Cumplido |
| RNF-047 | Comunicación frontend-backend | API REST bajo `/api`, documentada con OpenAPI; el cliente usa tipos **generados** del esquema (`npm run tipos`), y la integración continua verifica que estén al día | Tipos regenerados y comparados sin diferencias | Cumplido |
| RNF-048 | Intercambio de datos | Esquemas pydantic de entrada y salida, estructura de error y de paginación uniformes | `vt::campos_opcionales_aceptan_null_explicito`, `catinv::cantidades_invalidas_y_lineas_repetidas` | Cumplido |
| RNF-049 | Integración con agentes | `/api/agentes/*` con llaves propias: solo lectura, con alcances, vencimiento, restricción por sede y revocación. Ejemplo en [`agents/`](../agents/README.md) | `agentes::*` (8 pruebas) | Cumplido |
| RNF-050 | Manejo de errores de comunicación | El cliente distingue falta de conexión, tiempo agotado, sesión vencida (cierra la sesión y vuelve al ingreso), sin permiso, no encontrado y error del servidor, con mensajes en español | `errors.test.ts` (conexión, mensajes propios, sin filtrar detalles internos). El cierre automático de sesión ante un 401 está en `lib/http.ts` y se comprobó en navegador, sin prueba automatizada | Cumplido |

---

## 4. Sistema Integrado de Gestión (versión 1.1)

El módulo SIG se pidió después del documento de grado, por lo que sus requisitos no tienen identificador allí. Aquí se
numeran `SIG-01` a `SIG-10` siguiendo la solicitud recibida, y a continuación se relacionan los 12 escenarios de
aceptación que esa solicitud exige comprobar. Las decisiones de diseño están en [D-28 a D-33](DECISIONES.md#d-28).

### 4.1 Requisitos

| ID | Requisito | Implementación | Evidencia | Estado |
|---|---|---|---|---|
| SIG-01 | Entrada **SIG** en el menú con cuatro apartados (PQRS y sugerencias, Seguridad y Salud en el Trabajo, Calidad, Gestión ambiental), cada uno con su vista y sus permisos | Grupo desplegable «SIG» en `components/layout/navegacion.ts` y `AppShell`; rutas `/sig/pqrs`, `/sig/sst`, `/sig/calidad`, `/sig/ambiental` protegidas por permiso | `navegacion.test.ts` (módulo SIG: visibilidad por rol); recorrido en navegador con administrador y operario | Cumplido |
| SIG-02 | **PQRS**: tipo, asunto, descripción, usuario y fecha automáticos, evidencias opcionales, confirmación, estado de las propias; la administración lista, filtra, cambia el estado, responde y ve el historial | `api/pqrs.py` · `pqrs_service` · tablas `pqrs` y `pqrs_historial` · `PqrsPage.tsx`; adjuntos en `adjuntos_service`. No hay aviso por correo (D-29) | `sigpq::pqrs_flujo_completo`, `sigpq::pqrs_filtros_y_conteo`, `sigpq::pqrs_validaciones`, `sigpq::pqrs_aisladas_entre_empresas`, `sigpq::adjuntos_*` (3); recorrido en navegador | Cumplido |
| SIG-03 | **Pausas activas** automáticas para quien no administra: mensaje, ejercicio, instrucciones, duración y recomendaciones; intervalo configurable con valor por defecto; sin repeticiones ni pausas simultáneas; sin interrumpir operaciones críticas; registro de cumplimiento; sección de administración | `sst_service` · `api/sst.py` · tablas `sst_*` · `PausasActivas.tsx`, `ModalPausa.tsx`, `programacion.ts`, `lib/bloqueoPausas.ts`, `SstPage.tsx` (D-32) | `sigsst::*` (8, una PG); `programacion.test.ts`, `PausasActivas.test.tsx`, `bloqueoPausas.test.tsx`; en navegador: la pausa aparece al operario, no aparece con un formulario abierto ni al administrador | Cumplido |
| SIG-04 | **No conformidades**: sección educativa, formulario completo, estados, listado con filtros, historial, vínculo con la entrada de origen, **sin modificar el inventario** | `calidad_service` · `api/calidad.py` · tablas `no_conformidades` y `no_conformidad_historial` · `NoConformidades.tsx`, `GuiaCalidad.tsx` (D-30) | `sigcal::registrar_no_conformidad_no_modifica_inventario`, `sigcal::no_conformidad_nace_de_una_entrada_sin_digitar_dos_veces`, `sigcal::no_conformidad_validaciones`, `sigcal::no_conformidad_historial_de_observaciones_y_gestion`, `sigcal::no_conformidades_filtros_y_alcance_por_sede`; `reglas.test.ts` | Cumplido |
| SIG-05 | **Garantías**: producto, documento de respaldo (factura, entrada, venta u otro), fechas, defecto, observaciones, evidencias, estados, respuesta del proveedor, solución y responsable | `calidad_service` · tablas `garantias` y `garantia_historial` · `Garantias.tsx` | `sigcal::garantia_ciclo_completo_con_historial`, `sigcal::garantia_con_documentos_de_entrada_y_venta`, `sigcal::garantias_filtros_y_alcance`, `sigcal::evidencias_de_calidad` | Cumplido |
| SIG-06 | **Gestión ambiental**: ventas confirmadas de categorías configuradas como vehículo; panel con vehículos vendidos, CO₂ evitado estimado, acumulado mensual y anual, historial y gráficos; sin cifras inventadas; real distinguido de estimado; «pendiente de parametrización»; anuladas excluidas; sin doble conteo | `ambiental_service` · ganchos en `ventas_service` · tablas `amb_*` · `AmbientalPage.tsx` y pestañas (D-33) | `sigamb::*` (13); `calculos.test.ts`, `AmbientalPage.test.tsx`; en navegador con la demostración | Cumplido |
| SIG-07 | **Observaciones por entrada** de inventario, enlazadas a ella, que no se pierden ni se sobrescriben | `entradas_service` · tablas `entradas_inventario` y `entrada_observaciones` (solo inserción) · `DialogoEntradaDetalle.tsx`, pestaña **Entradas de mercancía** de Movimientos | `sigcal::entrada_crea_cabecera_con_observacion_inicial`, `sigcal::observaciones_se_acumulan_y_no_se_pierden_al_reponer_stock`, `sigcal::observacion_de_entrada_validaciones_y_permisos` | Cumplido |
| SIG-08 | **Historial de observaciones** en garantías y no conformidades | `*_historial` de solo inserción (disparador) · `LineaTiempo` en la interfaz | `sigcal::no_conformidad_historial_de_observaciones_y_gestion`, `sigcal::garantia_ciclo_completo_con_historial`, `migr::migracion_del_sig_conserva_datos_se_revierte_y_protege_historiales` (PG) | Cumplido |
| SIG-09 | **Roles y permisos** aplicados en la interfaz y en el servidor | 9 permisos nuevos (de 52 a 61) en `core/permisos.py`; cada ruta `/api/sig/*` exige el suyo; alcance de sede en calidad y ambiental (D-28) | `sigpq::pqrs_flujo_completo` (403 al usuario sin permiso), `sigcal::*_filtros_y_alcance*`, `sigamb::permisos_y_alcance_por_sede`, `sigcal::observacion_de_entrada_validaciones_y_permisos`, `sigperm::actualizar_una_instalacion_existente_reparte_los_permisos_del_sig`, `sigperm::sincronizar_de_nuevo_no_devuelve_un_permiso_que_la_empresa_quito`; navegador: los endpoints de gestión responden 403 a un operario | Cumplido |
| SIG-10 | **Base de datos y arquitectura**: reutilizar lo existente, migración compatible con Alembic, sin cambiar el *framework*, conservar los datos | Migración `0004_sig` (15 tablas nuevas y `movimientos.entrada_id`); mismas capas, convenciones y componentes del proyecto; sin dependencias nuevas ni variables de entorno nuevas | `migr::migracion_desde_base_vacia_y_alembic_check` (PG), `migr::migracion_hacia_atras_y_adelante` (PG), `migr::migracion_del_sig_conserva_datos_se_revierte_y_protege_historiales` (PG) | Cumplido |

El requisito de **diseño coherente** de la solicitud se resolvió reutilizando los componentes de `components/ui` y los
*tokens* de diseño existentes (RNF-041 y RNF-044); se revisó en navegador a 1440 y 390 px.

### 4.2 Escenarios de aceptación

| # | Escenario | Evidencia |
|---|---|---|
| 1 | Un usuario registra una PQRS y la administración la consulta | `sigpq::pqrs_flujo_completo`; navegador |
| 2 | La administración cambia el estado de una PQRS y registra una respuesta | `sigpq::pqrs_flujo_completo` (estado, respuesta e historial) |
| 3 | Las pausas activas aparecen solas a quien no administra, según la configuración | `sigsst::pausa_aparece_para_operativos_y_no_para_administracion`, `sigsst::administracion_configura_frecuencia_y_contenido`; `PausasActivas.test.tsx`, `programacion.test.ts`; navegador |
| 4 | Los administradores no reciben las pausas automáticas | `sigsst::pausa_aparece_para_operativos_y_no_para_administracion`; navegador |
| 5 | Una no conformidad se registra, consulta y actualiza sin modificar el inventario | `sigcal::registrar_no_conformidad_no_modifica_inventario`, `sigcal::no_conformidad_historial_de_observaciones_y_gestion` |
| 6 | Una garantía conserva sus observaciones y su historial de seguimiento | `sigcal::garantia_ciclo_completo_con_historial` |
| 7 | Las observaciones de una entrada quedan vinculadas a ella y no se pierden al agregar más unidades | `sigcal::observaciones_se_acumulan_y_no_se_pierden_al_reponer_stock` |
| 8 | Una venta confirmada de un vehículo actualiza los indicadores según los parámetros configurados | `sigamb::configurar_calcula_las_ventas_pendientes_con_la_formula`, `sigamb::formula_documentada`, `sigamb::sin_parametrizar_cuenta_unidades_y_queda_pendiente`; `calculos.test.ts` |
| 9 | Una venta anulada se excluye de los indicadores | `sigamb::venta_anulada_deja_de_contar_y_no_se_duplica` |
| 10 | Las operaciones no generan duplicados ni alteran información histórica | `sigamb::ventas_simultaneas_no_duplican_registros`, `sigsst::peticiones_simultaneas_no_duplican_la_pausa` (PG), `sigsst::no_se_repiten_ni_se_solapan_pausas`, `sigamb::cambiar_parametros_no_altera_lo_ya_calculado`, `migr::migracion_del_sig_conserva_datos_se_revierte_y_protege_historiales` (PG) |
| 11 | Los permisos impiden que un usuario no autorizado gestione información administrativa | Ver SIG-09 |
| 12 | Las funcionalidades existentes (productos, inventario, ventas, usuarios…) siguen funcionando | Las 137 pruebas del backend anteriores a la versión 1.1 y el escenario integral de 17 pasos (`flujo::test_flujo_completo_de_una_empresa`) siguen pasando junto con las nuevas; ver [LIMITACIONES.md](LIMITACIONES.md#resultado-de-las-pruebas) |

El escenario 12 menciona «compras»: el sistema no tiene un módulo de compras (ver LIMITACIONES); la recepción de mercancía
se registra como entrada de inventario, que sí se verificó.

---

## 5. Resumen

| Tipo | Total | Cumplido | Cumplido con una salvedad | Cumplido (navegador) | Parcial | Preparado, sin verificar | Fuera del software |
|---|---|---|---|---|---|---|---|
| Funcionales (RF) | 38 | 37 | 1 (RF-006: el envío real de correo no se probó) | 0 | 0 | 0 | 0 |
| De negocio (RN) | 12 | 10 | 0 | 0 | 2 (RN-011, RN-012) | 0 | 0 |
| No funcionales (RNF) | 50 | 35 | 1 (RNF-037: la integración continua no se ejecutó) | 4 | 6 (RNF-009, 011, 013, 015, 027, 043) | 2 (RNF-006, 020) | 2 (RNF-002, 039) |
| SIG (versión 1.1) | 10 | 10 | 0 | 0 | 0 | 0 | 0 |

Los puntos «parciales» y «sin verificar» se desarrollan en [LIMITACIONES.md](LIMITACIONES.md).
