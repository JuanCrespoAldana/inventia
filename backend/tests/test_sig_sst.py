"""SIG · SST: pausas activas automáticas y su administración."""

import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import func, select, update

from app.model.sst import SstPausa
from app.util.tiempo import ahora_utc
from tests.ayuda import crear_empresa, crear_sede, crear_usuario


async def escenario(cliente, db):
    admin = await crear_empresa(db, cliente)
    norte = await crear_sede(admin, "Norte")
    ana = await crear_usuario(admin, "usuario_inventario", "ana@andina.com", norte["id"], nombre="Ana Operaria")
    luis = await crear_usuario(admin, "encargado_sede", "luis@andina.com", norte["id"], nombre="Luis Encargado")
    return admin, norte, ana, luis


async def envejecer_pausas(db, minutos: int):
    """Simula que las pausas ya existentes se mostraron hace ``minutos`` minutos."""
    await db.execute(update(SstPausa).values(mostrada_en=ahora_utc() - timedelta(minutes=minutos)))
    await db.commit()


async def cuantas(db) -> int:
    return int(await db.scalar(select(func.count()).select_from(SstPausa)))


async def test_configuracion_inicial_y_contenido_por_defecto(cliente, db):
    admin, norte, ana, luis = await escenario(cliente, db)
    cfg = (await ana.get("/api/sig/sst/configuracion")).json()
    assert cfg == {"pausas_activas": True, "intervalo_minutos": 60}
    acts = (await ana.get("/api/sig/sst/actividades")).json()
    assert len(acts) == 7
    ojos = next(a for a in acts if a["area"] == "ojos")
    assert ojos["duracion_segundos"] == 60 and len(ojos["pasos"]) >= 3 and len(ojos["consejos"]) >= 1 and ojos["mensaje"]
    assert {a["area"] for a in acts} >= {"cuello", "hombros", "espalda", "manos_munecas", "ojos", "piernas", "respiracion"}
    # Pedir la configuración dos veces no duplica el contenido.
    await admin.get("/api/sig/sst/configuracion")
    assert len((await admin.get("/api/sig/sst/actividades")).json()) == 7


async def test_pausa_aparece_para_operativos_y_no_para_administracion(cliente, db):
    admin, norte, ana, luis = await escenario(cliente, db)
    ea = (await ana.get("/api/sig/sst/pausa/estado")).json()
    assert ea["aplica"] is True and ea["activo"] is True and ea["intervalo_minutos"] == 60 and ea["pendiente"] is None
    assert (await luis.get("/api/sig/sst/pausa/estado")).json()["aplica"] is True  # el encargado también

    r = (await ana.post("/api/sig/sst/pausa/iniciar")).json()
    assert r["mostrar"] is True and r["pausa"]["actividad"]["pasos"] and r["pausa"]["actividad"]["duracion_segundos"] >= 10

    # La administración ve el contenido pero no recibe pausas automáticas, ni queda registro suyo.
    assert (await admin.get("/api/sig/sst/pausa/estado")).json()["aplica"] is False
    r = (await admin.post("/api/sig/sst/pausa/iniciar")).json()
    assert r == {"mostrar": False, "pausa": None, "proxima_en": None, "motivo": "excluido"}
    assert len((await admin.get("/api/sig/sst/actividades")).json()) == 7
    assert await cuantas(db) == 1


