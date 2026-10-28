"""SIG · observaciones de entrada, no conformidades y garantías."""

from datetime import timedelta

from sqlalchemy import func, select

from app.model.inventario import InventarioSede, Movimiento
from app.util.tiempo import hoy_local
from tests.ayuda import crear_categoria, crear_empresa, crear_producto, crear_sede, crear_usuario, existencias


async def escenario(cliente, db):
    admin = await crear_empresa(db, cliente)
    norte, sur = await crear_sede(admin, "Norte"), await crear_sede(admin, "Sur")
    cat = await crear_categoria(admin)
    casco = await crear_producto(admin, cat["id"], "ACC-001", "Casco certificado", descripcion="Casco talla M", precio_venta=250000)
    bateria = await crear_producto(admin, cat["id"], "BAT-001", "Batería 48V", precio_venta=900000)
    ana = await crear_usuario(admin, "usuario_inventario", "ana@andina.com", norte["id"], nombre="Ana Operaria")
    pedro = await crear_usuario(admin, "usuario_inventario", "pedro@andina.com", sur["id"], nombre="Pedro Sur")
    gerente = await crear_usuario(admin, "gerente", "gerente@andina.com", None, nombre="Gerente")
    return admin, norte, sur, casco, bateria, ana, pedro, gerente


async def recibir(sesion, sede_id, lineas: dict[int, int], observacion: str | None = None, motivo="compra"):
    r = await sesion.post("/api/inventario/entradas", {
        "sede_id": sede_id, "motivo": motivo, "observacion": observacion,
        "items": [{"producto_id": p, "cantidad": c} for p, c in lineas.items()],
    })
    assert r.status_code == 201, r.text
    return r.json()


async def totales(db) -> tuple[int, int]:
    """(suma de existencias, cantidad de movimientos): lo que NO debe cambiar al registrar calidad."""
    return (
        int(await db.scalar(select(func.coalesce(func.sum(InventarioSede.cantidad), 0)))),
        int(await db.scalar(select(func.count()).select_from(Movimiento))),
    )


# ----------------------------------------------------------------------------- observaciones de entrada


async def test_entrada_crea_cabecera_con_observacion_inicial(cliente, db):
    admin, norte, sur, casco, bateria, ana, pedro, gerente = await escenario(cliente, db)
    res = await recibir(ana, norte["id"], {casco["id"]: 10, bateria["id"]: 4}, "Llegó una caja con el empaque golpeado")
    assert res["entrada_numero"] == 1 and res["entrada_id"]
    assert {m["entrada_numero"] for m in res["movimientos"]} == {1}

    d = (await ana.get(f"/api/inventario/entradas/{res['entrada_id']}")).json()
    assert d["numero"] == 1 and d["unidades"] == 14 and d["lineas"] == 2 and d["sede"]["id"] == norte["id"]
    assert d["usuario_nombre"] == "Ana Operaria" and d["motivo"] == "compra"
    assert sorted((l["producto"]["codigo"], l["cantidad"]) for l in d["detalle_lineas"]) == [("ACC-001", 10), ("BAT-001", 4)]
    assert [o["contenido"] for o in d["historial_observaciones"]] == ["Llegó una caja con el empaque golpeado"]
    assert d["historial_observaciones"][0]["usuario_nombre"] == "Ana Operaria"
    assert d["puede_observar"] is True and d["puede_reportar_calidad"] is True

    # Sin observación inicial: la entrada existe y el historial arranca vacío.
    sin = await recibir(ana, norte["id"], {casco["id"]: 1})
    assert (await ana.get(f"/api/inventario/entradas/{sin['entrada_id']}")).json()["historial_observaciones"] == []
    assert sin["entrada_numero"] == 2


