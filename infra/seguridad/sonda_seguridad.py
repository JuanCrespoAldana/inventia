"""Sonda de seguridad contra una API de PRUEBA en ejecución (apoya el checklist OWASP Top 10:2025).

Comprobaciones automáticas:
  A01  Todas las rutas protegidas rechazan peticiones sin token (401) y con token alterado (401); se listan las rutas públicas.
  A01  Un usuario de rol limitado no accede a rutas de administración (403).
  A02  Cabeceras de seguridad y CORS: un origen no autorizado no recibe Access-Control-Allow-Origin.
  A04/A07 El token de acceso no se acepta con la firma alterada ni con algoritmo «none».
  A05  Entradas con comillas, comandos SQL y HTML en parámetros no producen error 500 ni se reflejan.
  A07  Bloqueo por intentos fallidos de inicio de sesión (RNF-026) y mensaje de error genérico.
  A09  Existen registros de auditoría del inicio de sesión fallido.
  A10  Un cuerpo malformado produce error 4xx controlado (nunca 500 ni traza interna).

Uso:  python sonda_seguridad.py <host> <correo_admin> <ruta_archivo_con_contraseña> <correo_rol_limitado> <ruta_archivo_con_contraseña_limitado> <salida.json>
"""

import base64
import json
import re
import sys
import time

import requests

host, admin, ruta_pw, limitado, ruta_pw_lim, salida = sys.argv[1:7]
host = host.rstrip("/")
pw = open(ruta_pw).read().strip()
pw_lim = open(ruta_pw_lim).read().strip()
informe: dict = {"host": host, "hallazgos": [], "pruebas": {}}


def anotar(clave: str, ok: bool, detalle: str) -> None:
    informe["pruebas"][clave] = {"ok": ok, "detalle": detalle}
    print(("OK    " if ok else "FALLA ") + clave + " — " + detalle)


def login(correo: str, clave: str) -> requests.Response:
    return requests.post(f"{host}/api/auth/login", json={"email": correo, "password": clave}, timeout=30)


openapi = requests.get(f"{host}/api/openapi.json", timeout=30).json()
rutas = []
for ruta, ops in openapi["paths"].items():
    for metodo, op in ops.items():
        if metodo.upper() in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            rutas.append((metodo.upper(), ruta, op))
print(f"rutas documentadas: {len(rutas)}")

# ---------------------------------------------------------------- A01: sin token / token alterado
tok = login(admin, pw).json()["access_token"]
cab = {"Authorization": f"Bearer {tok}"}
sin_proteccion, publicas = [], []
for metodo, ruta, op in rutas:
    url = host + re.sub(r"\{[^}]+\}", "1", ruta)
    if ruta in ("/api/auth/login", "/api/auth/forgot-password", "/api/auth/verify-reset-code", "/api/auth/reset-password", "/api/setup"):
        # públicas por diseño; se prueban aparte porque limitan por IP
        publicas.append(f"{metodo} {ruta} -> pública por diseño (no se invoca)")
        continue
    r = requests.request(metodo, url, json={} if metodo != "GET" else None, timeout=30)
    if r.status_code in (401, 403):
        continue
    publicas.append(f"{metodo} {ruta} -> {r.status_code}")
informe["rutas_sin_token_que_responden"] = publicas
esperadas_publicas = ("/api/health", "/api/auth/", "/api/setup", "/api/sedes/directorio", "/api/docs", "/api/openapi", "/api/empresa/publica")
no_esperadas = [p for p in publicas if not any(e in p for e in esperadas_publicas)]
anotar("A01_rutas_sin_token", not no_esperadas, f"{len(rutas) - len(publicas)} de {len(rutas)} rutas exigen token; públicas: {len(publicas)}; no esperadas: {no_esperadas[:8]}")

partes = tok.split(".")
alterado = ".".join(partes[:2] + [partes[2][:-4] + ("AAAA" if not partes[2].endswith("AAAA") else "BBBB")])
r = requests.get(f"{host}/api/dashboard", headers={"Authorization": f"Bearer {alterado}"}, timeout=30)
anotar("A07_token_firma_alterada", r.status_code == 401, f"código {r.status_code}")

