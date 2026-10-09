# Guía de desarrollo

Cómo preparar el entorno, ejecutar el sistema en su máquina, correr las pruebas y hacer cambios sin romper nada.
Los comandos funcionan igual en Windows (PowerShell), macOS y Linux salvo donde se indica.

## Requisitos

| Herramienta | Versión | Para qué |
|---|---|---|
| Python | 3.13 (mínimo 3.12) | Backend |
| Node.js | 22 (mínimo 20) | Frontend y scripts |
| PostgreSQL | 16 | Base de datos (local o en Docker) |
| Docker Desktop | Opcional | Levantar PostgreSQL con un comando; despliegue completo |

## Puesta en marcha

Desde la raíz del repositorio:

```bash
npm install            # instala la herramienta que lanza backend y frontend a la vez
npm run setup          # crea backend/.venv, instala dependencias del backend y del frontend, crea backend/.env
```

1. **Base de datos.** Con Docker: copie `infra/.env.example` como `infra/.env`, defina `POSTGRES_PASSWORD`, `SECRET_KEY`
   y `SETUP_TOKEN`, y ejecute

   ```bash
   docker compose -f infra/docker-compose.yml --env-file infra/.env up -d db
   ```

   Sin Docker: instale PostgreSQL 16 y cree una base vacía (`CREATE DATABASE inventia;`).