async def test_observaciones_se_acumulan_y_no_se_pierden_al_reponer_stock(cliente, db):
    admin, norte, sur, casco, bateria, ana, pedro, gerente = await escenario(cliente, db)
    primera = await recibir(ana, norte["id"], {casco["id"]: 10}, "Primera entrada: todo conforme")
    antes = await totales(db)

    r = await ana.post(f"/api/inventario/entradas/{primera['entrada_id']}/observaciones", {"contenido": "Se detectaron 2 cascos con rayones", "producto_id": casco["id"]})
    assert r.status_code == 201, r.text
    r = await admin.post(f"/api/inventario/entradas/{primera['entrada_id']}/observaciones", {"contenido": "Proveedor avisado por teléfono"})
    assert r.status_code == 201
    hist = r.json()["historial_observaciones"]
    assert [o["contenido"] for o in hist] == ["Primera entrada: todo conforme", "Se detectaron 2 cascos con rayones", "Proveedor avisado por teléfono"]
    assert [o["usuario_nombre"] for o in hist] == ["Ana Operaria", "Ana Operaria", "Administrador Demo"]
    assert hist[1]["producto"]["codigo"] == "ACC-001"
    assert await totales(db) == (antes[0], antes[1])  # agregar observaciones NO toca existencias ni movimientos

    # Reponer más stock del mismo producto crea OTRA entrada y no pisa las observaciones de la primera.
    segunda = await recibir(ana, norte["id"], {casco["id"]: 5}, "Reposición sin novedades")
    assert segunda["entrada_id"] != primera["entrada_id"]
    d1 = (await ana.get(f"/api/inventario/entradas/{primera['entrada_id']}")).json()
    d2 = (await ana.get(f"/api/inventario/entradas/{segunda['entrada_id']}")).json()
    assert len(d1["historial_observaciones"]) == 3 and [o["contenido"] for o in d2["historial_observaciones"]] == ["Reposición sin novedades"]
    # Los datos del producto no se tocaron: la observación de la entrada no es la descripción del producto.
    assert (await admin.get(f"/api/productos/{casco['id']}")).json()["descripcion"] == "Casco talla M"
    # El historial de movimientos muestra el número de entrada y conserva la observación de cada una.
    movs = (await admin.get("/api/movimientos?tipo=entrada")).json()["items"]
    assert {(m["entrada_numero"], m["observacion"]) for m in movs} == {(1, "Primera entrada: todo conforme"), (2, "Reposición sin novedades")}
    listado = (await admin.get("/api/inventario/entradas")).json()
    assert [(e["numero"], e["observaciones"]) for e in listado["items"]] == [(2, 1), (1, 3)]


async def test_observacion_de_entrada_validaciones_y_permisos(cliente, db):
    admin, norte, sur, casco, bateria, ana, pedro, gerente = await escenario(cliente, db)
    e = await recibir(ana, norte["id"], {casco["id"]: 3})
    url = f"/api/inventario/entradas/{e['entrada_id']}/observaciones"
    assert (await ana.post(url, {"contenido": "ok", "producto_id": None})).status_code == 422  # muy corta
    r = await ana.post(url, {"contenido": "Producto que no vino en la entrada", "producto_id": bateria["id"]})
    assert r.status_code == 400 and r.json()["codigo"] == "producto_fuera_de_entrada"
    # Quien consulta pero no registra entradas (gerente) puede leer, no escribir.
    assert (await gerente.get(f"/api/inventario/entradas/{e['entrada_id']}")).json()["puede_observar"] is False
    assert (await gerente.post(url, {"contenido": "Nota del gerente"})).status_code == 403
    # Otra sede: no ve la entrada ni puede observarla.
    assert (await pedro.get(f"/api/inventario/entradas/{e['entrada_id']}")).status_code == 403
    assert (await pedro.post(url, {"contenido": "Intento desde otra sede"})).status_code == 403
    assert (await pedro.get("/api/inventario/entradas")).json()["total"] == 0
    assert (await admin.get("/api/inventario/entradas/9999")).status_code == 404


# ----------------------------------------------------------------------------- no conformidades


