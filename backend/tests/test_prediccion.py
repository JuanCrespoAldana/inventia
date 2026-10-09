"""Predicción de demanda por API: ejecución, resultados, permisos, aislamiento y alertas de riesgo."""

from datetime import timedelta

import pytest
from sqlalchemy import select, update

from app.core.tiempo import ahora_utc
from app.models.enums import EstadoEjecucion
from app.models.inventario import Alerta
from app.models.prediccion import EjecucionPrediccion
from app.services import prediccion_service
from tests.ayuda import (
    crear_categoria,
    crear_empresa,
    crear_producto,
    crear_sede,
    crear_usuario,
    entrada,
    patron_semanal,
    sembrar_historial,
)


async def escenario(cliente, db):
    """Dos sedes y cuatro productos: P1 con historial regular en ambas sedes (Sur casi agotada),
    P2 con ventas esporádicas, P3 recién creado sin historial y P4 sin ninguna venta."""
    admin = await crear_empresa(db, cliente)
    norte, sur = await crear_sede(admin, "Norte"), await crear_sede(admin, "Sur")
    cat = await crear_categoria(admin)
    p1 = await crear_producto(admin, cat["id"], "A-1", "Arroz", costo=2000, precio_venta=3000)
    p2 = await crear_producto(admin, cat["id"], "A-2", "Sal", costo=500, precio_venta=900)
    p3 = await crear_producto(admin, cat["id"], "A-3", "Producto nuevo", costo=500, precio_venta=900)
    await sembrar_historial(db, admin, norte["id"], p1["id"], patron_semanal(semilla=1), stock_final=400)
    await sembrar_historial(db, admin, sur["id"], p1["id"], patron_semanal(semilla=2), stock_final=8)
    esporadico = [0] * 56
    esporadico[10] = esporadico[40] = 2
    await sembrar_historial(db, admin, norte["id"], p2["id"], esporadico, stock_final=50)
    await entrada(admin, norte["id"], {p3["id"]: 20})
    return admin, norte, sur, p1, p2, p3


async def ejecutar(sesion, horizonte=14):
    r = await sesion.post("/api/predicciones/ejecutar", {"horizonte_dias": horizonte})
    assert r.status_code == 202, r.text
    return r.json()


async def test_la_ejecucion_guarda_predicciones_metricas_y_explica_lo_omitido(cliente, db):
    admin, norte, sur, p1, p2, p3 = await escenario(cliente, db)
    ej = await ejecutar(admin)
    assert ej["estado"] == "en_cola" and ej["horizonte_dias"] == 14

    # La API ya terminó el cálculo en segundo plano: se consulta el resultado.
    detalle = (await admin.get(f"/api/predicciones/ejecuciones/{ej['id']}")).json()
    assert detalle["estado"] == "completada", detalle
    r = detalle["resumen"]
    assert r["series_con_prediccion"] == 2 and r["series_omitidas"] == 2  # P1 en dos sedes; P2 y P3 sin datos suficientes
    assert r["wape_global"] is not None and r["wape_linea_base_global"] is not None
    motivos = {(o["codigo"], o["sede"]): o["motivo"] for o in r["omitidas"]}
    assert "Pocas ventas" in motivos[("A-2", "Norte")]
    assert "Historial insuficiente" in motivos[("A-3", "Norte")]
    assert detalle["parametros"]["linea_base"] == "media_28" and len(detalle["parametros"]["modelos"]) == 6

    lista = (await admin.get("/api/predicciones?orden=producto")).json()
    assert lista["total"] == 2
    for p in lista["items"]:
        assert p["producto"]["codigo"] == "A-1" and p["ejecucion_id"] == ej["id"]
        assert p["fecha_fin"] > p["fecha_inicio"] and p["limite_inferior"] <= p["demanda_estimada"] <= p["limite_superior"]
        assert p["metricas"]["wape"] is not None and p["metricas"]["wape_linea_base"] is not None
        assert p["modelo_descripcion"] and p["confianza"] in ("alta", "media", "baja")
    sur_pred = next(p for p in lista["items"] if p["sede"]["nombre"] == "Sur")
    assert sur_pred["existencias_actuales"] == 8 and sur_pred["cobertura_dias"] < 3  # casi sin stock

    # Serie: historial real y pronóstico por separado (el pronóstico nunca se mezcla con ventas)
    s = (await admin.get(f"/api/predicciones/serie?sede_id={sur['id']}&producto_id={p1['id']}&dias=30")).json()
    assert len(s["historial"]) == 30 and len(s["pronostico"]) == 14 and s["modelo"]
    assert s["historial"][-1][0] < s["pronostico"][0][0]
    sin = (await admin.get(f"/api/predicciones/serie?sede_id={norte['id']}&producto_id={p2['id']}")).json()
    assert sin["pronostico"] == [] and "Pocas ventas" in sin["motivo_sin_prediccion"]

    # Auditoría de la ejecución
    ops = (await admin.get("/api/auditoria?modulo=prediccion")).json()["items"]
    assert {o["accion"] for o in ops} >= {"ejecutar", "completar"}


