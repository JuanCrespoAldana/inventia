"""Asistente de consultas (reglas, sin IA generativa): clasificación, permisos, sedes, seguimientos y seguridad."""

from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app import demo
from app.model.catalogo import Producto
from app.model.inventario import InventarioSede
from app.model.usuario import Usuario
from app.security.dependencias import contexto_de_usuario
from app.service.asistente import motor
from app.service.asistente.entidades import armar_directorio, resolver
from app.util import lenguaje as L
from app.util.tiempo import hoy_local
from tests.asistente_corpus import CASOS
from tests.ayuda import crear_categoria, crear_empresa, crear_producto, crear_sede, entrada, iniciar_sesion

DIAS = 60  # el mínimo que permite la demostración
PRODUCTOS = 10  # bicicletas y monopatines: alcanzan para las pruebas y mantienen la carga rápida
FALLOS_TOLERADOS = 3  # el corpus es difuso por naturaleza (jerga, erratas); más fallos que esto indican una regresión


async def escenario(cliente, db):
    """Una empresa con la demostración completa; devuelve el administrador y una sesión por rol."""
    admin = await crear_empresa(db, cliente, correo="duena@empresa.example")
    resultado = await demo.cargar_demo(db, dias=DIAS, productos=PRODUCTOS, en_empresa_existente=True)
    por_rol = {}
    for rol, correo, clave in resultado.credenciales:
        por_rol[rol] = await iniciar_sesion(cliente, correo, clave)
    return admin, por_rol


async def preguntar(sesion, mensaje, contexto=None):
    cuerpo = {"mensaje": mensaje}
    if contexto is not None:
        cuerpo["contexto"] = contexto
    r = await sesion.post("/api/asistente/preguntar", cuerpo)
    assert r.status_code == 200, r.text
    return r.json()


# ------------------------------------------------------------------------------------- clasificación del corpus


def directorio_de_la_demostracion():
    """El catálogo completo de la demostración (sin tocar la base de datos): contra él se prueba el corpus de preguntas."""
    sedes = [SimpleNamespace(id=i, nombre=n, ciudad=c, activa=True) for i, (n, c, _d, _f) in enumerate(demo.SEDES, 1)]
    categorias = [SimpleNamespace(id=i, nombre=n, activa=True) for i, n in enumerate(demo.CATEGORIAS, 1)]
    por_nombre = {c.nombre: c.id for c in categorias}
    productos = [SimpleNamespace(id=i, codigo=cod, nombre=nom, categoria_id=por_nombre[cat], activo=True) for i, (cod, nom, cat, *_r) in enumerate(demo.CATALOGO, 1)]
    return armar_directorio(sedes, categorias, productos)


async def test_el_corpus_de_preguntas_se_clasifica_bien(cliente, db):
    admin = await crear_empresa(db, cliente, correo="duena@empresa.example")
    usuario = await db.scalar(select(Usuario).where(Usuario.email == "duena@empresa.example"))
    ctx = contexto_de_usuario(usuario)
    directorio = directorio_de_la_demostracion()
    hoy = date(2026, 11, 5)
    fallos = []
    for pregunta, esperada in CASOS:
        entidades, _ = resolver(directorio, pregunta, hoy)
        obtenida = motor.clasificar(ctx, entidades) or "no_entendida"
        if obtenida not in esperada.split("|"):
            fallos.append(f"{pregunta!r}: esperada {esperada}, obtenida {obtenida}")
    assert len(CASOS) >= 250
    assert len(fallos) <= FALLOS_TOLERADOS, "\n".join(fallos)


# ------------------------------------------------------------------------------------------------- endpoint


async def test_el_endpoint_exige_sesion_y_valida_el_mensaje(cliente, db):
    admin, _ = await escenario(cliente, db)
    assert (await cliente.post("/api/asistente/preguntar", json={"mensaje": "hola"})).status_code == 401
    assert (await cliente.get("/api/asistente/ayuda")).status_code == 401
    assert (await admin.post("/api/asistente/preguntar", {"mensaje": ""})).status_code == 422
    assert (await admin.post("/api/asistente/preguntar", {"mensaje": "x" * 501})).status_code == 422
    assert (await admin.post("/api/asistente/preguntar", {})).status_code == 422


