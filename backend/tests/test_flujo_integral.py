"""Escenario de punta a punta (sección 26 del documento maestro), solo a través de la API.

Único paso que no pasa por la API: el 14. La API no permite fechar ventas en el pasado (es deliberado: el
historial no se puede falsificar), así que el historial se carga con los mismos servicios que usa la API.
"""

from tests.ayuda import PASSWORD, crear_empresa, crear_usuario, iniciar_sesion, patron_semanal, sembrar_historial

SETUP = {
    "empresa_nombre": "Comercial Sabana S.A.S.", "empresa_identificacion": "900.123.456-7", "empresa_ciudad": "Bogotá",
    "admin_nombre": "Administración General", "admin_email": "admin@sabana.com", "admin_password": PASSWORD,
}


async def test_flujo_completo_de_una_empresa(cliente, db):
    # 1-2. Empresa y administrador inicial, de forma controlada (solo una vez)
    r = await cliente.post("/api/setup", json=SETUP)
    assert r.status_code == 201 and r.json()["usuario"]["rol"]["clave"] == "admin"
    assert (await cliente.post("/api/setup", json={**SETUP, "admin_email": "intruso@x.com"})).status_code == 409

    # 3. El administrador inicia sesión
    admin = await iniciar_sesion(cliente, "admin@sabana.com")

    # 4. Dos sedes
    norte = (await admin.post("/api/sedes", {"nombre": "Sede Norte", "ciudad": "Bogotá"})).json()
    sur = (await admin.post("/api/sedes", {"nombre": "Sede Sur", "ciudad": "Bogotá"})).json()

    # 5. Usuarios con roles distintos, asignados a sedes
    gerente = await crear_usuario(admin, "gerente", "gerente@sabana.com")
    analista = await crear_usuario(admin, "analista_compras", "compras@sabana.com")
    enc_norte = await crear_usuario(admin, "encargado_sede", "enc.norte@sabana.com", norte["id"])
    op_sur = await crear_usuario(admin, "usuario_inventario", "op.sur@sabana.com", sur["id"])
    assert enc_norte.usuario["sede"]["id"] == norte["id"] and op_sur.usuario["rol"]["clave"] == "usuario_inventario"

    # 6. Categorías y productos
    cat = (await admin.post("/api/categorias", {"nombre": "Abarrotes"})).json()
    arroz = (await admin.post("/api/productos", {"codigo": "ARZ-1", "nombre": "Arroz 1 kg", "categoria_id": cat["id"], "costo": 3000, "precio_venta": 4500})).json()
    aceite = (await admin.post("/api/productos", {"codigo": "ACE-1", "nombre": "Aceite 1 L", "categoria_id": cat["id"], "costo": 9000, "precio_venta": 12000})).json()

    # 7. Existencias iniciales (por entrada con motivo «inventario inicial»)
    r = await enc_norte.post("/api/inventario/entradas", {"sede_id": norte["id"], "motivo": "inventario_inicial", "items": [
        {"producto_id": arroz["id"], "cantidad": 100}, {"producto_id": aceite["id"], "cantidad": 40}]})
    assert r.status_code == 201, r.text
    assert (await admin.post("/api/inventario/entradas", {"sede_id": sur["id"], "motivo": "inventario_inicial", "items": [
        {"producto_id": arroz["id"], "cantidad": 30}]})).status_code == 201
    # un encargado no puede cargar inventario en una sede que no es la suya
    assert (await enc_norte.post("/api/inventario/entradas", {"sede_id": sur["id"], "motivo": "compra", "items": [
        {"producto_id": arroz["id"], "cantidad": 1}]})).status_code == 403

    # 8. Inventario por sede y consolidado (el consolidado se calcula, no se duplica)
    inv_norte = (await admin.get(f"/api/inventario?sede_id={norte['id']}")).json()["items"]
    assert {f["producto"]["codigo"]: f["cantidad"] for f in inv_norte if f["cantidad"]} == {"ARZ-1": 100, "ACE-1": 40}
    cons = {f["producto"]["codigo"]: f for f in (await gerente.get("/api/inventario/consolidado")).json()["items"]}
    assert cons["ARZ-1"]["total"] == 130 and {s["sede"]: s["cantidad"] for s in cons["ARZ-1"]["sedes"]} == {"Sede Norte": 100, "Sede Sur": 30}

    # 9. Entradas y salidas
    assert (await enc_norte.post("/api/inventario/entradas", {"sede_id": norte["id"], "motivo": "compra", "items": [{"producto_id": arroz["id"], "cantidad": 20}]})).status_code == 201
    assert (await enc_norte.post("/api/inventario/salidas", {"sede_id": norte["id"], "motivo": "perdida", "observacion": "Bolsa rota", "items": [{"producto_id": arroz["id"], "cantidad": 5}]})).status_code == 201
    sobrante = await enc_norte.post("/api/inventario/salidas", {"sede_id": norte["id"], "motivo": "perdida", "items": [{"producto_id": aceite["id"], "cantidad": 999}]})
    assert sobrante.status_code == 409 and sobrante.json()["codigo"] == "existencias_insuficientes"  # nunca stock negativo

    # 10. Ventas y descuento de existencias (Norte arroz: 100 + 20 - 5 - 15 = 100)
    v = await enc_norte.post("/api/ventas", {"sede_id": norte["id"], "items": [{"producto_id": arroz["id"], "cantidad": 15}, {"producto_id": aceite["id"], "cantidad": 2}]})
    assert v.status_code == 201 and v.json()["total"] == 15 * 4500 + 2 * 12000
    inv = {f["producto"]["codigo"]: f["cantidad"] for f in (await enc_norte.get(f"/api/inventario?sede_id={norte['id']}")).json()["items"]}
    assert inv == {"ARZ-1": 100, "ACE-1": 38}

    # 11. Traslado Norte -> Sur: las existencias solo cambian al confirmar
    t = (await enc_norte.post("/api/traslados", {"sede_origen_id": norte["id"], "sede_destino_id": sur["id"], "items": [{"producto_id": arroz["id"], "cantidad": 40}]})).json()
    assert (await enc_norte.post(f"/api/traslados/{t['id']}/aprobar")).status_code == 200
    antes_sur = {f["producto"]["codigo"]: f["cantidad"] for f in (await op_sur.get(f"/api/inventario?sede_id={sur['id']}")).json()["items"]}
    assert antes_sur["ARZ-1"] == 30  # aún no llega
    assert (await op_sur.post(f"/api/traslados/{t['id']}/confirmar")).status_code == 200
    por_sede = {s["sede"]: s["cantidad"] for s in next(f for f in (await admin.get("/api/inventario/consolidado")).json()["items"] if f["producto"]["codigo"] == "ARZ-1")["sedes"]}
    assert por_sede == {"Sede Norte": 60, "Sede Sur": 70}

    # 12. Movimientos y reportes
    movs = (await admin.get("/api/movimientos?tamano=100")).json()
    tipos = {m["tipo"] for m in movs["items"]}
    assert {"entrada", "salida", "venta", "traslado_salida", "traslado_entrada"} <= tipos
    rep = (await admin.get("/api/reportes/inventario")).json()
    assert rep["total"] >= 3 and (await admin.get("/api/reportes/inventario?formato=xlsx")).status_code == 200
    assert (await gerente.get("/api/reportes/ventas?formato=csv")).status_code == 200
    assert (await op_sur.get("/api/reportes/ventas")).status_code == 403

    # 13. Alertas de inventario
    assert (await admin.put("/api/inventario/niveles", {"sede_id": norte["id"], "producto_id": aceite["id"], "stock_minimo": 50, "stock_maximo": 200})).status_code == 200
    alertas = (await admin.get("/api/alertas")).json()["items"]
    assert any(a["tipo"] == "inventario_bajo" and a["producto"]["codigo"] == "ACE-1" for a in alertas)

    # 14. Historial de ventas suficiente para el modelo (60 días con patrón semanal) en las dos sedes
    await sembrar_historial(db, admin, norte["id"], arroz["id"], patron_semanal(60, semilla=11), stock_final=20)
    await sembrar_historial(db, admin, sur["id"], arroz["id"], patron_semanal(60, semilla=12), stock_final=300)

    gran_venta = await enc_norte.post("/api/ventas", {"sede_id": norte["id"], "items": [{"producto_id": arroz["id"], "cantidad": 55}]})
    assert gran_venta.status_code == 201  # Norte queda con 25 unidades de arroz; Sur con 370

    # 15. Predicción (con datos suficientes y con la aclaración de los que no alcanzan) y recomendaciones
    ej = (await analista.post("/api/predicciones/ejecutar", {"horizonte_dias": 14})).json()
    detalle = (await analista.get(f"/api/predicciones/ejecuciones/{ej['id']}")).json()
    assert detalle["estado"] == "completada"
    assert detalle["resumen"]["series_con_prediccion"] == 2 and detalle["resumen"]["series_omitidas"] == 1  # el aceite no tiene ventas
    assert "Pocas ventas" in detalle["resumen"]["omitidas"][0]["motivo"] or "Historial" in detalle["resumen"]["omitidas"][0]["motivo"]
    preds = (await analista.get("/api/predicciones")).json()["items"]
    assert all(p["metricas"]["wape"] is not None for p in preds)
    gen = (await analista.post("/api/recomendaciones/generar")).json()
    assert gen["generadas"] == 1 and gen["traslados"] == 1  # Sur tiene de sobra y Norte se queda corta
    rec = (await gerente.get("/api/recomendaciones?estado=pendiente")).json()["items"][0]
    assert rec["tipo"] == "traslado" and rec["sede"]["nombre"] == "Sede Norte" and rec["sede_origen"]["nombre"] == "Sede Sur"
    assert rec["resumen"] and rec["estado"] == "pendiente"  # nada se ejecuta sin aprobación humana
    assert (await gerente.post(f"/api/recomendaciones/{rec['id']}/aprobar", {"comentario": "De acuerdo"})).status_code == 200

    # 16. Aislamiento: otra empresa no ve nada de la primera, ni siquiera conociendo los identificadores
    otra = await crear_empresa(db, cliente, "Otra Empresa", "admin@otra.com", "3")
    for ruta in (
        f"/api/sedes/{norte['id']}", f"/api/productos/{arroz['id']}", f"/api/traslados/{t['id']}",
        f"/api/predicciones/ejecuciones/{ej['id']}", f"/api/recomendaciones/{rec['id']}",
    ):
        assert (await otra.get(ruta)).status_code == 404, ruta
    assert (await otra.get(f"/api/inventario?sede_id={norte['id']}")).status_code == 404
    assert (await otra.get("/api/productos")).json()["total"] == 0 and (await otra.get("/api/ventas")).json()["total"] == 0
    ajena = (await otra.get("/api/auditoria?tamano=100")).json()["items"]
    assert {a["usuario_email"] for a in ajena} == {"admin@otra.com"}  # solo su propia actividad (configuración e inicio de sesión)
    # y dentro de la misma empresa, una sede no ve la otra
    assert (await op_sur.get(f"/api/inventario?sede_id={norte['id']}")).status_code == 403

    # 17. Las operaciones importantes quedaron auditadas
    filas, pagina = [], 1
    while True:
        bloque = (await admin.get(f"/api/auditoria?tamano=100&pagina={pagina}")).json()
        filas += bloque["items"]
        if len(filas) >= bloque["total"]:
            break
        pagina += 1
    registro = {"items": filas}
    acciones = {(a["modulo"], a["accion"]) for a in filas}
    esperadas = {
        ("empresa", "configuracion_inicial"), ("sedes", "crear"), ("usuarios", "crear"), ("categorias", "crear"),
        ("productos", "crear"), ("inventario", "entrada"), ("inventario", "salida"), ("ventas", "registrar"),
        ("traslados", "solicitar"), ("traslados", "aprobar"), ("traslados", "confirmar"), ("prediccion", "ejecutar"),
        ("prediccion", "completar"), ("recomendaciones", "generar"), ("recomendaciones", "aprobar"),
        ("reportes", "exportar"), ("auth", "inicio_sesion"),
    }
    assert esperadas <= acciones, esperadas - acciones
    usuarios_que_actuaron = {a["usuario_email"] for a in registro["items"]}
    assert {"enc.norte@sabana.com", "op.sur@sabana.com", "compras@sabana.com"} <= usuarios_que_actuaron
    assert PASSWORD not in str(registro) and "password" not in str(registro).lower().replace("restablecer_password", "")
