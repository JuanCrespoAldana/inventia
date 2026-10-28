"""Categorías, productos, existencias por sede, consolidado, movimientos y alertas."""

from sqlalchemy import func, select

from app.model.inventario import InventarioSede, Movimiento
from tests.ayuda import (
    crear_categoria,
    crear_empresa,
    crear_producto,
    crear_sede,
    crear_usuario,
    entrada,
    existencias,
)

# ---------------------------------------------------------------- catálogo


async def test_categorias_crud_y_reglas(cliente, db):
    admin = await crear_empresa(db, cliente)
    c = await crear_categoria(admin, "Ferretería")
    assert (await admin.post("/api/categorias", {"nombre": "FERRETERÍA"})).status_code == 409
    r = await admin.put(f"/api/categorias/{c['id']}", {"nombre": "Ferretería general", "descripcion": "Tornillos y más"})
    assert r.status_code == 200 and r.json()["nombre"] == "Ferretería general"
    await crear_producto(admin, c["id"])
    r = await admin.patch(f"/api/categorias/{c['id']}/estado", {"activa": False})
    assert r.status_code == 409 and r.json()["codigo"] == "categoria_con_productos"
    lista = (await admin.get("/api/categorias")).json()
    assert lista["items"][0]["total_productos"] == 1


async def test_productos_crud_codigo_inmutable_y_unico(cliente, db):
    admin = await crear_empresa(db, cliente)
    c = await crear_categoria(admin)
    p = await crear_producto(admin, c["id"], codigo=" tor-01 ", nombre="Tornillo 1/4", costo=100, precio_venta=150.5)
    assert p["codigo"] == "TOR-01" and p["precio_venta"] == 150.5 and p["existencias_total"] == 0
    r = await admin.post("/api/productos", {"codigo": "tor-01", "nombre": "Otro", "categoria_id": c["id"]})
    assert r.status_code == 409 and r.json()["codigo"] == "codigo_duplicado"
    r = await admin.put(f"/api/productos/{p['id']}", {"codigo": "NUEVO"})
    assert r.status_code == 422  # el código no es editable
    r = await admin.put(f"/api/productos/{p['id']}", {"nombre": "Tornillo 1/4 pulgada", "costo": 120})
    assert r.status_code == 200 and r.json()["nombre"] == "Tornillo 1/4 pulgada" and r.json()["costo"] == 120
    r = await admin.post("/api/productos", {"codigo": "X", "nombre": "Neg", "categoria_id": c["id"], "costo": -5})
    assert r.status_code == 422
    r = await admin.get("/api/productos?q=tornillo")
    assert r.json()["total"] == 1
    r = await admin.patch(f"/api/productos/{p['id']}/estado", {"activo": False})
    assert r.json()["activo"] is False
    assert (await admin.get("/api/productos?activo=true")).json()["total"] == 0


async def test_producto_inhabilitado_no_recibe_entradas(cliente, db):
    admin = await crear_empresa(db, cliente)
    sede, cat = await crear_sede(admin), await crear_categoria(admin)
    p = await crear_producto(admin, cat["id"])
    await admin.patch(f"/api/productos/{p['id']}/estado", {"activo": False})
    r = await admin.post("/api/inventario/entradas", {"sede_id": sede["id"], "items": [{"producto_id": p["id"], "cantidad": 5}]})
    assert r.status_code == 400 and r.json()["codigo"] == "producto_inactivo"


# ---------------------------------------------------------------- inventario


async def escenario(cliente, db):
    admin = await crear_empresa(db, cliente)
    norte, sur = await crear_sede(admin, "Norte"), await crear_sede(admin, "Sur")
    cat = await crear_categoria(admin)
    p1 = await crear_producto(admin, cat["id"], "A-1", "Tornillo", costo=10)
    p2 = await crear_producto(admin, cat["id"], "A-2", "Tuerca")
    return admin, norte, sur, p1, p2


async def test_entrada_salida_ajuste_y_movimientos(cliente, db):
    admin, norte, sur, p1, p2 = await escenario(cliente, db)
    res = await entrada(admin, norte["id"], {p1["id"]: 100, p2["id"]: 40})
    assert len(res["movimientos"]) == 2
    assert await existencias(admin, norte["id"], p1["id"]) == 100

    r = await admin.post("/api/inventario/salidas", {"sede_id": norte["id"], "motivo": "perdida", "items": [{"producto_id": p1["id"], "cantidad": 30}]})
    assert r.status_code == 201
    mov = r.json()["movimientos"][0]
    assert (mov["delta"], mov["saldo_anterior"], mov["saldo_posterior"]) == (-30, 100, 70)

    r = await admin.post("/api/inventario/ajustes", {"sede_id": norte["id"], "producto_id": p1["id"], "cantidad_real": 65, "motivo": "conteo_fisico", "observacion": "Conteo de cierre de mes"})
    assert r.status_code == 201 and r.json()["movimientos"][0]["delta"] == -5
    assert await existencias(admin, norte["id"], p1["id"]) == 65

    r = await admin.post("/api/inventario/ajustes", {"sede_id": norte["id"], "producto_id": p1["id"], "cantidad_real": 65, "observacion": "Sin cambios aquí"})
    assert r.status_code == 400 and r.json()["codigo"] == "sin_diferencia"

    historial = (await admin.get(f"/api/movimientos?producto_id={p1['id']}")).json()
    assert historial["total"] == 3 and [m["tipo"] for m in historial["items"]] == ["ajuste", "salida", "entrada"]
    # Invariante: la suma de los movimientos = existencias actuales
    suma = await db.scalar(select(func.sum(Movimiento.delta)).where(Movimiento.producto_id == p1["id"]))
    cant = await db.scalar(select(InventarioSede.cantidad).where(InventarioSede.producto_id == p1["id"]))
    assert suma == cant == 65


