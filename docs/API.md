# Referencia de la API

La API es REST sobre JSON. La documentación interactiva y el esquema completo se publican con la propia aplicación:

| Recurso | Dirección |
|---|---|
| Documentación interactiva (Swagger) | `/api/docs` |
| Esquema OpenAPI | `/api/openapi.json` |
| Estado del servicio | `GET /api/health` |
| Estado de la base de datos | `GET /api/health/ready` (responde `503` si no hay conexión) |

> El esquema OpenAPI es la **fuente de verdad** del contrato: de él se generan los tipos del frontend
> (`npm run tipos`). Este documento resume las convenciones y el mapa de rutas; para los campos exactos de cada
> petición, consulte `/api/docs`.

## Autenticación

**Usuarios.** `POST /api/auth/login` con `{"email": "...", "password": "..."}` devuelve un token JWT. Cada petición
posterior lleva `Authorization: Bearer <token>`. El token vence (60 min por defecto) y deja de valer si la
persona cambia su contraseña o se inhabilita su cuenta.

```bash
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@empresa.example", "password": "<su contraseña>"}'

curl -s http://localhost:8000/api/inventario/consolidado \
  -H "Authorization: Bearer <token>"
```

**Agentes de IA.** Las rutas `/api/agentes/*` usan una llave en la cabecera `X-API-Key` (se crea en la pantalla
**Agentes de IA**). Ver [`agents/README.md`](../agents/README.md).

**Configuración inicial.** `POST /api/setup` (con el campo `token_configuracion` igual a `SETUP_TOKEN`) solo funciona
mientras no exista ninguna empresa.

## Convenciones

### Listas paginadas

Todos los listados aceptan `?pagina=1&tamano=20` (máximo 100 por página) y responden:

```json
{ "items": [ ... ], "total": 134, "pagina": 1, "tamano": 20, "paginas": 7 }
```

Los filtros se pasan como parámetros de consulta (`q`, `sede_id`, `estado`, `desde`, `hasta`…). Las fechas son
`AAAA-MM-DD`; las marcas de tiempo, ISO 8601 en UTC.

### Errores

Todas las respuestas de error tienen la misma forma:

```json
{
  "detail": "Existencias insuficientes de «Aceite vegetal 1 L» en Sede Norte: hay 2 y se necesitan 3",
  "codigo": "existencias_insuficientes",
  "request_id": "9f2c1a7b4d3e8a10",
  "errores": [ { "campo": "items.0.cantidad", "mensaje": "Debe ser mayor que 0" } ]
}
```

`detail` es un mensaje en español apto para mostrar; `codigo` es estable y sirve para programar; `errores` solo
aparece en validaciones. `request_id` coincide con la cabecera `X-Request-ID` y con el registro del servidor.

| HTTP | Cuándo |
|---|---|
| 400 | Regla de negocio incumplida |
| 401 | Sin sesión, token inválido o vencido, llave de agente inválida |
| 403 | Falta de permiso, sede o alcance no autorizado, contraseña temporal sin cambiar |
| 404 | El recurso no existe **o pertenece a otra empresa** (no se distingue, a propósito) |
| 409 | Conflicto: existencias insuficientes, estado inválido, duplicado, ejecución en curso |
| 422 | Validación de campos |
| 423 | Cuenta bloqueada temporalmente |
| 429 | Demasiadas solicitudes |
| 503 | Base de datos no disponible (`/api/health/ready`) |

### Límites de solicitudes

Por IP: ingreso 10/min, cambio de contraseña 5/min, solicitud de código de recuperación 3/min, validación del
código 10/min, restablecimiento 5/min, configuración inicial 5/min y rutas de agentes 60/min.

### Reportes

`GET /api/reportes/{tipo}?formato=json|csv|xlsx` con `tipo` en `inventario`, `ventas`, `movimientos`, `traslados`,
`alertas`, `predicciones`, `recomendaciones`. Con `formato=json` devuelve una vista previa (`columnas`, `filas`,
`resumen`, `truncado`); con `csv` o `xlsx` devuelve el archivo. Cada generación queda en la auditoría.

## Mapa de rutas

La columna **Acceso** indica el permiso necesario; «o» significa que basta con uno de ellos. El servidor valida
siempre el permiso y, para roles de sede, restringe los resultados a la sede asignada.

#### Configuración inicial

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| GET | `/api/setup/estado` | ¿Ya se configuró la empresa? | Pública |
| POST | `/api/setup` | Crear la empresa y su primer administrador (solo una vez) | Pública |

#### Autenticación

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| POST | `/api/auth/login` | Iniciar sesión | Pública |
| POST | `/api/auth/logout` | Cerrar sesión (queda en la auditoría) | Sesión iniciada (también con contraseña temporal) |
| GET | `/api/auth/me` | Datos y permisos del usuario autenticado | Sesión iniciada (también con contraseña temporal) |
| POST | `/api/auth/cambiar-password` | Cambiar la contraseña propia | Sesión iniciada (también con contraseña temporal) |
| POST | `/api/auth/forgot-password` | Solicitar código de recuperación | Pública |
| POST | `/api/auth/verify-reset-code` | Validar el código recibido | Pública |
| POST | `/api/auth/reset-password` | Crear la nueva contraseña | Pública |

