"""Empresa, sedes, usuarios y roles (RF-007 a RF-014, RF-038) y aislamiento entre empresas (RNF-020)."""

from sqlalchemy import select

from app.models.auditoria import Auditoria
from tests.ayuda import PASSWORD, crear_empresa, crear_sede, crear_usuario, iniciar_sesion, roles_por_clave

# ---------- Empresa ----------


async def test_empresa_consultar_y_modificar(cliente, db):
    admin = await crear_empresa(db, cliente)
    r = await admin.get("/api/empresa")
    assert r.status_code == 200 and r.json()["nombre"] == "Distribuidora Andina"
    r = await admin.put("/api/empresa", {"nombre": "Andina Distribuciones", "ciudad": "Medellín"})
    assert r.status_code == 200 and r.json()["ciudad"] == "Medellín"


async def test_parametros_de_empresa_se_validan(cliente, db):
    admin = await crear_empresa(db, cliente)
    r = await admin.put("/api/empresa/parametros", {"plazo_entrega_dias": 10, "dias_seguridad": 2})
    assert r.status_code == 200, r.text
    assert r.json()["parametros"]["plazo_entrega_dias"] == 10
    assert r.json()["parametros"]["dias_cobertura_objetivo"] == 21  # conserva el resto
    r = await admin.put("/api/empresa/parametros", {"plazo_entrega_dias": -3})
    assert r.status_code == 422


async def test_dos_empresas_no_pueden_repetir_identificacion(cliente, db):
    await crear_empresa(db, cliente)
    from app.core.exceptions import Conflicto
    from app.services import setup_service

    try:
        await setup_service.crear_empresa_con_admin(
            db, nombre="Otra", identificacion="900100000-1", direccion=None, ciudad=None, telefono=None,
            email_empresa=None, admin_nombre="X Y", admin_email="otro@otra.com", admin_password=PASSWORD,
        )
    except Conflicto as e:
        assert e.codigo == "identificacion_duplicada"
    else:
        raise AssertionError("debió rechazar la identificación repetida")


# ---------- Sedes ----------


async def test_crud_sedes(cliente, db):
    admin = await crear_empresa(db, cliente)
    s = await crear_sede(admin, "Sede Norte", direccion="Calle 100 # 15-20")
    assert s["activa"] is True
    r = await admin.get("/api/sedes")
    assert r.json()["total"] == 1
    r = await admin.put(f"/api/sedes/{s['id']}", {"nombre": "Sede Norte Principal"})
    assert r.status_code == 200 and r.json()["nombre"] == "Sede Norte Principal"
    r = await admin.get("/api/sedes?q=principal")
    assert r.json()["total"] == 1
    r = await admin.get("/api/sedes?q=zzz")
    assert r.json()["total"] == 0


async def test_nombre_de_sede_unico_sin_importar_mayusculas(cliente, db):
    admin = await crear_empresa(db, cliente)
    await crear_sede(admin, "Centro")
    r = await admin.post("/api/sedes", {"nombre": "  CENTRO ", "ciudad": "Cali"})
    assert r.status_code == 409


async def test_sede_inhabilitar_y_reactivar(cliente, db):
    admin = await crear_empresa(db, cliente)
    s = await crear_sede(admin)
    r = await admin.patch(f"/api/sedes/{s['id']}/estado", {"activa": False})
    assert r.status_code == 200 and r.json()["activa"] is False
    r = await admin.patch(f"/api/sedes/{s['id']}/estado", {"activa": True})
    assert r.json()["activa"] is True


async def test_validaciones_de_sede_en_espanol(cliente, db):
    admin = await crear_empresa(db, cliente)
    r = await admin.post("/api/sedes", {"nombre": "", "ciudad": ""})
    assert r.status_code == 422
    assert r.json()["detail"] == "Hay datos que no son válidos"
    assert {e["campo"] for e in r.json()["errores"]} >= {"nombre", "ciudad"}


# ---------- Usuarios ----------


async def test_crud_usuarios_y_roles_de_sede(cliente, db):
    admin = await crear_empresa(db, cliente)
    sede = await crear_sede(admin)
    enc = await crear_usuario(admin, "encargado_sede", "enc@andina.com", sede["id"])
    assert enc.usuario["rol"]["clave"] == "encargado_sede"
    assert enc.usuario["sede"]["id"] == sede["id"]
    r = await admin.get("/api/usuarios")
    assert r.json()["total"] == 2


