"""SIG · gestión ambiental: vehículos vendidos (real) y CO₂ evitado (estimación parametrizada)."""

import asyncio
from decimal import Decimal

from sqlalchemy import func, select

from app.model.ambiental import AmbRegistro
from app.service.ambiental_service import co2_por_unidad
from tests.ayuda import crear_categoria, crear_empresa, crear_producto, crear_sede, crear_usuario, entrada

# Ejemplo de la documentación: 5 000 km/año, 1 año, 5 kWh/100 km, referencia 70 g/km y red a 0,220 kg/kWh
#   5 000 × (0,070 − 0,05 × 0,220) = 5 000 × 0,059 = 295,000 kg por unidad.
PARAMETROS = {
    "tipo_vehiculo": "motocicleta_electrica", "propulsion": "electrica", "distancia_anual_km": 5000, "consumo_kwh_100km": 5,
    "emision_referencia_gco2_km": 70, "vehiculo_referencia": "Motocicleta de combustión de 125 cc (ejemplo de prueba)",
    "horizonte_anios": 1, "fuente": "Valores ficticios solo para las pruebas automáticas",
}
FACTOR = {"valor": 0.22, "anio": 2024, "fuente": "Valor de prueba (no es una fuente real)"}


async def escenario(cliente, db):
    admin = await crear_empresa(db, cliente)
    norte, sur = await crear_sede(admin, "Norte"), await crear_sede(admin, "Sur")
    motos = await crear_categoria(admin, "Motocicletas eléctricas")
    cascos = await crear_categoria(admin, "Accesorios")
    moto = await crear_producto(admin, motos["id"], "MOTO-1", "Moto urbana", precio_venta=9_000_000)
    casco = await crear_producto(admin, cascos["id"], "CASCO-1", "Casco integral", precio_venta=250_000)
    for sede in (norte, sur):
        await entrada(admin, sede["id"], {moto["id"]: 20, casco["id"]: 20})
    return admin, norte, sur, motos, cascos, moto, casco


async def vender(sesion, sede_id, *lineas: tuple[dict, int]):
    r = await sesion.post("/api/ventas", {"sede_id": sede_id, "items": [{"producto_id": p["id"], "cantidad": c} for p, c in lineas]})
    assert r.status_code == 201, r.text
    return r.json()


async def configurar(admin, categoria, factor=True, **cambios):
    r = await admin.put(f"/api/sig/ambiental/categorias/{categoria['id']}", {**PARAMETROS, **cambios})
    assert r.status_code == 200, r.text
    if factor:
        r2 = await admin.put("/api/sig/ambiental/factor-red", FACTOR)
        assert r2.status_code == 200, r2.text
        return r2.json()
    return r.json()


async def resumen(sesion, **query):
    r = await sesion.get("/api/sig/ambiental/resumen", **({"params": query} if query else {}))
    assert r.status_code == 200, r.text
    return r.json()


# ----------------------------------------------------------------------------- fórmula


def test_formula_documentada():
    class Cfg:  # basta con los atributos que usa la fórmula
        distancia_anual_km, horizonte_anios, consumo_kwh_100km, emision_referencia_gco2_km = 5000, 1, 5, 70
        vehiculo_referencia, fuente = "ref", "fuente"

    valor, params = co2_por_unidad(Cfg(), Decimal("0.22"))
    assert valor == Decimal("295.000")
    assert params["co2_por_unidad_kg"] == "295.000" and params["factor_red_kgco2_kwh"] == "0.22"

    Cfg.horizonte_anios = 3
    assert co2_por_unidad(Cfg(), Decimal("0.22"))[0] == Decimal("885.000")
    # Si faltan datos no se inventa nada.
    assert co2_por_unidad(Cfg(), None) == (None, None)
    assert co2_por_unidad(None, Decimal("0.22")) == (None, None)
    Cfg.consumo_kwh_100km = None
    assert co2_por_unidad(Cfg(), Decimal("0.22")) == (None, None)


