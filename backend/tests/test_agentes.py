"""Agentes de IA (RNF-049): autenticación por llave, alcances, límite por sede, auditoría y solo lectura."""

from datetime import timedelta

from sqlalchemy import select, update

from app.core.tiempo import ahora_utc
from app.models.auditoria import ApiKey, Auditoria
from tests.ayuda import (
    crear_categoria,
    crear_empresa,
    crear_producto,
    crear_sede,
    crear_usuario,
    entrada,
)
from tests.test_prediccion import ejecutar, escenario


async def crear_llave(admin, *, alcances=("inventario:leer",), sede_id=None, nombre="Agente de compras", dias=30):
    r = await admin.post("/api/integraciones/llaves", {"nombre": nombre, "alcances": list(alcances), "sede_id": sede_id, "dias_vigencia": dias})
    assert r.status_code == 201, r.text
    return r.json()


def con_llave(cliente, llave: str):
    async def get(ruta):
        return await cliente.get(ruta, headers={"X-API-Key": llave})

    return get


async def test_la_llave_se_muestra_una_vez_y_solo_se_guarda_su_huella(cliente, db):
    admin, *_ = await escenario(cliente, db)
    k = await crear_llave(admin)
    assert k["llave"].startswith("inv_") and k["llave"].startswith(k["prefijo"]) and len(k["llave"]) > 40
    fila = await db.scalar(select(ApiKey))
    assert fila.key_hash != k["llave"] and len(fila.key_hash) == 64 and k["llave"] not in str(fila.__dict__)

    lista = (await admin.get("/api/integraciones/llaves")).json()
    assert lista[0]["prefijo"] == k["prefijo"] and "llave" not in lista[0] and "key_hash" not in lista[0]
    # la auditoría registra la creación sin incluir el secreto
    ops = (await db.scalars(select(Auditoria).where(Auditoria.modulo == "agentes"))).all()
    assert [o.accion for o in ops] == ["crear_llave"] and k["llave"] not in str(ops[0].detalle)


async def test_solo_quien_tiene_el_permiso_administra_llaves(cliente, db):
    admin, *_ = await escenario(cliente, db)
    for rol, correo in (("gerente", "g@andina.com"), ("analista_compras", "a@andina.com")):
        s = await crear_usuario(admin, rol, correo)
        assert (await s.get("/api/integraciones/llaves")).status_code == 403
        assert (await s.post("/api/integraciones/llaves", {"nombre": "Agente", "alcances": ["inventario:leer"]})).status_code == 403
    assert (await cliente.get("/api/integraciones/llaves")).status_code == 401


async def test_validaciones_al_crear_llaves(cliente, db):
    admin, *_ = await escenario(cliente, db)
    r = await admin.post("/api/integraciones/llaves", {"nombre": "Agente", "alcances": ["usuarios:escribir"]})
    assert r.status_code == 400 and r.json()["codigo"] == "alcance_desconocido"
    r = await admin.post("/api/integraciones/llaves", {"nombre": "Agente", "alcances": []})
    assert r.status_code == 422
    otra = await crear_empresa(db, cliente, "Otra", "admin@otra.com", "8")
    sede_ajena = await crear_sede(otra, "Sede ajena")
    r = await admin.post("/api/integraciones/llaves", {"nombre": "Agente", "alcances": ["inventario:leer"], "sede_id": sede_ajena["id"]})
    assert r.status_code == 404


async def test_un_agente_consulta_lo_autorizado_y_nada_mas(cliente, db):
    admin, norte, sur, p1, *_ = await escenario(cliente, db)
    await ejecutar(admin)
    k = await crear_llave(admin, alcances=["inventario:leer", "alertas:leer"])
    get = con_llave(cliente, k["llave"])

    yo = (await get("/api/agentes/yo")).json()
    assert yo["alcances"] == ["alertas:leer", "inventario:leer"] and yo["solo_lectura"] is True
    inv = (await get("/api/agentes/inventario?tamano=100")).json()
    assert inv["total"] == 4 and {f["sede"] for f in inv["items"]} == {"Norte", "Sur"}
    sur_arroz = next(f for f in inv["items"] if f["sede"] == "Sur" and f["codigo"] == "A-1")
    assert sur_arroz["cantidad"] == 8
    alertas = (await get("/api/agentes/alertas")).json()
    assert alertas["total"] >= 1

    # Lo que no está en sus alcances se rechaza y queda en auditoría
    for ruta in ("/api/agentes/predicciones", "/api/agentes/recomendaciones"):
        r = await get(ruta)
        assert r.status_code == 403 and r.json()["codigo"] == "alcance_no_autorizado"
    rechazos = (await db.scalars(select(Auditoria).where(Auditoria.accion == "acceso_denegado"))).all()
    assert len(rechazos) == 2 and all(r.resultado == "fallido" and k["llave"] not in str(r.detalle) for r in rechazos)
    assert (await db.scalar(select(ApiKey.ultimo_uso_en))) is not None


