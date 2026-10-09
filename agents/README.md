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

## Recomendaciones para quien integre un asistente

- Trate la salida de predicciones como lo que es: **estimaciones con margen de error**. Cada fila trae su nivel de
  confianza y sus advertencias; un buen asistente debe mencionarlas.
- Las recomendaciones están **pendientes**: el asistente puede resumirlas, pero no debe presentarlas como decisiones
  tomadas.
- No guarde la llave en el código ni en un repositorio; use variables de entorno o un gestor de secretos.
- Pida al administrador la llave con los alcances y la sede mínimos que necesite (mínimo privilegio).
