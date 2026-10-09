"""Configuración inicial y autenticación (RF-001, RF-002, RF-007, RNF-024..RNF-030)."""

import pytest
from sqlalchemy import select

import app.core.config as cfg
from app.models.auditoria import Auditoria
from app.models.usuario import Usuario
from tests.ayuda import PASSWORD, crear_empresa, iniciar_sesion

DATOS_SETUP = {
    "empresa_nombre": "Comercial Sabana S.A.S.",
    "empresa_identificacion": "900.123.456-7",
    "empresa_telefono": "3001234567",
    "empresa_ciudad": "Bogotá",
    "admin_nombre": "Laura Gómez",
    "admin_email": "Laura@Sabana.com",
    "admin_password": PASSWORD,
}


async def test_estado_inicial_no_configurado(cliente):
    r = await cliente.get("/api/setup/estado")
    assert r.status_code == 200
    assert r.json() == {"configurado": False, "requiere_token": False, "nombre_aplicacion": "Inventia"}


async def test_setup_crea_empresa_roles_y_admin(cliente, db):
    r = await cliente.post("/api/setup", json=DATOS_SETUP)
    assert r.status_code == 201, r.text
    sesion = r.json()["usuario"]
    assert sesion["rol"]["clave"] == "admin"
    assert sesion["email"] == "laura@sabana.com"  # el correo se normaliza
    assert "usuarios.crear" in sesion["permisos"]
    r = await cliente.get("/api/setup/estado")
    assert r.json()["configurado"] is True
    # Los cinco roles del documento existen.
    admin = await iniciar_sesion(cliente, "laura@sabana.com")
    claves = {rol["clave"] for rol in (await admin.get("/api/roles")).json()}
    assert {"admin", "gerente", "encargado_sede", "usuario_inventario", "analista_compras"} <= claves


async def test_setup_solo_una_vez(cliente):
    assert (await cliente.post("/api/setup", json=DATOS_SETUP)).status_code == 201
    r = await cliente.post("/api/setup", json={**DATOS_SETUP, "admin_email": "otra@persona.com"})
    assert r.status_code == 409
    assert r.json()["codigo"] == "ya_configurado"


async def test_setup_exige_token_si_esta_definido(cliente, monkeypatch):
    monkeypatch.setattr(cfg.settings, "setup_token", "token-de-instalacion-123")
    r = await cliente.post("/api/setup", json=DATOS_SETUP)
    assert r.status_code == 403
    assert r.json()["codigo"] == "token_configuracion_invalido"
    r = await cliente.post("/api/setup", json={**DATOS_SETUP, "token_configuracion": "token-de-instalacion-123"})
    assert r.status_code == 201


async def test_no_existe_registro_publico(cliente):
    r = await cliente.post("/api/auth/register", json={"email": "x@y.com", "password": PASSWORD, "nombre": "X"})
    assert r.status_code in (404, 405)


async def test_setup_rechaza_password_debil_en_espanol(cliente):
    r = await cliente.post("/api/setup", json={**DATOS_SETUP, "admin_password": "abc"})
    assert r.status_code == 422
    assert any("contraseña" in e["mensaje"].lower() for e in r.json()["errores"])


async def test_login_correcto_y_me(cliente, db):
    await crear_empresa(db, cliente)
    s = await iniciar_sesion(cliente, "admin@andina.com")
    r = await s.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "admin@andina.com"


async def test_login_incorrecto_mensaje_generico_y_auditado(cliente, db):
    await crear_empresa(db, cliente)
    r = await cliente.post("/api/auth/login", json={"email": "admin@andina.com", "password": "Incorrecta#1"})
    assert r.status_code == 401
    r2 = await cliente.post("/api/auth/login", json={"email": "noexiste@andina.com", "password": "Incorrecta#1"})
    assert r2.status_code == 401
    assert r.json()["detail"] == r2.json()["detail"]  # no revela si el correo existe
    filas = (await db.scalars(select(Auditoria).where(Auditoria.accion == "inicio_sesion"))).all()
    assert {f.resultado for f in filas} >= {"fallido"}
    assert all("Incorrecta" not in str(f.detalle) for f in filas)  # jamás se guarda la contraseña


async def test_bloqueo_tras_intentos_fallidos(cliente, db):
    await crear_empresa(db, cliente)
    for _ in range(5):
        await cliente.post("/api/auth/login", json={"email": "admin@andina.com", "password": "Incorrecta#1"})
    r = await cliente.post("/api/auth/login", json={"email": "admin@andina.com", "password": PASSWORD})
    assert r.status_code == 423  # aun con la contraseña correcta, la cuenta está bloqueada


async def test_limite_de_solicitudes_por_ip_en_el_ingreso(cliente):
    """Más de 10 intentos de ingreso por minuto desde una misma IP reciben 429 (RNF-025)."""
    for _ in range(10):
        r = await cliente.post("/api/auth/login", json={"email": "nadie@andina.com", "password": "Incorrecta#1"})
        assert r.status_code == 401
    r = await cliente.post("/api/auth/login", json={"email": "nadie@andina.com", "password": "Incorrecta#1"})
    assert r.status_code == 429
    assert r.json()["codigo"] == "demasiadas_peticiones"
    assert "Retry-After" in r.headers or "retry-after" in r.headers


async def test_rutas_protegidas_sin_token(cliente):
    for ruta in ("/api/auth/me", "/api/sedes", "/api/usuarios", "/api/roles", "/api/empresa"):
        assert (await cliente.get(ruta)).status_code == 401, ruta


async def test_token_invalido(cliente):
    r = await cliente.get("/api/auth/me", headers={"Authorization": "Bearer abc.def.ghi"})
    assert r.status_code == 401