# ----------------------------------------------------------------------------- venta de un vehículo


async def test_sin_parametrizar_cuenta_unidades_y_queda_pendiente(cliente, db):
    admin, norte, sur, motos, cascos, moto, casco = await escenario(cliente, db)
    # Antes de configurar nada no hay categorías de vehículo.
    assert (await resumen(admin))["parametrizacion"]["estado"] == "sin_categorias"

    # Se marca la categoría como vehículo pero sin parámetros de cálculo.
    solo_tipo = {"tipo_vehiculo": "motocicleta_electrica", "propulsion": "electrica", "horizonte_anios": 1}
    assert (await admin.put(f"/api/sig/ambiental/categorias/{motos['id']}", solo_tipo)).status_code == 200
    await vender(admin, norte["id"], (moto, 3), (casco, 2))

    r = await resumen(admin)
    assert r["parametrizacion"]["estado"] == "pendiente" and "Pendiente de parametrización" in r["parametrizacion"]["mensaje"]
    assert r["acumulado"] == {"unidades": 3, "co2_estimado_kg": 0.0, "unidades_sin_parametrizar": 3}
    assert r["mes_actual"]["unidades"] == 3 and r["anio_seleccionado"]["unidades"] == 3
    assert r["por_tipo"][0]["tipo_vehiculo"] == "motocicleta_electrica"

    filas = (await admin.get("/api/sig/ambiental/registros")).json()["items"]
    assert len(filas) == 1 and filas[0]["parametrizado"] is False and filas[0]["co2_estimado_kg"] is None


async def test_configurar_calcula_las_ventas_pendientes_con_la_formula(cliente, db):
    admin, norte, sur, motos, cascos, moto, casco = await escenario(cliente, db)
    solo_tipo = {"tipo_vehiculo": "motocicleta_electrica", "propulsion": "electrica", "horizonte_anios": 1}
    await admin.put(f"/api/sig/ambiental/categorias/{motos['id']}", solo_tipo)
    await vender(admin, norte["id"], (moto, 3))

    # Parámetros completos + factor de la red: lo pendiente se calcula y lo nuevo ya nace calculado.
    res = await configurar(admin, motos)
    assert res == {"incorporados": 0, "calculados": 1}
    await vender(admin, sur["id"], (moto, 2))

    r = await resumen(admin)
    assert r["parametrizacion"]["estado"] == "completa"
    assert r["acumulado"] == {"unidades": 5, "co2_estimado_kg": 1475.0, "unidades_sin_parametrizar": 0}  # 5 × 295 kg

    registros = (await admin.get("/api/sig/ambiental/registros")).json()["items"]
    assert sorted(f["co2_estimado_kg"] for f in registros) == [590.0, 885.0]

    cfg = (await admin.get("/api/sig/ambiental/configuracion")).json()
    fila = next(c for c in cfg["categorias"] if c["categoria_id"] == motos["id"])
    assert fila["es_vehiculo"] and fila["parametros_completos"] and fila["co2_por_unidad_kg"] == 295.0 and fila["unidades_vendidas"] == 5
    assert cfg["factor_red"]["valor"] == 0.22 and cfg["factor_red"]["anio"] == 2024 and cfg["puede_configurar"] is True
    otra = next(c for c in cfg["categorias"] if c["categoria_id"] == cascos["id"])
    assert otra["es_vehiculo"] is False and otra["unidades_vendidas"] == 0