def datos_nc(producto_id, **extra):
    return {
        "producto_id": producto_id, "tipo": "dano_en_transporte", "descripcion": "Dos unidades llegaron con la carcasa rota",
        "fecha_deteccion": hoy_local().isoformat(), "cantidad_afectada": 2, "referencia": "LOTE-2210", **extra,
    }


async def test_registrar_no_conformidad_no_modifica_inventario(cliente, db):
    admin, norte, sur, casco, bateria, ana, pedro, gerente = await escenario(cliente, db)
    await recibir(ana, norte["id"], {casco["id"]: 10})
    antes = await totales(db)
    r = await ana.post("/api/sig/calidad/no-conformidades", datos_nc(casco["id"], observaciones="Se tomaron fotos al abrir la caja"))
    assert r.status_code == 201, r.text
    nc = r.json()
    assert nc["numero"] == 1 and nc["estado"] == "reportado" and nc["sede"]["id"] == norte["id"]  # sede de la persona
    assert nc["usuario_nombre"] == "Ana Operaria" and nc["cantidad_afectada"] == 2 and nc["referencia"] == "LOTE-2210"
    assert [(h["evento"], h["contenido"]) for h in nc["historial"]] == [("creacion", "Se tomaron fotos al abrir la caja")]
    assert await totales(db) == antes
    assert await existencias(ana, norte["id"], casco["id"]) == 10


async def test_no_conformidad_nace_de_una_entrada_sin_digitar_dos_veces(cliente, db):
    admin, norte, sur, casco, bateria, ana, pedro, gerente = await escenario(cliente, db)
    e = await recibir(ana, norte["id"], {casco["id"]: 10, bateria["id"]: 2}, "Cajas con humedad")
    o = (await ana.post(f"/api/inventario/entradas/{e['entrada_id']}/observaciones", {"contenido": "3 cascos con la visera rayada", "producto_id": casco["id"]})).json()
    obs_id = o["historial_observaciones"][-1]["id"]

    r = await ana.post("/api/sig/calidad/no-conformidades", datos_nc(casco["id"], tipo="defecto_de_fabrica", entrada_id=e["entrada_id"], entrada_observacion_id=obs_id))
    assert r.status_code == 201, r.text
    nc = r.json()
    assert nc["entrada"]["numero"] == 1 and nc["observacion_origen"] == "3 cascos con la visera rayada"
    # Desde la entrada se ve la NC vinculada, tanto en la entrada como en la observación de origen.
    d = (await ana.get(f"/api/inventario/entradas/{e['entrada_id']}")).json()
    assert [n["numero"] for n in d["no_conformidades_vinculadas"]] == [1] and d["no_conformidades"] == 1
    assert [n["numero"] for n in d["historial_observaciones"][-1]["no_conformidades"]] == [1]
    assert d["historial_observaciones"][0]["no_conformidades"] == []
    # La observación solo se refiere a esa línea: otro producto no puede usarla.
    r = await ana.post("/api/sig/calidad/no-conformidades", datos_nc(bateria["id"], entrada_id=e["entrada_id"], entrada_observacion_id=obs_id))
    assert r.status_code == 400 and r.json()["codigo"] == "observacion_de_otro_producto"
    # Un producto que no vino en la entrada no se puede vincular.
    otro = await crear_producto(admin, (await crear_categoria(admin, "Otra"))["id"], "ZZZ-1", "Ajeno")
    r = await ana.post("/api/sig/calidad/no-conformidades", datos_nc(otro["id"], entrada_id=e["entrada_id"]))
    assert r.status_code == 400 and r.json()["codigo"] == "producto_fuera_de_entrada"
    # Y por sede: Pedro (Sur) no puede vincular una entrada de Norte.
    r = await pedro.post("/api/sig/calidad/no-conformidades", datos_nc(casco["id"], entrada_id=e["entrada_id"]))
    assert r.status_code == 403
    # Filtro por entrada
    assert (await ana.get(f"/api/sig/calidad/no-conformidades?entrada_id={e['entrada_id']}")).json()["total"] == 1