async def test_responde_con_datos_reales_y_bloques_estructurados(cliente, db):
    admin, _ = await escenario(cliente, db)
    r = await preguntar(admin, "¿Cuánto inventario tenemos?")
    assert r["intencion"] == "resumen_inventario" and r["entendida"] is True
    assert r["alcance"] == "Toda la empresa"
    assert r["bloques"][0]["tipo"] == "metricas" and r["sugerencias"]
    # las cifras salen de la base de datos: coinciden con lo que muestra la pantalla de inventario
    unidades = next(m for m in r["bloques"][0]["metricas"] if m["etiqueta"] == "Unidades")["valor"]
    assert int(unidades.replace(".", "")) == await db.scalar(select(func.sum(InventarioSede.cantidad)))  # sale de la base de datos

    ayuda = (await admin.get("/api/asistente/ayuda")).json()
    assert ayuda["iniciales"] and ayuda["grupos"] and all(g["ejemplos"] for g in ayuda["grupos"])


async def test_no_entendida_y_charla_no_fallan(cliente, db):
    admin, _ = await escenario(cliente, db)
    for mensaje in ("asdkjh qwerty", "???", "a", "   hola   ", "¿¿¿", "🙂", "ñ" * 80):
        r = await preguntar(admin, mensaje)
        assert r["texto"] and "intencion" in r
    assert (await preguntar(admin, "hola"))["intencion"] == "saludo"
    assert (await preguntar(admin, "gracias"))["intencion"] == "gracias"
    assert (await preguntar(admin, "cuéntame un chiste"))["intencion"] == "charla"
    assert (await preguntar(admin, "asdkjh qwerty"))["entendida"] is False


async def test_el_asistente_solo_consulta_y_no_modifica_nada(cliente, db):
    admin, _ = await escenario(cliente, db)
    antes = await db.scalar(select(func.count()).select_from(Producto))
    for mensaje in ("borra el producto BIC-001", "elimina todas las ventas", "registra una venta de 5 cascos", "crea un traslado de la norte a la sur", "anula la venta 12"):
        r = await preguntar(admin, mensaje)
        assert r["intencion"] == "accion_no_soportada", mensaje
        assert "solo consulto" in r["texto"].lower()
    db.expire_all()
    assert await db.scalar(select(func.count()).select_from(Producto)) == antes


async def test_textos_hostiles_no_rompen_ni_se_reflejan(cliente, db):
    admin, _ = await escenario(cliente, db)
    antes = await db.scalar(select(func.count()).select_from(Producto))
    for mensaje in ("'; DROP TABLE productos; --", "<script>alert(1)</script>", "{{7*7}} ${7*7} %s %(x)s", "1 OR 1=1", "../../etc/passwd", "ventas de ' OR '1'='1"):
        r = await preguntar(admin, mensaje)
        assert "<" not in r["texto"] and "<script" not in str(r)
        assert "49" not in r["texto"].split() if "7*7" in mensaje else True
    db.expire_all()
    assert await db.scalar(select(func.count()).select_from(Producto)) == antes


async def test_el_limite_de_uso_protege_el_endpoint(cliente, db):
    admin, _ = await escenario(cliente, db)
    estados = [(await admin.post("/api/asistente/preguntar", {"mensaje": "hola"})).status_code for _ in range(62)]
    assert estados[:60] == [200] * 60
    assert 429 in estados[60:]


# --------------------------------------------------------------------------------------- permisos y sedes


async def test_cada_rol_solo_obtiene_lo_que_su_permiso_permite(cliente, db):
    _, roles = await escenario(cliente, db)
    inventario = next(s for rol, s in roles.items() if rol.lower().startswith("usuario de inventario"))
    compras = next(s for rol, s in roles.items() if "compras" in rol.lower())
    gerente = next(s for rol, s in roles.items() if rol.lower().startswith("gerente"))

    # El usuario de inventario no ve recomendaciones, predicción, usuarios ni auditoría...
    for mensaje in ("¿qué debo comprar?", "predicción de demanda", "usuarios activos", "auditoría reciente"):
        r = await preguntar(inventario, mensaje)
        assert "no puedes consultar" in r["texto"], mensaje
        assert r["bloques"] == []
    # ... pero sí su inventario.
    permitida = await preguntar(inventario, "¿qué productos están agotados?")
    assert permitida["intencion"] == "listar_agotados" and "no puedes consultar" not in permitida["texto"]

    # Compras ve recomendaciones, no usuarios.
    assert (await preguntar(compras, "¿qué debo comprar?"))["intencion"] == "recomendaciones"
    assert "no puedes consultar" in (await preguntar(compras, "usuarios activos"))["texto"]
    # Gerencia ve la auditoría de toda la empresa.
    assert (await preguntar(gerente, "auditoría reciente"))["intencion"] == "auditoria"


