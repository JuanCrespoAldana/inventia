"""Recomendaciones de reabastecimiento y traslado: reglas, explicación, aprobación humana y alcance."""

import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import func, select, update

from app.core.tiempo import hoy_local
from app.models.operaciones import Traslado
from app.models.prediccion import EjecucionPrediccion, Recomendacion
from tests.ayuda import (
    crear_categoria,
    crear_empresa,
    crear_producto,
    crear_sede,
    crear_usuario,
    existencias,
    patron_semanal,
    sembrar_historial,
)
from tests.test_prediccion import ejecutar, escenario


async def generar(sesion):
    r = await sesion.post("/api/recomendaciones/generar")
    assert r.status_code == 201, r.text
    return r.json()


async def listar(sesion, query=""):
    r = await sesion.get(f"/api/recomendaciones?tamano=100{query}")
    assert r.status_code == 200, r.text
    return r.json()["items"]


async def una_sede_con_faltante(cliente, db, *, stock_final=8, maximo=None):
    admin = await crear_empresa(db, cliente, "Mono Sede", "admin@mono.com", "5")
    sede = await crear_sede(admin, "Unica")
    cat = await crear_categoria(admin)
    p = await crear_producto(admin, cat["id"], "M-1", "Harina", costo=1000, precio_venta=1800)
    await sembrar_historial(db, admin, sede["id"], p["id"], patron_semanal(semilla=9), stock_final=stock_final)
    if maximo:
        r = await admin.put("/api/inventario/niveles", {"sede_id": sede["id"], "producto_id": p["id"], "stock_minimo": 5, "stock_maximo": maximo})
        assert r.status_code == 200, r.text
    await ejecutar(admin)
    return admin, sede, p


async def test_no_se_generan_recomendaciones_sin_una_prediccion_vigente(cliente, db):
    admin, *_ = await escenario(cliente, db)
    r = await admin.post("/api/recomendaciones/generar")
    assert r.status_code == 400 and r.json()["codigo"] == "sin_prediccion_vigente"
    await ejecutar(admin)
    await db.execute(update(EjecucionPrediccion).values(fecha_corte=hoy_local() - timedelta(days=30)))
    await db.commit()
    r = await admin.post("/api/recomendaciones/generar")  # una predicción de hace 30 días no sirve
    assert r.status_code == 400 and r.json()["codigo"] == "sin_prediccion_vigente"


async def test_la_sede_sin_stock_recibe_un_traslado_de_la_que_tiene_excedente(cliente, db):
    admin, norte, sur, p1, *_ = await escenario(cliente, db)
    await ejecutar(admin)
    resumen = await generar(admin)
    assert resumen["traslados"] == 1 and resumen["generadas"] == 1

    rec = (await listar(admin))[0]
    assert rec["tipo"] == "traslado" and rec["estado"] == "pendiente" and rec["prioridad"] in ("critica", "alta")
    assert rec["sede"]["nombre"] == "Sur" and rec["sede_origen"]["nombre"] == "Norte" and rec["producto"]["codigo"] == "A-1"
    j = rec["justificacion"]
    assert 100 < rec["cantidad_sugerida"] <= j["necesidad"] and j["existencias"] == 8
    assert j["punto_reposicion"] > j["existencias"] and j["origen"]["existencias"] == 400
    assert j["origen"]["nivel_a_conservar"] > 0 and j["modelo"] and j["demanda_diaria"] > 0
    # Explicación legible: qué pasa, con qué datos y qué se propone
    assert all(t in rec["resumen"] for t in ("Arroz", "Sur", "Norte", "días", "trasladar"))
    assert rec["acciones"] == ["aprobar", "rechazar"]


async def test_aprobar_un_traslado_crea_la_solicitud_pero_no_mueve_existencias(cliente, db):
    admin, norte, sur, p1, *_ = await escenario(cliente, db)
    await ejecutar(admin)
    await generar(admin)
    rec = (await listar(admin))[0]
    antes = (await existencias(admin, norte["id"], p1["id"]), await existencias(admin, sur["id"], p1["id"]))

    r = await admin.post(f"/api/recomendaciones/{rec['id']}/aprobar", {"comentario": "Autorizado por gerencia"})
    assert r.status_code == 200, r.text
    aprobada = r.json()
    assert aprobada["estado"] == "ejecutada" and aprobada["traslado_numero"] == 1 and aprobada["revisada_por_nombre"]
    assert aprobada["comentario_revision"] == "Autorizado por gerencia" and aprobada["acciones"] == []

    # La recomendación NO ejecuta nada por sí sola (RNF-034): solo queda una solicitud pendiente de aprobar y confirmar.
    assert (await existencias(admin, norte["id"], p1["id"]), await existencias(admin, sur["id"], p1["id"])) == antes
    t = (await admin.get(f"/api/traslados/{aprobada['traslado_id']}")).json()
    assert t["estado"] == "solicitado" and t["recomendacion_id"] == rec["id"]
    assert t["items"][0]["cantidad"] == rec["cantidad_sugerida"]

    # El traslado sigue su flujo normal; solo al confirmar se mueve el inventario.
    assert (await admin.post(f"/api/traslados/{t['id']}/aprobar")).status_code == 200
    assert (await admin.post(f"/api/traslados/{t['id']}/confirmar")).status_code == 200
    assert await existencias(admin, norte["id"], p1["id"]) == antes[0] - rec["cantidad_sugerida"]
    assert await existencias(admin, sur["id"], p1["id"]) == antes[1] + rec["cantidad_sugerida"]