#### Empresa

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| GET | `/api/empresa` | Consultar la empresa | `empresa.ver` o `empresa.editar` |
| PUT | `/api/empresa` | Modificar los datos de la empresa | `empresa.editar` |
| PUT | `/api/empresa/parametros` | Configurar plazos y reglas de inventario/IA | `empresa.editar` |

#### Sedes

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| GET | `/api/sedes` | Listar y buscar sedes | `sedes.ver` |
| GET | `/api/sedes/directorio` | Sedes activas de la empresa (nombre y ciudad), para elegir la contraparte de un traslado | `traslados.solicitar` o `traslados.ver` o `sedes.ver` |
| POST | `/api/sedes` | Registrar una sede | `sedes.crear` |
| GET | `/api/sedes/{sede_id}` | Consultar una sede | `sedes.ver` |
| PUT | `/api/sedes/{sede_id}` | Modificar una sede | `sedes.editar` |
| PATCH | `/api/sedes/{sede_id}/estado` | Inhabilitar o reactivar una sede | `sedes.inhabilitar` |

#### Usuarios

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| GET | `/api/usuarios` | Consultar usuarios | `usuarios.ver` |
| POST | `/api/usuarios` | Registrar un usuario | `usuarios.crear` |
| GET | `/api/usuarios/{usuario_id}` | Consultar un usuario | `usuarios.ver` |
| PUT | `/api/usuarios/{usuario_id}` | Modificar datos, rol o sede de un usuario | `usuarios.editar` |
| PATCH | `/api/usuarios/{usuario_id}/estado` | Activar o inhabilitar una cuenta | `usuarios.inhabilitar` |
| POST | `/api/usuarios/{usuario_id}/restablecer-password` | Asignar una contraseña temporal | `usuarios.editar` |
| POST | `/api/usuarios/{usuario_id}/desbloquear` | Quitar el bloqueo por intentos fallidos | `usuarios.editar` |

#### Roles y permisos

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| GET | `/api/permisos` | Catálogo de permisos | `roles.ver` |
| GET | `/api/roles` | Consultar roles y sus permisos | `roles.ver` o `usuarios.ver` |
| POST | `/api/roles` | Crear un rol | `roles.crear` |
| GET | `/api/roles/{rol_id}` | Consultar un rol | `roles.ver` |
| PUT | `/api/roles/{rol_id}` | Modificar un rol | `roles.editar` |
| PUT | `/api/roles/{rol_id}/permisos` | Asignar permisos a un rol | `roles.asignar_permisos` |
| DELETE | `/api/roles/{rol_id}` | Eliminar un rol personalizado sin usuarios | `roles.editar` |

#### Categorías

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| GET | `/api/categorias` | Listar y buscar categorías | `categorias.ver` |
| POST | `/api/categorias` | Crear una categoría | `categorias.crear` |
| GET | `/api/categorias/{categoria_id}` | Consultar una categoría | `categorias.ver` |
| PUT | `/api/categorias/{categoria_id}` | Modificar una categoría | `categorias.editar` |
| PATCH | `/api/categorias/{categoria_id}/estado` | Inhabilitar o reactivar una categoría | `categorias.editar` |

#### Productos

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| GET | `/api/productos` | Listar y buscar productos | `productos.ver` |
| POST | `/api/productos` | Registrar un producto | `productos.crear` |
| GET | `/api/productos/{producto_id}` | Consultar un producto | `productos.ver` |
| PUT | `/api/productos/{producto_id}` | Modificar un producto (el código no cambia) | `productos.editar` |
| PATCH | `/api/productos/{producto_id}/estado` | Inhabilitar o reactivar un producto | `productos.inhabilitar` |

#### Inventario

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| GET | `/api/inventario` | Existencias de una sede | `inventario.ver` |
| GET | `/api/inventario/consolidado` | Inventario consolidado de la empresa | `inventario.consolidado` |
| POST | `/api/inventario/entradas` | Registrar entrada de productos | `inventario.entrada` |
| POST | `/api/inventario/salidas` | Registrar salida de productos | `inventario.salida` |
| POST | `/api/inventario/ajustes` | Ajustar existencias a un conteo físico | `inventario.ajustar` |
| PUT | `/api/inventario/niveles` | Configurar stock mínimo y máximo | `inventario.niveles` |
| GET | `/api/movimientos` | Historial de movimientos | `movimientos.ver` |

#### Alertas

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| GET | `/api/alertas` | Consultar alertas de inventario | `alertas.ver` |
| GET | `/api/alertas/resumen` | Conteo de alertas activas | `alertas.ver` |
| POST | `/api/alertas/recalcular` | Re-evaluar todas las alertas | `alertas.recalcular` |