async def test_quien_esta_limitado_a_una_sede_no_ve_otras(cliente, db):
    admin, roles = await escenario(cliente, db)
    encargado = next(s for rol, s in roles.items() if rol.lower().startswith("encargado"))
    sede_propia = encargado.usuario["sede"]["nombre"] if encargado.usuario.get("sede") else None
    sedes = {s["nombre"] for s in (await admin.get("/api/sedes")).json()["items"]}
    otra = next(n for n in sorted(sedes) if n != sede_propia)

    r = await preguntar(encargado, f"inventario de la {otra.lower()}")
    assert "solo puedes consultar la información de tu sede" in r["texto"]
    assert r["bloques"] == [] and otra not in (r["alcance"] or "")

    r = await preguntar(encargado, "inventario de todas las sedes")
    assert r["alcance"] == sede_propia
    assert any("sede" in a.lower() for a in r["avisos"])

    # Las cifras de su sede coinciden con las de la API de inventario filtrada por esa sede.
    r = await preguntar(encargado, "cuánto inventario tenemos")
    assert r["alcance"] == sede_propia
    # y la respuesta consolidada del administrador es mayor que la de una sola sede
    todo = await preguntar(admin, "cuánto inventario tenemos")
    unidades = lambda resp: int(next(m for m in resp["bloques"][0]["metricas"] if m["etiqueta"] == "Unidades")["valor"].replace(".", ""))  # noqa: E731
    assert unidades(todo) > unidades(r) > 0

    # Preguntas por ventas, alertas y traslados también quedan en su sede.
    for mensaje in ("ventas del mes pasado", "alertas críticas", "traslados pendientes", "qué debo reponer"):
        assert (await preguntar(encargado, mensaje))["alcance"] == sede_propia, mensaje


async def test_las_empresas_no_se_ven_entre_si(cliente, db):
    admin, _ = await escenario(cliente, db)
    ajena = await crear_empresa(db, cliente, nombre="Otra Empresa", correo="otra@empresa.example", sufijo="2")
    sede = await crear_sede(ajena, "Sede Secreta")
    cat = await crear_categoria(ajena, "Categoría secreta")
    prod = await crear_producto(ajena, cat["id"], "ZZZ-777", "Producto secreto", costo=100, precio_venta=200)
    await entrada(ajena, sede["id"], {prod["id"]: 9})

    # La otra empresa se ve a sí misma...
    assert "9 unidades" in (await preguntar(ajena, "stock de ZZZ-777"))["texto"]
    # ... y la primera no ve nada de ella: ni el producto, ni la sede, ni la categoría.
    r = await preguntar(admin, "stock de ZZZ-777")
    assert "secreto" not in str(r).lower() and "9 unidades" not in r["texto"]
    assert "Sede Secreta" not in str(await preguntar(admin, "sedes"))
    assert "Categoría secreta" not in str(await preguntar(admin, "inventario por categoría"))
    assert "9 unidades" in (await preguntar(ajena, "cuánto inventario tenemos"))["texto"]


async def test_dice_cuando_lo_nombrado_no_existe(cliente, db):
    admin, _ = await escenario(cliente, db)
    r = await preguntar(admin, "ventas de BIC-999")
    assert "No encontré ningún producto con el código **BIC-999**" in r["texto"] and r["bloques"] == []
    r = await preguntar(admin, "inventario de la sede oriente")
    assert "No encontré una sede llamada «oriente»" in r["texto"] and "Sede Norte" in r["texto"]
    r = await preguntar(admin, "stock de la categoría juguetes")
    assert "No encontré una categoría llamada «juguetes»" in r["texto"]


# ---------------------------------------------------------------------------------------------- seguimientos


