"""Lista, por pantalla, los elementos que se salen del ancho de la ventana sin estar dentro de un contenedor con desplazamiento propio.

Uso: python desborde.py RUTAS_SEPARADAS_POR_COMAS [ANCHO]   (ANCHO por defecto 390). Entra como «admin».
"""
import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("INVENTIA_URL", "http://127.0.0.1:5173")
creds = json.loads(Path(os.environ.get("INVENTIA_CREDENCIALES", "credenciales.json")).read_text())
rutas = sys.argv[1].split(",")
ancho = int(sys.argv[2]) if len(sys.argv) > 2 else 390
JS = """() => { const vw = document.documentElement.clientWidth; const out = [];
for (const el of document.querySelectorAll('body *')) { const r = el.getBoundingClientRect();
 if (r.width > 0 && r.right > vw + 1) { let p = el.parentElement, oculto = false;
   while (p && p !== document.body) { const o = getComputedStyle(p).overflowX; if (o === 'auto' || o === 'scroll' || o === 'hidden') { oculto = true; break; } p = p.parentElement; }
   if (!oculto) out.push(el.tagName + '.' + (el.className.toString().slice(0, 80)) + ' right=' + Math.round(r.right)); } }
return out.slice(0, 8); }"""
with sync_playwright() as p:
    nav = p.chromium.launch(); ctx = nav.new_context(viewport={"width": ancho, "height": 844}); pag = ctx.new_page()
    pag.goto(f"{BASE}/login")
    pag.get_by_label("Correo electrónico").fill(creds["admin"][0]); pag.get_by_label("Contraseña", exact=False).first.fill(creds["admin"][1])
    pag.get_by_role("button", name="Ingresar").click(); pag.wait_for_url(f"{BASE}/")
    for r in rutas:
        pag.goto(BASE + r); pag.wait_for_load_state("networkidle"); pag.wait_for_timeout(500)
        print(r, pag.evaluate(JS))
    nav.close()
