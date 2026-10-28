"""Genera los diagramas del modelo relacional (físico) a partir del esquema real de PostgreSQL.

    python relacional.py esquema.json      # esquema.json: salida de infra/.../volcar_esquema.py (ver docs/MODELO_DATOS.md)

Muestra llaves primarias (PK), foráneas (FK) y las columnas de negocio más relevantes; el detalle completo está en el
diccionario de datos (anexo). Las llaves foráneas a ``empresas`` se omiten para legibilidad (todas las tablas de negocio
llevan ``empresa_id``).
"""
import json
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).parent
E = json.load(open(sys.argv[1], encoding="utf-8"))

TIPOS = {"integer": "int", "bigint": "bigint", "smallint": "smallint", "boolean": "bool", "text": "text", "jsonb": "jsonb", "json": "json",
         "date": "date", "bytea": "bytea", "timestamp with time zone": "timestamptz", "timestamp without time zone": "timestamp"}


def tipo(c):
    t = c["tipo"]
    if t == "character varying":
        return f"varchar({c['largo']})" if c["largo"] else "varchar"
    if t == "numeric":
        return f"numeric({c['precision']},{c['escala']})" if c["precision"] else "numeric"
    return TIPOS.get(t, t)


CLAVES = {  # columnas de negocio a mostrar además de PK y FK
    "empresas": ["nombre", "identificacion", "ciudad", "activa", "configuracion"],
    "sedes": ["nombre", "ciudad", "activa"],
    "usuarios": ["nombre", "email", "password_hash", "activo", "intentos_fallidos", "bloqueado_hasta"],
    "roles": ["clave", "nombre", "alcance", "es_sistema"],
    "permisos": ["modulo", "descripcion"], "rol_permisos": [],
    "password_reset_tokens": ["codigo_hash", "expires_at", "intentos", "used"],
    "auditoria": ["fecha", "modulo", "accion", "resultado"],
    "api_keys": ["nombre", "prefijo", "key_hash", "alcances", "expira_en", "activa"],
    "categorias": ["nombre", "activa"],
    "productos": ["codigo", "nombre", "unidad_medida", "costo", "precio_venta", "activo"],
    "inventario_sede": ["cantidad", "stock_minimo", "stock_maximo"],
    "movimientos": ["tipo", "delta", "saldo_anterior", "saldo_posterior", "fecha"],
    "alertas": ["tipo", "prioridad", "estado", "abierta_en", "resuelta_en"],
    "ventas": ["numero", "fecha", "fecha_dia", "total", "estado"],
    "venta_items": ["cantidad", "precio_unitario", "subtotal"],
    "traslados": ["numero", "estado", "solicitado_en", "aprobado_en", "confirmado_en"],
    "traslado_items": ["cantidad"],
    "ejecuciones_prediccion": ["estado", "horizonte_dias", "fecha_corte", "parametros", "resumen"],
    "predicciones": ["fecha_inicio", "fecha_fin", "demanda_estimada", "limite_inferior", "limite_superior", "modelo", "confianza", "metricas"],
    "recomendaciones": ["tipo", "cantidad_sugerida", "prioridad", "estado", "justificacion"],
    "entradas_inventario": ["numero", "motivo", "fecha"],
    "entrada_observaciones": ["fecha", "contenido"],
    "pqrs": ["numero", "tipo", "asunto", "estado", "respuesta"],
    "pqrs_historial": ["fecha", "evento", "estado_anterior", "estado_nuevo"],
    "no_conformidades": ["numero", "tipo", "fecha_deteccion", "cantidad_afectada", "estado", "proveedor"],
    "no_conformidad_historial": ["fecha", "evento", "estado_nuevo"],
    "garantias": ["numero", "cantidad", "fecha_compra", "garantia_hasta", "defecto", "estado"],
    "garantia_historial": ["fecha", "evento", "estado_nuevo"],
    "sig_adjuntos": ["nombre", "tipo_mime", "tamano", "sha256"],
    "sst_configuracion": ["pausas_activas", "intervalo_minutos"],
    "sst_actividades": ["titulo", "area", "duracion_segundos", "activa"],
    "sst_pausas": ["actividad_titulo", "mostrada_en", "estado", "cerrada_en"],
    "amb_configuracion": ["factor_red_kgco2_kwh", "factor_red_anio", "factor_red_fuente"],
    "amb_categorias": ["tipo_vehiculo", "propulsion", "distancia_anual_km", "consumo_kwh_100km", "horizonte_anios"],
    "amb_registros": ["fecha", "unidades", "estado", "co2_evitado_kg"],
}