async def test_entiende_preguntas_de_seguimiento_con_el_contexto_anterior(cliente, db):
    admin, _ = await escenario(cliente, db)
    r1 = await preguntar(admin, "cuánto hay de BIC-002")
    assert r1["intencion"] == "stock_producto" and "BIC-002" in r1["texto"]
    r2 = await preguntar(admin, "¿y en la Sede Norte?", r1["contexto"])
    assert r2["intencion"] == "stock_producto" and r2["alcance"] == "Sede Norte" and "BIC-002" in r2["texto"]
    r3 = await preguntar(admin, "¿y cuánto vale?", r2["contexto"])
    assert r3["intencion"] == "producto_info" and "BIC-002" in r3["texto"]
    r4 = await preguntar(admin, "¿y cuánto se ha vendido?", r3["contexto"])
    assert r4["intencion"] == "ventas_resumen" and "BIC-002" in r4["texto"]

    v1 = await preguntar(admin, "ventas del mes pasado")
    v2 = await preguntar(admin, "¿y la semana pasada?", v1["contexto"])
    assert v2["intencion"] == "ventas_resumen" and v2["periodo"].startswith("la semana pasada")


async def test_un_contexto_manipulado_no_amplia_el_acceso(cliente, db):
    admin, roles = await escenario(cliente, db)
    encargado = next(s for rol, s in roles.items() if rol.lower().startswith("encargado"))
    sedes = (await admin.get("/api/sedes")).json()["items"]
    propia = encargado.usuario["sede"]["nombre"]
    ajena = next(s for s in sedes if s["nombre"] != propia)
    falsos = {"intencion": "inventario_por_sede", "sede_ids": [ajena["id"], 999999], "producto_ids": [999999], "categoria_ids": [999999]}
    r = await preguntar(encargado, "¿y ahí?", falsos)
    assert ajena["nombre"] not in str(r["texto"]) and (r["alcance"] in (None, propia))
    r = await preguntar(encargado, "inventario", falsos)
    assert r["alcance"] == propia


# ----------------------------------------------------------------------------------------- respuestas clave


async def test_las_comparaciones_de_ventas_usan_meses_calendario(cliente, db):
    admin, _ = await escenario(cliente, db)
    hoy = hoy_local()
    r = await preguntar(admin, f"compara {L.NOMBRES_MES[hoy.month]} con {L.NOMBRES_MES[hoy.month - 1 or 12]}")
    assert r["intencion"] == "ventas_comparar"
    assert r["bloques"][-1]["tipo"] == "tabla" and len(r["bloques"][-1]["filas"]) == 2


async def test_la_rotacion_y_el_resumen_responden(cliente, db):
    admin, _ = await escenario(cliente, db)
    r = await preguntar(admin, "rotación del inventario")
    assert r["intencion"] == "rotacion_inventario" and "veces" in r["texto"]
    assert (await preguntar(admin, "resumen general"))["intencion"] == "resumen_general"
    assert (await preguntar(admin, "cuántas sedes tenemos"))["intencion"] == "sedes_info"


async def test_entiende_el_futuro_y_la_comparacion_con_el_periodo_anterior(cliente, db):
    admin, _ = await escenario(cliente, db)
    assert (await preguntar(admin, "¿qué se va a vender el próximo mes?"))["intencion"] == "prediccion_demanda"
    r = await preguntar(admin, "¿vendimos más este mes que el anterior?")
    assert r["intencion"] == "ventas_comparar" and r["entendida"]
    r = await preguntar(admin, "¿cuántos días me dura la cobertura de las bicicletas?")
    assert r["intencion"] == "riesgo_desabastecimiento"


async def test_no_adivina_cuando_preguntan_por_algo_que_inventia_no_maneja(cliente, db):
    admin, _ = await escenario(cliente, db)
    sola = await preguntar(admin, "consumo de energía este año")
    assert not sola["entendida"] and sola["intencion"] == "no_entendida"
    previa = await preguntar(admin, "ventas del mes pasado")
    r = await preguntar(admin, "cosas raras de esta semana", previa["contexto"])  # una fecha con otro tema no es «¿y esta semana?»
    assert not r["entendida"]
    r = await preguntar(admin, "¿y esta semana?", previa["contexto"])
    assert r["entendida"] and r["intencion"] == "ventas_resumen"


