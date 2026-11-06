# Agentes de IA

Inventia permite que un asistente o agente externo **consulte** información autorizada del inventario (RNF-049).
Los agentes **solo leen**: no pueden registrar movimientos, aprobar recomendaciones ni cambiar nada. Las decisiones
las toma una persona en la aplicación (RNF-034).

## Cómo obtener una llave

1. Ingrese como administrador y abra **Administración → Agentes de IA**.
2. Pulse **Nueva llave** y elija: nombre, qué puede consultar (alcances), una sede (opcional) y la vigencia.
3. Copie la llave cuando se muestre: **aparece una sola vez**. En el sistema solo queda su huella.
4. Si se pierde o se filtra, **revóquela** en la misma pantalla y cree otra.

Cada llave:

- pertenece a una sola empresa;
- puede limitarse a **una sede**;
- tiene **alcances** explícitos: `inventario:leer`, `alertas:leer`, `predicciones:leer`, `recomendaciones:leer`;
- vence (90 días por defecto);
- no sirve en la API normal, y los tokens de usuario no sirven en `/api/agentes`.

## Rutas

Todas son `GET` y requieren la cabecera `X-API-Key: inv_...`. Límite: 60 solicitudes por minuto por IP.

| Ruta | Alcance | Devuelve |
|---|---|---|
| `/api/agentes/yo` | (cualquiera) | Qué puede consultar esta llave |
| `/api/agentes/inventario` | `inventario:leer` | Existencias por sede y producto (`sede_id`, `q`) |
| `/api/agentes/alertas` | `alertas:leer` | Alertas de inventario activas (`sede_id`, `tipo`) |
| `/api/agentes/predicciones` | `predicciones:leer` | Última predicción de demanda, marcada como **estimación** (`sede_id`, `q`) |
| `/api/agentes/recomendaciones` | `recomendaciones:leer` | Recomendaciones **pendientes de aprobación humana** (`sede_id`) |

Los listados están paginados (`pagina`, `tamano` hasta 100). Intentos con una llave inválida, vencida, sin alcance o
fuera de su sede reciben `401` o `403` y quedan en la auditoría.

## Ejemplo

`consultar_inventia.py` consulta las cuatro rutas y arma un resumen. Usa solo la biblioteca estándar de Python.

```bash
# bash
export INVENTIA_URL=http://localhost:8000
export INVENTIA_API_KEY=<la llave que copió>
python agents/consultar_inventia.py
```

```powershell
# PowerShell
$env:INVENTIA_URL = "http://localhost:8000"
$env:INVENTIA_API_KEY = "<la llave que copió>"
python agents\consultar_inventia.py
```

Con `curl`:

```bash
curl -s http://localhost:8000/api/agentes/alertas -H "X-API-Key: $INVENTIA_API_KEY"
```

## Conectar con Claude Desktop (servidor MCP)

`servidor_mcp.py` es un conector [MCP](https://modelcontextprotocol.io) que le da a Claude cinco herramientas **de solo lectura**:
`quien_soy`, `consultar_inventario`, `consultar_alertas`, `consultar_predicciones` y `consultar_recomendaciones`. Claude decide
cuál usar según la pregunta ("¿qué está agotado?", "¿qué debo reponer esta semana?") y responde con los datos que devuelve
Inventia. Solo usa la biblioteca estándar de Python y no instala nada.

1. Con el programa corriendo (`npm run dev`), cree una llave en **Administración → Agentes de IA** con los cuatro alcances y copie
   la llave (empieza con `inv_`).
2. En Claude Desktop abra **Configuración → Desarrollador → Editar configuración**. Se abre `claude_desktop_config.json`; agregue
   el bloque `inventia` (ajuste las rutas a donde tiene el proyecto y pegue la llave):

```json
{
  "mcpServers": {
    "inventia": {
      "command": "D:\\Juan\\Desktop\\inventario-ia-pymes\\backend\\.venv\\Scripts\\python.exe",
      "args": ["D:\\Juan\\Desktop\\inventario-ia-pymes\\agents\\servidor_mcp.py"],
      "env": {
        "INVENTIA_URL": "http://localhost:8000",
        "INVENTIA_API_KEY": "inv_PEGUE_AQUI_LA_LLAVE"
      }
    }
  }
}
```

   En macOS o Linux, `command` es `backend/.venv/bin/python` (o simplemente `python3`) y las rutas usan `/`.
3. Cierre Claude Desktop **por completo** (en Windows, también desde la bandeja del sistema) y ábralo de nuevo. En el cuadro de
   mensaje debe aparecer el conector **inventia** con sus herramientas; la primera vez Claude pide permiso para usarlas.
4. Pregunte, por ejemplo: «¿Qué productos están agotados y en qué sede?», «¿Qué alertas críticas hay?», «¿Qué recomendaciones
   están pendientes?», «¿Cuánto se estima que se venderá del acelerador de puño en las próximas dos semanas?».

Notas:

- El programa (backend) debe estar encendido; si no, la herramienta responde que no pudo conectar.
- La llave queda guardada en `claude_desktop_config.json`, que es un archivo de su computador: no lo suba a un repositorio ni
  lo muestre en pantalla. Para una demostración, revóquela al terminar.
- Lo que Claude consulta pasa por la conversación: use datos de demostración o datos que pueda compartir.
- Si el conector no aparece, abra el registro de Claude Desktop (**Configuración → Desarrollador**, botón del servidor `inventia`) y
  revise el mensaje; los errores más comunes son una ruta mal escrita o las barras `\\` sin duplicar en el JSON.

## Recomendaciones para quien integre un asistente

- Trate la salida de predicciones como lo que es: **estimaciones con margen de error**. Cada fila trae su nivel de
  confianza y sus advertencias; un buen asistente debe mencionarlas.
- Las recomendaciones están **pendientes**: el asistente puede resumirlas, pero no debe presentarlas como decisiones
  tomadas.
- No guarde la llave en el código ni en un repositorio; use variables de entorno o un gestor de secretos.
- Pida al administrador la llave con los alcances y la sede mínimos que necesite (mínimo privilegio).