async def test_reabastecimiento_aprobada_ejecutada_y_estados_finales(cliente, db):
    admin, sede, p = await una_sede_con_faltante(cliente, db)
    resumen = await generar(admin)
    assert resumen["reabastecimientos"] == 1 and resumen["traslados"] == 0
    rec = (await listar(admin))[0]
    assert rec["tipo"] == "reabastecimiento" and rec["sede_origen"] is None and rec["cantidad_sugerida"] > 100
    assert "pedir" in rec["resumen"] and "plazo de entrega" in rec["resumen"]
    stock = await existencias(admin, sede["id"], p["id"])

    # No se puede marcar como realizada algo que no fue aprobado
    assert (await admin.post(f"/api/recomendaciones/{rec['id']}/ejecutar", {})).status_code == 409
    ap = (await admin.post(f"/api/recomendaciones/{rec['id']}/aprobar", {})).json()
    assert ap["estado"] == "aprobada" and ap["acciones"] == ["ejecutar"] and ap["traslado_id"] is None
    assert await existencias(admin, sede["id"], p["id"]) == stock  # aprobar no compra ni suma stock
    assert (await admin.post(f"/api/recomendaciones/{rec['id']}/aprobar", {})).status_code == 409
    assert (await admin.post(f"/api/recomendaciones/{rec['id']}/rechazar", {})).status_code == 409
    ej = (await admin.post(f"/api/recomendaciones/{rec['id']}/ejecutar", {"comentario": "Orden de compra 1450"})).json()
    assert ej["estado"] == "ejecutada" and ej["comentario_revision"] == "Orden de compra 1450"
    assert (await admin.post(f"/api/recomendaciones/{rec['id']}/ejecutar", {})).status_code == 409

    ops = (await admin.get("/api/auditoria?modulo=recomendaciones")).json()["items"]
    assert [o["accion"] for o in ops][:3] == ["ejecutar", "aprobar", "generar"]


async def test_rechazar_y_regenerar_conserva_historial(cliente, db):
    admin, sede, p = await una_sede_con_faltante(cliente, db)
    await generar(admin)
    primera = (await listar(admin))[0]
    rech = (await admin.post(f"/api/recomendaciones/{primera['id']}/rechazar", {"comentario": "Ya se pidió por teléfono"})).json()
    assert rech["estado"] == "rechazada" and rech["acciones"] == []

    segunda = await generar(admin)  # nada pendiente que reemplazar: la rechazada se conserva tal cual
    assert segunda["reemplazadas"] == 0
    tercera = await generar(admin)  # ahora sí había una pendiente
    assert tercera["reemplazadas"] == 1
    estados = sorted(r["estado"] for r in await listar(admin))
    assert estados == ["pendiente", "rechazada", "reemplazada"]
    assert len(await listar(admin, "&estado=pendiente")) == 1


async def test_una_recomendacion_aprobada_no_se_duplica_al_regenerar(cliente, db):
    admin, sede, p = await una_sede_con_faltante(cliente, db)
    await generar(admin)
    rec = (await listar(admin))[0]
    await admin.post(f"/api/recomendaciones/{rec['id']}/aprobar", {})
    r = await generar(admin)
    assert r["generadas"] == 0  # ya existe una compra aprobada para esa sede y producto


async def test_el_stock_maximo_limita_la_cantidad_sugerida(cliente, db):
    admin, sede, p = await una_sede_con_faltante(cliente, db, stock_final=8, maximo=60)
    await generar(admin)
    rec = (await listar(admin))[0]
    assert rec["cantidad_sugerida"] == 60 - 8 and "limitado por el stock máximo" in rec["resumen"]


