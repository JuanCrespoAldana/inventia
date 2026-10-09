"""Concurrencia real contra PostgreSQL (se omite si no hay TEST_DATABASE_URL).

Demuestra que las existencias nunca quedan negativas, que no se cuentan dos veces las confirmaciones y que
los consecutivos no se repiten cuando varias personas operan al mismo tiempo (RNF-005, RNF-006)."""

import asyncio

import pytest
from sqlalchemy import func, select

from app.models.inventario import InventarioSede, Movimiento
from app.models.operaciones import Venta
from tests.ayuda import crear_categoria, crear_empresa, crear_producto, crear_sede, entrada, existencias

pytestmark = pytest.mark.postgres


async def preparar(cliente, db, stock=10):
    admin = await crear_empresa(db, cliente)
    norte, sur = await crear_sede(admin, "Norte"), await crear_sede(admin, "Sur")
    cat = await crear_categoria(admin)
    p = await crear_producto(admin, cat["id"], "C-1", "Producto concurrente", costo=10, precio_venta=20)
    await entrada(admin, norte["id"], {p["id"]: stock})
    return admin, norte, sur, p


async def test_salidas_simultaneas_nunca_dejan_stock_negativo(cliente, db):
    admin, norte, sur, p = await preparar(cliente, db, stock=10)
    cuerpo = {"sede_id": norte["id"], "motivo": "perdida", "items": [{"producto_id": p["id"], "cantidad": 1}]}
    respuestas = await asyncio.gather(*[admin.post("/api/inventario/salidas", cuerpo) for _ in range(30)])
    codigos = [r.status_code for r in respuestas]
    assert codigos.count(201) == 10 and codigos.count(409) == 20, codigos
    assert await existencias(admin, norte["id"], p["id"]) == 0
    suma = await db.scalar(select(func.sum(Movimiento.delta)).where(Movimiento.producto_id == p["id"]))
    assert suma == 0


async def test_ventas_simultaneas_consecutivos_unicos_y_sin_sobreventa(cliente, db):
    admin, norte, sur, p = await preparar(cliente, db, stock=12)
    cuerpo = {"sede_id": norte["id"], "items": [{"producto_id": p["id"], "cantidad": 2}]}
    respuestas = await asyncio.gather(*[admin.post("/api/ventas", cuerpo) for _ in range(15)])
    exitosas = [r for r in respuestas if r.status_code == 201]
    assert len(exitosas) == 6 and all(r.status_code == 409 for r in respuestas if r.status_code != 201)
    numeros = sorted(r.json()["numero"] for r in exitosas)
    assert numeros == [1, 2, 3, 4, 5, 6]  # sin huecos ni repetidos
    assert await existencias(admin, norte["id"], p["id"]) == 0
    assert await db.scalar(select(func.count()).select_from(Venta)) == 6


async def test_confirmacion_simultanea_de_un_traslado_mueve_una_sola_vez(cliente, db):
    admin, norte, sur, p = await preparar(cliente, db, stock=100)
    t = (await admin.post("/api/traslados", {"sede_origen_id": norte["id"], "sede_destino_id": sur["id"], "items": [{"producto_id": p["id"], "cantidad": 40}]})).json()
    await admin.post(f"/api/traslados/{t['id']}/aprobar")
    respuestas = await asyncio.gather(*[admin.post(f"/api/traslados/{t['id']}/confirmar") for _ in range(6)])
    codigos = sorted(r.status_code for r in respuestas)
    assert codigos == [200, 409, 409, 409, 409, 409], codigos
    assert await existencias(admin, norte["id"], p["id"]) == 60 and await existencias(admin, sur["id"], p["id"]) == 40


async def test_anulacion_simultanea_reintegra_una_sola_vez(cliente, db):
    admin, norte, sur, p = await preparar(cliente, db, stock=20)
    v = (await admin.post("/api/ventas", {"sede_id": norte["id"], "items": [{"producto_id": p["id"], "cantidad": 5}]})).json()
    respuestas = await asyncio.gather(*[admin.post(f"/api/ventas/{v['id']}/anular", {"motivo": "Anulación simultánea"}) for _ in range(5)])
    assert sorted(r.status_code for r in respuestas) == [200, 409, 409, 409, 409]
    assert await existencias(admin, norte["id"], p["id"]) == 20


async def test_traslados_cruzados_no_generan_interbloqueo(cliente, db):
    admin, norte, sur, p = await preparar(cliente, db, stock=100)
    await entrada(admin, sur["id"], {p["id"]: 100})
    ids = []
    for origen, destino in [(norte, sur), (sur, norte)] * 4:
        t = (await admin.post("/api/traslados", {"sede_origen_id": origen["id"], "sede_destino_id": destino["id"], "items": [{"producto_id": p["id"], "cantidad": 5}]})).json()
        await admin.post(f"/api/traslados/{t['id']}/aprobar")
        ids.append(t["id"])
    respuestas = await asyncio.wait_for(asyncio.gather(*[admin.post(f"/api/traslados/{i}/confirmar") for i in ids]), timeout=60)
    assert all(r.status_code == 200 for r in respuestas), [r.text for r in respuestas if r.status_code != 200]
    total = await db.scalar(select(func.sum(InventarioSede.cantidad)).where(InventarioSede.producto_id == p["id"]))
    assert total == 200  # lo que sale de una sede entra en la otra


async def test_alertas_no_se_duplican_con_movimientos_simultaneos(cliente, db):
    admin, norte, sur, p = await preparar(cliente, db, stock=50)
    await admin.put("/api/inventario/niveles", {"sede_id": norte["id"], "producto_id": p["id"], "stock_minimo": 40})
    cuerpo = {"sede_id": norte["id"], "motivo": "perdida", "items": [{"producto_id": p["id"], "cantidad": 1}]}
    respuestas = await asyncio.gather(*[admin.post("/api/inventario/salidas", cuerpo) for _ in range(12)])
    assert all(r.status_code == 201 for r in respuestas)
    activas = (await admin.get("/api/alertas")).json()
    assert activas["total"] == 1 and activas["items"][0]["tipo"] == "inventario_bajo"
