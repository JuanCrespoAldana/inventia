# Guía de despliegue

Cómo poner Inventia en un servidor real, qué configurar antes de abrirlo a los usuarios y cómo mantenerlo.

> **Estado de verificación.** Qué se comprobó y qué no:
>
> | Comprobado | No comprobado |
> |---|---|
> | `docker-compose.yml` es válido (`docker compose config`): esquema, interpolación y rechazo de variables obligatorias vacías | Construcción de las imágenes (`docker build`): el registro de imágenes estaba bloqueado en el entorno de desarrollo |
> | El script de arranque del contenedor (`docker-entrypoint.sh`) aplica las migraciones sobre una base PostgreSQL vacía y luego inicia la API | Ejecución real de los contenedores, su red y sus comprobaciones de salud |
> | La API arranca con `ENVIRONMENT=production`, responde `/api/health/ready`, rechaza un token de configuración incorrecto (403), acepta el correcto (201) y no permite repetir la configuración (409) | `frontend/nginx.conf` (no había nginx para validarlo) y la interfaz servida con él |
> | Volcado y restauración con `pg_dump`/`pg_restore` contra PostgreSQL local | Los scripts `respaldar` y `restaurar` en sus versiones `.sh` y `.ps1` ejecutados contra Docker Compose (solo se revisó la sintaxis de los `.sh`) |
>
> Haga el primer despliegue en un entorno de prueba y siga la lista de la sección
> [«Primera prueba»](#primera-prueba-del-despliegue) antes de confiar datos reales al sistema.

## Opciones

| Opción | Cuándo | Qué necesita |
|---|---|---|
| **A. Docker Compose** (recomendada) | Un servidor propio o una máquina virtual | Docker 24+ con Compose v2, ~2 GB de RAM libres |
| **B. Servicios separados** | Plataformas administradas (PaaS) | Una base PostgreSQL 16, un servicio Python para la API y un hosting estático para la interfaz |

## Opción A · Docker Compose

### 1. Preparar la configuración

```bash
cp infra/.env.example infra/.env
```

Edite `infra/.env` y complete los tres valores obligatorios con secretos **propios y únicos**:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"   # ejecútelo una vez por cada valor
```

| Variable | Obligatoria | Descripción |
|---|---|---|
| `POSTGRES_PASSWORD` | Sí | Contraseña de PostgreSQL. Solo letras, números, `-` y `_` (se incrusta en la URL de conexión) |
| `SECRET_KEY` | Sí | Firma de los tokens de sesión (mínimo 32 caracteres) |
| `SETUP_TOKEN` | Sí | Token para crear la primera empresa (mínimo 16 caracteres) |
| `PUBLIC_URL` | Recomendada | Dirección pública del sistema (p. ej. `https://inventarios.miempresa.example`), usada para CORS |
| `WEB_PORT` | No | Puerto de la interfaz (por defecto 8080) |
| `APP_TIMEZONE` | No | Zona horaria de la empresa (por defecto `America/Bogota`) |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM` | Para recuperar contraseñas | Cuenta de correo saliente. Con Gmail use una «contraseña de aplicación» |

`infra/.env` **no se sube a Git** (ya está en `.gitignore`).

### 2. Levantar los servicios

```bash
docker compose -f infra/docker-compose.yml --env-file infra/.env up -d --build
docker compose -f infra/docker-compose.yml --env-file infra/.env ps       # todos deben quedar «healthy»
```

El orden de arranque es automático: PostgreSQL → API (aplica las migraciones y arranca solo si salen bien) →
interfaz. La interfaz queda en `http://localhost:8080` (o el `WEB_PORT` elegido).

### 3. Crear la primera empresa

Abra la interfaz: como no hay empresa, lo lleva a **Configuración inicial**. Escriba el `SETUP_TOKEN`, los datos de
la empresa y los del administrador. Desde ese momento la pantalla deja de funcionar.

Alternativa por terminal:

```bash
docker compose -f infra/docker-compose.yml --env-file infra/.env exec backend \
  python -m app.cli inicializar --empresa "Mi Empresa" --admin-nombre "Nombre Apellido" --admin-correo admin@empresa.example
```

### 4. (Opcional) Datos de demostración

Solo en una base **vacía**, para conocer el sistema:

```bash
docker compose -f infra/docker-compose.yml --env-file infra/.env --profile demo run --rm demo
```

Muestra una sola vez las credenciales generadas. **No use datos de demostración en una instalación real.**

### 5. HTTPS

El sistema no termina TLS. Publique el puerto de la interfaz detrás de un proxy inverso con certificado (Caddy,
Traefik, nginx con Let's Encrypt, o el balanceador de su proveedor). Ejemplo mínimo con Caddy:

```
inventarios.miempresa.example {
    reverse_proxy 127.0.0.1:8080
}
```

Con HTTPS en su lugar, agregue `Strict-Transport-Security` en ese proxy y fije `PUBLIC_URL` con `https://`.

> **Proxy delante del nginx incluido.** El nginx de la interfaz toma como IP del cliente la del equipo que se le
> conecta. Si hay otro proxy delante (Caddy en el servidor, un balanceador), esa IP será la del proxy y el límite de
> intentos por IP trataría a todos los usuarios como uno solo. Para evitarlo, agregue al bloque `server` de
> `frontend/nginx.conf` (ajuste el rango al de su proxy; **esta configuración no se probó**):
>
> ```nginx
> set_real_ip_from 172.16.0.0/12;   # red de Docker o dirección de su proxy
> real_ip_header X-Forwarded-For;
> real_ip_recursive on;
> ```
>
> Solo declare como confiables las direcciones de proxies que usted controla.

### 6. Comprobaciones

| Qué | Cómo |
|---|---|
| API viva | `curl http://localhost:8080/api/health` → `{"status":"ok"}` |
| Base de datos | `curl http://localhost:8080/api/health/ready` → `{"status":"ok","database":"ok"}` |
| Interfaz | `curl -I http://localhost:8080/` → `200` con `Content-Security-Policy` |
| Registros | `docker compose … logs -f backend` |

## Opción B · Servicios separados

1. **Base de datos:** PostgreSQL 16. Con proveedores administrados (por ejemplo Neon) use la cadena de conexión con
   el controlador asíncrono: `postgresql+asyncpg://USUARIO:CLAVE@HOST/BASE`. Para servidores remotos el SSL se
   exige automáticamente (`DATABASE_SSL=auto`). Con *poolers* de conexión de transacción puede necesitar ajustar
   `DB_POOL_SIZE`.
2. **API:** construya `backend/Dockerfile` o instale `requirements.txt` en Python 3.13 y ejecute

   ```bash
   alembic upgrade head
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

   con las variables de `backend/.env.example` (en producción: `ENVIRONMENT=production`, `SECRET_KEY`,
   `SETUP_TOKEN`, `DATABASE_URL`, `FRONTEND_URL`).
3. **Interfaz:** `cd frontend && npm ci && npm run build` y sirva `frontend/dist` como sitio estático. Debe
   reenviar `/api` a la API en el mismo dominio (como hace `frontend/nginx.conf`) o, si va en otro dominio,
   compilar con `VITE_API_URL` y agregar ese origen a `CORS_ORIGINS` en la API. Cualquier ruta que no sea un
   archivo debe devolver `index.html`.
4. Activar `TRUST_PROXY_HEADERS=true` **solo** si hay un proxy de confianza que reescribe `X-Forwarded-For`.

## Lista de comprobación de producción

- [ ] `ENVIRONMENT=production` (el nombre del entorno en el contenedor ya lo fija).
- [ ] `SECRET_KEY`, `SETUP_TOKEN` y contraseña de base de datos **nuevos**, generados aleatoriamente, no reutilizados de
      ningún otro entorno ni compartidos por chat o correo.
- [ ] HTTPS activo y `PUBLIC_URL` con `https://`.
- [ ] El puerto de PostgreSQL **no** es accesible desde Internet (Compose lo publica solo en `127.0.0.1`).
- [ ] SMTP configurado y probado con una recuperación de contraseña real.
- [ ] Primer administrador creado; luego rote o elimine `SETUP_TOKEN` si no piensa usarlo de nuevo.
- [ ] Respaldos automáticos programados y **una restauración probada** en otro entorno.
- [ ] Zona horaria (`APP_TIMEZONE`) correcta para la empresa.
- [ ] Usuarios con el rol de menor privilegio necesario; ningún usuario de demostración.
- [ ] Sin datos de demostración cargados.
- [ ] Monitoreo de `/api/health/ready` desde un servicio externo.

## Respaldos y restauración (RNF-009)

**Respaldar** (volcado comprimido de PostgreSQL, con permisos restringidos):

```bash
./infra/scripts/respaldar.sh [carpeta]             # Linux / macOS / Git Bash
.\infra\scripts\respaldar.ps1 [-Destino carpeta]   # Windows PowerShell
```

**Restaurar** (reemplaza todos los datos actuales; pide escribir `RESTAURAR` para continuar):

```bash
./infra/scripts/restaurar.sh ruta/al/respaldo.dump
.\infra\scripts\restaurar.ps1 ruta\al\respaldo.dump
```

Recomendaciones:

- Programe el respaldo (cron en Linux, Programador de tareas en Windows) al menos una vez al día y **copie el
  archivo fuera del servidor**: contiene todos los datos de la empresa y debe tratarse como información sensible.
- Pruebe la restauración en un entorno aparte antes de necesitarla.
- Con una base administrada (Neon u otra), use además sus propias copias y recuperación a un punto en el tiempo.
- Los volcados y restauraciones se probaron contra una instancia local de PostgreSQL; los scripts que los envuelven con
  Docker Compose no se ejecutaron (ver arriba).

## Actualizar a una versión nueva

1. Haga un respaldo.
2. Obtenga el código nuevo y reconstruya: `docker compose … up -d --build`.
3. Al arrancar, la API aplica las migraciones pendientes; si una falla, el contenedor termina con error y **no** sirve
   tráfico (revise `docker compose … logs backend`; los datos siguen intactos, porque cada migración es transaccional
   en PostgreSQL).
4. Compruebe `/api/health/ready` y revise [`CHANGELOG.md`](../CHANGELOG.md) por cambios que requieran acciones.

Con varias réplicas de la API, ejecute las migraciones como un trabajo aparte y arranque las réplicas con
`RUN_MIGRATIONS=false`.

## Migrar desde la versión anterior del proyecto

La migración `0003_inventia` convierte una base de la versión anterior conservando sus datos (ver
[MODELO_DATOS.md](MODELO_DATOS.md#migraciones) y la decisión [D-06](DECISIONES.md#d-06)). **Haga un respaldo antes**, ejecute
`alembic upgrade head` y revise después, en **Usuarios**, los roles asignados y las sedes de los usuarios que
quedaron inhabilitados por no tener sede.

Si prefiere empezar de cero en lugar de migrar, cree una base nueva y vacía.

## Predicción programada

La predicción se puede generar desde la interfaz o programarla para fuera del horario de operación:

```bash
docker compose -f infra/docker-compose.yml --env-file infra/.env exec -T backend python -m app.cli predecir
# o sin Docker:  cd backend && python -m app.cli predecir [--empresa-id N] [--horizonte 14]
```

Ejemplo (cron, todos los días a las 2:00 a. m.):

```
0 2 * * * cd /ruta/inventia && docker compose -f infra/docker-compose.yml --env-file infra/.env exec -T backend python -m app.cli predecir
```

El comando genera la predicción (y con ella las alertas de riesgo de desabastecimiento). Las **recomendaciones** se
generan después desde la pantalla *Recomendaciones*, para que una persona las revise.

## Dimensionamiento orientativo

Estas cifras son una orientación, **no resultados de pruebas de carga**.

| Escala | Recursos sugeridos |
|---|---|
| Hasta ~5 sedes, ~5 000 productos, ~20 usuarios | 2 vCPU, 2 GB de RAM |
| Predicción de más de ~10 000 series (sede × producto) | Más CPU y programar la predicción fuera del horario de operación |

Sin ninguna medición de carga con cientos de usuarios simultáneos, no se garantiza el rendimiento a esa escala.

## Primera prueba del despliegue

Antes de usar el sistema con datos reales, en un entorno de prueba:

1. `docker compose … up -d --build` termina sin errores y `ps` muestra los tres servicios en estado saludable.
2. Crear la empresa desde **Configuración inicial** con el token.
3. Iniciar sesión, crear una sede, un producto, registrar una entrada y una venta.
4. Cargar la demostración (`--profile demo`) en una base aparte y generar una predicción.
5. Solicitar una recuperación de contraseña y comprobar que llega el correo.
6. Hacer un respaldo, borrar los datos y restaurarlos.
7. Reiniciar los contenedores y comprobar que los datos siguen allí.

Si algo de esta lista falla, es información valiosa: corrija y anótelo en el `CHANGELOG`.
