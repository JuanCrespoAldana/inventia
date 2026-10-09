"""Ventas (cabecera + detalle + anulación) y traslados entre sedes."""

from sqlalchemy import func, select

from app.models.inventario import InventarioSede, Movimiento
from app.models.operaciones import Venta
from tests.ayuda import (
    crear_categoria,
    crear_empresa,
    crear_producto,
    crear_sede,
    crear_usuario,
    entrada,
    existencias,
)


async def base(cliente, db):
    admin = await crear_empresa(db, cliente)
    norte, sur = await crear_sede(admin, "Norte"), await crear_sede(admin, "Sur")
    cat = await crear_categoria(admin)
    p1 = await crear_producto(admin, cat["id"], "V-1", "Cuaderno", costo=1000, precio_venta=2500)
    p2 = await crear_producto(admin, cat["id"], "V-2", "Lápiz", costo=200)  # sin precio de venta
    await entrada(admin, norte["id"], {p1["id"]: 50, p2["id"]: 100})
    return admin, norte, sur, p1, p2


# ----------------------------------------------------------------------------- ventas


async def test_venta_descuenta_existencias_y_calcula_totales(cliente, db):
    admin, norte, sur, p1, p2 = await base(cliente, db)
    r = await admin.post("/api/ventas", {"sede_id": norte["id"], "items": [
        {"producto_id": p1["id"], "cantidad": 4}, {"producto_id": p2["id"], "cantidad": 10, "precio_unitario": 350.5}]})
    assert r.status_code == 201, r.text
    v = r.json()
    assert v["numero"] == 1 and v["estado"] == "registrada" and v["unidades"] == 14
    assert v["total"] == 4 * 2500 + 10 * 350.5 == 13505.0
    assert {i["producto"]["codigo"]: i["subtotal"] for i in v["items"]} == {"V-1": 10000.0, "V-2": 3505.0}
    assert await existencias(admin, norte["id"], p1["id"]) == 46
    v2 = (await admin.post("/api/ventas", {"sede_id": norte["id"], "items": [{"producto_id": p1["id"], "cantidad": 1}]})).json()
    assert v2["numero"] == 2  # consecutivo por empresa
    movs = (await admin.get(f"/api/movimientos?tipo=venta")).json()["items"]
    assert len(movs) == 3 and all(m["venta_numero"] in (1, 2) for m in movs)


async def test_venta_sin_precio_ni_stock_se_rechaza_completa(cliente, db):
    admin, norte, sur, p1, p2 = await base(cliente, db)
    r = await admin.post("/api/ventas", {"sede_id": norte["id"], "items": [{"producto_id": p2["id"], "cantidad": 1}]})
    assert r.status_code == 400 and r.json()["codigo"] == "precio_requerido"
    r = await admin.post("/api/ventas", {"sede_id": norte["id"], "items": [
        {"producto_id": p1["id"], "cantidad": 5}, {"producto_id": p2["id"], "cantidad": 101, "precio_unitario": 1}]})
    assert r.status_code == 409
    assert await existencias(admin, norte["id"], p1["id"]) == 50  # nada se descontó
    assert (await admin.get("/api/ventas")).json()["total"] == 0
    # el consecutivo no se consume en una venta fallida
    ok = (await admin.post("/api/ventas", {"sede_id": norte["id"], "items": [{"producto_id": p1["id"], "cantidad": 1}]})).json()
    assert ok["numero"] == 1


async def test_anular_venta_reintegra_y_no_se_repite(cliente, db):
    admin, norte, sur, p1, p2 = await base(cliente, db)
    v = (await admin.post("/api/ventas", {"sede_id": norte["id"], "items": [{"producto_id": p1["id"], "cantidad": 7}]})).json()
    assert await existencias(admin, norte["id"], p1["id"]) == 43
    assert (await admin.post(f"/api/ventas/{v['id']}/anular", {"motivo": "x"})).status_code == 422  # el motivo es obligatorio
    r = await admin.post(f"/api/ventas/{v['id']}/anular", {"motivo": "Cliente devolvió todo"})
    assert r.status_code == 200 and r.json()["estado"] == "anulada" and r.json()["motivo_anulacion"] == "Cliente devolvió todo"
    assert await existencias(admin, norte["id"], p1["id"]) == 50
    r = await admin.post(f"/api/ventas/{v['id']}/anular", {"motivo": "Otra vez no"})
    assert r.status_code == 409 and r.json()["codigo"] == "venta_ya_anulada"
    assert await existencias(admin, norte["id"], p1["id"]) == 50
    tipos = [m["tipo"] for m in (await admin.get(f"/api/movimientos?producto_id={p1['id']}")).json()["items"]]
    assert tipos == ["anulacion_venta", "venta", "entrada"]  # el historial se conserva
    # La venta anulada sigue existiendo y se puede filtrar
    assert (await admin.get("/api/ventas?estado=anulada")).json()["total"] == 1