async def test_no_conformidad_validaciones(cliente, db):
    admin, norte, sur, casco, bateria, ana, pedro, gerente = await escenario(cliente, db)
    manana = (hoy_local() + timedelta(days=2)).isoformat()
    assert (await ana.post("/api/sig/calidad/no-conformidades", datos_nc(casco["id"], fecha_deteccion=manana))).status_code == 422
    assert (await ana.post("/api/sig/calidad/no-conformidades", datos_nc(casco["id"], cantidad_afectada=0))).status_code == 422
    assert (await ana.post("/api/sig/calidad/no-conformidades", datos_nc(casco["id"], tipo="inventado"))).status_code == 422
    assert (await ana.post("/api/sig/calidad/no-conformidades", datos_nc(99999))).status_code == 404
    # El gerente consulta calidad pero no la reporta.
    assert (await gerente.post("/api/sig/calidad/no-conformidades", datos_nc(casco["id"]))).status_code == 403
    # Un administrador (sin sede propia) debe indicar la sede.
    r = await admin.post("/api/sig/calidad/no-conformidades", datos_nc(casco["id"]))
    assert r.status_code == 400 and r.json()["codigo"] == "sede_requerida"
    r = await admin.post("/api/sig/calidad/no-conformidades", datos_nc(casco["id"], sede_id=sur["id"]))
    assert r.status_code == 201 and r.json()["sede"]["id"] == sur["id"]


async def test_no_conformidad_historial_de_observaciones_y_gestion(cliente, db):
    admin, norte, sur, casco, bateria, ana, pedro, gerente = await escenario(cliente, db)
    nc = (await ana.post("/api/sig/calidad/no-conformidades", datos_nc(casco["id"], observaciones="Observación inicial"))).json()
    base = f"/api/sig/calidad/no-conformidades/{nc['id']}"

    r = await ana.post(f"{base}/observaciones", {"contenido": "Se contactó al transportador"})
    assert r.status_code == 201
    r = await admin.post(f"{base}/observaciones", {"contenido": "Pendiente respuesta del proveedor"})
    contenido = [(h["evento"], h["usuario_nombre"], h["contenido"]) for h in r.json()["historial"]]
    assert contenido == [("creacion", "Ana Operaria", "Observación inicial"), ("observacion", "Ana Operaria", "Se contactó al transportador"),
                         ("observacion", "Administrador Demo", "Pendiente respuesta del proveedor")]
    assert r.json()["observaciones"] == 3  # nada se sobrescribió

    # Solo quien gestiona calidad cambia estados; los estados avanzan en orden y exigen solución al resolver.
    assert (await ana.patch(base, {"estado": "en_revision"})).status_code == 403
    r = await admin.patch(base, {"estado": "en_revision", "responsable_id": ana.usuario["id"], "comentario": "Asignada a Ana"})
    assert r.status_code == 200 and r.json()["estado"] == "en_revision" and r.json()["responsable_nombre"] == "Ana Operaria"
    r = await admin.patch(base, {"estado": "resuelto"})
    assert r.status_code == 400 and r.json()["codigo"] == "solucion_requerida"
    r = await admin.patch(base, {"estado": "reportado"})
    assert r.status_code == 400 and r.json()["codigo"] == "transicion_invalida"
    r = await admin.patch(base, {"estado": "en_proceso_solucion", "solucion": "Reposición por parte del proveedor"})
    assert r.json()["estado"] == "en_proceso_solucion" and r.json()["solucion"] == "Reposición por parte del proveedor"
    r = await admin.patch(base, {"estado": "resuelto"})
    assert r.json()["estado"] == "resuelto" and r.json()["resuelta_en"]
    r = await admin.patch(base, {"estado": "en_proceso_solucion", "comentario": "El reemplazo también llegó dañado"})  # reapertura
    assert r.json()["estado"] == "en_proceso_solucion" and r.json()["resuelta_en"] is None
    await admin.patch(base, {"estado": "resuelto"})
    r = await admin.patch(base, {"estado": "cerrado"})
    assert r.json()["estado"] == "cerrado" and r.json()["cerrada_en"] and r.json()["puede_gestionar"] is False
    # Cerrada: no admite cambios ni observaciones.
    assert (await admin.patch(base, {"comentario": "x" * 5})).status_code == 409
    assert (await ana.post(f"{base}/observaciones", {"contenido": "Observación tardía"})).status_code == 409
    eventos = [h["evento"] for h in (await ana.get(base)).json()["historial"]]
    assert eventos.count("estado") == 6 and eventos[0] == "creacion"