async def test_no_se_repiten_ni_se_solapan_pausas(cliente, db):
    admin, norte, ana, luis = await escenario(cliente, db)
    a = (await ana.post("/api/sig/sst/pausa/iniciar")).json()
    b = (await ana.post("/api/sig/sst/pausa/iniciar")).json()  # segunda pestaña o recarga: la MISMA pausa
    assert a["pausa"]["id"] == b["pausa"]["id"] and await cuantas(db) == 1
    assert (await ana.get("/api/sig/sst/pausa/estado")).json()["pendiente"]["id"] == a["pausa"]["id"]  # recargar no crea otra

    r = (await ana.post(f"/api/sig/sst/pausa/{a['pausa']['id']}/cerrar", {"resultado": "realizada", "duracion_segundos": 58})).json()
    assert r["estado"] == "realizada" and r["duracion_segundos"] == 58 and r["cerrada_en"]
    # Cerrar de nuevo es inofensivo y no cambia el primer resultado.
    r = (await ana.post(f"/api/sig/sst/pausa/{a['pausa']['id']}/cerrar", {"resultado": "omitida"})).json()
    assert r["estado"] == "realizada"

    # Recién terminada: todavía no toca otra.
    c = (await ana.post("/api/sig/sst/pausa/iniciar")).json()
    assert c["mostrar"] is False and c["motivo"] == "muy_pronto" and c["proxima_en"] and await cuantas(db) == 1
    # Pasado el intervalo sí, y rota a otra actividad.
    await envejecer_pausas(db, 61)
    d = (await ana.post("/api/sig/sst/pausa/iniciar")).json()
    assert d["mostrar"] is True and d["pausa"]["id"] != a["pausa"]["id"]
    assert d["pausa"]["actividad"]["id"] != a["pausa"]["actividad"]["id"] and await cuantas(db) == 2
    # Las pausas de una persona no las puede cerrar otra.
    assert (await luis.post(f"/api/sig/sst/pausa/{d['pausa']['id']}/cerrar", {"resultado": "omitida"})).status_code == 404


async def test_pausa_olvidada_se_da_por_omitida(cliente, db):
    admin, norte, ana, luis = await escenario(cliente, db)
    a = (await ana.post("/api/sig/sst/pausa/iniciar")).json()
    await envejecer_pausas(db, 65)  # quedó abierta: pasaron más de 30 minutos y más que el intervalo
    estado = (await ana.get("/api/sig/sst/pausa/estado")).json()
    assert estado["pendiente"] is None
    historial = (await ana.get("/api/sig/sst/pausas")).json()["items"]
    assert [(p["id"], p["estado"]) for p in historial] == [(a["pausa"]["id"], "omitida")]
    assert (await ana.post("/api/sig/sst/pausa/iniciar")).json()["mostrar"] is True  # ya puede recibir la siguiente


async def test_administracion_configura_frecuencia_y_contenido(cliente, db):
    admin, norte, ana, luis = await escenario(cliente, db)
    assert (await ana.put("/api/sig/sst/configuracion", {"intervalo_minutos": 5})).status_code == 403
    assert (await admin.put("/api/sig/sst/configuracion", {"intervalo_minutos": 0})).status_code == 422
    assert (await admin.put("/api/sig/sst/configuracion", {"intervalo_minutos": 481})).status_code == 422
    assert (await admin.put("/api/sig/sst/configuracion", {})).status_code == 422
    assert (await admin.put("/api/sig/sst/configuracion", {"intervalo_minutos": 30})).json() == {"pausas_activas": True, "intervalo_minutos": 30}

    primera = (await ana.post("/api/sig/sst/pausa/iniciar")).json()
    await ana.post(f"/api/sig/sst/pausa/{primera['pausa']['id']}/cerrar", {"resultado": "realizada"})
    await envejecer_pausas(db, 20)
    assert (await ana.post("/api/sig/sst/pausa/iniciar")).json()["motivo"] == "muy_pronto"  # 20 min < 30
    await envejecer_pausas(db, 31)
    assert (await ana.post("/api/sig/sst/pausa/iniciar")).json()["mostrar"] is True  # el nuevo intervalo se respeta

    # Desactivar las pausas las detiene para todos sin borrar nada.
    await admin.put("/api/sig/sst/configuracion", {"pausas_activas": False})
    await envejecer_pausas(db, 600)
    r = (await luis.post("/api/sig/sst/pausa/iniciar")).json()
    assert r["mostrar"] is False and r["motivo"] == "desactivadas"
    assert (await luis.get("/api/sig/sst/pausa/estado")).json()["activo"] is False

    # Contenido: crear, editar, desactivar y eliminar; el personal operativo solo lo ve.
    nuevo = {"titulo": "Estiramiento de piernas", "area": "piernas", "mensaje": "Mueve las piernas un momento.",
             "instrucciones": "Levántate.\nCamina un minuto.", "duracion_segundos": 45, "recomendaciones": "Usa calzado cómodo.", "orden": 20}
    assert (await ana.post("/api/sig/sst/actividades", nuevo)).status_code == 403
    a = (await admin.post("/api/sig/sst/actividades", nuevo)).json()
    assert a["pasos"] == ["Levántate.", "Camina un minuto."] and a["consejos"] == ["Usa calzado cómodo."]
    assert (await admin.post("/api/sig/sst/actividades", {**nuevo, "duracion_segundos": 5})).status_code == 422
    e = (await admin.patch(f"/api/sig/sst/actividades/{a['id']}", {"duracion_segundos": 90, "activa": False})).json()
    assert e["duracion_segundos"] == 90 and e["activa"] is False
    assert len((await ana.get("/api/sig/sst/actividades")).json()) == 7   # las inactivas no se muestran al personal
    assert len((await admin.get("/api/sig/sst/actividades?todas=true")).json()) == 8
    assert len((await ana.get("/api/sig/sst/actividades?todas=true")).json()) == 7  # sin permiso, el parámetro no cambia nada
    assert (await admin.patch(f"/api/sig/sst/actividades/{a['id']}", {})).status_code == 422
    assert (await admin.delete(f"/api/sig/sst/actividades/{a['id']}")).status_code == 204
    assert (await admin.delete(f"/api/sig/sst/actividades/{a['id']}")).status_code == 404