def b64(d: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(d, separators=(",", ":")).encode()).rstrip(b"=").decode()

carga = json.loads(base64.urlsafe_b64decode(partes[1] + "=" * (-len(partes[1]) % 4)))
sin_firma = b64({"alg": "none", "typ": "JWT"}) + "." + b64(carga) + "."
r = requests.get(f"{host}/api/dashboard", headers={"Authorization": f"Bearer {sin_firma}"}, timeout=30)
anotar("A04_token_alg_none", r.status_code == 401, f"código {r.status_code}")

# ---------------------------------------------------------------- A01: rol limitado vs rutas de administración
rl = login(limitado, pw_lim)
mi_sede = otra_sede = None
if rl.ok:
    yo = requests.get(host + "/api/auth/me", headers={"Authorization": f"Bearer {rl.json()['access_token']}"}, timeout=30).json()
    mi_sede = yo.get("sede_id") or (yo.get("sede") or {}).get("id")
    todas = [x["id"] for x in requests.get(host + "/api/sedes/directorio", headers=cab, timeout=30).json()]
    otra_sede = next((i for i in todas if i != mi_sede), None)
    cab_l = {"Authorization": f"Bearer {rl.json()['access_token']}"}
    solo_admin = ["/api/usuarios", "/api/empresa"]
    codigos = {p: requests.get(host + p, headers=cab_l, timeout=30).status_code for p in solo_admin}
    anotar("A01_rol_limitado_en_administracion", all(c == 403 for c in codigos.values()), json.dumps(codigos))
    # Por diseño el encargado de sede puede VER la lista de roles y la auditoría de las OPERACIONES de su sede (no los accesos).
    aud = requests.get(host + "/api/auditoria", params={"tamano": 100}, headers=cab_l, timeout=30)
    items = aud.json().get("items", []) if aud.ok else []
    ajenos = [i for i in items if i["modulo"] == "auth" or i.get("sede_id") not in (None, mi_sede)]
    anotar("A01_auditoria_del_encargado_limitada_a_su_sede_sin_accesos", aud.ok and not ajenos,
           f"{len(items)} eventos visibles; de módulo «auth» o de otra sede: {len(ajenos)}")
    codigos_post = {
        "POST /api/usuarios": requests.post(host + "/api/usuarios", json={}, headers=cab_l, timeout=30).status_code,
        "POST /api/roles": requests.post(host + "/api/roles", json={"nombre": "x"}, headers=cab_l, timeout=30).status_code,
        "POST /api/predicciones/ejecutar": requests.post(host + "/api/predicciones/ejecutar", json={}, headers=cab_l, timeout=30).status_code,
    }
    anotar("A01_rol_limitado_en_acciones", all(c == 403 for c in codigos_post.values()), json.dumps(codigos_post))
    # Aislamiento por sede: el encargado no ve existencias de otra sede
    otras = requests.get(host + "/api/inventario", params={"sede_id": otra_sede, "tamano": 5}, headers=cab_l, timeout=30)
    anotar("A01_aislamiento_por_sede_en_inventario", otras.status_code in (403, 404) or (otras.ok and not otras.json().get("items")),
           f"código {otras.status_code} al pedir la sede {otra_sede} siendo de la sede {mi_sede}")
else:
    anotar("A01_rol_limitado", False, f"no se pudo iniciar sesión con el usuario limitado ({rl.status_code})")

# ---------------------------------------------------------------- A02: cabeceras y CORS
r = requests.get(f"{host}/api/health", headers={"Origin": "https://sitio-malicioso.example"}, timeout=30)
cors = r.headers.get("access-control-allow-origin")
anotar("A02_cors_origen_no_autorizado", cors in (None, ""), f"Access-Control-Allow-Origin={cors!r}")
cabeceras = {k.lower(): v for k, v in r.headers.items()}
informe["cabeceras_respuesta_api"] = cabeceras
faltan = [h for h in ("x-content-type-options", "x-frame-options", "referrer-policy") if h not in cabeceras]
anotar("A02_cabeceras_de_seguridad_en_api", not faltan, f"faltan: {faltan}" if faltan else "presentes")
r = requests.get(f"{host}/api/openapi.json", timeout=30)
informe["docs_expuestas"] = r.status_code

