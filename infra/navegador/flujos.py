"""Nueve flujos completos en el navegador (Playwright + Chromium) como administrador, contra una base de PRUEBAS con datos de demostración.

Uso: INVENTIA_CREDENCIALES=credenciales.json python flujos.py
Crea registros (una venta, un traslado, un usuario, un rol, una llave); no lo use con datos reales.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("INVENTIA_URL", "http://127.0.0.1:5173")
CREDENCIALES = Path(os.environ.get("INVENTIA_CREDENCIALES", "credenciales.json"))
SUF = str(int(time.time()) % 100000)
creds = json.loads(CREDENCIALES.read_text())
problemas = []
resultados = []


def paso(nombre, fn):
    try:
        fn()
        resultados.append(("OK", nombre))
    except Exception as e:  # noqa: BLE001
        resultados.append(("FALLA", f"{nombre}: {str(e)[:300]}"))


with sync_playwright() as p:
    nav = p.chromium.launch()
    ctx = nav.new_context(viewport={"width": 1366, "height": 900}, locale="es-CO")
    ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=BASE)
    pag = ctx.new_page()
    pag.on("console", lambda m: problemas.append(("consola", pag.url, m.text)) if m.type == "error" else None)
    pag.on("pageerror", lambda e: problemas.append(("excepcion", pag.url, str(e))))
    pag.on("response", lambda r: problemas.append(("http", r.url, r.status)) if r.status >= 500 else None)

    pag.goto(f"{BASE}/login")
    pag.get_by_label("Correo electrónico").fill(creds["admin"][0])
    pag.get_by_label("Contraseña", exact=False).first.fill(creds["admin"][1])
    pag.get_by_role("button", name="Ingresar").click()
    pag.wait_for_url(f"{BASE}/")

    # ---------------------------------------------------------------- venta + anulación
    def venta():
        pag.goto(f"{BASE}/ventas/nueva")
        pag.get_by_placeholder("Buscar por código o nombre…").click()
        pag.get_by_placeholder("Buscar por código o nombre…").fill("Aceite")
        pag.get_by_role("listbox").get_by_role("option").first.click()
        pag.get_by_role("button", name="Registrar venta").click()
        pag.wait_for_url(re.compile(r"/ventas/\d+$"), timeout=10000)
        expect(pag.get_by_text("Registrada").first).to_be_visible()
        pag.get_by_role("button", name=re.compile("Anular")).first.click()
        pag.get_by_label(re.compile("Motivo", re.I)).fill("Prueba de anulación desde la interfaz")
        pag.get_by_role("button", name=re.compile("^Anular")).last.click()
        expect(pag.get_by_text("Anulada").first).to_be_visible(timeout=8000)

    paso("venta registrada y anulada", venta)

    # ---------------------------------------------------------------- traslado: solicitar → aprobar → confirmar
    def traslado():
        pag.goto(f"{BASE}/traslados/nuevo")
        selects = pag.locator("select")
        selects.nth(0).select_option(index=1)
        selects.nth(1).select_option(index=2)
        pag.get_by_placeholder("Buscar por código o nombre…").click()
        pag.get_by_placeholder("Buscar por código o nombre…").fill("Aceite")
        pag.get_by_role("listbox").get_by_role("option").first.click()
        pag.get_by_role("button", name=re.compile("Solicitar traslado")).last.click()
        pag.wait_for_url(re.compile(r"/traslados/\d+$"), timeout=10000)
        expect(pag.get_by_text("Solicitado").first).to_be_visible()
        pag.get_by_role("button", name="Aprobar").first.click()
        pag.get_by_role("button", name="Aprobar").last.click()
        expect(pag.get_by_text("Aprobado").first).to_be_visible(timeout=8000)
        pag.get_by_role("button", name=re.compile("Confirmar")).first.click()
        pag.get_by_role("button", name=re.compile("Confirmar")).last.click()
        expect(pag.get_by_text("Confirmado").first).to_be_visible(timeout=8000)

    paso("traslado solicitado, aprobado y confirmado", traslado)

    # ---------------------------------------------------------------- usuario nuevo
    def usuario():
        pag.goto(f"{BASE}/usuarios")
        pag.get_by_role("button", name="Nuevo usuario").click()
        d = pag.get_by_role("dialog")
        d.get_by_label("Nombre completo").fill("Auxiliar de Bodega")
        d.get_by_label("Correo electrónico").fill(f"auxiliar{SUF}@demo.inventia.example")
        d.get_by_label("Rol").select_option(label="Usuario de inventario")
        d.get_by_label("Sede").select_option(index=1)
        d.get_by_role("button", name=re.compile("Generar contraseña")).click()
        d.get_by_role("button", name="Crear usuario").click()
        expect(pag.get_by_text(f"auxiliar{SUF}@demo.inventia.example")).to_be_visible(timeout=8000)

    paso("usuario creado desde la interfaz", usuario)

    # ---------------------------------------------------------------- validación de formulario
    def validacion():
        pag.get_by_role("button", name="Nuevo usuario").click()
        d = pag.get_by_role("dialog")
        d.get_by_role("button", name="Crear usuario").click()
        expect(d.get_by_text("El nombre es obligatorio", exact=False)).to_be_visible()
        expect(d.locator("p[role=alert]", has_text="Seleccione un rol")).to_be_visible()
        d.get_by_role("button", name="Cancelar").click()

    paso("validaciones en español en el formulario", validacion)

    # ---------------------------------------------------------------- rol nuevo + permisos
    def rol():
        pag.goto(f"{BASE}/roles")
        pag.get_by_role("button", name="Nuevo rol").click()
        d = pag.get_by_role("dialog")
        d.get_by_label("Nombre del rol").fill(f"Auxiliar de consulta {SUF}")
        d.get_by_role("button", name="Crear rol").click()
        expect(pag.get_by_role("heading", name=f"Auxiliar de consulta {SUF}")).to_be_visible(timeout=8000)
        pag.get_by_label("Consultar productos", exact=False).first.check()
        pag.get_by_role("button", name="Guardar permisos").click()
        expect(pag.get_by_text("Permisos actualizados.")).to_be_visible(timeout=8000)

    paso("rol creado y permisos asignados", rol)

    # ---------------------------------------------------------------- llave de agente
    def llave():
        pag.goto(f"{BASE}/integraciones")
        pag.get_by_role("button", name="Nueva llave").first.click()
        d = pag.get_by_role("dialog")
        d.get_by_label("Nombre de la llave").fill(f"Asistente {SUF}")
        d.get_by_role("checkbox").first.check()
        d.get_by_role("button", name="Crear llave").click()
        secreto = pag.get_by_test_id("llave-secreta")
        expect(secreto).to_be_visible(timeout=8000)
        valor = secreto.inner_text()
        assert valor.startswith("inv_") or len(valor) > 20, valor
        pag.get_by_role("button", name="Copiar").click()
        expect(pag.get_by_role("button", name="Copiada")).to_be_visible()
        pag.get_by_role("button", name="Ya la guardé").click()
        expect(pag.get_by_text(f"Asistente {SUF}").first).to_be_visible()
        pag.get_by_role("button", name="Revocar").first.click()
        pag.get_by_role("button", name="Revocar").last.click()
        expect(pag.get_by_text("Revocada").first).to_be_visible(timeout=8000)

    paso("llave de agente creada, copiada y revocada", llave)

    # ---------------------------------------------------------------- recomendación: rechazar con comentario
    def recomendacion():
        pag.goto(f"{BASE}/recomendaciones")
        pag.get_by_role("button", name="Rechazar").first.click()
        d = pag.get_by_role("dialog")
        d.get_by_label(re.compile("Comentario|Motivo", re.I)).fill("No se requiere por ahora")
        d.get_by_role("button", name="Rechazar").click()
        expect(pag.get_by_role("status").filter(has_text=re.compile("rechazad", re.I)).first).to_be_visible(timeout=8000)

    paso("recomendación rechazada con comentario", recomendacion)

    # ---------------------------------------------------------------- reportes: descarga
    def reporte():
        pag.goto(f"{BASE}/reportes")
        with pag.expect_download(timeout=15000) as dl:
            pag.get_by_role("button", name="Excel").click()
        assert dl.value.suggested_filename.endswith(".xlsx"), dl.value.suggested_filename
        with pag.expect_download(timeout=15000) as dl2:
            pag.get_by_role("button", name="CSV").click()
        assert dl2.value.suggested_filename.endswith(".csv")

    paso("descarga de reporte Excel y CSV", reporte)

    # ---------------------------------------------------------------- cerrar sesión
    def salir():
        pag.get_by_role("button", name=re.compile("Salir")).first.click()
        pag.wait_for_url(re.compile("/login"))

    paso("cierre de sesión", salir)
    nav.close()

for r in resultados:
    print(*r)
print("problemas:", problemas)
sys.exit(1 if any(r[0] == "FALLA" for r in resultados) or problemas else 0)