async def test_plazo_de_anulacion(cliente, db):
    from datetime import timedelta

    from app.core.tiempo import ahora_utc

    admin, norte, sur, p1, p2 = await base(cliente, db)
    v = (await admin.post("/api/ventas", {"sede_id": norte["id"], "items": [{"producto_id": p1["id"], "cantidad": 1}]})).json()
    venta = await db.get(Venta, v["id"])
    venta.fecha = ahora_utc() - timedelta(days=45)
    await db.commit()
    r = await admin.post(f"/api/ventas/{v['id']}/anular", {"motivo": "Demasiado tarde"})
    assert r.status_code == 400 and r.json()["codigo"] == "plazo_de_anulacion_vencido"
    assert (await admin.get(f"/api/ventas/{v['id']}")).json()["puede_anularse"] is False
    await admin.put("/api/empresa/parametros", {"dias_max_anulacion": 60})
    assert (await admin.post(f"/api/ventas/{v['id']}/anular", {"motivo": "Ahora sí hay plazo"})).status_code == 200


async def test_usuario_de_sede_solo_vende_y_ve_su_sede(cliente, db):
    admin, norte, sur, p1, p2 = await base(cliente, db)
    op_sur = await crear_usuario(admin, "usuario_inventario", "sur@andina.com", sur["id"])
    r = await op_sur.post("/api/ventas", {"sede_id": norte["id"], "items": [{"producto_id": p1["id"], "cantidad": 1}]})
    assert r.status_code == 403
    v = (await admin.post("/api/ventas", {"sede_id": norte["id"], "items": [{"producto_id": p1["id"], "cantidad": 1}]})).json()
    assert (await op_sur.get(f"/api/ventas/{v['id']}")).status_code == 403
    assert (await op_sur.get("/api/ventas")).json()["total"] == 0
    assert (await op_sur.post(f"/api/ventas/{v['id']}/anular", {"motivo": "No me corresponde"})).status_code == 403


# ----------------------------------------------------------------------------- traslados


async def test_traslado_flujo_completo_y_atomico(cliente, db):
    admin, norte, sur, p1, p2 = await base(cliente, db)
    r = await admin.post("/api/traslados", {"sede_origen_id": norte["id"], "sede_destino_id": sur["id"],
                                           "items": [{"producto_id": p1["id"], "cantidad": 20}, {"producto_id": p2["id"], "cantidad": 30}]})
    assert r.status_code == 201, r.text
    t = r.json()
    assert t["estado"] == "solicitado" and t["numero"] == 1
    assert {i["producto"]["codigo"]: i["existencias_origen"] for i in t["items"]} == {"V-1": 50, "V-2": 100}
    # Pedir el traslado NO mueve existencias
    assert await existencias(admin, norte["id"], p1["id"]) == 50
    assert (await admin.post(f"/api/traslados/{t['id']}/confirmar")).status_code == 409  # primero se aprueba

    assert (await admin.post(f"/api/traslados/{t['id']}/aprobar")).json()["estado"] == "aprobado"
    assert await existencias(admin, norte["id"], p1["id"]) == 50  # aprobar tampoco mueve
    r = await admin.post(f"/api/traslados/{t['id']}/confirmar")
    assert r.status_code == 200 and r.json()["estado"] == "confirmado"
    assert await existencias(admin, norte["id"], p1["id"]) == 30 and await existencias(admin, sur["id"], p1["id"]) == 20
    assert await existencias(admin, norte["id"], p2["id"]) == 70 and await existencias(admin, sur["id"], p2["id"]) == 30
    # Cada línea genera salida en origen y entrada en destino con la sede contraparte
    movs = (await admin.get(f"/api/movimientos?producto_id={p1['id']}&sede_id={sur['id']}")).json()["items"]
    assert movs[0]["tipo"] == "traslado_entrada" and movs[0]["sede_contraparte"]["id"] == norte["id"] and movs[0]["traslado_numero"] == 1
    # Confirmar dos veces no duplica
    assert (await admin.post(f"/api/traslados/{t['id']}/confirmar")).status_code == 409
    assert await existencias(admin, sur["id"], p1["id"]) == 20
    # El total de la empresa no cambia: el consolidado se conserva
    cons = {f["producto"]["codigo"]: f["total"] for f in (await admin.get("/api/inventario/consolidado")).json()["items"]}
    assert cons == {"V-1": 50, "V-2": 100}


