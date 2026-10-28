"""Recorre las 21 pantallas como un rol dado, registra errores de consola, excepciones y respuestas HTTP con error, y detecta desbordamiento horizontal.

Uso: python recorrido.py ROL [ANCHO] [RUTAS_SEPARADAS_POR_COMAS]   (ROL es una clave del archivo de credenciales; ANCHO por defecto 1440)
Ejemplo: INVENTIA_CREDENCIALES=credenciales.json python recorrido.py gerente 390
"""
import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("INVENTIA_URL", "http://127.0.0.1:5173")
CREDENCIALES = Path(os.environ.get("INVENTIA_CREDENCIALES", "credenciales.json"))
SALIDA = Path(os.environ.get("INVENTIA_CAPTURAS", "capturas"))
SALIDA.mkdir(parents=True, exist_ok=True)
creds = json.loads(CREDENCIALES.read_text())
rol = sys.argv[1] if len(sys.argv) > 1 else "admin"
ancho = int(sys.argv[2]) if len(sys.argv) > 2 else 1440
alto = 900 if ancho > 700 else 844
rutas = sys.argv[3].split(",") if len(sys.argv) > 3 else [
    "/", "/inventario", "/inventario/consolidado", "/movimientos", "/productos", "/categorias", "/ventas",
    "/ventas/nueva", "/traslados", "/traslados/nuevo", "/alertas", "/predicciones", "/recomendaciones",
    "/reportes", "/empresa", "/sedes", "/usuarios", "/roles", "/auditoria", "/integraciones", "/perfil",
]

problemas = []
with sync_playwright() as p:
    nav = p.chromium.launch()
    ctx = nav.new_context(viewport={"width": ancho, "height": alto}, locale="es-CO")
    pag = ctx.new_page()
    pag.on("console", lambda m: problemas.append(("consola", pag.url, m.text)) if m.type in ("error", "warning") else None)
    pag.on("pageerror", lambda e: problemas.append(("excepcion", pag.url, str(e))))
    pag.on("response", lambda r: problemas.append(("http", pag.url, f"{r.status} {r.request.method} {r.url}")) if r.status >= 400 and "/api/" in r.url else None)

    pag.goto(f"{BASE}/login")
    pag.get_by_label("Correo electrónico").fill(creds[rol][0])
    pag.get_by_label("Contraseña", exact=False).first.fill(creds[rol][1])
    pag.get_by_role("button", name="Ingresar").click()
    pag.wait_for_url(f"{BASE}/", timeout=15000)

    for ruta in rutas:
        pag.goto(f"{BASE}{ruta}")
        pag.wait_for_load_state("networkidle")
        pag.wait_for_timeout(400)
        nombre = (ruta.strip("/").replace("/", "_") or "panel")
        pag.screenshot(path=str(SALIDA / f"{rol}_{ancho}_{nombre}.png"), full_page=False)
        desborde = pag.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
        titulo = pag.locator("h1").first.inner_text() if pag.locator("h1").count() else "(sin h1)"
        print(f"{ruta:28} h1={titulo!r:40} desborde_horizontal={desborde}")
    nav.close()

print("\n== PROBLEMAS ==")
for t in problemas:
    print(t)
print(f"total={len(problemas)}")
sys.exit(1 if problemas else 0)