async def test_el_agente_con_alcance_de_predicciones_ve_estimaciones_marcadas(cliente, db):
    admin, *_ = await escenario(cliente, db)
    await ejecutar(admin)
    await admin.post("/api/recomendaciones/generar")
    k = await crear_llave(admin, alcances=["predicciones:leer", "recomendaciones:leer"])
    get = con_llave(cliente, k["llave"])
    pred = (await get("/api/agentes/predicciones")).json()
    assert pred["total"] == 2 and all(p["es_estimacion"] for p in pred["items"]) and pred["ejecucion_id"]
    rec = (await get("/api/agentes/recomendaciones")).json()
    assert rec["total"] == 1 and rec["items"][0]["requiere_aprobacion_humana"] is True


async def test_llaves_invalidas_vencidas_o_revocadas_reciben_401(cliente, db):
    admin, *_ = await escenario(cliente, db)
    k = await crear_llave(admin)
    sin = await cliente.get("/api/agentes/inventario")
    falsa = await cliente.get("/api/agentes/inventario", headers={"X-API-Key": k["prefijo"] + "_" + "x" * 43})
    ajena = await cliente.get("/api/agentes/inventario", headers={"X-API-Key": "Bearer abc"})
    assert (sin.status_code, falsa.status_code, ajena.status_code) == (401, 401, 401)
    assert falsa.json()["codigo"] == sin.json()["codigo"] == "llave_invalida"  # no revela si el prefijo existe
    intentos = (await db.scalars(select(Auditoria).where(Auditoria.accion == "acceso_rechazado"))).all()
    assert len(intentos) == 1 and k["llave"] not in str(intentos[0].detalle)  # solo el intento con prefijo conocido

    assert (await con_llave(cliente, k["llave"])("/api/agentes/yo")).status_code == 200
    assert (await admin.post(f"/api/integraciones/llaves/{k['id']}/revocar")).json()["activa"] is False
    assert (await con_llave(cliente, k["llave"])("/api/agentes/yo")).status_code == 401

    k2 = await crear_llave(admin, nombre="Otra")
    await db.execute(update(ApiKey).where(ApiKey.id == k2["id"]).values(expira_en=ahora_utc() - timedelta(minutes=1)))
    await db.commit()
    assert (await con_llave(cliente, k2["llave"])("/api/agentes/yo")).status_code == 401


async def test_una_llave_limitada_a_una_sede_no_ve_las_demas(cliente, db):
    admin, norte, sur, *_ = await escenario(cliente, db)
    k = await crear_llave(admin, sede_id=sur["id"])
    get = con_llave(cliente, k["llave"])
    inv = (await get("/api/agentes/inventario")).json()
    assert {f["sede"] for f in inv["items"]} == {"Sur"}
    assert (await get(f"/api/agentes/inventario?sede_id={sur['id']}")).status_code == 200
    r = await get(f"/api/agentes/inventario?sede_id={norte['id']}")
    assert r.status_code == 403 and r.json()["codigo"] == "sede_no_autorizada"


async def test_una_llave_nunca_ve_datos_de_otra_empresa(cliente, db):
    admin_a, *_ = await escenario(cliente, db)
    admin_b = await crear_empresa(db, cliente, "Otra", "admin@otra.com", "9")
    sede = await crear_sede(admin_b, "Unica B")
    cat = await crear_categoria(admin_b)
    p = await crear_producto(admin_b, cat["id"], "B-1", "Producto de B")
    await entrada(admin_b, sede["id"], {p["id"]: 7})
    k = await crear_llave(admin_b)
    inv = (await con_llave(cliente, k["llave"])("/api/agentes/inventario")).json()
    assert [f["codigo"] for f in inv["items"]] == ["B-1"]  # nada de A-1, A-2, A-3
    # y una llave de A no puede administrarse desde B
    ka = await crear_llave(admin_a)
    assert (await admin_b.post(f"/api/integraciones/llaves/{ka['id']}/revocar")).status_code == 404
    assert [x["id"] for x in (await admin_b.get("/api/integraciones/llaves")).json()] == [k["id"]]


async def test_los_agentes_son_de_solo_lectura_y_la_llave_no_sirve_en_la_api_normal(cliente, db):
    admin, *_ = await escenario(cliente, db)
    k = await crear_llave(admin, alcances=["inventario:leer"])
    cab = {"X-API-Key": k["llave"]}
    for metodo in (cliente.post, cliente.put, cliente.patch, cliente.delete):
        r = await metodo("/api/agentes/inventario", headers=cab)
        assert r.status_code == 405
    assert (await cliente.get("/api/inventario?sede_id=1", headers=cab)).status_code == 401
    assert (await cliente.get("/api/inventario?sede_id=1", headers={"Authorization": f"Bearer {k['llave']}"})).status_code == 401
    # y un token de usuario no sirve como llave de agente
    assert (await cliente.get("/api/agentes/yo", headers={"X-API-Key": admin.token})).status_code == 401