async def test_traslado_sin_stock_suficiente_no_mueve_nada(cliente, db):
    admin, norte, sur, p1, p2 = await base(cliente, db)
    t = (await admin.post("/api/traslados", {"sede_origen_id": norte["id"], "sede_destino_id": sur["id"],
                                            "items": [{"producto_id": p1["id"], "cantidad": 10}, {"producto_id": p2["id"], "cantidad": 500}]})).json()
    await admin.post(f"/api/traslados/{t['id']}/aprobar")
    r = await admin.post(f"/api/traslados/{t['id']}/confirmar")
    assert r.status_code == 409 and r.json()["codigo"] == "existencias_insuficientes"
    assert await existencias(admin, norte["id"], p1["id"]) == 50 and await existencias(admin, sur["id"], p1["id"]) == 0
    assert (await admin.get(f"/api/traslados/{t['id']}")).json()["estado"] == "aprobado"  # sigue pendiente de confirmar
    # Tras reabastecer el origen, se puede confirmar
    await entrada(admin, norte["id"], {p2["id"]: 400})
    assert (await admin.post(f"/api/traslados/{t['id']}/confirmar")).status_code == 200


async def test_traslado_rechazar_cancelar_y_validaciones(cliente, db):
    admin, norte, sur, p1, p2 = await base(cliente, db)
    cuerpo = {"sede_origen_id": norte["id"], "sede_destino_id": sur["id"], "items": [{"producto_id": p1["id"], "cantidad": 1}]}
    assert (await admin.post("/api/traslados", {**cuerpo, "sede_destino_id": norte["id"]})).status_code == 422
    t1 = (await admin.post("/api/traslados", cuerpo)).json()
    r = await admin.post(f"/api/traslados/{t1['id']}/rechazar", {"motivo": "No hay transporte esta semana"})
    assert r.json()["estado"] == "rechazado" and r.json()["motivo_cierre"] == "No hay transporte esta semana"
    assert (await admin.post(f"/api/traslados/{t1['id']}/aprobar")).status_code == 409
    t2 = (await admin.post("/api/traslados", cuerpo)).json()
    assert (await admin.post(f"/api/traslados/{t2['id']}/cancelar", {"motivo": "Ya no hace falta"})).json()["estado"] == "cancelado"
    assert (await admin.get("/api/traslados?estado=cancelado")).json()["total"] == 1
    # Una sede inhabilitada no puede ser destino
    await admin.patch(f"/api/sedes/{sur['id']}/estado", {"activa": False})
    assert (await admin.post("/api/traslados", cuerpo)).status_code == 400


