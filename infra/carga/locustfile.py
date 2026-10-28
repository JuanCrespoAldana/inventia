"""Prueba de carga de Inventia con Locust (RNF-011 tiempo de respuesta, RNF-012 y RNF-014 operaciones simultáneas).

Cada usuario virtual hace lo que haría una persona en la plataforma: mira el panel, consulta existencias, productos,
ventas, alertas, predicciones y recomendaciones, genera un reporte y registra ventas y entradas de mercancía.

    cd infra/carga
    pip install -r requirements.txt
    export INVENTIA_EMAIL=...  INVENTIA_PASSWORD=...        # un usuario administrador de una base de PRUEBA
    locust -f locustfile.py --headless --host http://127.0.0.1:8000 -u 20 -r 5 -t 90s --csv resultados/u20

Variables opcionales:
  INVENTIA_SOLO_LECTURA=1   no registra ventas ni entradas (no modifica datos)
  INVENTIA_PDF=1            incluye la generación de PDF entre las tareas (trabajo pesado de CPU)

IMPORTANTE: usar solo contra una base de pruebas o de demostración. Las tareas de escritura registran ventas y
entradas reales (de una unidad). La sesión se inicia una sola vez al comenzar la prueba y se comparte: el inicio de
sesión está limitado por IP (RNF-026) y probarlo con cientos de usuarios desde una sola máquina solo mediría ese límite.
"""

import os
import random

import requests
from locust import HttpUser, between, events, task

_EMAIL = os.environ.get("INVENTIA_EMAIL", "")
_PASSWORD = os.environ.get("INVENTIA_PASSWORD", "")
SOLO_LECTURA = os.environ.get("INVENTIA_SOLO_LECTURA") == "1"
CON_PDF = os.environ.get("INVENTIA_PDF") == "1"

_estado: dict = {"cabeceras": {}, "sedes": [], "vendibles": {}}


def _abortar(environment, mensaje: str) -> None:
    """Detiene la prueba con un mensaje claro (una excepción en este punto se perdería en el registro de Locust)."""
    print(f"\nERROR DE PREPARACIÓN: {mensaje}\n", flush=True)
    environment.process_exit_code = 2
    if environment.runner:
        environment.runner.quit()
    raise SystemExit(2)


@events.test_start.add_listener
def preparar(environment, **_):
    """Inicia sesión una vez y reúne las sedes y los productos con existencias para las ventas de prueba."""
    if not _EMAIL or not _PASSWORD:
        _abortar(environment, "defina INVENTIA_EMAIL e INVENTIA_PASSWORD (usuario de una base de pruebas).")
    host = environment.host.rstrip("/")
    r = requests.post(f"{host}/api/auth/login", json={"email": _EMAIL, "password": _PASSWORD}, timeout=30)
    if not r.ok:
        _abortar(environment, f"el inicio de sesión respondió {r.status_code}: {r.text[:200]}")
    _estado["cabeceras"] = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = requests.get(f"{host}/api/sedes/directorio", headers=_estado["cabeceras"], timeout=30)
    if not r.ok or not r.json():
        _abortar(environment, f"no se obtuvieron sedes ({r.status_code}). ¿La base tiene datos de demostración?")
    _estado["sedes"] = [s["id"] for s in r.json()]
    for sede_id in _estado["sedes"]:
        filas = requests.get(
            f"{host}/api/inventario", params={"sede_id": sede_id, "tamano": 100}, headers=_estado["cabeceras"], timeout=30
        ).json()["items"]
        _estado["vendibles"][sede_id] = [f["producto"]["id"] for f in filas if f["cantidad"] >= 20]


class UsuarioInventia(HttpUser):
    wait_time = between(0.5, 2.0)  # tiempo de lectura de una persona entre una acción y la siguiente

    def on_start(self):
        self.client.headers.update(_estado["cabeceras"])
        self.sede = random.choice(_estado["sedes"])

    # ------------------------------------------------------------------ consultas
    @task(4)
    def panel(self):
        self.client.get("/api/dashboard", name="GET /api/dashboard")

    @task(3)
    def consolidado(self):
        self.client.get("/api/inventario/consolidado?tamano=50", name="GET /api/inventario/consolidado")

    @task(3)
    def existencias_de_la_sede(self):
        self.client.get(f"/api/inventario?sede_id={self.sede}&tamano=50", name="GET /api/inventario (sede)")

    @task(3)
    def productos(self):
        self.client.get("/api/productos?tamano=50", name="GET /api/productos")

    @task(2)
    def ventas(self):
        self.client.get("/api/ventas?tamano=50", name="GET /api/ventas")

    @task(2)
    def alertas(self):
        self.client.get("/api/alertas?tamano=50", name="GET /api/alertas")

    @task(1)
    def predicciones(self):
        self.client.get("/api/predicciones?tamano=50", name="GET /api/predicciones")

    @task(1)
    def recomendaciones(self):
        self.client.get("/api/recomendaciones?tamano=50", name="GET /api/recomendaciones")

    @task(1)
    def reporte_en_pantalla(self):
        self.client.get("/api/reportes/inventario?formato=json", name="GET /api/reportes/inventario (vista previa)")

    @task(1 if CON_PDF else 0)
    def reporte_pdf(self):
        self.client.get("/api/reportes/inventario?formato=pdf", name="GET /api/reportes/inventario (PDF)")

    # ------------------------------------------------------------------ escrituras (RNF-014)
    @task(0 if SOLO_LECTURA else 2)
    def registrar_venta(self):
        productos = _estado["vendibles"].get(self.sede) or []
        if not productos:
            return
        cuerpo = {"sede_id": self.sede, "items": [{"producto_id": random.choice(productos), "cantidad": 1}]}
        self.client.post("/api/ventas", json=cuerpo, name="POST /api/ventas")

    @task(0 if SOLO_LECTURA else 1)
    def registrar_entrada(self):
        productos = _estado["vendibles"].get(self.sede) or []
        if not productos:
            return
        cuerpo = {"sede_id": self.sede, "motivo": "compra", "items": [{"producto_id": random.choice(productos), "cantidad": 2}]}
        self.client.post("/api/inventario/entradas", json=cuerpo, name="POST /api/inventario/entradas")