async def test_no_conformidades_filtros_y_alcance_por_sede(cliente, db):
    admin, norte, sur, casco, bateria, ana, pedro, gerente = await escenario(cliente, db)
    a = (await ana.post("/api/sig/calidad/no-conformidades", datos_nc(casco["id"]))).json()
    b = (await pedro.post("/api/sig/calidad/no-conformidades", datos_nc(bateria["id"], tipo="producto_equivocado", referencia="OC-77"))).json()
    assert (a["numero"], b["numero"]) == (1, 2)
    # Cada operario ve solo su sede; administración y gerencia ven todo.
    assert (await ana.get("/api/sig/calidad/no-conformidades")).json()["total"] == 1
    assert (await pedro.get("/api/sig/calidad/no-conformidades")).json()["total"] == 1
    assert (await gerente.get("/api/sig/calidad/no-conformidades")).json()["total"] == 2
    assert (await ana.get(f"/api/sig/calidad/no-conformidades/{b['id']}")).status_code == 403
    assert (await ana.get(f"/api/sig/calidad/no-conformidades?sede_id={sur['id']}")).status_code == 403
    async def numeros(qs):
        return [n["numero"] for n in (await admin.get(f"/api/sig/calidad/no-conformidades?{qs}")).json()["items"]]
    assert await numeros("tipo=producto_equivocado") == [2]
    assert await numeros("q=OC-77") == [2]
    assert await numeros("q=casco") == [1]
    assert await numeros(f"sede_id={norte['id']}") == [1]
    assert await numeros(f"producto_id={bateria['id']}") == [2]
    assert await numeros("estado=cerrado") == []
    assert await numeros("desde=2999-01-01") == []
    resumen = (await admin.get("/api/sig/calidad/resumen")).json()
    assert resumen["no_conformidades_abiertas"] == 2 and resumen["garantias_abiertas"] == 0
    assert (await ana.get("/api/sig/calidad/resumen")).json()["no_conformidades_abiertas"] == 1


# ----------------------------------------------------------------------------- garantías


def datos_garantia(producto_id, **extra):
    hoy = hoy_local()
    return {
        "producto_id": producto_id, "documento_tipo": "factura_compra", "documento_referencia": "FC-1020",
        "fecha_compra": (hoy - timedelta(days=30)).isoformat(), "garantia_hasta": (hoy + timedelta(days=300)).isoformat(),
        "defecto": "La batería no sostiene la carga", "proveedor": "Baterías del Valle", **extra,
    }