async def test_cambiar_password_invalida_tokens_anteriores(cliente, db):
    await crear_empresa(db, cliente)
    s = await iniciar_sesion(cliente, "admin@andina.com")
    r = await s.post("/api/auth/cambiar-password", {"password_actual": PASSWORD, "nueva_password": "Nueva#Clave22"})
    assert r.status_code == 200, r.text
    assert (await s.get("/api/auth/me")).status_code == 401  # el token viejo ya no sirve
    nuevo = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert (await cliente.get("/api/auth/me", headers=nuevo)).status_code == 200
    ok = await cliente.post("/api/auth/login", json={"email": "admin@andina.com", "password": "Nueva#Clave22"})
    assert ok.status_code == 200


async def test_cambiar_password_exige_la_actual(cliente, db):
    await crear_empresa(db, cliente)
    s = await iniciar_sesion(cliente, "admin@andina.com")
    r = await s.post("/api/auth/cambiar-password", {"password_actual": "Mala#Clave1", "nueva_password": "Nueva#Clave22"})
    assert r.status_code in (400, 401)


async def test_usuario_con_cambio_obligatorio_solo_puede_cambiar_password(cliente, db):
    admin = await crear_empresa(db, cliente)
    roles = {r["clave"]: r for r in (await admin.get("/api/roles")).json()}
    r = await admin.post("/api/usuarios", {
        "nombre": "Nuevo Ingreso", "email": "nuevo@andina.com", "password": "Temporal#123",
        "rol_id": roles["gerente"]["id"],
    })
    assert r.status_code == 201, r.text
    nuevo = await iniciar_sesion(cliente, "nuevo@andina.com", "Temporal#123")
    assert nuevo.usuario["debe_cambiar_password"] is True
    assert (await nuevo.get("/api/sedes")).status_code == 403  # bloqueado hasta cambiar la clave
    assert (await nuevo.get("/api/auth/me")).status_code == 200
    r = await nuevo.post("/api/auth/cambiar-password", {"password_actual": "Temporal#123", "nueva_password": "Definitiva#123"})
    assert r.status_code == 200
    ok = await iniciar_sesion(cliente, "nuevo@andina.com", "Definitiva#123")
    assert (await ok.get("/api/sedes")).status_code == 200


async def test_recuperacion_de_contraseña_flujo_completo(cliente, db, monkeypatch):
    await crear_empresa(db, cliente)
    enviados = []

    async def falso_envio(destino, nombre, codigo):
        enviados.append((destino, codigo))

    import app.services.auth_service as svc

    monkeypatch.setattr(svc, "enviar_codigo_recuperacion", falso_envio, raising=False)
    r = await cliente.post("/api/auth/forgot-password", json={"email": "admin@andina.com"})
    assert r.status_code == 202
    # El correo desconocido recibe la MISMA respuesta
    r2 = await cliente.post("/api/auth/forgot-password", json={"email": "nadie@andina.com"})
    assert r2.status_code == 202 and r2.json() == r.json()
    assert len(enviados) == 1
    destino, codigo = enviados[0]
    assert destino == "admin@andina.com" and len(codigo) == 6 and codigo.isdigit()

    malo = await cliente.post("/api/auth/verify-reset-code", json={"email": destino, "codigo": "000000" if codigo != "000000" else "111111"})
    assert malo.status_code == 400
    bueno = await cliente.post("/api/auth/verify-reset-code", json={"email": destino, "codigo": codigo})
    assert bueno.status_code == 200, bueno.text
    token = bueno.json()["session_token"]
    r = await cliente.post("/api/auth/reset-password", json={"session_token": token, "nueva_password": "Restaurada#77"})
    assert r.status_code == 200
    # El token de sesión es de un solo uso
    r = await cliente.post("/api/auth/reset-password", json={"session_token": token, "nueva_password": "Otra#Clave88"})
    assert r.status_code == 400
    await iniciar_sesion(cliente, "admin@andina.com", "Restaurada#77")


async def test_codigo_se_invalida_tras_demasiados_intentos(cliente, db, monkeypatch):
    await crear_empresa(db, cliente)
    enviados = []

    async def falso_envio(destino, nombre, codigo):
        enviados.append(codigo)

    import app.services.auth_service as svc

    monkeypatch.setattr(svc, "enviar_codigo_recuperacion", falso_envio, raising=False)
    await cliente.post("/api/auth/forgot-password", json={"email": "admin@andina.com"})
    codigo = enviados[0]
    equivocado = "123456" if codigo != "123456" else "654321"
    for _ in range(5):
        await cliente.post("/api/auth/verify-reset-code", json={"email": "admin@andina.com", "codigo": equivocado})
        from app.core.limiter import limiter

        limiter.reset()
    r = await cliente.post("/api/auth/verify-reset-code", json={"email": "admin@andina.com", "codigo": codigo})
    assert r.status_code == 400  # el código correcto ya no sirve: fue invalidado


async def test_ninguna_respuesta_expone_hash_ni_secretos(cliente, db):
    admin = await crear_empresa(db, cliente)
    for ruta in ("/api/auth/me", "/api/usuarios", "/api/empresa"):
        texto = (await admin.get(ruta)).text
        assert "password_hash" not in texto and "$argon2" not in texto
    u = (await db.scalars(select(Usuario))).first()
    assert u.password_hash.startswith("$argon2id$")


async def test_cabeceras_de_seguridad_y_request_id(cliente):
    r = await cliente.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-request-id"]
    r2 = await cliente.get("/api/health")
    assert r2.headers["x-request-id"] != r.headers["x-request-id"]


async def test_error_interno_no_filtra_detalles(cliente, monkeypatch):
    pytest.importorskip("fastapi")
    r = await cliente.get("/api/ruta-que-no-existe")
    assert r.status_code == 404
    assert "Traceback" not in r.text