async def test_solo_cuentan_las_categorias_configuradas_como_vehiculo(cliente, db):
    admin, norte, sur, motos, cascos, moto, casco = await escenario(cliente, db)
    await configurar(admin, motos)
    await vender(admin, norte["id"], (casco, 10))
    r = await resumen(admin)
    assert r["acumulado"]["unidades"] == 0
    assert await db.scalar(select(func.count()).select_from(AmbRegistro)) == 0
    # Una venta mixta solo cuenta la línea del vehículo.
    await vender(admin, norte["id"], (moto, 1), (casco, 4))
    assert (await resumen(admin))["acumulado"]["unidades"] == 1

    # Si la categoría se desactiva, las ventas nuevas dejan de contarse (las ya contadas se conservan).
    assert (await admin.put(f"/api/sig/ambiental/categorias/{motos['id']}", {**PARAMETROS, "activa": False})).status_code == 200
    await vender(admin, norte["id"], (moto, 1))
    assert (await resumen(admin))["acumulado"]["unidades"] == 1


# ----------------------------------------------------------------------------- anulación y duplicados


async def test_venta_anulada_deja_de_contar_y_no_se_duplica(cliente, db):
    admin, norte, sur, motos, cascos, moto, casco = await escenario(cliente, db)
    await configurar(admin, motos)
    v1 = await vender(admin, norte["id"], (moto, 2))
    await vender(admin, norte["id"], (moto, 1))
    assert (await resumen(admin))["acumulado"] == {"unidades": 3, "co2_estimado_kg": 885.0, "unidades_sin_parametrizar": 0}

    r = await admin.post(f"/api/ventas/{v1['id']}/anular", {"motivo": "Cliente desistió de la compra"})
    assert r.status_code == 200, r.text
    assert (await resumen(admin))["acumulado"] == {"unidades": 1, "co2_estimado_kg": 295.0, "unidades_sin_parametrizar": 0}

    # La línea anulada se conserva en el historial marcada como anulada (no se borra).
    anulados = (await admin.get("/api/sig/ambiental/registros?estado=anulado")).json()["items"]
    assert len(anulados) == 1 and anulados[0]["venta_id"] == v1["id"] and anulados[0]["anulado_en"]

    # Sincronizar no vuelve a contar lo anulado ni duplica lo vigente (idempotente).
    for _ in range(2):
        s = await admin.post("/api/sig/ambiental/sincronizar", {})
        assert s.status_code == 200 and s.json() == {"incorporados": 0, "calculados": 0}
    assert (await resumen(admin))["acumulado"]["unidades"] == 1
    assert await db.scalar(select(func.count()).select_from(AmbRegistro)) == 2


async def test_incorporar_ventas_anteriores_a_la_configuracion(cliente, db):
    admin, norte, sur, motos, cascos, moto, casco = await escenario(cliente, db)
    antes = await vender(admin, norte["id"], (moto, 2))  # categoría aún sin marcar como vehículo
    anulada = await vender(admin, norte["id"], (moto, 5))
    await admin.post(f"/api/ventas/{anulada['id']}/anular", {"motivo": "Error al digitar la venta"})
    assert (await resumen(admin))["acumulado"]["unidades"] == 0

    # Al marcar la categoría se incorpora la venta vigente (la anulada no); sin factor de red aún queda pendiente.
    r1 = await admin.put(f"/api/sig/ambiental/categorias/{motos['id']}", PARAMETROS)
    assert r1.json() == {"incorporados": 1, "calculados": 0}
    assert (await resumen(admin))["acumulado"] == {"unidades": 2, "co2_estimado_kg": 0.0, "unidades_sin_parametrizar": 2}
    r2 = await admin.put("/api/sig/ambiental/factor-red", FACTOR)
    assert r2.json() == {"incorporados": 0, "calculados": 1}
    assert (await resumen(admin))["acumulado"] == {"unidades": 2, "co2_estimado_kg": 590.0, "unidades_sin_parametrizar": 0}
    registro = (await admin.get("/api/sig/ambiental/registros")).json()["items"][0]
    assert registro["venta_id"] == antes["id"]

    # Repetir la acción no duplica nada.
    assert (await admin.post("/api/sig/ambiental/sincronizar", {})).json() == {"incorporados": 0, "calculados": 0}
    assert (await resumen(admin))["acumulado"]["unidades"] == 2