async def test_garantia_ciclo_completo_con_historial(cliente, db):
    admin, norte, sur, casco, bateria, ana, pedro, gerente = await escenario(cliente, db)
    await recibir(ana, norte["id"], {bateria["id"]: 5})
    antes = await totales(db)
    r = await ana.post("/api/sig/calidad/garantias", datos_garantia(bateria["id"], observaciones="El cliente trajo la factura"))
    assert r.status_code == 201, r.text
    g = r.json()
    assert g["numero"] == 1 and g["estado"] == "reportada" and g["en_garantia"] is True and g["sede"]["id"] == norte["id"]
    assert await totales(db) == antes  # una garantía no mueve inventario
    base = f"/api/sig/calidad/garantias/{g['id']}"

    await ana.post(f"{base}/observaciones", {"contenido": "Se reprodujo la falla en el taller"})
    assert (await ana.patch(base, {"estado": "pendiente_revision"})).status_code == 403
    r = await admin.patch(base, {"estado": "pendiente_revision", "responsable_id": ana.usuario["id"]})
    assert r.json()["estado"] == "pendiente_revision" and r.json()["responsable_nombre"] == "Ana Operaria"
    # No se puede saltar pasos incoherentes ni aprobar sin respuesta del proveedor.
    assert (await admin.patch(base, {"estado": "solucionada"})).json()["codigo"] == "transicion_invalida"
    r = await admin.patch(base, {"estado": "aprobada"})
    assert r.status_code == 400 and r.json()["codigo"] == "respuesta_requerida"
    r = await admin.patch(base, {"estado": "enviada_proveedor"})
    assert r.json()["estado"] == "enviada_proveedor" and r.json()["fecha_envio_proveedor"] == hoy_local().isoformat()
    r = await admin.patch(base, {"estado": "aprobada", "respuesta_proveedor": "Aprobamos el cambio de la batería"})
    assert r.json()["estado"] == "aprobada" and r.json()["fecha_respuesta_proveedor"] == hoy_local().isoformat()
    r = await admin.patch(base, {"estado": "solucionada"})
    assert r.status_code == 400 and r.json()["codigo"] == "solucion_requerida"
    r = await admin.patch(base, {"estado": "solucionada", "solucion": "Entregamos una batería nueva al cliente"})
    assert r.json()["estado"] == "solucionada" and r.json()["fecha_solucion"]
    r = await admin.patch(base, {"estado": "cerrada"})
    assert r.json()["estado"] == "cerrada" and r.json()["cerrada_en"]
    assert (await admin.patch(base, {"comentario": "Nota posterior"})).status_code == 409

    h = (await ana.get(base)).json()["historial"]
    assert [(x["evento"], x["estado_nuevo"]) for x in h if x["evento"] in ("creacion", "estado")] == [
        ("creacion", "reportada"), ("estado", "pendiente_revision"), ("estado", "enviada_proveedor"),
        ("estado", "aprobada"), ("estado", "solucionada"), ("estado", "cerrada"),
    ]
    assert h[0]["contenido"] == "El cliente trajo la factura" and h[1]["contenido"] == "Se reprodujo la falla en el taller"
    assert all(x["fecha"] and x["usuario_nombre"] for x in h)


async def test_garantia_con_documentos_de_entrada_y_venta(cliente, db):
    admin, norte, sur, casco, bateria, ana, pedro, gerente = await escenario(cliente, db)
    e = await recibir(ana, norte["id"], {bateria["id"]: 5})
    r = await ana.post("/api/sig/calidad/garantias", datos_garantia(bateria["id"], documento_tipo="entrada_inventario", documento_referencia=None, entrada_id=e["entrada_id"]))
    assert r.status_code == 201, r.text
    assert r.json()["documento_referencia"] == "Entrada #1" and r.json()["entrada"]["numero"] == 1
    venta = (await ana.post("/api/ventas", {"sede_id": norte["id"], "items": [{"producto_id": bateria["id"], "cantidad": 1}]})).json()
    r = await ana.post("/api/sig/calidad/garantias", datos_garantia(bateria["id"], documento_tipo="venta", documento_referencia=None, venta_id=venta["id"]))
    assert r.status_code == 201 and r.json()["venta_numero"] == venta["numero"] and r.json()["documento_referencia"] == f"Venta #{venta['numero']}"
    # Una venta anulada ya no respalda una garantía.
    await admin.post(f"/api/ventas/{venta['id']}/anular", {"motivo": "Error de digitación"})
    r = await ana.post("/api/sig/calidad/garantias", datos_garantia(bateria["id"], documento_tipo="venta", documento_referencia=None, venta_id=venta["id"]))
    assert r.status_code == 400 and r.json()["codigo"] == "venta_anulada"
    # Producto que no está en la entrada / documento obligatorio / fechas incoherentes.
    r = await ana.post("/api/sig/calidad/garantias", datos_garantia(casco["id"], documento_tipo="entrada_inventario", documento_referencia=None, entrada_id=e["entrada_id"]))
    assert r.status_code == 400 and r.json()["codigo"] == "producto_fuera_de_entrada"
    assert (await ana.post("/api/sig/calidad/garantias", datos_garantia(bateria["id"], documento_referencia=None))).status_code == 422
    futuro = (hoy_local() + timedelta(days=3)).isoformat()
    assert (await ana.post("/api/sig/calidad/garantias", datos_garantia(bateria["id"], fecha_compra=futuro))).status_code == 422
    vencida = datos_garantia(bateria["id"], garantia_hasta=(hoy_local() - timedelta(days=1)).isoformat())
    assert (await ana.post("/api/sig/calidad/garantias", vencida)).json()["en_garantia"] is False


