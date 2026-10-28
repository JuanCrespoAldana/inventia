"""Toma las capturas de pantalla de la documentación contra una instancia en ejecución (demostración).

Uso:  INVENTIA_URL=http://127.0.0.1:5173 INVENTIA_EMAIL=... INVENTIA_PASSWORD=... python3 tomar_capturas.py [escritorio|movil]
Las credenciales llegan por variables de entorno; el script no guarda contraseñas."""
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("INVENTIA_URL", "http://127.0.0.1:5173")
EMAIL, PASSWORD = os.environ["INVENTIA_EMAIL"], os.environ["INVENTIA_PASSWORD"]
MODO = sys.argv[1] if len(sys.argv) > 1 else "escritorio"
VISTA = {"escritorio": {"width": 1440, "height": 900}, "movil": {"width": 390, "height": 844}}[MODO]
SALIDA = Path(__file__).parent

PANTALLAS = [
    ("panel", "/"), ("existencias", "/inventario"), ("consolidado", "/inventario/consolidado"), ("movimientos", "/movimientos"),
    ("productos", "/productos"), ("categorias", "/categorias"), ("ventas", "/ventas"), ("nueva_venta", "/ventas/nueva"),
    ("traslados", "/traslados"), ("nuevo_traslado", "/traslados/nuevo"), ("alertas", "/alertas"), ("predicciones", "/predicciones"),
    ("recomendaciones", "/recomendaciones"), ("reportes", "/reportes"), ("auditoria", "/auditoria"), ("roles", "/roles"),
    ("usuarios", "/usuarios"), ("sedes", "/sedes"), ("empresa", "/empresa"), ("integraciones", "/integraciones"),
    ("sig_pqrs", "/sig/pqrs"), ("sig_sst", "/sig/sst"), ("sig_calidad", "/sig/calidad"), ("sig_ambiental", "/sig/ambiental"),
]

with sync_playwright() as p:
    nav = p.chromium.launch()
    ctx = nav.new_context(viewport=VISTA, locale="es-CO", timezone_id="America/Bogota", device_scale_factor=2 if MODO == "movil" else 1)
    pag = ctx.new_page()
    pag.goto(f"{BASE}/login")
    pag.wait_for_load_state("networkidle")
    pag.screenshot(path=str(SALIDA / f"login_{MODO}.png"))
    pag.get_by_label("Correo electrónico").fill(EMAIL)
    pag.get_by_label("Contraseña", exact=False).first.fill(PASSWORD)
    pag.get_by_role("button", name="Ingresar").click()
    pag.wait_for_url(f"{BASE}/", timeout=15000)
    for nombre, ruta in PANTALLAS:
        pag.goto(f"{BASE}{ruta}")
        pag.wait_for_load_state("networkidle")
        pag.wait_for_timeout(600)
        pag.screenshot(path=str(SALIDA / f"{nombre}_{MODO}.png"))
        print(nombre)
    nav.close()