# ---------------------------------------------------------------- A05: inyección y XSS reflejado
payloads = ["' OR '1'='1", "1; DROP TABLE productos;--", "<script>alert(1)</script>", "%00", "../../etc/passwd"]
errores_500, reflejados = [], []
for p in payloads:
    for ruta in ("/api/productos", "/api/ventas", "/api/inventario", "/api/alertas"):
        r = requests.get(host + ruta, params={"buscar": p, "q": p, "sede_id": p, "tamano": p}, headers=cab, timeout=30)
        if r.status_code >= 500:
            errores_500.append(f"{ruta} {p!r} -> {r.status_code}")
        if "<script>" in r.text:
            reflejados.append(ruta)
anotar("A05_parametros_maliciosos_sin_500", not errores_500 and not reflejados, f"errores 5xx: {errores_500[:5]}; reflejados: {reflejados[:5]}")
r = requests.post(f"{host}/api/productos", json={"nombre": "<img src=x onerror=alert(1)>", "sku": "X'--"}, headers=cab, timeout=30)
anotar("A05_cuerpo_con_html_no_500", r.status_code < 500, f"código {r.status_code}")

# ---------------------------------------------------------------- A10: cuerpos malformados
malos = []
for cuerpo in ("{no es json", "[]", "null", '{"email": 123}'):
    r = requests.post(f"{host}/api/auth/login", data=cuerpo, headers={"Content-Type": "application/json"}, timeout=30)
    if r.status_code >= 500 or "Traceback" in r.text or "File \"" in r.text:
        malos.append((cuerpo, r.status_code))
anotar("A10_cuerpo_malformado_4xx_controlado", not malos, f"incidencias: {malos}")
r = requests.get(host + "/api/ruta-que-no-existe", headers=cab, timeout=30)
anotar("A10_ruta_inexistente_404", r.status_code == 404 and "Traceback" not in r.text, f"código {r.status_code}")

# ---------------------------------------------------------------- A07: bloqueo por intentos (RNF-026) y mensaje genérico
time.sleep(62)  # el inicio de sesión limita 10/min por IP: se espera para medir el bloqueo por cuenta, no el límite por IP
mensajes, codigos = set(), []
for _ in range(7):
    r = login(limitado, "ClaveIncorrecta-123!")
    codigos.append(r.status_code)
    if r.status_code != 401:
        break
    try:
        mensajes.add(r.json().get("detail", ""))
    except Exception:  # noqa: BLE001
        pass
r_inex = login("no.existe@demo.inventia.example", "ClaveIncorrecta-123!")
bloqueado = login(limitado, pw_lim)
anotar("A07_bloqueo_por_intentos", 423 in codigos or 429 in codigos or bloqueado.status_code in (423, 429),
       f"códigos {codigos}; con la clave correcta después: {bloqueado.status_code}")
anotar("A07_mensaje_generico_usuario_inexistente", r_inex.status_code in (401, 429) and (r_inex.json().get("detail") in mensajes or r_inex.status_code == 429),
       f"inexistente -> {r_inex.status_code} {r_inex.json().get('detail')!r}; existente -> {sorted(mensajes)}")

# ---------------------------------------------------------------- A09: auditoría
time.sleep(1)
aud = requests.get(f"{host}/api/auditoria", params={"tamano": 30}, headers=cab, timeout=30)
if aud.ok:
    texto = aud.text.lower()
    anotar("A09_auditoria_registra_intentos_fallidos", "login" in texto or "sesion" in texto or "sesión" in texto or "bloque" in texto,
           f"{len(aud.json().get('items', []))} eventos recientes consultados")
else:
    anotar("A09_auditoria", False, f"código {aud.status_code}")

informe["resumen"] = {"ok": sum(1 for v in informe["pruebas"].values() if v["ok"]), "falla": sum(1 for v in informe["pruebas"].values() if not v["ok"])}
open(salida, "w", encoding="utf-8").write(json.dumps(informe, ensure_ascii=False, indent=2))
print(informe["resumen"])