async def test_rol_de_sede_exige_sede_y_rol_de_empresa_no_la_admite(cliente, db):
    admin = await crear_empresa(db, cliente)
    roles = await roles_por_clave(admin)
    sede = await crear_sede(admin)
    base = {"nombre": "Persona Uno", "email": "uno@andina.com", "password": PASSWORD}
    r = await admin.post("/api/usuarios", {**base, "rol_id": roles["encargado_sede"]["id"]})
    assert r.status_code in (400, 422)  # falta la sede
    r = await admin.post("/api/usuarios", {**base, "email": "dos@andina.com", "rol_id": roles["gerente"]["id"], "sede_id": sede["id"]})
    assert r.status_code == 201 and r.json()["sede"] is None  # un gerente opera sobre toda la empresa


async def test_correo_de_usuario_unico(cliente, db):
    admin = await crear_empresa(db, cliente)
    roles = await roles_por_clave(admin)
    cuerpo = {"nombre": "Ana Ruiz", "email": "ana@andina.com", "password": PASSWORD, "rol_id": roles["gerente"]["id"]}
    assert (await admin.post("/api/usuarios", cuerpo)).status_code == 201
    r = await admin.post("/api/usuarios", {**cuerpo, "email": "ANA@andina.com"})
    assert r.status_code == 409


async def test_no_se_puede_inhabilitar_al_ultimo_administrador(cliente, db):
    admin = await crear_empresa(db, cliente)
    r = await admin.patch(f"/api/usuarios/{admin.usuario['id']}/estado", {"activo": False})
    assert r.status_code == 400
    assert r.json()["codigo"] == "auto_inhabilitacion"


async def test_no_se_puede_quitar_el_rol_al_ultimo_administrador(cliente, db):
    admin = await crear_empresa(db, cliente)
    roles = await roles_por_clave(admin)
    r = await admin.put(f"/api/usuarios/{admin.usuario['id']}", {"rol_id": roles["gerente"]["id"]})
    assert r.status_code == 409 and r.json()["codigo"] == "ultimo_administrador"


async def test_usuario_inhabilitado_pierde_acceso(cliente, db):
    admin = await crear_empresa(db, cliente)
    g = await crear_usuario(admin, "gerente", "g@andina.com")
    assert (await g.get("/api/sedes")).status_code == 200
    r = await admin.patch(f"/api/usuarios/{g.usuario['id']}/estado", {"activo": False})
    assert r.status_code == 200
    assert (await g.get("/api/sedes")).status_code == 401  # el token ya no sirve
    r = await cliente.post("/api/auth/login", json={"email": "g@andina.com", "password": PASSWORD})
    assert r.status_code in (401, 403)


async def test_restablecer_password_por_admin_fuerza_cambio_e_invalida_sesion(cliente, db):
    admin = await crear_empresa(db, cliente)
    g = await crear_usuario(admin, "gerente", "g@andina.com")
    r = await admin.post(f"/api/usuarios/{g.usuario['id']}/restablecer-password", {"nueva_password": "Temporal#4567"})
    assert r.status_code == 200
    assert (await g.get("/api/sedes")).status_code == 401
    nuevo = await iniciar_sesion(cliente, "g@andina.com", "Temporal#4567")
    assert nuevo.usuario["debe_cambiar_password"] is True


async def test_desbloquear_cuenta(cliente, db):
    admin = await crear_empresa(db, cliente)
    await crear_usuario(admin, "gerente", "g@andina.com")
    for _ in range(5):
        await cliente.post("/api/auth/login", json={"email": "g@andina.com", "password": "Mala#Clave99"})
    uid = (await admin.get("/api/usuarios?q=g@andina")).json()["items"][0]["id"]
    assert (await admin.get(f"/api/usuarios/{uid}")).json()["bloqueado"] is True
    assert (await admin.post(f"/api/usuarios/{uid}/desbloquear")).status_code == 200
    await iniciar_sesion(cliente, "g@andina.com")


# ---------- Roles y permisos ----------


async def test_catalogo_de_permisos_y_roles_del_sistema(cliente, db):
    admin = await crear_empresa(db, cliente)
    permisos = (await admin.get("/api/permisos")).json()
    assert len(permisos) >= 40 and all("codigo" in p for p in permisos)
    roles = await roles_por_clave(admin)
    assert set(roles) == {"admin", "gerente", "encargado_sede", "usuario_inventario", "analista_compras"}
    assert roles["admin"]["es_sistema"] is True
    assert "auditoria.ver" in roles["admin"]["permisos"]
    assert "auditoria.ver" not in roles["usuario_inventario"]["permisos"]
    assert roles["encargado_sede"]["alcance"] == "sede"


