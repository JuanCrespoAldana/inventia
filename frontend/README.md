# Inventia: interfaz web

Aplicación de una sola página (SPA) en React que consume la API de Inventia. Todo el texto visible está en español.
La visión general del proyecto está en el [README principal](../README.md).

## Tecnología

| Pieza | Uso |
|---|---|
| React 19 + TypeScript (modo estricto) | Interfaz |
| Vite | Servidor de desarrollo y compilación |
| Tailwind CSS v4 | Estilos (tokens de diseño en `src/index.css`) |
| react-router-dom | Rutas y rutas protegidas por permiso |
| TanStack Query | Datos del servidor, caché e invalidación |
| axios | Cliente HTTP (`src/lib/http.ts`) |
| React Hook Form + zod | Formularios y validación |
| framer-motion | Transiciones sobrias |
| lucide-react | Íconos |
| vitest + Testing Library | Pruebas |
| oxlint | Lint (`--deny-warnings`) |

## Comandos

Desde esta carpeta (o con `npm run … ` equivalente desde la raíz del repositorio):

| Comando | Qué hace |
|---|---|
| `npm install` | Instala dependencias |
| `npm run dev` | Servidor de desarrollo en <http://localhost:5173>; redirige `/api` al backend |
| `npm run lint` | oxlint; cualquier advertencia es un error |
| `npm run typecheck` | `tsc -b` |
| `npm test` | Pruebas (vitest) |
| `npm run build` | Tipos + compilación de producción en `dist/` |
| `npm run preview` | Sirve `dist/` localmente |
| `npm run tipos` | Regenera `src/types/api.gen.ts` a partir del OpenAPI del backend |

El backend debe estar en <http://localhost:8000>; para otra dirección defina `VITE_PROXY_API`.

## Variables de entorno

Vite las incrusta al compilar, así que **no pueden contener secretos**. En desarrollo no hace falta definir ninguna.
Están documentadas en [`.env.example`](.env.example):

| Variable | Por defecto | Para qué |
|---|---|---|
| `VITE_PROXY_API` | `http://localhost:8000` | Destino del proxy de desarrollo |
| `VITE_API_URL` | vacío (mismo origen) | URL base de la API si se sirve desde otro dominio |
| `VITE_LOCALE` | `es-CO` | Formato de números y fechas |
| `VITE_MONEDA` | `COP` | Moneda de los valores |

## Estructura de `src/`

```
src/
├── api/            Funciones que llaman a la API, agrupadas por módulo
├── auth/           Sesión, rutas protegidas por permiso
├── components/
│   ├── ui/         Botones, campos, tablas, modales, avisos, esqueletos…
│   ├── layout/     Estructura general, menú lateral, selector de sede
│   └── charts/     Gráficos propios (sin librería externa)
├── features/       Una carpeta por módulo (acceso, panel, catálogo, inventario,
│                   ventas, traslados, alertas, predicción, recomendaciones,
│                   reportes, auditoría, administración)
├── hooks/          useFiltros, useMutacion, useSedeActiva, useCatalogos
├── lib/            Formato es-CO, errores, permisos, etiquetas, formularios
├── types/          api.gen.ts (generado; no se edita a mano)
└── test/           Preparación de pruebas y utilidades
```

## Convenciones

- **Los tipos de la API se generan.** No se escriben a mano: tras cambiar un esquema del backend, ejecute `npm run tipos`
  y luego `npm run typecheck`. La integración continua falla si `api.gen.ts` quedó desactualizado.
- **Cada pantalla resuelve cuatro estados:** cargando (esqueletos con la forma del contenido), vacío (con la acción para
  poblarlo), error (con opción de reintentar) y contenido.
- **Los filtros viven en la URL** (`useFiltros`), de modo que un enlace conserva la vista y el botón «atrás» funciona.
- **Las mutaciones usan `useMutacion`:** muestran el aviso de éxito o error y refrescan la caché afectada.
- **Los errores del servidor** (`{detail, codigo, errores[]}`) se traducen a mensajes por campo con `lib/errors.ts`.
- **Permisos:** la interfaz oculta lo que la persona no puede usar (`lib/permisos.ts`), pero la autoridad es siempre el
  backend; ocultar un botón no es una medida de seguridad.
- **Formato:** números, fechas y moneda pasan siempre por `lib/format.ts`; no use `toLocaleString` suelto.
- **Texto:** español correcto (tildes, «ñ», signos de apertura ¿ ¡). Sin nombres personales en textos de ejemplo.
- **Accesibilidad:** etiquetas asociadas a cada campo, foco visible, diálogos con foco atrapado y cierre con Escape,
  y el estado nunca se comunica solo con color. No se realizó una auditoría WCAG formal (ver
  [`docs/LIMITACIONES.md`](../docs/LIMITACIONES.md)).

## Sesión y seguridad en el navegador

- El token de acceso se guarda en `sessionStorage` (se pierde al cerrar la pestaña) y se envía en
  `Authorization: Bearer`. Solo si la persona marca «Mantener la sesión iniciada en este equipo» se guarda en `localStorage`. Se descarta
  cuando la API responde `401` (sesión vencida o contraseña cambiada). Los accesos al almacenamiento están protegidos con
  `try/catch`: en modo privado la aplicación sigue funcionando.
- Un token en el almacenamiento del navegador es legible por cualquier script de la misma página; por eso la CSP del
  nginx solo permite scripts propios y no se usa `dangerouslySetInnerHTML`.
- No se usa `dangerouslySetInnerHTML`; React escapa todo lo que se muestra.
- nginx (`nginx.conf`) sirve los archivos estáticos con cabeceras de seguridad y reenvía `/api` al backend.

## Pruebas

Las pruebas del frontend cubren las piezas con lógica propia: rutas y permisos, navegación por rol, formularios y
validación, traducción de errores, formato, filtros en la URL, editor de líneas de venta/traslado, gráfico, y las
pantallas de ingreso, usuarios y roles. Las pruebas de extremo a extremo del flujo completo se hicieron contra la API
real (ver [`docs/LIMITACIONES.md`](../docs/LIMITACIONES.md)).
