"""Entradas de mercancía (RF-017): cada recepción queda numerada y se consulta, sin poder editarse ni borrarse.

La entrada la crea ``POST /api/inventario/entradas`` junto con sus movimientos. Aquí se comprueba lo que queda
consultable (número, sede, fecha, motivo, responsable y, por línea, cantidad y saldo posterior), los filtros del
listado y el alcance por sede y por empresa. Estas pruebas conservan lo que de la consulta de entradas probaba el SIG;
al retirar ese módulo en la versión 1.2.0 las observaciones y las no conformidades salieron, la entrada no."""

from datetime import timedelta

from app.util.tiempo import hoy_local
from tests.ayuda import (
    crear_categoria,
    crear_empresa,
    crear_producto,
    crear_sede,
    crear_usuario,
    entrada,
)


async def escenario(cliente, db):
    admin = await crear_empresa(db, cliente)
    norte, sur = await crear_sede(admin, "Norte"), await crear_sede(admin, "Sur")
    cat = await crear_categoria(admin)
    casco = await crear_producto(admin, cat["id"], "ACC-001", "Casco certificado", precio_venta=250000)
    bateria = await crear_producto(admin, cat["id"], "BAT-001", "Batería 48V", precio_venta=900000)
    ana = await crear_usuario(admin, "usuario_inventario", "ana@andina.com", norte["id"], nombre="Ana Operaria")
    pedro = await crear_usuario(admin, "usuario_inventario", "pedro@andina.com", sur["id"], nombre="Pedro Sur")
    gerente = await crear_usuario(admin, "gerente", "gerente@andina.com", None, nombre="Gerente")
    return admin, norte, sur, casco, bateria, ana, pedro, gerente


async def test_cada_recepcion_queda_numerada_y_su_detalle_muestra_lo_recibido(cliente, db):
    admin, norte, sur, casco, bateria, ana, pedro, gerente = await escenario(cliente, db)
    res = await entrada(ana, norte["id"], {casco["id"]: 10, bateria["id"]: 4})
    assert res["entrada_numero"] == 1 and res["entrada_id"]
    assert {m["entrada_numero"] for m in res["movimientos"]} == {1}

    d = (await ana.get(f"/api/inventario/entradas/{res['entrada_id']}")).json()
    assert d["numero"] == 1 and d["unidades"] == 14 and d["lineas"] == 2 and d["sede"]["id"] == norte["id"]
    assert d["usuario_nombre"] == "Ana Operaria" and d["motivo"] == "compra"
    assert sorted((linea["producto"]["codigo"], linea["cantidad"], linea["saldo_posterior"]) for linea in d["detalle_lineas"]) == [
        ("ACC-001", 10, 10), ("BAT-001", 4, 4),
    ]
    assert not {"observaciones", "historial_observaciones"} & d.keys()  # retirado con el SIG (versión 1.2.0)

    # Reponer el mismo producto crea OTRA entrada con el siguiente número; la primera no cambia y el saldo se acumula.
    segunda = await entrada(ana, norte["id"], {casco["id"]: 5})
    assert segunda["entrada_numero"] == 2 and segunda["entrada_id"] != res["entrada_id"]
    d2 = (await ana.get(f"/api/inventario/entradas/{segunda['entrada_id']}")).json()
    assert [(linea["cantidad"], linea["saldo_posterior"]) for linea in d2["detalle_lineas"]] == [(5, 15)]
    assert (await ana.get(f"/api/inventario/entradas/{res['entrada_id']}")).json() == d

    # La entrada no se edita ni se borra (RF-017): la API no ofrece esas operaciones.
    ruta = f"/api/inventario/entradas/{res['entrada_id']}"
    assert (await admin.put(ruta, {"motivo": "ajuste"})).status_code == 405
    assert (await admin.patch(ruta, {"motivo": "ajuste"})).status_code == 405
    assert (await admin.delete(ruta)).status_code == 405
    assert (await admin.post(f"{ruta}/observaciones", {"contenido": "Nota sobre la entrada"})).status_code == 404  # retirado


async def test_el_listado_va_de_la_mas_reciente_a_la_mas_antigua_y_filtra(cliente, db):
    admin, norte, sur, casco, bateria, ana, pedro, gerente = await escenario(cliente, db)
    await entrada(ana, norte["id"], {casco["id"]: 10})
    await entrada(ana, norte["id"], {bateria["id"]: 4}, motivo="devolucion_cliente")
    await entrada(pedro, sur["id"], {casco["id"]: 7})

    def numeros(r):
        return [e["numero"] for e in r.json()["items"]]

    todas = await admin.get("/api/inventario/entradas")
    assert todas.status_code == 200 and todas.json()["total"] == 3 and numeros(todas) == [3, 2, 1]
    assert [(e["unidades"], e["lineas"]) for e in todas.json()["items"]] == [(7, 1), (4, 1), (10, 1)]
    assert numeros(await admin.get("/api/inventario/entradas?numero=2")) == [2]
    assert numeros(await admin.get(f"/api/inventario/entradas?sede_id={sur['id']}")) == [3]
    assert numeros(await admin.get(f"/api/inventario/entradas?sede_id={norte['id']}")) == [2, 1]

    hoy, manana, ayer = hoy_local(), hoy_local() + timedelta(days=1), hoy_local() - timedelta(days=1)
    assert numeros(await admin.get(f"/api/inventario/entradas?desde={hoy}&hasta={hoy}")) == [3, 2, 1]
    assert numeros(await admin.get(f"/api/inventario/entradas?desde={manana}")) == []
    assert numeros(await admin.get(f"/api/inventario/entradas?hasta={ayer}")) == []
    pagina = (await admin.get("/api/inventario/entradas?tamano=2&pagina=2")).json()
    assert pagina["total"] == 3 and [e["numero"] for e in pagina["items"]] == [1]
    assert (await admin.get("/api/inventario/entradas?numero=0")).status_code == 422


async def test_la_consulta_respeta_la_sede_la_empresa_y_el_permiso(cliente, db):
    admin, norte, sur, casco, bateria, ana, pedro, gerente = await escenario(cliente, db)
    e = await entrada(ana, norte["id"], {casco["id"]: 3})
    ruta = f"/api/inventario/entradas/{e['entrada_id']}"

    # Quien está limitado a otra sede no la ve en el listado ni en el detalle.
    assert (await pedro.get("/api/inventario/entradas")).json()["total"] == 0
    assert (await pedro.get(ruta)).status_code == 403
    assert (await ana.get(ruta)).status_code == 200
    # El gerente consulta todas las sedes, pero no registra entradas.
    assert (await gerente.get(ruta)).status_code == 200
    assert (await gerente.get("/api/inventario/entradas")).json()["total"] == 1
    r = await gerente.post("/api/inventario/entradas", {"sede_id": norte["id"], "motivo": "compra", "items": [{"producto_id": casco["id"], "cantidad": 1}]})
    assert r.status_code == 403
    assert (await admin.get("/api/inventario/entradas/9999")).status_code == 404

    # Otra empresa no ve las entradas de esta, ni siquiera conociendo su identificador.
    otra = await crear_empresa(db, cliente, nombre="Otra Empresa", correo="admin@otra.com", sufijo="2")
    assert (await otra.get(ruta)).status_code == 404
    assert (await otra.get("/api/inventario/entradas")).json()["total"] == 0
