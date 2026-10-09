# Arquitectura

Inventia es una aplicación web de tres capas (interfaz, API y base de datos) más un módulo de predicción
que corre dentro de la API. Está pensada para una PyME con una o varias sedes y una sola base de datos central.

## Vista general

```mermaid
flowchart TB
    subgraph Navegador
        SPA[Aplicación React<br/>TypeScript · Vite · Tailwind]
    end

    subgraph Servidor
        NGINX[nginx<br/>archivos estáticos + proxy /api]
        API[API FastAPI<br/>Python 3.13]
        ML[Módulo de predicción<br/>numpy · statsmodels · scikit-learn]
        API --- ML
    end

    DB[(PostgreSQL 16)]
    SMTP[Servidor de correo SMTP]
    AGENTE[Agente de IA externo<br/>solo lectura]

    SPA -- HTTPS · JWT --> NGINX
    NGINX -- /api --> API
    API -- SQL asíncrono --> DB
    API -- códigos de recuperación --> SMTP
    AGENTE -- X-API-Key --> API
```

| Pieza | Tecnología | Responsabilidad |
|---|---|---|
| Interfaz | React 19, TypeScript estricto, Vite, Tailwind v4, TanStack Query, React Hook Form + zod | Presentación, validación en el cliente, ocultar lo que el usuario no puede usar |
| Servidor web | nginx (imagen sin privilegios) | Servir la aplicación compilada, reenviar `/api`, cabeceras de seguridad |
| API | FastAPI, SQLAlchemy 2 asíncrono, Alembic, pydantic v2 | Reglas de negocio, permisos, transacciones, auditoría |
| Predicción | numpy, pandas, statsmodels, scikit-learn | Pronóstico de demanda y evaluación (sin acceso a la base de datos) |
| Base de datos | PostgreSQL 16 | Única fuente de verdad; restricciones, índices y disparadores de solo inserción |

## Capas del backend

```
backend/app/
├── api/         Rutas HTTP: validan entrada, exigen permisos y delegan. Sin reglas de negocio.
├── services/    Reglas de negocio y transacciones. Reciben un Contexto, nunca ids de empresa del cliente.
├── ml/          Cálculo de predicción puro (sin base de datos): modelos, evaluación, pipeline, extracción.
├── models/      Tablas SQLAlchemy.
├── schemas/     Esquemas pydantic de entrada y salida (generan el contrato OpenAPI).
├── core/        Configuración, seguridad, permisos, errores, contexto de petición, base de datos.
├── cli.py       Administración desde la terminal (inicializar, predecir, cargar-demo, sincronizar-permisos).
└── demo.py      Datos de demostración generados a través de los mismos servicios que usa la API.
```

Reglas que se mantienen en todo el código:

- **Las rutas no contienen reglas de negocio.** Una ruta valida, exige permiso y llama a un servicio.
- **El contexto manda.** Cada servicio recibe un `Contexto` (usuario, empresa, permisos, sedes autorizadas).
  Ninguna consulta confía en una empresa o sede enviada por el navegador sin comprobarla contra el contexto.
- **Un servicio, una transacción.** Cada operación confirma (`commit`) una sola vez al final; si algo falla, no
  queda nada a medias.
- **Los errores de negocio son excepciones tipadas** (`ReglaNegocio`, `Conflicto`, `SinPermiso`,
  `ExistenciasInsuficientes`…) que un único manejador convierte en la respuesta JSON uniforme.

## Aislamiento de empresas y sedes

```mermaid
flowchart LR
    T[Token JWT] --> U[Usuario + rol + permisos]
    U --> C[Contexto]
    C -->|empresa_id| F1[Todas las consultas<br/>filtran por empresa]
    C -->|sedes_autorizadas| F2[Rol de sede: solo su sede<br/>Rol de empresa: todas]
    C -->|permisos| F3[requiere&#40;permiso&#41;<br/>en cada ruta]
```

- **Multiempresa:** todas las tablas de negocio llevan `empresa_id` y todas las consultas lo filtran con el valor
  del contexto. Hay pruebas que crean dos empresas y verifican que ninguna ve ni modifica datos de la otra.
- **Multisede:** un rol con alcance `sede` queda restringido a la sede que tiene asignada; un rol con alcance
  `empresa` ve todas. El filtro se aplica en el servidor, no en la interfaz.
- **Permisos:** 52 permisos agrupados por módulo. Cada ruta declara cuáles acepta (`requiere(a, b)` = «alguno de»).

## Integridad del inventario

La cantidad disponible vive **únicamente** en `inventario_sede`. El consolidado es una suma de esas filas.

```mermaid
sequenceDiagram
    participant C as Cliente
    participant S as Servicio
    participant DB as PostgreSQL
    C->>S: Registrar venta de 3 unidades
    S->>DB: UPDATE inventario_sede SET cantidad = cantidad − 3<br/>WHERE cantidad − 3 ≥ 0 RETURNING cantidad
    alt hay existencias
        DB-->>S: saldo nuevo
        S->>DB: INSERT movimientos (saldo anterior y posterior)
        S->>DB: Re-evaluar alertas (misma transacción)
        S->>DB: COMMIT
        S-->>C: 201 venta registrada
    else existencias insuficientes
        DB-->>S: 0 filas
        S->>DB: ROLLBACK
        S-->>C: 409 «hay 2 y se necesitan 3»
    end
```