async def test_traslado_permisos_por_sede(cliente, db):
    admin, norte, sur, p1, p2 = await base(cliente, db)
    enc_norte = await crear_usuario(admin, "encargado_sede", "encn@andina.com", norte["id"])
    enc_sur = await crear_usuario(admin, "encargado_sede", "encs@andina.com", sur["id"])
    tercera = await crear_sede(admin, "Centro")
    otro = await crear_usuario(admin, "encargado_sede", "encc@andina.com", tercera["id"])

    cuerpo = {"sede_origen_id": norte["id"], "sede_destino_id": sur["id"], "items": [{"producto_id": p1["id"], "cantidad": 5}]}
    assert (await otro.post("/api/traslados", cuerpo)).status_code == 403  # no es su sede de origen ni de destino
    t = (await enc_sur.post("/api/traslados", cuerpo)).json()  # el destino pide la mercancía
    assert t["estado"] == "solicitado"
    assert (await otro.get(f"/api/traslados/{t['id']}")).status_code == 404
    assert (await otro.get("/api/traslados")).json()["total"] == 0
    assert (await enc_sur.post(f"/api/traslados/{t['id']}/aprobar")).status_code == 403  # aprueba el ORIGEN
    assert (await enc_norte.post(f"/api/traslados/{t['id']}/aprobar")).status_code == 200
    assert (await enc_norte.post(f"/api/traslados/{t['id']}/confirmar")).status_code == 403  # confirma el DESTINO
    r = await enc_sur.post(f"/api/traslados/{t['id']}/confirmar")
    assert r.status_code == 200
    assert await existencias(enc_sur, sur["id"], p1["id"]) == 5
    det = (await enc_norte.get(f"/api/traslados/{t['id']}")).json()
    assert det["acciones"] == [] and det["aprobado_por_nombre"] and det["confirmado_por_nombre"]


async def test_no_se_inhabilita_sede_ni_producto_con_traslado_pendiente(cliente, db):
    admin, norte, sur, p1, p2 = await base(cliente, db)
    await admin.post("/api/traslados", {"sede_origen_id": norte["id"], "sede_destino_id": sur["id"], "items": [{"producto_id": p1["id"], "cantidad": 1}]})
    assert (await admin.patch(f"/api/sedes/{sur['id']}/estado", {"activa": False})).status_code == 409
    r = await admin.patch(f"/api/productos/{p1['id']}/estado", {"activo": False})
    assert r.status_code == 409 and r.json()["codigo"] == "producto_en_traslados"


async def test_invariantes_de_inventario_tras_operar(cliente, db):
    admin, norte, sur, p1, p2 = await base(cliente, db)
    await admin.post("/api/ventas", {"sede_id": norte["id"], "items": [{"producto_id": p1["id"], "cantidad": 9}]})
    t = (await admin.post("/api/traslados", {"sede_origen_id": norte["id"], "sede_destino_id": sur["id"], "items": [{"producto_id": p1["id"], "cantidad": 11}]})).json()
    await admin.post(f"/api/traslados/{t['id']}/aprobar")
    await admin.post(f"/api/traslados/{t['id']}/confirmar")
    await admin.post("/api/inventario/ajustes", {"sede_id": sur["id"], "producto_id": p1["id"], "cantidad_real": 10, "observacion": "Se encontró una unidad rota"})
    filas = (await db.execute(select(InventarioSede.sede_id, InventarioSede.producto_id, InventarioSede.cantidad))).all()
    for sede_id, producto_id, cantidad in filas:
        suma = await db.scalar(select(func.sum(Movimiento.delta)).where(Movimiento.sede_id == sede_id, Movimiento.producto_id == producto_id))
        assert suma == cantidad and cantidad >= 0
    # saldo_anterior + delta = saldo_posterior en cada movimiento
    for m in (await db.scalars(select(Movimiento))).all():
        assert m.saldo_anterior + m.delta == m.saldo_posterior


async def test_campos_opcionales_aceptan_null_explicito(cliente, db):
    """El navegador envía ``null`` en los campos vacíos: no debe fallar ni responder 500."""
    admin, norte, sur, p1, p2 = await base(cliente, db)
    r = await admin.post("/api/ventas", {"sede_id": norte["id"], "observacion": None, "items": [{"producto_id": p1["id"], "cantidad": 1}]})
    assert r.status_code == 201, r.text
    r = await admin.post("/api/traslados", {"sede_origen_id": norte["id"], "sede_destino_id": sur["id"], "observacion": None,
                                            "items": [{"producto_id": p1["id"], "cantidad": 1}]})
    assert r.status_code == 201, r.text
    r = await admin.post("/api/ventas", {"sede_id": norte["id"], "observacion": "   ", "items": [{"producto_id": p1["id"], "cantidad": 1}]})
    assert r.status_code == 201 and r.json()["observacion"] is None  # el texto vacío se normaliza a null