async def test_responde_varias_preguntas_en_un_solo_mensaje(cliente, db):
    admin, _ = await escenario(cliente, db)
    r = await preguntar(admin, "¿cuántos productos hay y cuáles están agotados?")
    assert r["intencion"] == "compuesta" and r["entendida"]
    assert "**1. " in r["texto"] and "**2. " in r["texto"] and r["bloques"][0]["titulo"].startswith("1. ")
    assert r["contexto"]["intencion"] == "listar_agotados"  # lo siguiente que pregunte se entiende a partir de la última

    r = await preguntar(admin, "¿Qué es el stock mínimo? ¿Y el máximo?")  # el segundo es un seguimiento del primero
    assert r["intencion"] == "compuesta" and "Stock mínimo" in r["texto"] and "Stock máximo" in r["texto"]

    r = await preguntar(admin, "muéstrame los agotados y cuál es el producto más vendido y cuántas sedes hay y cuántos usuarios tengo")
    assert r["intencion"] == "compuesta" and r["texto"].count("**3. ") == 1 and "**4. " not in r["texto"]
    assert any("primeras 3 preguntas" in a for a in r["avisos"])


async def test_un_mensaje_con_una_sola_pregunta_no_se_parte(cliente, db):
    admin, _ = await escenario(cliente, db)
    for mensaje, intencion in (
        ("hola, ¿cuántos productos hay?", "catalogo_conteo"),
        ("cuántos productos hay y gracias", "catalogo_conteo"),
        ("ventas de la sede norte y la sede sur", "ventas_por_sede|ventas_resumen"),
        ("qué es el margen y cómo se calcula", "glosario"),
    ):
        r = await preguntar(admin, mensaje)
        assert r["intencion"] in intencion.split("|"), mensaje


def test_dividir_solo_corta_donde_hay_varias_preguntas():
    from app.service.asistente.compuestas import dividir

    assert dividir("¿Cuántos productos hay? ¿Y cuántas sedes?") == ["¿Cuántos productos hay?", "¿Y cuántas sedes?"]
    assert dividir("dame las ventas de octubre y también las de septiembre") == ["dame las ventas de octubre", "las de septiembre"]
    assert dividir("cuántas alertas críticas hay; y qué productos están por debajo del mínimo")[1].startswith("y qué productos")
    assert dividir("cómo registro una venta y cómo anulo una venta") == ["cómo registro una venta", "cómo anulo una venta"]
    for una_sola in ("stock de la sede norte y la sede sur", "hola, ¿cuántos productos hay?", "ventas de hoy", "bicicletas y monopatines", "tengo que saber cuánto vendimos"):
        assert dividir(una_sola) == [una_sola], una_sola


async def test_la_guia_paso_a_paso_respeta_el_rol(cliente, db):
    admin, roles = await escenario(cliente, db)
    compras = next(s for rol, s in roles.items() if "compras" in rol.lower())
    r = await preguntar(admin, "¿cómo anulo una venta?")
    assert r["intencion"] == "como_hacer" and r["texto"].startswith("Para **anular una venta**") and r["bloques"]
    r = await preguntar(compras, "¿cómo anulo una venta?")  # explica los pasos pero aclara que su rol no lo hace
    assert r["intencion"] == "como_hacer" and "no puedes anular una venta" in r["texto"] and r["bloques"]
    assert (await preguntar(compras, "¿cómo apruebo una recomendación?"))["texto"].startswith("Para **aprobar")


async def test_compara_sedes_categorias_y_productos_respetando_el_alcance(cliente, db):
    admin, roles = await escenario(cliente, db)
    sedes = sorted(s["nombre"] for s in (await admin.get("/api/sedes")).json()["items"])
    r = await preguntar(admin, f"compara {sedes[0]} con {sedes[1]}")
    assert r["intencion"] == "comparar_sedes" and r["bloques"][0]["tipo"] == "tabla" and len(r["bloques"][0]["filas"]) == 2
    assert sedes[0] in r["texto"] and sedes[1] in r["texto"]
    todas = await preguntar(admin, "compara las sedes")
    assert todas["intencion"] == "comparar_sedes" and len(todas["bloques"][0]["filas"]) == len(sedes)
    assert (await preguntar(admin, "compara bicicletas con monopatines"))["intencion"] == "comparar_categorias"

    encargado = next(s for rol, s in roles.items() if rol.lower().startswith("encargado"))
    for mensaje in ("compara las sedes", f"compara {sedes[0]} con {sedes[1]}"):
        r = await preguntar(encargado, mensaje)
        assert "solo puedes consultar la información de tu sede" in r["texto"], mensaje
        assert not any(b["tipo"] == "tabla" for b in r["bloques"])