async def test_salida_con_existencias_insuficientes_no_modifica_nada(cliente, db):
    admin, norte, sur, p1, p2 = await escenario(cliente, db)
    await entrada(admin, norte["id"], {p1["id"]: 10, p2["id"]: 3})
    r = await admin.post("/api/inventario/salidas", {"sede_id": norte["id"], "motivo": "perdida", "items": [
        {"producto_id": p1["id"], "cantidad": 5}, {"producto_id": p2["id"], "cantidad": 4}]})
    assert r.status_code == 409 and r.json()["codigo"] == "existencias_insuficientes"
    assert r.json()["disponibles"] == 3
    # Transacción atómica: la línea válida tampoco se aplicó.
    assert await existencias(admin, norte["id"], p1["id"]) == 10
    assert (await admin.get("/api/movimientos")).json()["total"] == 2


async def test_cantidades_invalidas_y_lineas_repetidas(cliente, db):
    admin, norte, sur, p1, p2 = await escenario(cliente, db)
    for cantidad in (0, -3, 1.5):
        r = await admin.post("/api/inventario/entradas", {"sede_id": norte["id"], "items": [{"producto_id": p1["id"], "cantidad": cantidad}]})
        assert r.status_code == 422
    r = await admin.post("/api/inventario/entradas", {"sede_id": norte["id"], "items": [{"producto_id": p1["id"], "cantidad": 1}, {"producto_id": p1["id"], "cantidad": 2}]})
    assert r.status_code == 422
    r = await admin.post("/api/inventario/salidas", {"sede_id": norte["id"], "motivo": "otro", "items": [{"producto_id": p1["id"], "cantidad": 1}]})
    assert r.status_code == 422  # «otro» exige explicación


async def test_niveles_generan_y_resuelven_alertas(cliente, db):
    admin, norte, sur, p1, p2 = await escenario(cliente, db)
    await entrada(admin, norte["id"], {p1["id"]: 8})
    r = await admin.put("/api/inventario/niveles", {"sede_id": norte["id"], "producto_id": p1["id"], "stock_minimo": 10, "stock_maximo": 50})
    assert r.status_code == 200
    alertas = (await admin.get("/api/alertas")).json()
    assert alertas["total"] == 1 and alertas["items"][0]["tipo"] == "inventario_bajo"
    assert (await admin.put("/api/inventario/niveles", {"sede_id": norte["id"], "producto_id": p1["id"], "stock_minimo": 60, "stock_maximo": 50})).status_code == 422

    # Reabastecer resuelve la alerta de bajo; pasarse del máximo abre la de exceso
    res = await entrada(admin, norte["id"], {p1["id"]: 100})
    assert res["alertas_resueltas"] == 1
    tipos = {a["tipo"] for a in (await admin.get("/api/alertas")).json()["items"]}
    assert tipos == {"inventario_excesivo"}
    historico = (await admin.get("/api/alertas?estado=resuelta")).json()
    assert historico["total"] == 1 and historico["items"][0]["resuelta_en"]
    # Vaciar el producto: alerta crítica de agotado
    await admin.post("/api/inventario/salidas", {"sede_id": norte["id"], "motivo": "perdida", "items": [{"producto_id": p1["id"], "cantidad": 108}]})
    activas = (await admin.get("/api/alertas")).json()["items"]
    assert [(a["tipo"], a["prioridad"]) for a in activas] == [("inventario_bajo", "critica")]
    resumen = (await admin.get("/api/alertas/resumen")).json()
    assert resumen["total"] == 1 and resumen["por_prioridad"] == {"critica": 1}


async def test_alertas_sin_duplicados_y_recalculo(cliente, db):
    admin, norte, sur, p1, p2 = await escenario(cliente, db)
    await entrada(admin, norte["id"], {p1["id"]: 3})
    await admin.put("/api/inventario/niveles", {"sede_id": norte["id"], "producto_id": p1["id"], "stock_minimo": 10})
    await admin.put("/api/inventario/niveles", {"sede_id": norte["id"], "producto_id": p1["id"], "stock_minimo": 10})
    r = await admin.post("/api/alertas/recalcular")
    assert r.status_code == 200 and r.json()["activas"] == 1
    assert (await admin.get("/api/alertas")).json()["total"] == 1


