# Pruebas en el navegador

Tres guiones de [Playwright](https://playwright.dev/python/) que controlan Chromium como lo haría una persona. Verifican lo que las pruebas de la API
no pueden: que la interfaz muestre el resultado, que las pantallas no se desborden en un teléfono y que no haya errores en la consola.

| Archivo | Para qué sirve |
|---|---|
| `recorrido.py` | Abre las 21 pantallas con un rol y un ancho de ventana (1440, 1280, 390 o 320 px); informa errores de consola, excepciones, respuestas HTTP con error y desbordamiento horizontal; guarda una captura por pantalla |
| `flujos.py` | Nueve flujos completos como administrador: venta y anulación, traslado (solicitar, aprobar, confirmar), usuario nuevo, validación de formulario, rol nuevo con permisos, llave de agente, rechazo de una recomendación, descarga de reportes y cierre de sesión |
| `desborde.py` | Lista los elementos que se salen del ancho de la ventana en las pantallas indicadas |

```bash
pip install playwright && playwright install chromium

# 1) Levante la API y el frontend (npm run dev) con una base de PRUEBAS y los datos de demostración (npm run demo).
# 2) Cree credenciales.json con los usuarios de esa base: {"admin": ["correo", "contraseña"], "gerente": ["…", "…"]}
export INVENTIA_URL=http://127.0.0.1:5173            # opcional
export INVENTIA_CREDENCIALES=credenciales.json
python recorrido.py gerente 390
python flujos.py
python desborde.py /inventario,/ventas 390
```

`flujos.py` **crea registros** (una venta, un traslado, un usuario, un rol y una llave): úselo solo contra una base de pruebas. Los tres terminan con código
de salida distinto de cero si encuentran un problema. No sustituyen una prueba de usabilidad con personas ni una prueba en otros navegadores (solo se probó Chromium).
