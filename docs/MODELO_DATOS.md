# Modelo de datos

Esquema de PostgreSQL gestionado con Alembic. Los nombres de índices y restricciones siguen una convención fija
(`ix_`, `uq_`, `ck_`, `fk_`, `pk_`), de modo que las migraciones son predecibles. Las columnas de estado se
guardan como texto (sin tipos `ENUM` nativos) para poder añadir valores sin migrar tipos.

## Diagrama

```mermaid
erDiagram
    empresas ||--o{ sedes : tiene
    empresas ||--o{ roles : define
    empresas ||--o{ usuarios : emplea
    empresas ||--o{ categorias : organiza
    empresas ||--o{ productos : cataloga
    roles ||--o{ rol_permisos : otorga
    permisos ||--o{ rol_permisos : "se asigna en"
    roles ||--o{ usuarios : "se asigna a"
    sedes ||--o{ usuarios : "opera en"
    categorias ||--o{ productos : agrupa

    sedes ||--o{ inventario_sede : guarda
    productos ||--o{ inventario_sede : "existe en"
    inventario_sede }o--|| empresas : pertenece
    sedes ||--o{ movimientos : registra
    productos ||--o{ movimientos : afecta
    usuarios ||--o{ movimientos : realiza

    sedes ||--o{ ventas : realiza
    ventas ||--|{ venta_items : contiene
    productos ||--o{ venta_items : vendido
    ventas ||--o{ movimientos : origina

    sedes ||--o{ traslados : "origen y destino"
    traslados ||--|{ traslado_items : contiene
    traslados ||--o{ movimientos : origina
    recomendaciones |o--o{ traslados : "da lugar a"

    inventario_sede ||--o{ alertas : "genera (por sede y producto)"

    empresas ||--o{ ejecuciones_prediccion : lanza
    ejecuciones_prediccion ||--o{ predicciones : produce
    ejecuciones_prediccion ||--o{ recomendaciones : "origina"
    productos ||--o{ predicciones : estima
    sedes ||--o{ predicciones : estima

    empresas ||--o{ auditoria : registra
    usuarios ||--o{ auditoria : actor
    empresas ||--o{ api_keys : emite
    usuarios ||--o{ password_reset_tokens : solicita
    empresas ||--o{ secuencias : numera
```

## Tablas

### Acceso y organización

| Tabla | Propósito | Reglas relevantes |
|---|---|---|
| `empresas` | Empresa cliente. `configuracion` (JSON) guarda los parámetros de inventario y predicción | `identificacion` única; inhabilitar la empresa bloquea el ingreso de todos sus usuarios |
| `sedes` | Ubicaciones de la empresa | Nombre único por empresa **sin distinguir mayúsculas** (`uq_sedes_empresa_nombre` sobre `lower(nombre)`) |
| `permisos` | Catálogo global de permisos (código, módulo, descripción) | Se define en `app/core/permisos.py` y se sincroniza al iniciar la API |
| `roles` | Roles por empresa. `clave` identifica los 5 del sistema; `alcance` es `empresa` o `sede` | Nombre único por empresa sin distinguir mayúsculas; clave única por empresa; los roles del sistema no se eliminan ni cambian de permisos |
| `rol_permisos` | Relación rol ↔ permiso | Clave compuesta; se borra en cascada con el rol |
| `usuarios` | Cuentas de acceso | `email` único global; `password_hash` (Argon2id); `password_version` invalida tokens; `intentos_fallidos` y `bloqueado_hasta` para el bloqueo temporal; `debe_cambiar_password` para contraseñas temporales |
| `password_reset_tokens` | Códigos de recuperación | El código y el token de sesión se guardan solo como hash; un solo uso; máx. 5 intentos; vencen |

### Catálogo e inventario

| Tabla | Propósito | Reglas relevantes |
|---|---|---|
| `categorias` | Agrupación de productos | Nombre único por empresa sin distinguir mayúsculas |
| `productos` | Catálogo | `(empresa_id, codigo)` único; el código no cambia; `costo` y `precio_venta` son datos distintos; `unidad_medida` |
| `inventario_sede` | **Única** fuente de existencias: cantidad por sede y producto, más `stock_minimo` y `stock_maximo` | `UNIQUE (sede_id, producto_id)`; `CHECK cantidad >= 0`; `CHECK stock_maximo >= stock_minimo` |
| `movimientos` | Historial inmutable de cada cambio de existencias | `CHECK delta <> 0` y `saldo_posterior >= 0`; guarda saldo anterior y posterior, usuario, sede contraparte (traslados) y la venta o traslado de origen; **solo inserción** (disparador) |
| `secuencias` | Consecutivos por empresa (`venta`, `traslado`) | Clave `(empresa_id, nombre)`; se incrementa de forma atómica |
| `alertas` | Alertas de inventario abiertas y resueltas | Índice único **parcial** `(sede_id, producto_id, tipo) WHERE estado = 'activa'`: nunca hay dos alertas activas iguales |

Tipos de movimiento: `entrada`, `salida`, `ajuste`, `venta`, `anulacion_venta`, `traslado_salida`, `traslado_entrada`.

### Ventas y traslados