async def test_consolidado_suma_las_sedes_sin_duplicar(cliente, db):
    admin, norte, sur, p1, p2 = await escenario(cliente, db)
    await entrada(admin, norte["id"], {p1["id"]: 60})
    await entrada(admin, sur["id"], {p1["id"]: 15, p2["id"]: 5})
    r = await admin.get("/api/inventario/consolidado")
    filas = {f["producto"]["codigo"]: f for f in r.json()["items"]}
    assert filas["A-1"]["total"] == 75 and filas["A-1"]["valor"] == 750.0
    assert {s["sede"]: s["cantidad"] for s in filas["A-1"]["sedes"]} == {"Norte": 60, "Sur": 15}
    assert filas["A-2"]["total"] == 5 and filas["A-2"]["valor"] is None  # sin costo: no se inventa un valor


async def test_inventario_lista_productos_sin_existencias(cliente, db):
    admin, norte, sur, p1, p2 = await escenario(cliente, db)
    await entrada(admin, norte["id"], {p1["id"]: 5})
    filas = (await admin.get(f"/api/inventario?sede_id={sur['id']}")).json()
    assert filas["total"] == 2 and all(f["cantidad"] == 0 and f["estado"] == "agotado" for f in filas["items"])
    assert (await admin.get(f"/api/inventario?sede_id={norte['id']}&estado=normal")).json()["total"] == 1


# ---------------------------------------------------------------- permisos por sede y aislamiento


async def test_usuario_de_sede_no_opera_en_otra_sede(cliente, db):
    admin, norte, sur, p1, p2 = await escenario(cliente, db)
    op = await crear_usuario(admin, "usuario_inventario", "op@andina.com", norte["id"])
    await entrada(op, norte["id"], {p1["id"]: 10})
    r = await op.post("/api/inventario/entradas", {"sede_id": sur["id"], "items": [{"producto_id": p1["id"], "cantidad": 1}]})
    assert r.status_code == 403
    assert (await op.get(f"/api/inventario?sede_id={sur['id']}")).status_code == 403
    assert (await op.get("/api/inventario")).json()["sede"]["id"] == norte["id"]  # por defecto, su sede
    assert (await op.get("/api/inventario/consolidado")).status_code == 403
    mov = (await op.get("/api/movimientos")).json()
    assert mov["total"] == 1
    assert (await op.get(f"/api/movimientos?sede_id={sur['id']}")).status_code == 403
    # No puede cambiar niveles (no tiene el permiso) ni crear productos
    assert (await op.put("/api/inventario/niveles", {"sede_id": norte["id"], "producto_id": p1["id"], "stock_minimo": 1})).status_code == 403
    assert (await op.post("/api/productos", {"codigo": "Z", "nombre": "Zz", "categoria_id": 1})).status_code == 403


async def test_aislamiento_de_inventario_entre_empresas(cliente, db):
    a = await crear_empresa(db, cliente, "Empresa A", "a@a.com", "1")
    b = await crear_empresa(db, cliente, "Empresa B", "b@b.com", "2")
    sede_a, sede_b = await crear_sede(a, "SA"), await crear_sede(b, "SB")
    cat_a, cat_b = await crear_categoria(a), await crear_categoria(b)
    prod_a = await crear_producto(a, cat_a["id"], "COD", "Producto A")
    prod_b = await crear_producto(b, cat_b["id"], "COD", "Producto B")  # el mismo código en otra empresa es válido
    await entrada(b, sede_b["id"], {prod_b["id"]: 50})

    assert (await a.get(f"/api/productos/{prod_b['id']}")).status_code == 404
    assert (await a.put(f"/api/productos/{prod_b['id']}", {"nombre": "Robado"})).status_code == 404
    assert (await a.get(f"/api/inventario?sede_id={sede_b['id']}")).status_code == 404
    r = await a.post("/api/inventario/entradas", {"sede_id": sede_b["id"], "items": [{"producto_id": prod_a["id"], "cantidad": 5}]})
    assert r.status_code == 404
    r = await a.post("/api/inventario/entradas", {"sede_id": sede_a["id"], "items": [{"producto_id": prod_b["id"], "cantidad": 5}]})
    assert r.status_code == 404  # producto de otra empresa
    assert (await a.post("/api/inventario/salidas", {"sede_id": sede_a["id"], "motivo": "perdida", "items": [{"producto_id": prod_b["id"], "cantidad": 1}]})).status_code == 404
    assert (await a.put("/api/inventario/niveles", {"sede_id": sede_a["id"], "producto_id": prod_b["id"], "stock_minimo": 1})).status_code == 404
    assert (await a.get("/api/movimientos")).json()["total"] == 0
    assert (await a.get("/api/alertas")).json()["total"] == 0
    assert (await a.get(f"/api/categorias/{cat_b['id']}")).status_code == 404
    assert (await a.post("/api/productos", {"codigo": "NN", "nombre": "Nombre", "categoria_id": cat_b["id"]})).status_code == 404
    cons = (await a.get("/api/inventario/consolidado")).json()["items"]
    assert [f["producto"]["nombre"] for f in cons] == ["Producto A"] and cons[0]["total"] == 0