async def test_rol_personalizado_ciclo_completo(cliente, db):
    admin = await crear_empresa(db, cliente)
    r = await admin.post("/api/roles", {"nombre": "Auditor externo", "alcance": "empresa", "permisos": ["auditoria.ver", "reportes.ventas"]})
    assert r.status_code == 201, r.text
    rol = r.json()
    assert set(rol["permisos"]) == {"auditoria.ver", "reportes.ventas"}
    r = await admin.put(f"/api/roles/{rol['id']}/permisos", {"permisos": ["auditoria.ver"]})
    assert r.json()["permisos"] == ["auditoria.ver"]
    r = await admin.post("/api/roles", {"nombre": "auditor EXTERNO", "permisos": []})
    assert r.status_code == 409
    r = await admin.post("/api/roles", {"nombre": "Con permiso falso", "permisos": ["no.existe"]})
    assert r.status_code in (400, 422)
    assert (await admin.delete(f"/api/roles/{rol['id']}")).status_code == 200


async def test_roles_del_sistema_no_se_eliminan_ni_cambian_permisos(cliente, db):
    admin = await crear_empresa(db, cliente)
    roles = await roles_por_clave(admin)
    assert (await admin.delete(f"/api/roles/{roles['admin']['id']}")).status_code in (400, 403)
    r = await admin.put(f"/api/roles/{roles['admin']['id']}/permisos", {"permisos": ["sedes.ver"]})
    assert r.status_code in (400, 403)


async def test_no_se_elimina_un_rol_con_usuarios(cliente, db):
    admin = await crear_empresa(db, cliente)
    rol = (await admin.post("/api/roles", {"nombre": "Supervisor", "alcance": "empresa", "permisos": ["sedes.ver"]})).json()
    r = await admin.post("/api/usuarios", {"nombre": "Pedro Sola", "email": "p@andina.com", "password": PASSWORD, "rol_id": rol["id"]})
    assert r.status_code == 201
    assert (await admin.delete(f"/api/roles/{rol['id']}")).status_code == 409


# ---------- Permisos efectivos (RF-038) ----------


async def test_gerente_no_gestiona_usuarios_ni_roles(cliente, db):
    admin = await crear_empresa(db, cliente)
    g = await crear_usuario(admin, "gerente", "g@andina.com")
    assert (await g.get("/api/usuarios")).status_code == 403
    assert (await g.post("/api/roles", {"nombre": "Nuevo rol", "permisos": []})).status_code == 403
    # Puede ver el historial de operaciones, pero NO la actividad de inicio de sesión de los usuarios.
    assert (await g.get("/api/auditoria?modulo=auth")).json()["total"] == 0


async def test_no_se_puede_escalar_privilegios_creando_roles(cliente, db):
    admin = await crear_empresa(db, cliente)
    # Un rol personalizado que SÍ puede crear roles pero no tiene auditoría.
    r = await admin.post("/api/roles", {"nombre": "Jefe de personal", "alcance": "empresa",
                                        "permisos": ["roles.ver", "roles.crear", "roles.asignar_permisos", "usuarios.ver"]})
    rol = r.json()
    r = await admin.post("/api/usuarios", {"nombre": "Jefa Personal", "email": "jp@andina.com", "password": PASSWORD, "rol_id": rol["id"], "forzar_cambio_password": False})
    assert r.status_code == 201
    jp = await iniciar_sesion(cliente, "jp@andina.com")
    r = await jp.post("/api/roles", {"nombre": "Super poderes", "alcance": "empresa", "permisos": ["auditoria.ver"]})
    assert r.status_code == 403  # no puede conceder lo que no tiene


async def test_encargado_de_sede_solo_ve_su_sede(cliente, db):
    admin = await crear_empresa(db, cliente)
    norte = await crear_sede(admin, "Norte")
    sur = await crear_sede(admin, "Sur")
    enc = await crear_usuario(admin, "encargado_sede", "enc@andina.com", norte["id"])
    items = (await enc.get("/api/sedes")).json()["items"]
    assert [s["id"] for s in items] == [norte["id"]]
    assert (await enc.get(f"/api/sedes/{sur['id']}")).status_code in (403, 404)