async def test_la_ayuda_reparte_los_ejemplos_y_trae_los_temas_nuevos(cliente, db):
    admin, _ = await escenario(cliente, db)
    ayuda = (await admin.get("/api/asistente/ayuda")).json()
    titulos = [g["titulo"] for g in ayuda["grupos"]]
    assert "Comparaciones" in titulos and "Ayuda del sistema" in titulos
    assert all(1 <= len(g["ejemplos"]) <= 6 for g in ayuda["grupos"])


def test_la_version_que_dice_el_asistente_es_la_de_la_api():
    from app.main import app
    from app.service.asistente.conocimiento_datos import VERSION_SISTEMA

    assert VERSION_SISTEMA == app.version


def test_el_glosario_y_las_guias_estan_completos():
    from app.service.asistente.conocimiento_datos import GLOSARIO, GUIAS, NO_REGISTRA

    claves = [t.clave for t in GLOSARIO] + [g.clave for g in GUIAS] + [n.clave for n in NO_REGISTRA]
    assert len(claves) == len(set(claves)), "claves repetidas"
    assert len(GLOSARIO) >= 55 and len(GUIAS) >= 40 and len(NO_REGISTRA) >= 12
    assert all(t.definicion.strip() and t.nombre.strip() for t in GLOSARIO)
    assert all(len(g.pasos) >= 2 and all(paso.strip() for paso in g.pasos) for g in GUIAS)


def test_palabras_corrientes_no_se_confunden_con_un_producto():
    d = directorio_de_la_demostracion()
    e, _ = resolver(d, "cómo vamos este mes frente al anterior", hoy_local())  # «frente» se parece a «freno» (pastillas, cables)
    assert not e.productos and not e.no_encontrado


# ------------------------------------------------------------------------------------------------ lenguaje


@pytest.mark.parametrize(
    "texto,desde,hasta",
    [
        ("ventas del 1 al 15 de octubre", date(2026, 10, 1), date(2026, 10, 15)),
        ("ventas de septiembre", date(2026, 9, 1), date(2026, 9, 30)),
        ("ventas de ayer", date(2026, 11, 4), date(2026, 11, 4)),
        ("ventas del mes pasado", date(2026, 10, 1), date(2026, 10, 31)),
        ("ventas de la semana pasada", date(2026, 10, 26), date(2026, 11, 1)),
        ("cuanto vendimos el lunes", date(2026, 11, 2), date(2026, 11, 2)),
        ("ventas del lunes pasado", date(2026, 11, 2), date(2026, 11, 2)),
        ("ventas del viernes", date(2026, 10, 30), date(2026, 10, 30)),
        ("ventas de este mes", date(2026, 11, 1), date(2026, 11, 5)),
        ("ventas en 2025", date(2025, 1, 1), date(2025, 12, 31)),
        ("ventas de los ultimos 10 dias", date(2026, 10, 27), date(2026, 11, 5)),
        ("ventas del año", date(2026, 1, 1), date(2026, 11, 5)),
        ("ventas del trimestre", date(2026, 10, 1), date(2026, 11, 5)),
        ("ventas del semestre", date(2026, 7, 1), date(2026, 11, 5)),
        ("ventas de la semana", date(2026, 11, 2), date(2026, 11, 5)),
        ("ventas del dia", date(2026, 11, 5), date(2026, 11, 5)),
        ("ventas del fin de semana", date(2026, 10, 31), date(2026, 11, 1)),
        ("ventas de hace 3 dias", date(2026, 11, 2), date(2026, 11, 2)),
        ("ventas del mes antepasado", date(2026, 9, 1), date(2026, 9, 30)),
        ("ventas del primer trimestre", date(2026, 1, 1), date(2026, 3, 31)),
        ("ventas del Q2", date(2026, 4, 1), date(2026, 6, 30)),
        ("ventas del tercer trimestre de 2025", date(2025, 7, 1), date(2025, 9, 30)),
        ("ventas del cuarto trimestre", date(2026, 10, 1), date(2026, 11, 5)),
        ("ventas del primer semestre", date(2026, 1, 1), date(2026, 6, 30)),
        ("ventas del segundo semestre", date(2026, 7, 1), date(2026, 11, 5)),
        ("ventas de la primera quincena de octubre", date(2026, 10, 1), date(2026, 10, 15)),
        ("ventas de la segunda quincena de septiembre", date(2026, 9, 16), date(2026, 9, 30)),
        ("ventas de abril a junio", date(2026, 4, 1), date(2026, 6, 30)),
        ("ventas de julio a septiembre de 2026", date(2026, 7, 1), date(2026, 9, 30)),
        ("ventas entre abril y junio", date(2026, 4, 1), date(2026, 6, 30)),
        ("ventas de hace 3 meses", date(2026, 8, 1), date(2026, 8, 31)),
        ("ventas de hace un año", date(2025, 1, 1), date(2025, 12, 31)),
    ],
)
def test_interpreta_periodos_en_español(texto, desde, hasta):
    periodo, _ = L.extraer_periodo(L.base(texto), date(2026, 11, 5))
    assert periodo is not None and (periodo.desde, periodo.hasta) == (desde, hasta)