2. **Configuración.** Edite `backend/.env`. Como mínimo:

   ```ini
   DATABASE_URL=postgresql+asyncpg://USUARIO:CLAVE@localhost:5432/inventia
   SECRET_KEY=<al menos 32 caracteres aleatorios>
   ```

   Genere la clave con `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
   Todas las variables están explicadas en [`backend/.env.example`](../backend/.env.example).

3. **Migraciones.**

   ```bash
   npm run migrar
   ```

4. **Primer administrador.** Elija una de las dos formas:

   - Abra la interfaz y complete la pantalla **Configuración inicial** (en desarrollo el token es opcional salvo que
     defina `SETUP_TOKEN`).
   - O por terminal (la contraseña se pide sin eco o se lee de `INVENTIA_ADMIN_PASSWORD`):

     ```bash
     cd backend
     python -m app.cli inicializar --empresa "Mi Empresa" --admin-nombre "Nombre Apellido" --admin-correo admin@empresa.example
     ```

5. **Datos de demostración (opcional).** Hay dos formas:

   - **En su propia empresa** (recomendada para una presentación): primero cree la empresa y su administrador con la
     pantalla **Configuración inicial** (o `python -m app.cli inicializar`), con su correo y la contraseña que elija.
     Después, con la API detenida:

     ```bash
     npm run demo -- --en-empresa-existente
     ```

     Carga en esa empresa tres sedes (Medellín y Envigado), 36 productos de movilidad eléctrica (bicicletas,
     monopatines, motos, baterías y cargadores, repuestos y accesorios) y cuatro meses de ventas, y genera la
     predicción y las recomendaciones. El administrador **conserva su correo y su contraseña**; solo se crean, con contraseñas al azar
     que se muestran **una sola vez**, los usuarios de ejemplo de los demás roles (`@demo.inventia.example`).
   - **Empresa ficticia completa**, en una base vacía: `npm run demo`. También crea el administrador
     (`admin@demo.inventia.example`, contraseña aleatoria que se muestra una sola vez).

   En la demostración los vehículos (bicicletas, monopatines y motos) se venden pocas unidades por día, así que
   buena parte de sus predicciones diarias sale con confianza «baja» o «media»; es el comportamiento esperado de las
   reglas de calidad (ver `docs/PREDICCION.md`), no un fallo. Los repuestos y accesorios de alta rotación sí alcanzan
   confianza «alta».

   La carga hace unas 50 mil consultas. Con la base en el mismo equipo tarda 1 o 2 minutos; contra una base remota
   (por ejemplo Neon) cada consulta paga la latencia de red y puede tardar de 20 minutos a una hora. Es una carga
   única; deje el equipo encendido y conectado hasta que termine. Si se interrumpe a la mitad, la empresa queda con
   datos parciales y hay que reiniciar la base (ver «Solución de problemas»).

6. **Datos de demostración del SIG (opcional).** La carga anterior no incluye el módulo SIG. Para ver el módulo con datos:

   ```bash
   npm run demo:sig                                   # en la empresa que ya tiene la demostración o sus propios datos
   npm run demo -- --en-empresa-existente --con-sig   # o todo junto, la primera vez
   ```

   Crea 5 PQRS en distintos estados, 2 entradas con observaciones, 3 no conformidades, 3 garantías, el historial de
   pausas activas de los últimos 10 días hábiles y la **configuración ambiental de ejemplo** (el factor de la red y los
   parámetros de las categorías de vehículos), marcada como «valores de demostración» en el campo fuente. Exige que
   la empresa tenga productos y usuarios operativos (los de la demostración sirven) y no se puede ejecutar dos veces
   (responde `demo_sig_ya_cargada`). **No la use en una instalación real:** los parámetros ambientales de ejemplo no
   son datos de ninguna empresa; en producción los define el administrador en **SIG → Gestión ambiental → Configuración**.
   Esta carga no necesita variables de entorno adicionales.


6. **Arrancar.**

   ```bash
   npm run dev
   ```

   - Interfaz: <http://localhost:5173>
   - API: <http://localhost:8000> · documentación interactiva: <http://localhost:8000/api/docs>

   Vite redirige `/api` al backend, así que en desarrollo no hace falta configurar CORS.

> `scripts/python.mjs` usa automáticamente `backend/.venv` (o `backend/venv`). Para usar otro intérprete defina
> `INVENTIA_PYTHON`.

## Estructura del repositorio

```
.
├── backend/          API (FastAPI), modelos, migraciones y pruebas
├── frontend/         Interfaz (React + TypeScript)
├── ml/               Experimentos reproducibles de predicción
├── agents/           Ejemplo de agente de IA que consulta la API
├── infra/            Docker Compose, scripts de respaldo y restauración
├── scripts/          Utilidades multiplataforma para npm run …
├── docs/             Documentación
└── .github/          Integración continua
```

## Pruebas

| Qué | Comando | Notas |
|---|---|---|
| Todo | `npm test` | Backend y frontend |
| Backend (rápido, SQLite) | `npm run test:backend` | No requiere nada instalado |
| Backend contra PostgreSQL | ver abajo | Concurrencia real, migraciones, disparadores, índices parciales |
| Frontend | `npm run test:frontend` | Vitest + Testing Library |
| Lint | `npm run lint` | oxlint con `--deny-warnings` |
| Tipos | `npm run typecheck` | `tsc -b` |
| Compilación | `npm run build` | Tipos + Vite |

**Pruebas con PostgreSQL.** Cree una base **vacía y descartable** (las pruebas la borran y recrean) y ejecute:

```bash
# bash
export TEST_DATABASE_URL=postgresql+asyncpg://USUARIO:CLAVE@localhost:5432/inventia_test
npm run test:backend
```

```powershell
# PowerShell
$env:TEST_DATABASE_URL = "postgresql+asyncpg://USUARIO:CLAVE@localhost:5432/inventia_test"
npm run test:backend
```

> **Nunca** apunte `TEST_DATABASE_URL` a una base con datos reales. Sin esa variable, las pruebas marcadas
> `postgres` se omiten (el informe lo indica con «SKIPPED»).

Las pruebas del backend (`backend/tests/`) se organizan por módulo:

| Archivo | Cubre |
|---|---|
| `test_setup_auth.py` | Configuración inicial, ingreso, bloqueo, recuperación, cabeceras de seguridad |
| `test_administracion.py` | Empresa, sedes, usuarios, roles, aislamiento entre empresas, auditoría |
| `test_catalogo_inventario.py` | Categorías, productos, entradas, salidas, ajustes, niveles, alertas, consolidado |
| `test_ventas_traslados.py` | Ventas, anulaciones, traslados, invariantes |
| `test_ml.py` | Modelos de pronóstico, validación temporal, calidad de datos |
| `test_prediccion.py` | Ejecución de predicciones, permisos, aislamiento |
| `test_recomendaciones.py` | Reglas de reposición y traslado, ciclo de vida |
| `test_dashboard_reportes.py` | Panel, reportes JSON/CSV/Excel, visibilidad de auditoría |
| `test_agentes.py` | Llaves de agentes, alcances, solo lectura |
| `test_demo.py` | Carga de la demostración (y de los datos de ejemplo del SIG) en la empresa de la configuración inicial |
| `test_sig_pqrs_adjuntos.py` | SIG: PQRS, historial, permisos y evidencias adjuntas |
| `test_sig_calidad_entradas.py` | SIG: entradas con observaciones, no conformidades y garantías (sin tocar el inventario) |
| `test_sig_sst.py` | SIG: pausas activas (servidor decide, sin repeticiones, sin pausas a administradores) |
| `test_sig_ambiental.py` | SIG: conteo de vehículos, fórmula, parámetros, anulaciones, sin doble conteo |
| `test_sig_permisos.py` | SIG: los permisos nuevos llegan a los roles de fábrica al actualizar una instalación existente |
| `test_flujo_integral.py` | Escenario de 17 pasos de principio a fin |
| `test_concurrencia.py` | Operaciones simultáneas (PostgreSQL) |
| `test_migraciones.py` | Migraciones desde cero, hacia atrás, con datos previos (PostgreSQL) |

## Convenciones de código

**Backend**

- Las rutas (`api/`) solo validan, exigen permisos y delegan. La lógica va en `services/`.
- Todo servicio recibe un `Contexto` y filtra por `ctx.empresa_id`. Nunca confíe en un `empresa_id` del cliente.
- Toda operación que cambie datos registra auditoría (`auditoria_service.registrar`) en la misma transacción.
- Los mensajes que ve el usuario van en español correcto (tildes, «ñ», signos de apertura).
- Las existencias solo se cambian con `inventario_service.aplicar_movimiento` o `aplicar_lote`.

**Frontend**

- Una carpeta por módulo en `src/features/`. Los componentes de uso común van en `src/components/ui/`.
- Cada pantalla resuelve carga, vacío, error y contenido.
- Los filtros viven en la URL (`useFiltros`); las mutaciones usan `useMutacion` (avisos e invalidación de caché).
- Todo texto visible en español correcto; los números y fechas pasan por `lib/format.ts` (`es-CO`).
- Los tipos de la API **no se escriben a mano**: se generan (ver abajo).

## Cambiar la API y mantener el frontend al día

Cuando cambie un esquema o una ruta del backend:

```bash
npm run tipos        # exporta el esquema OpenAPI y regenera frontend/src/types/api.gen.ts
npm run typecheck    # el compilador señala qué pantallas hay que ajustar
```

Confirme `api.gen.ts` junto con el cambio. La integración continua falla si los tipos quedaron desactualizados.

## Migraciones

```bash
cd backend
# 1. Modifique los modelos en app/models/
# 2. Genere la migración (revísela siempre antes de aplicarla)
python -m alembic revision --autogenerate -m "descripcion_corta"
# 3. Aplique y pruebe
python -m alembic upgrade head
python -m alembic downgrade -1 && python -m alembic upgrade head
```

Reglas:

- **Nunca edite una migración ya aplicada** en un entorno compartido; cree otra.
- Revise lo generado: Alembic no detecta cambios de nombre ni de datos.
- Si agrega una tabla de solo inserción, llame a `proteger_solo_insercion(tabla)` en el modelo y cree el disparador
  en la migración.
- `test_migracion_desde_base_vacia_y_alembic_check` falla si los modelos y las migraciones difieren: es la red de
  seguridad contra olvidar generar una migración.

## Permisos nuevos

1. Agréguelo en `backend/app/core/permisos.py` (`PERMISOS`) y, si corresponde, a los roles de fábrica.
2. Úselo en la ruta con `requiere("modulo.accion")`.
3. Reinicie la API: el catálogo se sincroniza al arrancar (también con `python -m app.cli sincronizar-permisos`).
   Un permiso nuevo se agrega **una sola vez**, al aparecer en el catálogo, a los roles del sistema de cada empresa
   cuyo conjunto por defecto en `ROLES_SISTEMA` lo incluya (el «Administrador» siempre). Los roles creados por la
   empresa no lo reciben: un administrador debe concederlo desde **Roles y permisos**. Como solo se actúa sobre
   permisos nuevos, si una empresa le quitó un permiso a un rol de fábrica no se le vuelve a poner.
   Las empresas nuevas reciben los valores por defecto de `ROLES_SISTEMA`.
4. Úselo en el frontend (`lib/permisos.ts`, `App.tsx`, `navegacion.ts`).
5. Agregue pruebas: con permiso, sin permiso y fuera de sede.

## Actualizar dependencias (RNF-039)

Las versiones están fijadas para que las compilaciones sean reproducibles. Cada cierto tiempo (por ejemplo, cada
trimestre, o de inmediato ante un aviso de seguridad):

```bash
# Backend
cd backend && pip list --outdated
# edite requirements.txt con la versión nueva, y luego
pip install -r requirements-dev.txt && python -m pytest