- La condición `cantidad + delta ≥ 0` está **dentro** del `UPDATE`, así que dos ventas simultáneas nunca dejan el
  stock negativo, sin necesidad de bloquear filas manualmente.
- Cuando una operación toca varias filas (venta con varios productos, traslado), se aplican siempre en el mismo
  orden (sede, producto) para evitar interbloqueos.
- Los consecutivos (número de venta y de traslado) salen de la tabla `secuencias` con una actualización atómica.
- La confirmación de un traslado es una «llave»: el `UPDATE` que pasa el estado de `aprobado` a `confirmado` solo
  tiene éxito una vez; si dos personas confirman a la vez, una de ellas recibe un conflicto y no se mueve nada.
- `movimientos` y `auditoria` son de **solo inserción**: un disparador de PostgreSQL rechaza `UPDATE` y `DELETE`
  incluso si alguien ejecuta SQL a mano. Los errores se corrigen con un movimiento compensatorio.
- Todas las fechas se guardan en UTC; el «día» de una venta se calcula en la zona horaria de la empresa.

## Ciclo de un traslado

```mermaid
stateDiagram-v2
    [*] --> solicitado: Solicitar
    solicitado --> aprobado: Aprueba la sede de origen
    solicitado --> rechazado: Rechaza la sede de origen
    solicitado --> cancelado: Cancelar
    aprobado --> cancelado: Cancelar
    aprobado --> confirmado: Confirma la sede de destino<br/>(mueve existencias)
    confirmado --> [*]
    rechazado --> [*]
    cancelado --> [*]
```

Las existencias solo cambian al **confirmar**, en una sola transacción que descuenta del origen y suma al destino.

## Predicción y recomendaciones

Ver [PREDICCION.md](PREDICCION.md). En términos de arquitectura:

- `app/ml/` no importa SQLAlchemy ni FastAPI (salvo `datos.py`, que es la única pieza que lee la base de datos).
  Eso permite probar los modelos con series construidas a mano y reutilizarlos desde scripts (`ml/`).
- La ejecución corre como tarea en segundo plano de FastAPI. La interfaz sondea el estado.
- Las recomendaciones solo leen predicciones y existencias; **no escriben inventario**.

## Integración con agentes de IA

```mermaid
flowchart LR
    ADM[Administrador] -- crea llave --> K[(api_keys<br/>solo el hash)]
    AG[Agente externo] -- X-API-Key --> RA[/api/agentes/*/]
    RA -- valida alcance, sede y vigencia --> K
    RA --> D[Inventario · alertas<br/>predicciones · recomendaciones]
```

Las llaves son independientes de los usuarios, de **solo lectura**, con alcances (`inventario:leer`,
`alertas:leer`, `predicciones:leer`, `recomendaciones:leer`), vencimiento (90 días por defecto; la interfaz permite
entre 30 y 730), restricción opcional a una sede y revocación inmediata. Una llave no sirve en la API normal y un token de usuario no sirve en `/api/agentes`.

## Frontend

```
frontend/src/
├── App.tsx            Rutas, cada una protegida por permiso
├── auth/              Sesión, rutas protegidas, rutas públicas
├── components/
│   ├── ui/            Biblioteca interna (botones, tablas, modales, confirmaciones, avisos…)
│   ├── charts/        Gráficos en SVG hechos a mano (líneas, barras) sin librerías externas
│   └── layout/        Estructura de la aplicación y navegación filtrada por permisos
├── features/          Una carpeta por módulo (inventario, ventas, traslados, prediccion, …)
├── hooks/             useFiltros (estado en la URL), useMutacion, catálogos compartidos
├── lib/               Cliente HTTP, errores, formato (es-CO), permisos, formularios
└── types/api.gen.ts   Tipos generados del esquema OpenAPI (npm run tipos)
```

Decisiones de interfaz que conviene conocer:

- **Los tipos vienen de la API.** `npm run tipos` los regenera desde el esquema OpenAPI; la integración continua
  falla si quedaron desactualizados. Así un cambio en el backend que rompe la interfaz se detecta al compilar.
- **Los filtros viven en la URL.** Se puede compartir un enlace con la lista ya filtrada y el botón «atrás»
  funciona como se espera.
- **Cada pantalla resuelve cuatro estados:** cargando (esqueletos con la forma final), vacío (con indicación de
  qué hacer), error (con reintento) y contenido.
- **Sin dependencias externas en tiempo de ejecución:** fuentes e iconos van empaquetados; la política de seguridad
  de contenido solo permite recursos del mismo origen.
- **Carga diferida por ruta:** cada pantalla se descarga cuando se visita por primera vez.

## Despliegue

```mermaid
flowchart LR
    subgraph Docker Compose
        W[frontend<br/>nginx :8080] --> B[backend<br/>uvicorn :8000]
        B --> P[(db<br/>postgres :5432)]
    end
    U[Navegador] -- HTTPS lo ofrece el proxy del cliente --> W
```

Al iniciar, el contenedor del backend aplica las migraciones pendientes (`alembic upgrade head`) y, si fallan, no
sirve tráfico. Ver [DESPLIEGUE.md](DESPLIEGUE.md) para el procedimiento y la lista de comprobación de producción.
La configuración de Docker se validó solo en parte (ver [DESPLIEGUE.md](DESPLIEGUE.md) y [LIMITACIONES.md](LIMITACIONES.md)).