async def test_catalogo_de_modelos_es_transparente(cliente, db):
    admin = await crear_empresa(db, cliente)
    r = (await admin.get("/api/predicciones/modelos")).json()
    nombres = {m["nombre"]: m for m in r["modelos"]}
    assert nombres["media_28"]["es_linea_base"] and not nombres["media_28"]["avanzado"]
    assert nombres["gbr_rezagos"]["avanzado"] and r["minimo_dias_historia"] == 28


async def test_sin_ventas_suficientes_la_ejecucion_termina_con_aviso_honesto(cliente, db):
    admin = await crear_empresa(db, cliente)
    sede = await crear_sede(admin)
    cat = await crear_categoria(admin)
    p = await crear_producto(admin, cat["id"], "Z-1", "Producto", precio_venta=1000)
    await entrada(admin, sede["id"], {p["id"]: 10})
    ej = await ejecutar(admin)
    d = (await admin.get(f"/api/predicciones/ejecuciones/{ej['id']}")).json()
    assert d["estado"] == "completada" and d["resumen"]["series_con_prediccion"] == 0
    assert "datos suficientes" in d["resumen"]["advertencia_global"]
    assert (await admin.get("/api/predicciones")).json()["total"] == 0


async def test_permisos_de_prediccion_por_rol(cliente, db):
    admin, norte, sur, p1, *_ = await escenario(cliente, db)
    await ejecutar(admin)
    analista = await crear_usuario(admin, "analista_compras", "analista@andina.com")
    gerente = await crear_usuario(admin, "gerente", "gerente@andina.com")
    enc_norte = await crear_usuario(admin, "encargado_sede", "enc.norte@andina.com", norte["id"])
    operario = await crear_usuario(admin, "usuario_inventario", "operario@andina.com", norte["id"])

    assert (await analista.post("/api/predicciones/ejecutar", {})).status_code == 202  # el analista genera
    assert (await gerente.get("/api/predicciones")).status_code == 200
    assert (await gerente.post("/api/predicciones/ejecutar", {})).status_code == 403
    assert (await enc_norte.post("/api/predicciones/ejecutar", {})).status_code == 403
    assert (await operario.get("/api/predicciones")).status_code == 403
    assert (await operario.get("/api/predicciones/ejecuciones")).status_code == 403
    assert (await cliente.get("/api/predicciones")).status_code == 401

    # El encargado ve solo su sede y no puede consultar otra
    vistas = (await enc_norte.get("/api/predicciones")).json()["items"]
    assert vistas and {p["sede"]["nombre"] for p in vistas} == {"Norte"}
    assert (await enc_norte.get(f"/api/predicciones?sede_id={sur['id']}")).status_code == 403
    assert (await enc_norte.get(f"/api/predicciones/serie?sede_id={sur['id']}&producto_id={p1['id']}")).status_code == 403
    ej_id = (await enc_norte.get("/api/predicciones/ejecuciones")).json()["items"][0]["id"]
    det = (await enc_norte.get(f"/api/predicciones/ejecuciones/{ej_id}")).json()
    assert all(o["sede_id"] == norte["id"] for o in det["resumen"].get("omitidas", []))