async def test_pausa_sin_actividades_activas(cliente, db):
    admin, norte, ana, luis = await escenario(cliente, db)
    for a in (await admin.get("/api/sig/sst/actividades")).json():
        await admin.patch(f"/api/sig/sst/actividades/{a['id']}", {"activa": False})
    r = (await ana.post("/api/sig/sst/pausa/iniciar")).json()
    assert r["mostrar"] is False and r["motivo"] == "sin_actividades" and await cuantas(db) == 0


async def test_registro_y_cumplimiento(cliente, db):
    admin, norte, ana, luis = await escenario(cliente, db)
    # Ana realiza una, Luis omite una y otra queda sin responder.
    p = (await ana.post("/api/sig/sst/pausa/iniciar")).json()["pausa"]
    await ana.post(f"/api/sig/sst/pausa/{p['id']}/cerrar", {"resultado": "realizada", "duracion_segundos": 60})
    q = (await luis.post("/api/sig/sst/pausa/iniciar")).json()["pausa"]
    await luis.post(f"/api/sig/sst/pausa/{q['id']}/cerrar", {"resultado": "omitida"})
    await envejecer_pausas(db, 61)
    await luis.post("/api/sig/sst/pausa/iniciar")

    mias = (await ana.get("/api/sig/sst/pausas")).json()
    assert mias["total"] == 1 and mias["items"][0]["estado"] == "realizada" and mias["items"][0]["actividad_titulo"]
    assert (await ana.get("/api/sig/sst/pausas?ambito=todas")).status_code == 403
    assert (await ana.get("/api/sig/sst/resumen")).status_code == 403
    todas = (await admin.get("/api/sig/sst/pausas?ambito=todas")).json()
    assert todas["total"] == 3 and {x["usuario_nombre"] for x in todas["items"]} == {"Ana Operaria", "Luis Encargado"}
    assert (await admin.get(f"/api/sig/sst/pausas?ambito=todas&usuario_id={luis.usuario['id']}&estado=omitida")).json()["total"] == 1
    r = (await admin.get("/api/sig/sst/resumen?dias=7")).json()
    assert (r["mostradas"], r["realizadas"], r["omitidas"], r["sin_responder"]) == (3, 1, 1, 1) and r["cumplimiento"] == 33.3
    assert {u["usuario_nombre"]: (u["mostradas"], u["realizadas"]) for u in r["por_usuario"]} == {"Ana Operaria": (1, 1), "Luis Encargado": (2, 0)}


@pytest.mark.postgres
async def test_peticiones_simultaneas_no_duplican_la_pausa(cliente, db):
    admin, norte, ana, luis = await escenario(cliente, db)
    respuestas = await asyncio.gather(*[ana.post("/api/sig/sst/pausa/iniciar") for _ in range(8)])
    assert all(r.status_code == 200 for r in respuestas)
    ids = {r.json()["pausa"]["id"] for r in respuestas if r.json()["mostrar"]}
    assert len(ids) == 1 and await cuantas(db) == 1