FIGURAS = {
    "relacional_acceso": ("Acceso, organización y auditoría",
                          ["empresas", "sedes", "usuarios", "roles", "rol_permisos", "permisos", "password_reset_tokens", "auditoria", "api_keys"], []),
    "relacional_catalogo_inventario": ("Catálogo e inventario",
                                       ["categorias", "productos", "inventario_sede", "movimientos", "alertas"],
                                       ["sedes", "usuarios", "ventas", "traslados"]),
    "relacional_ventas_traslados": ("Ventas y traslados",
                                    ["ventas", "venta_items", "traslados", "traslado_items"],
                                    ["sedes", "usuarios", "productos", "movimientos", "recomendaciones"]),
    "relacional_prediccion": ("Predicción y recomendaciones",
                              ["ejecuciones_prediccion", "predicciones", "recomendaciones"], ["sedes", "productos", "traslados", "usuarios"]),
    "relacional_sig_pqrs": ("SIG: PQRS y evidencias",
                            ["pqrs", "pqrs_historial", "sig_adjuntos"], ["sedes", "usuarios", "no_conformidades", "garantias"]),
    "relacional_sig_entradas": ("SIG: entradas de inventario y observaciones",
                                ["entradas_inventario", "entrada_observaciones"], ["sedes", "usuarios", "movimientos", "no_conformidades"]),
    "relacional_sig_calidad": ("SIG: no conformidades y garantías",
                               ["no_conformidades", "no_conformidad_historial", "garantias", "garantia_historial"],
                               ["sedes", "usuarios", "productos", "ventas", "entradas_inventario"]),
    "relacional_sig_sst": ("SIG: pausas activas", ["sst_configuracion", "sst_actividades", "sst_pausas"], ["usuarios", "sedes"]),
    "relacional_sig_ambiental": ("SIG: gestión ambiental", ["amb_configuracion", "amb_categorias", "amb_registros"],
                                 ["categorias", "venta_items", "ventas", "productos", "sedes"]),
}


def nodo(t, completo):
    d = E[t]
    fks = {f["columna"]: f for f in d["fks"]}
    if completo:
        cols = [c["nombre"] for c in d["columnas"] if c["nombre"] in d["pk"] or c["nombre"] in fks or c["nombre"] in CLAVES.get(t, [])]
    else:
        cols = d["pk"][:1] + [c for c in CLAVES.get(t, [])[:1]]
        cols = [c for c in cols if c]
    por_nombre = {c["nombre"]: c for c in d["columnas"]}
    filas = []
    for n in cols:
        c = por_nombre[n]
        marca = "PK" if n in d["pk"] else ("FK" if n in fks else "")
        if n in d["pk"] and n in fks:
            marca = "PK, FK"
        color = "#184f95" if "PK" in marca else ("#eb6834" if marca == "FK" else "#52514e")
        nulo = "" if not c["nulo"] else " ?"
        celda_marca = f'<font color="{color}" point-size="8"><b>{marca}</b></font>' if marca else '<font point-size="8"> </font>'
        filas.append(f'<tr><td align="left" port="{n}">{celda_marca}</td>'
                     f'<td align="left"><font point-size="9">{n}</font></td><td align="left"><font color="#7b7e8c" point-size="8">{tipo(c)}{nulo}</font></td></tr>')
    extra = len(d["columnas"]) - len(cols)
    if completo and extra > 0:
        filas.append(f'<tr><td></td><td align="left" colspan="2"><font color="#9a9890" point-size="8"><i>(+{extra} columnas más)</i></font></td></tr>')
    cab = "#3b5bf0" if completo else "#9a9890"
    return (f'  {t} [label=<<table border="1" cellborder="0" cellspacing="0" cellpadding="3" color="{cab}">'
            f'<tr><td colspan="3" bgcolor="{cab}"><font color="white" point-size="10"><b>{t}</b></font></td></tr>'
            + "".join(filas) + "</table>>];")


def dibujar(nombre, titulo, tablas, stubs):
    todas = set(tablas) | set(stubs)
    lineas = [f'digraph {nombre} {{',
              '  graph [rankdir=LR, fontname="Inter", nodesep=0.35, ranksep=0.9, pad=0.3, bgcolor="white", splines=true, concentrate=false];',
              '  node [shape=plain, fontname="Inter"];',
              '  edge [color="#52514e", arrowtail=crowodot, arrowhead=tee, dir=both, arrowsize=0.7, penwidth=0.9];']
    for t in tablas:
        lineas.append(nodo(t, True))
    for t in stubs:
        lineas.append(nodo(t, False))
    for t in tablas:
        pares = {}
        for f in E[t]["fks"]:
            if f["tabla"] == "empresas" or f["tabla"] not in todas or f["tabla"] == t:
                continue
            nulo = {c["nombre"]: c["nulo"] for c in E[t]["columnas"]}[f["columna"]]
            pares.setdefault(f["tabla"], []).append(nulo)
        for destino, nulos in pares.items():
            cab = "teeodot" if all(nulos) else "tee"
            etiqueta = f' label="{len(nulos)} FK" fontsize=8 fontcolor="#7b7e8c"' if len(nulos) > 1 else ""
            lineas.append(f'  {t} -> {destino} [arrowhead={cab}{etiqueta}];')
    lineas.append("}")
    ruta = AQUI / f"{nombre}.dot"
    ruta.write_text("\n".join(l for l in lineas if l), encoding="utf-8")
    subprocess.run(["dot", "-Tpng", "-Gdpi=200", str(ruta), "-o", str(AQUI / f"{nombre}.png")], check=True)
    print(nombre, len(tablas), "tablas")


for nombre, (titulo, tablas, stubs) in FIGURAS.items():
    dibujar(nombre, titulo, tablas, stubs)
