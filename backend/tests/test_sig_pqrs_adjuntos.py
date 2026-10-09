"""SIG · PQRS y evidencias adjuntas."""

import struct
import zlib

from tests.ayuda import crear_categoria, crear_empresa, crear_producto, crear_sede, crear_usuario


def png_minimo() -> bytes:
    def trozo(tipo: bytes, datos: bytes) -> bytes:
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF)

    return (
        b"\x89PNG\r\n\x1a\n" + trozo(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + trozo(b"IDAT", zlib.compress(b"\x00\xff\x00\x00")) + trozo(b"IEND", b"")
    )


async def subir(sesion, entidad, entidad_id, contenido: bytes, nombre="evidencia.png"):
    return await sesion.cliente.post(
        f"/api/sig/adjuntos?entidad={entidad}&entidad_id={entidad_id}&nombre={nombre}",
        content=contenido, headers={**sesion.cabeceras, "Content-Type": "application/octet-stream"},
    )


async def escenario(cliente, db):
    admin = await crear_empresa(db, cliente)
    norte = await crear_sede(admin, "Norte")
    ana = await crear_usuario(admin, "usuario_inventario", "ana@andina.com", norte["id"], nombre="Ana Operaria")
    luis = await crear_usuario(admin, "usuario_inventario", "luis@andina.com", norte["id"], nombre="Luis Operario")
    return admin, norte, ana, luis


async def nueva(sesion, **extra):
    datos = {"tipo": "queja", "asunto": "La pantalla de ventas tarda", "descripcion": "Al registrar una venta con varias líneas demora mucho.", **extra}
    r = await sesion.post("/api/sig/pqrs", datos)
    assert r.status_code == 201, r.text
    return r.json()


# ----------------------------------------------------------------------------- PQRS


async def test_pqrs_flujo_completo(cliente, db):
    admin, norte, ana, luis = await escenario(cliente, db)
    p = await nueva(ana)
    assert p["numero"] == 1 and p["estado"] == "pendiente" and p["usuario_nombre"] == "Ana Operaria"
    assert p["sede"]["id"] == norte["id"] and p["respuesta"] is None
    assert [e["evento"] for e in p["historial"]] == ["creacion"]

    # Ana ve la suya; Luis no; el administrador ve todas.
    assert (await ana.get("/api/sig/pqrs")).json()["total"] == 1
    assert (await luis.get("/api/sig/pqrs")).json()["total"] == 0
    assert (await admin.get("/api/sig/pqrs?ambito=todas")).json()["total"] == 1
    assert (await luis.get(f"/api/sig/pqrs/{p['id']}")).status_code == 403
    assert (await luis.get("/api/sig/pqrs?ambito=todas")).status_code == 403

    # Solo la administración gestiona.
    assert (await ana.patch(f"/api/sig/pqrs/{p['id']}", {"estado": "en_revision"})).status_code == 403
    r = await admin.patch(f"/api/sig/pqrs/{p['id']}", {"estado": "en_revision"})
    assert r.status_code == 200 and r.json()["estado"] == "en_revision"
    r = await admin.patch(f"/api/sig/pqrs/{p['id']}", {"estado": "en_proceso", "respuesta": "Estamos optimizando la consulta."})
    assert r.json()["estado"] == "en_proceso" and r.json()["respuesta"] == "Estamos optimizando la consulta."

    # Resolver exige respuesta; si ya existe una, alcanza.
    r = await admin.patch(f"/api/sig/pqrs/{p['id']}", {"estado": "resuelta"})
    assert r.status_code == 200 and r.json()["estado"] == "resuelta"
    q = await nueva(ana, tipo="sugerencia", asunto="Agregar filtro por categoría")
    r = await admin.patch(f"/api/sig/pqrs/{q['id']}", {"estado": "resuelta"})
    assert r.status_code == 400 and r.json()["codigo"] == "respuesta_requerida"
    r = await admin.patch(f"/api/sig/pqrs/{q['id']}", {"estado": "pendiente"})
    assert r.status_code == 400 and r.json()["codigo"] == "sin_cambios"

    # La persona ve el estado final, la respuesta y TODO el historial (fecha, usuario, cambio).
    detalle = (await ana.get(f"/api/sig/pqrs/{p['id']}")).json()
    assert detalle["estado"] == "resuelta" and detalle["respuesta"]
    assert [(e["evento"], e["estado_anterior"], e["estado_nuevo"]) for e in detalle["historial"]] == [
        ("creacion", None, "pendiente"), ("estado", "pendiente", "en_revision"),
        ("estado", "en_revision", "en_proceso"), ("estado", "en_proceso", "resuelta"),
    ]
    assert detalle["historial"][2]["comentario"] == "Estamos optimizando la consulta."
    assert detalle["historial"][1]["usuario_nombre"] == "Administrador Demo"


async def test_pqrs_filtros_y_conteo(cliente, db):
    admin, norte, ana, luis = await escenario(cliente, db)
    a = await nueva(ana, tipo="peticion", asunto="Solicito acceso a reportes")
    await nueva(luis, tipo="reclamo", asunto="Cobro duplicado en venta")
    await nueva(luis, tipo="sugerencia", asunto="Modo oscuro")
    await admin.patch(f"/api/sig/pqrs/{a['id']}", {"estado": "en_revision"})

    def ids(r):
        return [x["asunto"] for x in r.json()["items"]]

    assert ids(await admin.get("/api/sig/pqrs?ambito=todas&tipo=reclamo")) == ["Cobro duplicado en venta"]
    assert ids(await admin.get("/api/sig/pqrs?ambito=todas&estado=en_revision")) == ["Solicito acceso a reportes"]
    assert (await admin.get(f"/api/sig/pqrs?ambito=todas&usuario_id={luis.usuario['id']}")).json()["total"] == 2
    assert ids(await admin.get("/api/sig/pqrs?ambito=todas&q=oscuro")) == ["Modo oscuro"]
    assert (await admin.get("/api/sig/pqrs?ambito=todas&q=1")).json()["total"] == 1  # por número de radicado
    assert (await admin.get("/api/sig/pqrs?ambito=todas&desde=2999-01-01")).json()["total"] == 0
    conteo = (await admin.get("/api/sig/pqrs/conteo")).json()
    assert conteo == {"total": 3, "pendiente": 2, "en_revision": 1, "en_proceso": 0, "resuelta": 0}
    assert (await ana.get("/api/sig/pqrs/conteo")).status_code == 403


async def test_pqrs_validaciones(cliente, db):
    admin, norte, ana, luis = await escenario(cliente, db)
    r = await ana.post("/api/sig/pqrs", {"tipo": "queja", "asunto": "Hola", "descripcion": "corto"})
    assert r.status_code == 422
    r = await ana.post("/api/sig/pqrs", {"tipo": "otro", "asunto": "Asunto válido", "descripcion": "Descripción suficientemente larga"})
    assert r.status_code == 422
    r = await ana.post("/api/sig/pqrs", {"tipo": "queja", "asunto": "Asunto válido", "descripcion": "Descripción suficientemente larga", "estado": "resuelta"})
    assert r.status_code == 422  # no se puede crear una solicitud ya resuelta
    p = await nueva(ana)
    assert (await admin.patch(f"/api/sig/pqrs/{p['id']}", {})).status_code == 422
    assert (await cliente.get("/api/sig/pqrs")).status_code == 401


async def test_pqrs_aisladas_entre_empresas(cliente, db):
    admin, norte, ana, luis = await escenario(cliente, db)
    p = await nueva(ana)
    otra = await crear_empresa(db, cliente, nombre="Otra SAS", correo="admin@otra.com", sufijo="2")
    assert (await otra.get(f"/api/sig/pqrs/{p['id']}")).status_code == 404
    assert (await otra.get("/api/sig/pqrs?ambito=todas")).json()["total"] == 0


# ----------------------------------------------------------------------------- evidencias


async def test_adjuntos_pqrs_subir_descargar_eliminar(cliente, db):
    admin, norte, ana, luis = await escenario(cliente, db)
    p = await nueva(ana)
    png = png_minimo()
    r = await subir(ana, "pqrs", p["id"], png, "captura de pantalla.PNG")
    assert r.status_code == 201, r.text
    adj = r.json()
    assert adj["nombre"] == "captura de pantalla.png" and adj["tipo_mime"] == "image/png" and adj["tamano"] == len(png)

    detalle = (await admin.get(f"/api/sig/pqrs/{p['id']}")).json()
    assert [a["id"] for a in detalle["archivos"]] == [adj["id"]]
    d = await admin.get(f"/api/sig/adjuntos/{adj['id']}/archivo")
    assert d.status_code == 200 and d.content == png
    assert d.headers["content-type"] == "image/png" and d.headers["x-content-type-options"] == "nosniff"
    assert "attachment" in d.headers["content-disposition"]

    # Quien no es dueño ni gestor no ve ni descarga ni elimina.
    assert (await luis.get(f"/api/sig/adjuntos/{adj['id']}/archivo")).status_code == 403
    assert (await luis.delete(f"/api/sig/adjuntos/{adj['id']}")).status_code == 403
    assert (await subir(luis, "pqrs", p["id"], png)).status_code == 403

    assert (await ana.delete(f"/api/sig/adjuntos/{adj['id']}")).status_code == 200
    assert (await ana.get(f"/api/sig/adjuntos?entidad=pqrs&entidad_id={p['id']}")).json() == []
    assert (await ana.get(f"/api/sig/adjuntos/{adj['id']}/archivo")).status_code == 404


async def test_adjuntos_rechaza_archivos_peligrosos_o_excesivos(cliente, db):
    admin, norte, ana, luis = await escenario(cliente, db)
    p = await nueva(ana)
    # Un ejecutable renombrado como imagen se rechaza: manda el CONTENIDO, no la extensión.
    r = await subir(ana, "pqrs", p["id"], b"MZ\x90\x00" + b"\x00" * 200, "foto.png")
    assert r.status_code == 400 and r.json()["codigo"] == "tipo_no_permitido"
    r = await subir(ana, "pqrs", p["id"], b"<script>alert(1)</script>", "x.html")
    assert r.status_code == 400 and r.json()["codigo"] == "tipo_no_permitido"
    r = await subir(ana, "pqrs", p["id"], b"")
    assert r.status_code == 400 and r.json()["codigo"] == "archivo_vacio"
    r = await subir(ana, "pqrs", p["id"], png_minimo() + b"0" * (3 * 1024 * 1024))
    assert r.status_code == 400 and r.json()["codigo"] == "archivo_muy_grande"
    # El nombre no puede escapar de la carpeta ni traer caracteres de control.
    ok = await subir(ana, "pqrs", p["id"], b"%PDF-1.4\n%%EOF", "../../etc/pass%00wd.pdf")
    assert ok.status_code == 201 and "/" not in ok.json()["nombre"] and ok.json()["nombre"].endswith(".pdf")
    # Máximo 5 por registro.
    for _ in range(4):
        assert (await subir(ana, "pqrs", p["id"], png_minimo())).status_code == 201
    r = await subir(ana, "pqrs", p["id"], png_minimo())
    assert r.status_code == 400 and r.json()["codigo"] == "demasiados_archivos"


async def test_adjuntos_pqrs_resuelta_no_admite_mas_a_quien_la_envio(cliente, db):
    admin, norte, ana, luis = await escenario(cliente, db)
    p = await nueva(ana)
    await admin.patch(f"/api/sig/pqrs/{p['id']}", {"estado": "resuelta", "respuesta": "Listo, ya quedó corregido."})
    r = await subir(ana, "pqrs", p["id"], png_minimo())
    assert r.status_code == 400 and r.json()["codigo"] == "registro_cerrado"
    assert (await subir(admin, "pqrs", p["id"], png_minimo())).status_code == 201