# ---------- Aislamiento entre empresas (CRÍTICO) ----------


async def test_empresas_no_ven_datos_de_otras(cliente, db):
    a = await crear_empresa(db, cliente, "Empresa A", "a@empresa-a.com", "1")
    b = await crear_empresa(db, cliente, "Empresa B", "b@empresa-b.com", "2")
    sede_a = await crear_sede(a, "Sede A1")
    sede_b = await crear_sede(b, "Sede B1")
    user_a = await crear_usuario(a, "gerente", "g@empresa-a.com")
    user_b_id = (await b.get("/api/usuarios")).json()["items"][0]["id"]

    assert [s["id"] for s in (await a.get("/api/sedes")).json()["items"]] == [sede_a["id"]]
    assert (await a.get(f"/api/sedes/{sede_b['id']}")).status_code == 404
    assert (await a.put(f"/api/sedes/{sede_b['id']}", {"nombre": "Hackeada"})).status_code == 404
    assert (await a.patch(f"/api/sedes/{sede_b['id']}/estado", {"activa": False})).status_code == 404
    assert (await a.get(f"/api/usuarios/{user_b_id}")).status_code == 404
    assert (await a.patch(f"/api/usuarios/{user_b_id}/estado", {"activo": False})).status_code == 404
    assert (await a.post(f"/api/usuarios/{user_b_id}/restablecer-password", {"nueva_password": "Hackeo#12345"})).status_code == 404
    emails_a = {u["email"] for u in (await a.get("/api/usuarios")).json()["items"]}
    assert emails_a == {"a@empresa-a.com", "g@empresa-a.com"}
    roles_b = await roles_por_clave(b)
    assert (await a.get(f"/api/roles/{roles_b['gerente']['id']}")).status_code == 404
    # No se puede crear un usuario de A en la sede de B ni con un rol de B.
    roles_a = await roles_por_clave(a)
    cuerpo = {"nombre": "Intruso Uno", "email": "i@empresa-a.com", "password": PASSWORD}
    assert (await a.post("/api/usuarios", {**cuerpo, "rol_id": roles_b["gerente"]["id"]})).status_code in (400, 404, 422)
    assert (await a.post("/api/usuarios", {**cuerpo, "rol_id": roles_a["encargado_sede"]["id"], "sede_id": sede_b["id"]})).status_code in (400, 404, 422)
    assert user_a.usuario["empresa_id"] != b.usuario["empresa_id"]


async def test_auditoria_registra_altas_y_cambios_sin_secretos(cliente, db):
    admin = await crear_empresa(db, cliente)
    sede = await crear_sede(admin)
    await crear_usuario(admin, "gerente", "g@andina.com")
    await admin.patch(f"/api/sedes/{sede['id']}/estado", {"activa": False})
    filas = (await db.scalars(select(Auditoria))).all()
    acciones = {(f.modulo, f.accion) for f in filas}
    assert ("sedes", "crear") in acciones or ("sede", "crear") in acciones
    assert any(f.modulo.startswith("usuario") for f in filas)
    volcado = " ".join(str(f.detalle) for f in filas)
    assert PASSWORD not in volcado and "$argon2" not in volcado


async def test_directorio_de_sedes_para_usuario_limitado_a_su_sede(cliente, db):
    """Un encargado de sede solo lista su sede, pero el directorio le muestra las demás (datos mínimos)
    para poder solicitar traslados; nunca las de otra empresa."""
    admin = await crear_empresa(db, cliente)
    norte = await crear_sede(admin, "Sede Norte")
    sur = await crear_sede(admin, "Sede Sur")
    otra = await crear_empresa(db, cliente, nombre="Otra Empresa", correo="admin@otra.com", sufijo="2")
    await crear_sede(otra, "Sede Ajena")
    encargado = await crear_usuario(admin, "encargado_sede", "norte@andina.com", sede_id=norte["id"])

    r = await encargado.get("/api/sedes/directorio")
    assert r.status_code == 200, r.text
    assert {x["nombre"] for x in r.json()} == {"Sede Norte", "Sede Sur"}
    assert all(set(x) <= {"id", "nombre", "ciudad"} for x in r.json())
    propio = await encargado.get("/api/sedes")
    assert [x["id"] for x in propio.json()["items"]] == [norte["id"]]
    assert sur["id"] not in [x["id"] for x in propio.json()["items"]]
