# Inventia

**Sistema web de gestión inteligente de inventarios multisede para PyMEs.**

Inventia centraliza el inventario de una empresa con varias sedes, registra cada movimiento con trazabilidad
completa, avisa cuando algo requiere atención y usa los datos de ventas para **estimar la demanda** y **recomendar**
qué reponer o qué trasladar entre sedes. Las recomendaciones las aprueba siempre una persona.

Proyecto de grado. Los requisitos provienen del documento del proyecto (RF-001 a RF-038, RN-001 a RN-012,
RNF-001 a RNF-050); la correspondencia punto por punto está en [`docs/TRAZABILIDAD.md`](docs/TRAZABILIDAD.md).

## Qué hace

| Área | Funciones |
|---|---|
| **Empresa y sedes** | Varias empresas aisladas entre sí; sedes por empresa; parámetros configurables (plazos, cobertura, umbrales) |
| **Usuarios y permisos** | 5 roles de fábrica (Administrador, Gerente, Encargado de sede, Usuario de inventario, Analista de compras), roles personalizados, 52 permisos, alcance por sede |
| **Catálogo** | Categorías y productos con código inmutable, costo y precio |
| **Inventario** | Existencias por sede y consolidadas; entradas, salidas y ajustes con historial inmutable; mínimos y máximos |
| **Ventas** | Registro multiproducto con descuento atómico de existencias; anulación con motivo y reintegro |
| **Traslados** | Solicitud → aprobación de la sede de origen → confirmación de la sede de destino; las existencias se mueven solo al confirmar |
| **Alertas** | Inventario bajo, excesivo, riesgo de desabastecimiento (según demanda prevista) y sin rotación; se abren y cierran solas |
| **Predicción** | Pronóstico por sede y producto con 6 modelos comparados contra una línea base, validación temporal, error medido (WAPE/MAE), intervalo de 80 % y confianza; **omite con motivo** lo que no tiene datos suficientes |
| **Recomendaciones** | Reabastecimiento y traslado con explicación en español; aprobación humana obligatoria |
| **Reportes** | Siete reportes en vista previa, CSV y Excel |
| **Auditoría** | Accesos y operaciones; registro inmutable |
| **Agentes de IA** | API de solo lectura con llaves propias, alcances, vencimiento y revocación |

## Inicio rápido

### Con Docker Compose

```bash
cp infra/.env.example infra/.env     # complete POSTGRES_PASSWORD, SECRET_KEY y SETUP_TOKEN con valores propios
docker compose -f infra/docker-compose.yml --env-file infra/.env up -d --build
```

Abra <http://localhost:8080>: la pantalla **Configuración inicial** crea la empresa y su primer administrador (pide el
`SETUP_TOKEN`). Guía completa y lista de comprobación de producción: [`docs/DESPLIEGUE.md`](docs/DESPLIEGUE.md).

> La configuración de Docker se validó solo en parte (no se pudieron construir las imágenes en el entorno de
> desarrollo). Haga una primera prueba en un entorno de ensayo; detalles en [`docs/DESPLIEGUE.md`](docs/DESPLIEGUE.md).

### En su máquina (desarrollo)

Requisitos: Python 3.13, Node.js 22 y PostgreSQL 16.

```bash
npm install
npm run setup          # entorno virtual, dependencias y backend/.env
# edite backend/.env: DATABASE_URL y SECRET_KEY
npm run migrar
npm run demo           # opcional: empresa ficticia de movilidad eléctrica con 4 meses de ventas (base vacía); ver docs/DESARROLLO.md
npm run dev            # interfaz en :5173, API en :8000
```

Paso a paso, pruebas y solución de problemas: [`docs/DESARROLLO.md`](docs/DESARROLLO.md).

### Primer administrador

No existe registro público. El primer administrador se crea **una sola vez**, con el token de configuración, desde la
pantalla de configuración inicial o con:

```bash
cd backend && python -m app.cli inicializar --empresa "Mi Empresa" --admin-nombre "Nombre Apellido" --admin-correo admin@empresa.example
```