async def test_cambiar_parametros_no_altera_lo_ya_calculado(cliente, db):
    admin, norte, sur, motos, cascos, moto, casco = await escenario(cliente, db)
    await configurar(admin, motos)
    await vender(admin, norte["id"], (moto, 1))
    assert (await resumen(admin))["acumulado"]["co2_estimado_kg"] == 295.0

    # La administración cambia el factor de la red y la distancia: el histórico no se reescribe.
    await admin.put("/api/sig/ambiental/factor-red", {"valor": 0.35, "anio": 2025, "fuente": "Otro valor de prueba"})
    await admin.put(f"/api/sig/ambiental/categorias/{motos['id']}", {**PARAMETROS, "distancia_anual_km": 1000})
    assert (await resumen(admin))["acumulado"]["co2_estimado_kg"] == 295.0

    # Las ventas nuevas usan los parámetros vigentes: 1 000 × (0,070 − 0,05 × 0,35) = 52,5 kg.
    await vender(admin, norte["id"], (moto, 1))
    assert (await resumen(admin))["acumulado"] == {"unidades": 2, "co2_estimado_kg": 347.5, "unidades_sin_parametrizar": 0}
    guardado = await db.scalar(select(AmbRegistro.parametros).order_by(AmbRegistro.id.desc()).limit(1))
    assert guardado["factor_red_kgco2_kwh"] == "0.35000" or guardado["factor_red_kgco2_kwh"] == "0.35"
    assert guardado["distancia_anual_km"].startswith("1000")


async def test_parametrizacion_parcial_y_unidades_sin_estimar(cliente, db):
    admin, norte, sur, motos, cascos, moto, casco = await escenario(cliente, db)
    bicis = await crear_categoria(admin, "Bicicletas eléctricas")
    bici = await crear_producto(admin, bicis["id"], "BICI-1", "Bici de montaña", precio_venta=3_000_000)
    await entrada(admin, norte["id"], {bici["id"]: 10})
    await configurar(admin, motos)
    # La categoría de bicicletas queda marcada pero sin parámetros.
    await admin.put(f"/api/sig/ambiental/categorias/{bicis['id']}", {"tipo_vehiculo": "bicicleta_electrica", "propulsion": "asistida_pedaleo"})
    await vender(admin, norte["id"], (moto, 1), (bici, 4))

    r = await resumen(admin)
    assert r["parametrizacion"]["estado"] == "parcial"
    assert r["acumulado"] == {"unidades": 5, "co2_estimado_kg": 295.0, "unidades_sin_parametrizar": 4}
    por_tipo = {t["tipo_vehiculo"]: t for t in r["por_tipo"]}
    assert por_tipo["bicicleta_electrica"]["unidades_sin_parametrizar"] == 4 and por_tipo["bicicleta_electrica"]["co2_estimado_kg"] == 0
    assert por_tipo["motocicleta_electrica"]["co2_estimado_kg"] == 295.0

    pendientes = (await admin.get("/api/sig/ambiental/registros?pendientes=true")).json()
    assert pendientes["total"] == 1 and pendientes["items"][0]["producto"]["codigo"] == "BICI-1"


async def test_serie_mensual_anual_y_filtro_de_sede(cliente, db):
    admin, norte, sur, motos, cascos, moto, casco = await escenario(cliente, db)
    await configurar(admin, motos)
    await vender(admin, norte["id"], (moto, 2))
    await vender(admin, sur["id"], (moto, 3))

    r = await resumen(admin)
    assert len(r["meses"]) == 12 and [m["mes"] for m in r["meses"]] == list(range(1, 13))
    assert sum(m["unidades"] for m in r["meses"]) == 5 and r["anios"][-1]["unidades"] == 5
    assert r["anio"] in r["anios_disponibles"]

    solo_sur = await resumen(admin, sede_id=sur["id"])
    assert solo_sur["acumulado"] == {"unidades": 3, "co2_estimado_kg": 885.0, "unidades_sin_parametrizar": 0}
    otro_anio = await resumen(admin, anio=2001)
    assert otro_anio["anio_seleccionado"]["unidades"] == 0 and otro_anio["acumulado"]["unidades"] == 5