async def test_garantias_filtros_y_alcance(cliente, db):
    admin, norte, sur, casco, bateria, ana, pedro, gerente = await escenario(cliente, db)
    a = (await ana.post("/api/sig/calidad/garantias", datos_garantia(bateria["id"]))).json()
    b = (await pedro.post("/api/sig/calidad/garantias", datos_garantia(casco["id"], proveedor="Cascos Andes", documento_referencia="FC-9"))).json()
    assert (await ana.get("/api/sig/calidad/garantias")).json()["total"] == 1
    assert (await ana.get(f"/api/sig/calidad/garantias/{b['id']}")).status_code == 403
    assert (await gerente.get("/api/sig/calidad/garantias")).json()["total"] == 2
    async def numeros(qs):
        return [g["numero"] for g in (await admin.get(f"/api/sig/calidad/garantias?{qs}")).json()["items"]]
    assert await numeros("proveedor=andes") == [2]
    assert await numeros("q=FC-9") == [2]
    assert await numeros(f"producto_id={bateria['id']}") == [1]
    assert await numeros("estado=reportada") == [2, 1]
    await admin.patch(f"/api/sig/calidad/garantias/{a['id']}", {"estado": "pendiente_revision"})
    assert await numeros("estado=pendiente_revision") == [1]
    assert (await admin.get("/api/sig/calidad/resumen")).json()["garantias_abiertas"] == 2


async def test_evidencias_de_calidad(cliente, db):
    from tests.test_sig_pqrs_adjuntos import png_minimo, subir

    admin, norte, sur, casco, bateria, ana, pedro, gerente = await escenario(cliente, db)
    nc = (await ana.post("/api/sig/calidad/no-conformidades", datos_nc(casco["id"]))).json()
    r = await subir(ana, "no_conformidad", nc["id"], png_minimo(), "carcasa rota.png")
    assert r.status_code == 201
    g = (await ana.post("/api/sig/calidad/garantias", datos_garantia(bateria["id"]))).json()
    assert (await subir(ana, "garantia", g["id"], b"%PDF-1.4 factura")).status_code == 201
    assert (await ana.get(f"/api/sig/calidad/no-conformidades/{nc['id']}")).json()["archivos"][0]["nombre"] == "carcasa rota.png"
    # Otra sede no puede adjuntar ni descargar; el gerente (solo consulta) puede ver pero no adjuntar.
    assert (await subir(pedro, "no_conformidad", nc["id"], png_minimo())).status_code == 403
    assert (await pedro.get(f"/api/sig/adjuntos/{r.json()['id']}/archivo")).status_code == 403
    assert (await gerente.get(f"/api/sig/adjuntos/{r.json()['id']}/archivo")).status_code == 200
    assert (await subir(gerente, "no_conformidad", nc["id"], png_minimo())).status_code == 403
    # Una NC cerrada no admite más archivos.
    base = f"/api/sig/calidad/no-conformidades/{nc['id']}"
    await admin.patch(base, {"estado": "resuelto", "solucion": "Reposición"})
    await admin.patch(base, {"estado": "cerrado"})
    assert (await subir(ana, "no_conformidad", nc["id"], png_minimo())).json()["codigo"] == "registro_cerrado"