La contraseña se pide por consola sin eco (o se lee de `INVENTIA_ADMIN_PASSWORD`); nunca se pasa por argumentos.

## Tecnología

| Capa | Tecnología |
|---|---|
| Backend | Python 3.13 · FastAPI · SQLAlchemy 2 (asíncrono) · Alembic · pydantic v2 · Argon2 · JWT |
| Predicción | numpy · pandas · scipy · scikit-learn · statsmodels |
| Frontend | React 19 · TypeScript estricto · Vite · Tailwind v4 · TanStack Query · React Hook Form + zod |
| Datos | PostgreSQL 16 (SQLite solo para pruebas rápidas) |
| Infraestructura | Docker · Docker Compose · nginx · GitHub Actions |

## Estructura

```
.
├── backend/     API, modelos, migraciones y pruebas
├── frontend/    Interfaz web
├── ml/          Experimento reproducible de evaluación de modelos
├── agents/      Ejemplo de agente de IA (solo lectura)
├── infra/       Docker Compose y scripts de respaldo / restauración
├── scripts/     Utilidades multiplataforma para npm run …
└── docs/        Documentación
```

## Pruebas

```bash
npm test                      # backend (SQLite) + frontend
npm run lint && npm run typecheck && npm run build
```

Las pruebas que dependen de PostgreSQL (concurrencia, migraciones, disparadores) se ejecutan definiendo
`TEST_DATABASE_URL` con una base **descartable**. Resultados de la última ejecución y lo que no se probó:
[`docs/LIMITACIONES.md`](docs/LIMITACIONES.md).

## Documentación

| Documento | Para qué |
|---|---|
| [`docs/MANUAL_USUARIO.md`](docs/MANUAL_USUARIO.md) | Uso diario, por tareas y por rol |
| [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) | Capas, aislamiento, integridad del inventario, diagramas |
| [`docs/MODELO_DATOS.md`](docs/MODELO_DATOS.md) | Tablas, restricciones, índices e invariantes |
| [`docs/PREDICCION.md`](docs/PREDICCION.md) | Cómo se estima la demanda, se mide el error y se generan recomendaciones |
| [`docs/SEGURIDAD.md`](docs/SEGURIDAD.md) | Controles implementados, roles y responsabilidades de quien despliega |
| [`docs/API.md`](docs/API.md) | Convenciones y mapa de rutas |
| [`docs/DESARROLLO.md`](docs/DESARROLLO.md) | Entorno, pruebas, migraciones, convenciones |
| [`docs/DESPLIEGUE.md`](docs/DESPLIEGUE.md) | Docker, producción, respaldos, actualizaciones |
| [`docs/DECISIONES.md`](docs/DECISIONES.md) | Decisiones de diseño y diferencias con el documento de grado |
| [`docs/TRAZABILIDAD.md`](docs/TRAZABILIDAD.md) | Matriz RF / RN / RNF → implementación → prueba |
| [`docs/LIMITACIONES.md`](docs/LIMITACIONES.md) | Qué está probado, qué no y qué falta |
| [`CHANGELOG.md`](CHANGELOG.md) | Registro de cambios |

## Seguridad

- No hay contraseñas ni claves en este repositorio. Los archivos `.env` están excluidos; use los `.env.example`.
- Genere sus propios `SECRET_KEY`, `SETUP_TOKEN` y contraseña de base de datos. Si alguna vez compartió o publicó un
  valor de estos, **rótelo**.
- La aplicación no termina HTTPS: en producción publíquela detrás de un proxy con certificado.
- Lista de controles y de responsabilidades de quien despliega: [`docs/SEGURIDAD.md`](docs/SEGURIDAD.md).

## Estado

Versión **1.0.0**. Backend y frontend completos y probados; la predicción se validó con datos sintéticos de
demostración y debe medirse con las ventas reales de cada empresa antes de apoyarse en ella. Ver
[`docs/LIMITACIONES.md`](docs/LIMITACIONES.md) para el detalle honesto de lo verificado y lo pendiente.
