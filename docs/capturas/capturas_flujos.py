"""Capturas de flujos con interacción (justificación, rechazo, aprobación, traslado en tres pasos, validaciones, bloqueo).

Uso:  INVENTIA_URL=... INVENTIA_EMAIL=... INVENTIA_PASSWORD=... [INVENTIA_BLOQUEO_EMAIL=otro usuario] python3 capturas_flujos.py
Modifica datos de la demostración (aprueba una recomendación y avanza un traslado): úsese solo contra datos de ejemplo."""
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("INVENTIA_URL", "http://127.0.0.1:5173")
EMAIL, PASSWORD = os.environ["INVENTIA_EMAIL"], os.environ["INVENTIA_PASSWORD"]
BLOQUEO = os.environ.get("INVENTIA_BLOQUEO_EMAIL")
SALIDA = Path(__file__).parent


def entrar(pag, email, password):
    pag.goto(f"{BASE}/login")
    pag.get_by_label("Correo electrónico").fill(email)
    pag.get_by_label("Contraseña", exact=False).first.fill(password)
    pag.get_by_role("button", name="Ingresar").click()
    pag.wait_for_url(f"{BASE}/", timeout=15000)


def foto(pag, nombre):
    pag.wait_for_timeout(500)
    pag.screenshot(path=str(SALIDA / f"{nombre}.png"))
    print(nombre)


with sync_playwright() as p:
    nav = p.chromium.launch()
    ctx = nav.new_context(viewport={"width": 1440, "height": 900}, locale="es-CO", timezone_id="America/Bogota")
    pag = ctx.new_page()

    # Pantallas públicas
    pag.goto(f"{BASE}/recuperar"); pag.wait_for_load_state("networkidle"); foto(pag, "recuperar_escritorio")

    # Validaciones en español
    entrar(pag, EMAIL, PASSWORD)
    pag.goto(f"{BASE}/ventas/nueva"); pag.wait_for_load_state("networkidle")
    pag.get_by_role("button", name="Registrar venta").click()
    foto(pag, "validacion_venta_escritorio")

    # Recomendación: justificación y rechazo
    pag.goto(f"{BASE}/recomendaciones"); pag.wait_for_load_state("networkidle"); pag.wait_for_timeout(500)
    pag.get_by_text("Ver justificación").first.click()
    foto(pag, "recomendacion_justificacion_escritorio")
    pag.get_by_role("button", name="Rechazar").first.click()
    foto(pag, "recomendacion_rechazo_escritorio")
    pag.keyboard.press("Escape")

    # Aprobar una recomendación de reabastecimiento
    pag.goto(f"{BASE}/recomendaciones"); pag.wait_for_load_state("networkidle")
    pag.get_by_role("button", name="Aprobar", exact=True).first.click()
    foto(pag, "recomendacion_aprobar_escritorio")
    pag.get_by_role("dialog").get_by_role("button", name="Aprobar").click()
    pag.wait_for_load_state("networkidle")
    pag.goto(f"{BASE}/recomendaciones"); pag.wait_for_load_state("networkidle"); foto(pag, "recomendaciones_tras_aprobar_escritorio")

    # Traslado en tres pasos: solicitar, aprobar (sede de origen) y confirmar (sede de destino)
    pag.goto(f"{BASE}/traslados/nuevo"); pag.wait_for_load_state("networkidle")
    pag.get_by_placeholder("Buscar por código o nombre…").click()
    pag.get_by_placeholder("Buscar por código o nombre…").fill("Pastillas")
    pag.wait_for_timeout(900)
    foto(pag, "nuevo_traslado_busqueda_escritorio")
    pag.get_by_text("Pastillas de freno de disco").first.click()
    pag.get_by_placeholder("Opcional. Ej. urgente por promoción").fill("Reposición para el fin de semana")
    foto(pag, "nuevo_traslado_lleno_escritorio")
    pag.get_by_role("button", name="Solicitar traslado").click()
    pag.wait_for_url("**/traslados/*", timeout=15000); pag.wait_for_load_state("networkidle")
    foto(pag, "traslado_solicitado_escritorio")
    pag.get_by_role("button", name="Aprobar", exact=True).click()
    pag.wait_for_timeout(600)
    if pag.get_by_role("dialog").count():
        foto(pag, "traslado_aprobar_dialogo_escritorio")
        pag.get_by_role("dialog").get_by_role("button", name="Aprobar").click()
    pag.wait_for_load_state("networkidle"); pag.wait_for_timeout(500)
    foto(pag, "traslado_aprobado_escritorio")
    botones = [b.inner_text() for b in pag.get_by_role("button").all()]
    print(botones)
    boton = next((b for b in botones if "Confirmar" in b), None)
    if boton:
        pag.get_by_role("button", name=boton).first.click()
        pag.wait_for_timeout(600)
        if pag.get_by_role("dialog").count():
            foto(pag, "traslado_confirmar_dialogo_escritorio")
            pag.get_by_role("dialog").get_by_role("button", name="Confirmar").click()
        pag.wait_for_load_state("networkidle"); pag.wait_for_timeout(500)
        foto(pag, "traslado_confirmado_escritorio")
    pag.goto(f"{BASE}/movimientos"); pag.wait_for_load_state("networkidle"); foto(pag, "movimientos_tras_traslado_escritorio")

    # Bloqueo temporal por intentos fallidos (usuario de ejemplo; se desbloquea en la base al terminar)
    ctx2 = nav.new_context(viewport={"width": 1440, "height": 900}, locale="es-CO", timezone_id="America/Bogota")
    pg2 = ctx2.new_page()
    pg2.goto(f"{BASE}/login"); pg2.wait_for_load_state("networkidle")
    objetivo = BLOQUEO or "gerente@demo.inventia.example"
    for intento in range(1, 7):
        pg2.get_by_label("Correo electrónico").fill(objetivo)
        pg2.get_by_label("Contraseña", exact=False).first.fill("ClaveIncorrecta-123!")
        pg2.get_by_role("button", name="Ingresar").click()
        pg2.wait_for_timeout(900)
        if intento == 1:
            foto(pg2, "login_error_escritorio")
        if intento >= 5:
            foto(pg2, f"login_bloqueo_intento{intento}_escritorio")
    nav.close()