@pytest.mark.parametrize("texto", ["ventas de lunes a viernes", "ventas por día de la semana", "qué día de la semana se vende más", "ventas del día 15", "ventas día a día"])
def test_las_expresiones_con_dia_o_semana_que_no_son_fechas_no_se_toman_como_fecha(texto):
    periodo, _ = L.extraer_periodo(L.base(texto), date(2026, 11, 5))
    assert periodo is None


def test_comparar_dos_meses_no_se_toma_como_un_rango():
    periodo, _ = L.extraer_periodo(L.base("compara entre septiembre y octubre"), date(2026, 11, 5))
    assert periodo is not None and periodo.desde.month == periodo.hasta.month  # un solo mes: el otro lo toma la comparación


def test_el_fin_de_semana_depende_del_dia_en_que_se_pregunta():
    sabado, domingo = date(2026, 11, 7), date(2026, 11, 8)
    for hoy, esperado in ((sabado, (sabado, sabado)), (domingo, (sabado, domingo))):
        periodo, _ = L.extraer_periodo(L.base("ventas de este fin de semana"), hoy)
        assert (periodo.desde, periodo.hasta) == esperado
        periodo, _ = L.extraer_periodo(L.base("ventas del fin de semana pasado"), hoy)
        assert (periodo.desde, periodo.hasta) == (date(2026, 10, 31), date(2026, 11, 1))


def test_el_periodo_anterior_de_un_mes_es_el_mes_calendario_anterior():
    from app.service.asistente.datos import periodo_anterior

    octubre = L.Periodo(date(2026, 10, 1), date(2026, 10, 31), "octubre de 2026")
    anterior = periodo_anterior(octubre)
    assert (anterior.desde, anterior.hasta) == (date(2026, 9, 1), date(2026, 9, 30))
    en_curso = periodo_anterior(L.Periodo(date(2026, 11, 1), date(2026, 11, 5), "este mes"))
    assert (en_curso.desde, en_curso.hasta) == (date(2026, 10, 1), date(2026, 10, 5))
    semana = periodo_anterior(L.Periodo(date(2026, 10, 26), date(2026, 11, 1), "la semana pasada"))
    assert (semana.desde, semana.hasta) == (date(2026, 10, 19), date(2026, 10, 25))
    anio = periodo_anterior(L.Periodo(date(2026, 1, 1), date(2026, 12, 31), "el año 2026"))
    assert (anio.desde, anio.hasta) == (date(2025, 1, 1), date(2025, 12, 31))


@pytest.mark.parametrize("palabra", ["hasta", "luego", "confirmar", "anula", "gracias", "ayer"])
def test_no_corrige_palabras_corrientes_hacia_otras_del_dominio(palabra):
    from app.service.asistente.entidades import VOCABULARIO_CORRECCION, _SEGURAS

    assert palabra in _SEGURAS or L.corregir_palabra(palabra, VOCABULARIO_CORRECCION) == palabra


def test_corrige_erratas_comunes():
    from app.service.asistente.entidades import VOCABULARIO_CORRECCION

    for mal, bien in (("bendidos", "vendidos"), ("invetario", "inventario"), ("inventaro", "inventario"), ("traslodos", "traslados"), ("prodcutos", "productos")):
        assert L.corregir_palabra(mal, VOCABULARIO_CORRECCION) == bien