# Frontend
cd frontend && npm outdated
npm update && npm test && npm run build
```

Registre el cambio en [`CHANGELOG.md`](../CHANGELOG.md). Si la actualización toca la API de FastAPI, pydantic o
SQLAlchemy, ejecute además las pruebas con PostgreSQL.

## Solución de problemas

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| El backend no arranca: «SECRET_KEY debe tener al menos 32 caracteres» | Clave corta o de ejemplo | Genere una nueva (ver arriba) |
| «En producción SETUP_TOKEN es obligatorio» | `ENVIRONMENT=production` sin token | Defina `SETUP_TOKEN` (16+ caracteres) |
| La API arranca pero responde errores de tabla inexistente | Migraciones sin aplicar | `npm run migrar` |
| `connection refused` a la base | PostgreSQL apagado o puerto distinto | Revise `DATABASE_URL`; `docker compose … ps` |
| Error SSL con una base local | Detección automática errónea | `DATABASE_SSL=false` |
| `npm run tipos` falla: «No module named fastapi» | Se usó el Python del sistema | Ejecute `npm run setup` o defina `INVENTIA_PYTHON` |
| Las pruebas de PostgreSQL aparecen como omitidas | Falta `TEST_DATABASE_URL` | Defínala (base descartable) |
| La interfaz muestra «No se pudo conectar con el servidor» | El backend no está en :8000 | Inicie el backend o defina `VITE_PROXY_API` |
| La carga de demostración se interrumpió y al repetirla dice que la empresa ya tiene sedes o productos | Quedaron datos parciales | En una base **descartable**: `DROP SCHEMA public CASCADE; CREATE SCHEMA public;`, luego `npm run migrar` y repita desde la configuración inicial |