async def test_una_sola_ejecucion_activa_y_las_colgadas_se_cierran(cliente, db):
    admin, *_ = await escenario(cliente, db)
    empresa_id = admin.usuario["empresa_id"]
    activa = EjecucionPrediccion(
        empresa_id=empresa_id, usuario_id=admin.usuario["id"], estado=EstadoEjecucion.EJECUTANDO, horizonte_dias=14,
        iniciada_en=ahora_utc(), parametros={}, resumen={},
    )
    db.add(activa)
    await db.commit()
    r = await admin.post("/api/predicciones/ejecutar", {})
    assert r.status_code == 409 and r.json()["codigo"] == "ejecucion_en_curso"

    # Si lleva «ejecutando» mucho más que el tiempo máximo, el proceso murió: se marca fallida y se acepta la nueva.
    await db.execute(update(EjecucionPrediccion).where(EjecucionPrediccion.id == activa.id).values(iniciada_en=ahora_utc() - timedelta(hours=5)))
    await db.commit()
    assert (await admin.post("/api/predicciones/ejecutar", {})).status_code == 202
    await db.refresh(activa)
    assert activa.estado == EstadoEjecucion.FALLIDA and "interrumpió" in activa.error


async def test_un_error_de_calculo_deja_la_ejecucion_fallida_sin_detalles_tecnicos(cliente, db, monkeypatch):
    admin, *_ = await escenario(cliente, db)

    def explotar(*a, **k):
        raise RuntimeError("detalle interno: /ruta/secreta")

    monkeypatch.setattr(prediccion_service.pipeline, "pronosticar_lote", explotar)
    ej = await ejecutar(admin)
    d = (await admin.get(f"/api/predicciones/ejecuciones/{ej['id']}")).json()
    assert d["estado"] == "fallida" and "RuntimeError" in d["error"] and "secreta" not in d["error"]
    # tras fallar se puede volver a intentar
    monkeypatch.undo()
    assert (await admin.post("/api/predicciones/ejecutar", {})).status_code == 202


async def test_las_predicciones_estan_aisladas_entre_empresas(cliente, db):
    admin_a, *_ = await escenario(cliente, db)
    ej = await ejecutar(admin_a)
    admin_b = await crear_empresa(db, cliente, "Otra Empresa", "admin@otra.com", "2")
    assert (await admin_b.get("/api/predicciones")).json()["total"] == 0
    assert (await admin_b.get("/api/predicciones/ejecuciones")).json()["total"] == 0
    assert (await admin_b.get(f"/api/predicciones/ejecuciones/{ej['id']}")).status_code == 404
    assert (await admin_b.get(f"/api/predicciones?ejecucion_id={ej['id']}")).status_code == 404


async def test_la_prediccion_abre_alertas_de_riesgo_de_desabastecimiento(cliente, db):
    admin, norte, sur, p1, *_ = await escenario(cliente, db)
    antes = (await admin.get("/api/alertas?tipo=riesgo_desabastecimiento")).json()["total"]
    assert antes == 0  # sin predicción no hay riesgo calculable
    await ejecutar(admin)
    riesgo = (await admin.get("/api/alertas?tipo=riesgo_desabastecimiento")).json()["items"]
    assert [a["sede"]["nombre"] for a in riesgo] == ["Sur"]  # Norte tiene 400 unidades
    a = riesgo[0]
    assert a["prioridad"] in ("critica", "alta") and a["detalle"]["cobertura_dias"] < 3
    assert a["producto"]["codigo"] == "A-1" and "alcanzaría" in a["mensaje"]
    # Al reabastecer, la alerta se resuelve sola
    await entrada(admin, sur["id"], {p1["id"]: 600})
    assert (await admin.get("/api/alertas?tipo=riesgo_desabastecimiento")).json()["total"] == 0
    fila = (await db.scalars(select(Alerta).where(Alerta.tipo == "riesgo_desabastecimiento"))).all()
    assert len(fila) == 1 and fila[0].estado == "resuelta"


@pytest.mark.postgres
async def test_dos_solicitudes_simultaneas_crean_una_sola_ejecucion(cliente, db, monkeypatch):
    import asyncio

    admin, *_ = await escenario(cliente, db)

    async def sin_calculo(_id):  # las ejecuciones quedan «en cola»: el candado debe frenar a la segunda
        return None

    monkeypatch.setattr(prediccion_service, "ejecutar_en_segundo_plano", sin_calculo)
    respuestas = await asyncio.gather(*[admin.post("/api/predicciones/ejecutar", {}) for _ in range(4)])
    assert sorted(r.status_code for r in respuestas) == [202, 409, 409, 409]