async def test_roles_y_alcance_de_las_recomendaciones(cliente, db):
    admin, norte, sur, p1, *_ = await escenario(cliente, db)
    este = await crear_sede(admin, "Este")
    analista = await crear_usuario(admin, "analista_compras", "analista@andina.com")
    gerente = await crear_usuario(admin, "gerente", "gerente@andina.com")
    enc_sur = await crear_usuario(admin, "encargado_sede", "enc.sur@andina.com", sur["id"])
    enc_este = await crear_usuario(admin, "encargado_sede", "enc.este@andina.com", este["id"])
    operario = await crear_usuario(admin, "usuario_inventario", "operario@andina.com", sur["id"])

    await ejecutar(analista)
    assert (await gerente.post("/api/recomendaciones/generar")).status_code == 403
    assert (await enc_sur.post("/api/recomendaciones/generar")).status_code == 403
    await generar(analista)  # el analista de compras genera

    rec = (await listar(gerente))[0]
    assert rec["acciones"] == ["aprobar", "rechazar"]  # el gerente puede decidir
    assert (await operario.get("/api/recomendaciones")).status_code == 403
    assert len(await listar(enc_sur)) == 1  # la sede destino de la sugerencia la ve
    assert await listar(enc_este) == []  # otra sede no ve nada, ni por id:
    assert (await enc_este.get(f"/api/recomendaciones/{rec['id']}")).status_code == 404
    assert (await enc_este.post(f"/api/recomendaciones/{rec['id']}/aprobar", {})).status_code in (403, 404)
    assert (await enc_sur.get(f"/api/recomendaciones?sede_id={este['id']}")).status_code == 403

    # El encargado de la sede que necesita la mercancía puede aprobar la suya
    ok = await enc_sur.post(f"/api/recomendaciones/{rec['id']}/aprobar", {})
    assert ok.status_code == 200, ok.text


async def test_las_recomendaciones_no_cruzan_empresas(cliente, db):
    admin_a, *_ = await escenario(cliente, db)
    await ejecutar(admin_a)
    await generar(admin_a)
    rec = (await listar(admin_a))[0]
    admin_b = await crear_empresa(db, cliente, "Otra", "admin@otra.com", "7")
    assert await listar(admin_b) == []
    for ruta in ("", "/aprobar", "/rechazar", "/ejecutar"):
        r = await (admin_b.get if ruta == "" else admin_b.post)(f"/api/recomendaciones/{rec['id']}{ruta}", *([] if ruta == "" else [{}]))
        assert r.status_code == 404, ruta
    # tampoco se puede generar desde la predicción de otra empresa
    assert (await admin_b.post("/api/recomendaciones/generar")).json()["codigo"] == "sin_prediccion_vigente"


async def test_reglas_de_calculo_con_valores_conocidos():
    from app.services.recomendaciones_service import _calcular, _Serie

    # d = 10/día, plazo 7 + seguridad 3 -> punto de reposición 100; objetivo = 10·(7+3+21) = 310
    s = _Serie(1, 1, cantidad=80, minimo=20, maximo=None, demanda=10.0, confianza="alta", modelo="m", demanda_horizonte=140, horizonte=14)
    _calcular(s, 7, 3, 21)
    assert (s.punto_reposicion, s.objetivo, s.necesidad, s.prioridad) == (100, 310, 230, "alta")  # 8 días: entre 7 y 10
    s = _Serie(1, 1, cantidad=60, minimo=20, maximo=None, demanda=10.0, confianza="alta", modelo="m", demanda_horizonte=140, horizonte=14)
    _calcular(s, 7, 3, 21)
    assert s.prioridad == "critica"  # 6 días de cobertura: menos que el plazo de entrega
    # El stock máximo limita el objetivo y lo que viene en camino se descuenta
    s = _Serie(1, 1, cantidad=60, minimo=20, maximo=200, demanda=10.0, confianza="alta", modelo="m", demanda_horizonte=140, horizonte=14, en_camino=30)
    _calcular(s, 7, 3, 21)
    assert s.objetivo == 200 and s.necesidad == 110 and s.prioridad == "critica"
    s.confianza = "baja"
    _calcular(s, 7, 3, 21)
    assert s.prioridad == "media"
    # baja confianza nunca genera urgencia máxima; sin riesgo no hay necesidad
    s = _Serie(1, 1, cantidad=5, minimo=0, maximo=None, demanda=10.0, confianza="baja", modelo="m", demanda_horizonte=140, horizonte=14)
    _calcular(s, 7, 3, 21)
    assert s.necesidad > 0 and s.prioridad == "media"
    s = _Serie(1, 1, cantidad=400, minimo=0, maximo=None, demanda=10.0, confianza="alta", modelo="m", demanda_horizonte=140, horizonte=14)
    _calcular(s, 7, 3, 21)
    assert s.necesidad == 0 and s.excedente == 400 - 310


@pytest.mark.postgres
async def test_dos_aprobaciones_simultaneas_crean_un_solo_traslado(cliente, db):
    admin, *_ = await escenario(cliente, db)
    await ejecutar(admin)
    await generar(admin)
    rec = (await listar(admin))[0]
    respuestas = await asyncio.gather(*[admin.post(f"/api/recomendaciones/{rec['id']}/aprobar", {}) for _ in range(5)])
    assert sorted(r.status_code for r in respuestas) == [200, 409, 409, 409, 409]
    assert await db.scalar(select(func.count()).select_from(Traslado)) == 1