| Tabla | Propósito | Reglas relevantes |
|---|---|---|
| `ventas` | Cabecera de venta | `(empresa_id, numero)` único; `fecha_dia` es el día local para agrupar; la venta anulada se conserva con quién, cuándo y por qué |
| `venta_items` | Líneas de venta | `cantidad > 0`; un producto una sola vez por venta; el precio queda congelado en la línea |
| `traslados` | Solicitud de traslado entre sedes | `CHECK sede_origen_id <> sede_destino_id`; guarda quién solicitó, aprobó, confirmó o cerró, y cuándo; `recomendacion_id` si nació de una recomendación |
| `traslado_items` | Líneas de traslado | `cantidad > 0`; un producto una sola vez por traslado |

### Predicción y recomendaciones

| Tabla | Propósito | Reglas relevantes |
|---|---|---|
| `ejecuciones_prediccion` | Una corrida del módulo predictivo | Estado, horizonte, fecha de corte, parámetros y un `resumen` con series evaluadas, omitidas (con motivos) y métricas globales |
| `predicciones` | Demanda estimada de un producto en una sede para un periodo | `(ejecucion_id, sede_id, producto_id)` único; guarda modelo, intervalo, confianza, métricas de validación, serie diaria y advertencias. Se borra en cascada con su ejecución |
| `recomendaciones` | Sugerencias de reabastecimiento o traslado | Estados: `pendiente`, `aprobada`, `rechazada`, `ejecutada`, `reemplazada`; guarda la `justificacion` (datos de origen) y quién la revisó |

### Auditoría e integración

| Tabla | Propósito | Reglas relevantes |
|---|---|---|
| `auditoria` | Accesos y operaciones relevantes | **Solo inserción** (disparador); guarda copia del correo del actor, IP, `request_id` y resultado; `detalle` nunca contiene secretos |
| `api_keys` | Llaves de agentes de IA | Solo se guarda el hash SHA-256 y un prefijo visible; alcances, sede opcional, vencimiento, último uso, revocación (`activa`) |

## Índices pensados para las consultas reales

| Índice | Consulta que acelera |
|---|---|
| `ix_movimientos_empresa_fecha` | Historial por periodo, reportes de movimientos |
| `ix_movimientos_sede_producto_fecha` | Historial de un producto en una sede, reconstrucción de saldos para la predicción |
| `ix_ventas_empresa_fecha_dia`, `ix_ventas_sede_fecha_dia` | Listados y reportes de ventas, series de demanda |
| `ix_alertas_empresa_estado` | Contador y lista de alertas activas |
| `ix_traslados_empresa_estado` | Traslados pendientes |
| `ix_recomendaciones_empresa_estado` | Recomendaciones pendientes |
| `ix_predicciones_empresa_serie` | Última predicción de un producto en una sede |
| `ix_auditoria_empresa_fecha`, `ix_auditoria_modulo_accion` | Consulta de auditoría con filtros |

Las tablas con mayor crecimiento (`movimientos`, `auditoria`, `alertas`, `predicciones`) usan `BIGINT` como llave
primaria en PostgreSQL.

## Invariantes que el sistema garantiza

Estas propiedades las verifica `test_invariantes_de_inventario_tras_operar` y las pruebas de concurrencia:

1. `inventario_sede.cantidad` nunca es negativa.
2. Para cada sede y producto, la suma de los `delta` de `movimientos` es igual a `inventario_sede.cantidad`
   (la migración 0003 crea un movimiento de «inventario inicial» por cada saldo existente para que esto se cumpla
   también con datos migrados).
3. El inventario consolidado es igual a la suma de las existencias de todas las sedes.
4. Un traslado confirmado produce exactamente un movimiento de salida y uno de entrada por producto, con la
   misma cantidad.
5. Una venta anulada devuelve exactamente lo que descontó, una sola vez.
6. No existen dos alertas activas iguales para la misma sede, producto y tipo.
7. No existen consecutivos repetidos de venta ni de traslado dentro de una empresa.

## Migraciones

| Revisión | Contenido |
|---|---|
| `1951a4ae8cf0` | Modelos iniciales (versión anterior del proyecto) |
| `5cb4ddecc152` | Códigos de recuperación de 6 dígitos |
| `0003_inventia` | Reestructuración: RBAC con 5 roles, auditoría, catálogo, inventario por sede con movimientos, ventas, traslados, predicción, recomendaciones y llaves de agentes. **Conserva los datos** de la versión anterior |

Reglas de la migración 0003 sobre datos existentes:

- Cada empresa recibe sus cinco roles del sistema; `ADMIN_GENERAL` pasa a «Administrador» y `USUARIO_SEDE` a
  «Usuario de inventario» (mínimo privilegio). Un usuario de sede sin sede queda **inhabilitado** hasta que un
  administrador le asigne una.
- Los productos pasan a una categoría «General» por empresa; `sku` → `codigo`, `precio` → `precio_venta`.
- Cada saldo existente genera un movimiento de inventario inicial.
- Los nombres de sede repetidos se desambiguan añadiendo el identificador; las existencias negativas quedan en 0.
- Es una migración **solo para PostgreSQL** (usa disparadores y JSONB). Las pruebas la ejecutan desde una base
  vacía, hacia atrás y hacia adelante, y con datos de la versión anterior.

Cómo crear una migración nueva: ver [DESARROLLO.md](DESARROLLO.md#migraciones).