# ----------------------------------------------------------------------------- permisos y validación


async def test_permisos_y_alcance_por_sede(cliente, db):
    admin, norte, sur, motos, cascos, moto, casco = await escenario(cliente, db)
    ana = await crear_usuario(admin, "usuario_inventario", "ana@andina.com", norte["id"], nombre="Ana Operaria")
    await configurar(admin, motos)
    await vender(admin, norte["id"], (moto, 2))
    await vender(admin, sur["id"], (moto, 7))

    # Quien opera inventario ve los indicadores de SU sede pero no puede configurar nada.
    assert (await resumen(ana))["acumulado"]["unidades"] == 2
    assert (await ana.get(f"/api/sig/ambiental/resumen?sede_id={sur['id']}")).status_code == 403
    assert (await ana.get("/api/sig/ambiental/configuracion")).json()["puede_configurar"] is False
    assert (await ana.put(f"/api/sig/ambiental/categorias/{motos['id']}", PARAMETROS)).status_code == 403
    assert (await ana.put("/api/sig/ambiental/factor-red", FACTOR)).status_code == 403
    assert (await ana.post("/api/sig/ambiental/sincronizar", {})).status_code == 403
    assert {f["sede"]["id"] for f in (await ana.get("/api/sig/ambiental/registros")).json()["items"]} == {norte["id"]}

    # Sin sesión no se accede a nada.
    assert (await cliente.get("/api/sig/ambiental/resumen")).status_code == 401


async def test_validaciones_de_los_parametros(cliente, db):
    admin, norte, sur, motos, cascos, moto, casco = await escenario(cliente, db)
    url = f"/api/sig/ambiental/categorias/{motos['id']}"
    # Parámetros completos sin documentar la fuente.
    assert (await admin.put(url, {**PARAMETROS, "fuente": None})).status_code == 422
    # Valores fuera de rango o tipos desconocidos.
    assert (await admin.put(url, {**PARAMETROS, "distancia_anual_km": -5})).status_code == 422
    assert (await admin.put(url, {**PARAMETROS, "tipo_vehiculo": "cohete"})).status_code == 422
    assert (await admin.put(url, {**PARAMETROS, "campo_inventado": 1})).status_code == 422
    assert (await admin.put("/api/sig/ambiental/factor-red", {**FACTOR, "valor": 0})).status_code == 422
    assert (await admin.put("/api/sig/ambiental/factor-red", {**FACTOR, "fuente": ""})).status_code == 422
    # Categoría inexistente o de otra empresa.
    assert (await admin.put("/api/sig/ambiental/categorias/999999", PARAMETROS)).status_code == 404


async def test_la_configuracion_queda_auditada(cliente, db):
    admin, norte, sur, motos, cascos, moto, casco = await escenario(cliente, db)
    await configurar(admin, motos)
    r = await admin.get("/api/auditoria?modulo=ambiental")
    assert r.status_code == 200, r.text
    acciones = {e["accion"] for e in r.json()["items"]}
    assert {"configurar_categoria", "factor_red"} <= acciones


async def test_ventas_simultaneas_no_duplican_registros(cliente, db):
    admin, norte, sur, motos, cascos, moto, casco = await escenario(cliente, db)
    await configurar(admin, motos)
    respuestas = await asyncio.gather(*[vender(admin, norte["id"], (moto, 1)) for _ in range(5)])
    assert len(respuestas) == 5
    assert (await resumen(admin))["acumulado"]["unidades"] == 5
    assert await db.scalar(select(func.count(func.distinct(AmbRegistro.venta_item_id)))) == 5