#### Ventas

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| GET | `/api/ventas` | Consultar ventas | `ventas.ver` |
| POST | `/api/ventas` | Registrar una venta | `ventas.registrar` |
| GET | `/api/ventas/{venta_id}` | Consultar una venta con su detalle | `ventas.ver` |
| POST | `/api/ventas/{venta_id}/anular` | Anular una venta y reintegrar existencias | `ventas.anular` |

#### Traslados

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| GET | `/api/traslados` | Consultar traslados | `traslados.ver` |
| POST | `/api/traslados` | Solicitar un traslado entre sedes | `traslados.solicitar` |
| GET | `/api/traslados/{traslado_id}` | Consultar un traslado | `traslados.ver` |
| POST | `/api/traslados/{traslado_id}/aprobar` | Aprobar un traslado solicitado | `traslados.aprobar` |
| POST | `/api/traslados/{traslado_id}/rechazar` | Rechazar un traslado solicitado | `traslados.aprobar` |
| POST | `/api/traslados/{traslado_id}/confirmar` | Confirmar la recepción y mover las existencias | `traslados.confirmar` |
| POST | `/api/traslados/{traslado_id}/cancelar` | Cancelar un traslado pendiente | `traslados.solicitar` o `traslados.aprobar` |

#### Predicciones

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| POST | `/api/predicciones/ejecutar` | Generar predicciones de demanda (se calculan en segundo plano) | `prediccion.ejecutar` |
| GET | `/api/predicciones/ejecuciones` | Historial de ejecuciones | `prediccion.ver` |
| GET | `/api/predicciones/ejecuciones/{ejecucion_id}` | Detalle de una ejecución | `prediccion.ver` |
| GET | `/api/predicciones` | Consultar predicciones de demanda | `prediccion.ver` |
| GET | `/api/predicciones/serie` | Historial de ventas y pronóstico de un producto en una sede | `prediccion.ver` |
| GET | `/api/predicciones/modelos` | Modelos y reglas que usa la predicción | `prediccion.ver` |

#### Recomendaciones

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| GET | `/api/recomendaciones` | Consultar recomendaciones | `recomendaciones.ver` |
| POST | `/api/recomendaciones/generar` | Generar recomendaciones a partir de la última predicción | `recomendaciones.generar` |
| GET | `/api/recomendaciones/{recomendacion_id}` | Consultar una recomendación | `recomendaciones.ver` |
| POST | `/api/recomendaciones/{recomendacion_id}/aprobar` | Aprobar una recomendación | `recomendaciones.aprobar` |
| POST | `/api/recomendaciones/{recomendacion_id}/rechazar` | Rechazar una recomendación | `recomendaciones.aprobar` |
| POST | `/api/recomendaciones/{recomendacion_id}/ejecutar` | Marcar un reabastecimiento aprobado como realizado | `recomendaciones.aprobar` |

#### Auditoría

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| GET | `/api/auditoria` | Consultar la auditoría | `auditoria.ver` o `auditoria.operaciones` |
| GET | `/api/auditoria/opciones` | Módulos y acciones disponibles para filtrar | `auditoria.ver` o `auditoria.operaciones` |

#### Panel de control

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| GET | `/api/dashboard` | Indicadores del panel (solo las secciones que el usuario puede ver) | Sesión iniciada; cada sección exige su permiso |

#### Reportes

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| GET | `/api/reportes` | Reportes que el usuario puede generar | Sesión iniciada (lista solo los permitidos) |
| GET | `/api/reportes/{tipo}` | Generar un reporte: vista previa (json) o descarga (csv, xlsx) | `reportes.<tipo>` según el tipo |

#### Integraciones

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| GET | `/api/integraciones/alcances` | Alcances que se pueden conceder a un agente | `agentes.gestionar` |
| GET | `/api/integraciones/llaves` | Listar llaves de agentes | `agentes.gestionar` |
| POST | `/api/integraciones/llaves` | Crear una llave | `agentes.gestionar` |
| POST | `/api/integraciones/llaves/{llave_id}/revocar` | Revocar una llave | `agentes.gestionar` |

#### Agentes de IA

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| GET | `/api/agentes/yo` | Qué puede consultar esta llave | Llave de agente |
| GET | `/api/agentes/inventario` | Existencias por sede | Llave de agente |
| GET | `/api/agentes/alertas` | Alertas de inventario activas | Llave de agente |
| GET | `/api/agentes/predicciones` | Última predicción de demanda (son estimaciones, no ventas) | Llave de agente |
| GET | `/api/agentes/recomendaciones` | Recomendaciones pendientes de aprobación humana | Llave de agente |


#### Sistema

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| GET | `/api/health` | Estado del servicio | Pública |
| GET | `/api/health/ready` | Estado de la base de datos | Pública |

## Regenerar este mapa

Si agrega rutas, actualice esta tabla. El esquema `/api/openapi.json` se actualiza solo; para volcarlo a un archivo
use `python backend/scripts/exportar_openapi.py`.
