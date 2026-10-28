# Guía de la estructura del backend

Para quien conoce la organización de un proyecto Spring. El backend de Inventia está hecho con FastAPI y SQLAlchemy, pero
las carpetas se llaman igual que en Spring: `controller`, `dto`, `service`, `model`, `security`, `exception`,
`specification` y `mapper`. Esta guía dice qué hay en cada una, cómo viaja una petición y dónde agregar cada cosa.

## 1. Equivalencias con Spring

| En Spring | En Inventia (`backend/app/`) | Qué contiene | Ejemplo |
|---|---|---|---|
| `controller` (`@RestController`) | `controller/` | Una clase por módulo con las rutas HTTP. Valida la entrada, exige el permiso y llama a un servicio. No tiene reglas de negocio. | `ventas_controller.py` |
| `dto` (objetos de entrada y salida) | `dto/` | Esquemas pydantic: lo que recibe y lo que devuelve cada ruta. De ellos sale el contrato OpenAPI y los tipos del frontend. | `ventas_dto.py` (`VentaCrear`, `VentaDetalle`) |
| `service` (`@Service`) | `service/` | Reglas de negocio y transacciones. Cada operación hace `commit` una sola vez al final. | `ventas_service.py` |
| `model` / `entity` (`@Entity`) | `model/` | Las 37 tablas como clases SQLAlchemy. | `operaciones.py` (`Venta`, `Traslado`) |
| `repository` (`JpaRepository`) | *(dentro de `service/`)* | No hay carpeta aparte: cada servicio ejecuta sus consultas con la sesión de SQLAlchemy (`select(...)`). Ver [D-39](DECISIONES.md#d-39). | `ventas_service.listar_ventas` |
| `specification` (`Specification<T>`) | `specification/` | Arma la lista de condiciones SQL de un listado según los filtros recibidos (sede, estado, fechas…). | `ventas_spec.py` (`condiciones_ventas`) |
| `mapper` (MapStruct) | `mapper/` | Convierte una entidad en su DTO de salida cuando no hace falta consultar nada más. | `usuario_mapper.py` (`a_usuario_salida`) |
| `security` (`SecurityConfig`, filtros) | `security/` | JWT y Argon2, los 61 permisos, el `Contexto` de la petición (usuario, empresa, sedes) y la dependencia `requiere("permiso")`. | `dependencias.py`, `permisos.py` |
| `exception` (`@ControllerAdvice`) | `exception/` | `excepciones.py`: las excepciones de negocio. `manejadores.py`: las convierte en la respuesta JSON uniforme. | `ReglaNegocio`, `Conflicto` |
| `config` (`application.yml`, `@Configuration`) | `config/` | Variables de entorno, conexión a la base de datos y registro de eventos. | `settings.py` |
| `util` | `util/` | Utilidades pequeñas: fechas y zona horaria, niveles de stock, SQL. | `tiempo.py` |
| *(no existe en Spring)* | `ml/` | Cálculo de predicción puro, sin base de datos: modelos, evaluación y pipeline. | `pipeline.py` |

Otros archivos del backend:

| Ruta | Para qué sirve |
|---|---|
| `main.py` | Crea la aplicación, registra los controladores, los manejadores de excepciones y el middleware |
| `cli.py` | Comandos de terminal: inicializar, predecir, cargar datos de demostración, sincronizar permisos |
| `demo.py`, `demo_sig.py` | Datos de demostración (se generan usando los mismos servicios que usa la API) |
| `../alembic/` | Migraciones de la base de datos |
| `../tests/` | Pruebas automáticas (214) |
| `../scripts/` | Scripts de apoyo (por ejemplo, exportar el contrato OpenAPI) |

## 2. Recorrido de una petición: `GET /api/ventas?estado=registrada`

1. **`main.py`** recibe la petición y la entrega al controlador que tiene registrada la ruta `/api/ventas`.
2. **`controller/ventas_controller.py`** (`listar`): FastAPI valida los parámetros de la URL (`estado`, `desde`, `hasta`…). La
   dependencia `requiere("ventas.ver")` (de `security/dependencias.py`) lee el token JWT, carga al usuario y arma el `Contexto`;
   si el usuario no tiene el permiso, responde 403 aquí mismo.
3. **`service/ventas_service.py`** (`listar_ventas`): pide a la especificación las condiciones del listado.
4. **`specification/ventas_spec.py`** (`condiciones_ventas`): devuelve la lista de condiciones. La primera es siempre
   `Venta.empresa_id == ctx.empresa_id` y las sedes se limitan a las que el usuario puede ver. El cliente nunca decide la empresa.
5. De vuelta en el servicio, se ejecutan las consultas contra las entidades de **`model/operaciones.py`** (`Venta`, `VentaItem`)
   y se arman los resúmenes.
6. El resultado se devuelve como **`dto/ventas_dto.py`** (`VentaResumen`) dentro de `Pagina[...]` y FastAPI lo convierte en JSON.
7. Si algo falla con una regla de negocio, el servicio lanza una excepción de **`exception/excepciones.py`** y
   **`exception/manejadores.py`** la convierte en `{"detail": "...", "codigo": "..."}` con el estado HTTP que corresponde.

Una operación que modifica datos (por ejemplo `POST /api/ventas`) hace lo mismo con una diferencia: el servicio abre la
transacción, descuenta las existencias, registra la auditoría y hace un único `commit`; si cualquier línea falla, no queda nada a medias.

## 3. Dónde agregar algo nuevo

Para un módulo nuevo llamado `garantias`, en este orden:

1. **`model/garantias.py`**: la entidad. Luego se genera la migración (`python -m alembic revision --autogenerate`) y se
   importa el módulo en `model/__init__.py`.
2. **`dto/garantias_dto.py`**: los esquemas de entrada y de salida.
3. **`specification/garantias_spec.py`**: solo si el listado tiene filtros dinámicos.
4. **`mapper/garantias_mapper.py`**: solo si la conversión entidad → DTO se repite y no consulta la base.
5. **`service/garantias_service.py`**: la lógica. Recibe `(db, ctx, ...)`, filtra por `ctx.empresa_id`, registra auditoría y hace
   un solo `commit`.
6. **`controller/garantias_controller.py`**: las rutas; cada una con `requiere("permiso")`. Se registra en la lista `ROUTERS` de `main.py`.
7. **`security/permisos.py`**: los permisos nuevos (y a qué roles de fábrica se asignan).
8. **`tests/test_garantias.py`**, y `npm run tipos` (en `frontend/`) para regenerar los tipos del frontend.

## 4. Diferencias con Spring que conviene tener presentes

- **No hay inyección de dependencias por constructor.** FastAPI inyecta lo que necesita cada ruta con `Depends(...)`: la sesión
  de base de datos (`get_db`) y el `Contexto` (`requiere`). Los servicios son módulos con funciones, no clases.
- **No hay `@Transactional`.** La transacción es la sesión de SQLAlchemy y cada servicio hace `commit` al final de la operación.
- **No hay `repository`.** SQLAlchemy ya cumple ese papel; las consultas viven en el servicio que las usa (ver [D-39](DECISIONES.md#d-39)).
- **Todo es asíncrono** (`async def` / `await`), igual que en una pila reactiva.
- **El `Contexto` reemplaza al usuario autenticado de `SecurityContextHolder`:** además del usuario trae la empresa, los permisos
  y las sedes autorizadas, y cada servicio lo recibe como parámetro.

## 5. Frontend y el resto del repositorio

| Carpeta | Contenido |
|---|---|
| `backend/` | API (esta guía) |
| `frontend/` | Aplicación React + TypeScript; los tipos de la API se generan desde el contrato OpenAPI |
| `ml/` | Scripts para estudiar y repetir la evaluación de los modelos de predicción (el código que usa la API está en `backend/app/ml/`) |
| `infra/` | Docker, nginx, pruebas de carga y de seguridad |
| `docs/` | Documentación (arquitectura, decisiones, seguridad, API, trazabilidad…) |
| `datos_pruebas/` | Evidencias de las pruebas citadas en la memoria del proyecto |
