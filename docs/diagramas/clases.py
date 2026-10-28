"""Diagrama de clases UML del dominio de Inventia.

Los atributos y sus tipos se leen de backend/app/model/*.py (ast); las operaciones corresponden a las funciones
públicas de backend/app/service/*.py. Uso: python3 clases.py  (genera clases.dot y clases.png con Graphviz)."""
import ast
import subprocess
from pathlib import Path

MODELOS = Path(__file__).resolve().parents[2] / "backend" / "app" / "model"

# clase -> (archivo, atributos seleccionados, operaciones)
CLASES = {
    "Empresa": ("empresa", ["id", "nombre", "identificacion", "ciudad", "activa"], []),
    "Sede": ("sede", ["id", "nombre", "ciudad", "activa"], ["crear()", "inhabilitar()"]),
    "Usuario": ("usuario", ["id", "nombre", "email", "activo", "debe_cambiar_password", "intentos_fallidos", "bloqueado_hasta"],
                ["iniciar_sesion()", "cerrar_sesion()", "cambiar_password()", "recuperar_password()"]),
    "Rol": ("acceso", ["id", "clave", "nombre", "alcance", "es_sistema"], ["asignar_permisos()"]),
    "Permiso": ("acceso", ["codigo", "modulo", "descripcion"], []),
    "Categoria": ("catalogo", ["id", "nombre", "activa"], []),
    "Producto": ("catalogo", ["id", "codigo", "nombre", "unidad_medida", "costo", "precio_venta", "activo"], ["crear()", "inhabilitar()"]),
    "InventarioSede": ("inventario", ["cantidad", "stock_minimo", "stock_maximo"],
                       ["registrar_entrada()", "registrar_salida()", "ajustar()", "configurar_niveles()", "consolidado()"]),
    "Movimiento": ("inventario", ["id", "tipo", "motivo", "delta", "saldo_anterior", "saldo_posterior", "fecha"], ["(solo inserción)"]),
    "Alerta": ("inventario", ["id", "tipo", "prioridad", "estado", "mensaje", "abierta_en"], ["sincronizar()"]),
    "Venta": ("operaciones", ["id", "numero", "fecha", "total", "estado", "motivo_anulacion"], ["registrar()", "anular()"]),
    "VentaItem": ("operaciones", ["cantidad", "precio_unitario", "subtotal"], []),
    "Traslado": ("operaciones", ["id", "numero", "estado", "solicitado_en", "aprobado_en", "confirmado_en", "motivo_cierre"],
                 ["solicitar()", "aprobar()", "rechazar()", "cancelar()", "confirmar()"]),
    "TrasladoItem": ("operaciones", ["cantidad"], []),
    "EjecucionPrediccion": ("prediccion", ["id", "estado", "horizonte_dias", "fecha_corte", "resumen", "creada_en"], ["solicitar()", "ejecutar()"]),
    "Prediccion": ("prediccion", ["demanda_estimada", "limite_inferior", "limite_superior", "modelo", "es_linea_base", "metricas"], []),
    "Recomendacion": ("prediccion", ["id", "tipo", "cantidad_sugerida", "prioridad", "estado", "justificacion"], ["generar()", "aprobar()", "rechazar()", "ejecutar()"]),
    "Auditoria": ("auditoria", ["id", "fecha", "modulo", "accion", "entidad", "resultado", "ip"], ["(solo inserción)"]),
}
ENUMS = {("Venta", "estado"): "EstadoVenta", ("Traslado", "estado"): "EstadoTraslado", ("Recomendacion", "estado"): "EstadoRecomendacion",
         ("Recomendacion", "tipo"): "TipoRecomendacion", ("Alerta", "tipo"): "TipoAlerta", ("Alerta", "estado"): "EstadoAlerta",
         ("Alerta", "prioridad"): "PrioridadAlerta", ("EjecucionPrediccion", "estado"): "EstadoEjecucion", ("Movimiento", "tipo"): "TipoMovimiento",
         ("Rol", "alcance"): "AlcanceRol", ("Auditoria", "resultado"): "ResultadoAuditoria"}
TIPOS = {"int": "int", "str": "str", "Decimal": "Decimal", "datetime": "datetime", "date": "date", "bool": "bool", "dict": "JSON", "list": "JSON"}


def tipos_de(archivo, clase):
    arbol = ast.parse((MODELOS / f"{archivo}.py").read_text(encoding="utf-8"))
    for n in arbol.body:
        if isinstance(n, ast.ClassDef) and n.name == clase:
            res = {}
            for s in n.body:
                if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name):
                    ann = ast.unparse(s.annotation)
                    interior = ann[ann.index("[") + 1:-1] if ann.startswith("Mapped[") else ann
                    opcional = "None" in interior
                    base = interior.replace("| None", "").replace("None |", "").strip()
                    base = base.split("[")[0]
                    res[s.target.id] = TIPOS.get(base, base) + ("?" if opcional else "")
            return res
    raise KeyError(clase)


def nodo(nombre):
    archivo, attrs, ops = CLASES[nombre]
    t = tipos_de(archivo, nombre)
    filas = "".join(f'<TR><TD ALIGN="LEFT" BORDER="0"><FONT POINT-SIZE="10">{a}: {ENUMS.get((nombre, a), t[a])}</FONT></TD></TR>' for a in attrs)
    oper = "".join(f'<TR><TD ALIGN="LEFT" BORDER="0"><FONT POINT-SIZE="10" COLOR="#184f95">{o}</FONT></TD></TR>' for o in ops) or '<TR><TD BORDER="0"> </TD></TR>'
    return (f'{nombre} [label=<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3" COLOR="#52514e" BGCOLOR="white">'
            f'<TR><TD BGCOLOR="#eef1ff" BORDER="0"><B>{nombre}</B></TD></TR><HR/>{filas}<HR/>{oper}</TABLE>>];')


# (a, b, etiqueta, mult_a, mult_b)
RELACIONES = [
    ("Empresa", "Sede", "tiene", "1", "1..*"),
    ("Empresa", "Usuario", "emplea", "1", "1..*"),
    ("Empresa", "Rol", "define", "1", "1..*"),
    ("Rol", "Permiso", "concede", "*", "*"),
    ("Usuario", "Rol", "tiene", "*", "1"),
    ("Usuario", "Sede", "opera en", "*", "0..1"),
    ("Empresa", "Categoria", "organiza", "1", "*"),
    ("Categoria", "Producto", "agrupa", "0..1", "*"),
    ("Sede", "InventarioSede", "mantiene", "1", "*"),
    ("Producto", "InventarioSede", "se almacena", "1", "*"),
    ("InventarioSede", "Movimiento", "registra", "1", "*"),
    ("InventarioSede", "Alerta", "genera", "1", "*"),
    ("Venta", "Movimiento", "produce", "0..1", "*"),
    ("Venta", "VentaItem", "contiene", "1", "1..*"),
    ("VentaItem", "Producto", "vende", "*", "1"),
    ("Sede", "Venta", "registra", "1", "*"),
    ("Traslado", "TrasladoItem", "contiene", "1", "1..*"),
    ("TrasladoItem", "Producto", "mueve", "*", "1"),
    ("Traslado", "Movimiento", "produce", "0..1", "*"),
    ("Traslado", "Sede", "origen y destino", "*", "2"),
    ("EjecucionPrediccion", "Prediccion", "produce", "1", "*"),
    ("EjecucionPrediccion", "Recomendacion", "genera", "1", "*"),
    ("Prediccion", "Producto", "pronostica", "*", "1"),
    ("Recomendacion", "Traslado", "origina", "0..1", "0..1"),
    ("Prediccion", "Sede", "de la sede", "*", "1"),
    ("Recomendacion", "Sede", "para la sede", "*", "1"),
    ("Recomendacion", "Producto", "sobre", "*", "1"),
    ("Usuario", "Auditoria", "deja", "0..1", "*"),
]

def referencia(nombre, nota="(ver otro diagrama)"):
    return (f'{nombre} [label=<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3" COLOR="#b9b8b2" BGCOLOR="#f3f2ee" STYLE="dashed">'
            f'<TR><TD BORDER="0"><B>{nombre}</B></TD></TR><HR/><TR><TD BORDER="0"><FONT POINT-SIZE="9" COLOR="#52514e">{nota}</FONT></TD></TR></TABLE>>];')


DIAGRAMAS = {
    "clases_acceso_organizacion": dict(
        nodos=["Empresa", "Sede", "Usuario", "Rol", "Permiso", "Auditoria"],
        refs=[],
        filas=[["Usuario", "Rol"], ["Sede", "Permiso"]],
        rel=[("Permiso", "Rol"), ("Rol", "Empresa"), ("Empresa", "Sede"), ("Empresa", "Usuario"), ("Usuario", "Rol"),
             ("Usuario", "Sede"), ("Usuario", "Auditoria")]),
    "clases_catalogo_inventario": dict(
        nodos=["Categoria", "Producto", "InventarioSede", "Movimiento", "Alerta"],
        refs=["Empresa", "Sede"], ranksep=0.55,
        filas=[["Empresa", "Sede"], ["Categoria", "InventarioSede"], ["Producto", "Movimiento", "Alerta"]],
        rel=[("Empresa", "Categoria"), ("Categoria", "Producto"), ("Sede", "InventarioSede"), ("Producto", "InventarioSede"),
             ("InventarioSede", "Alerta"), ("InventarioSede", "Movimiento")]),
    "clases_ventas_traslados": dict(
        nodos=["Venta", "VentaItem", "Traslado", "TrasladoItem"],
        refs=["Producto", "Sede", "Movimiento"],
        filas=[["Traslado", "Sede", "Venta"], ["TrasladoItem", "VentaItem"], ["Producto", "Movimiento"]],
        rel=[("Venta", "VentaItem"), ("VentaItem", "Producto"), ("Sede", "Venta"), ("Venta", "Movimiento"), ("Traslado", "TrasladoItem"),
             ("TrasladoItem", "Producto"), ("Traslado", "Sede"), ("Traslado", "Movimiento")]),
    "clases_prediccion_recomendacion": dict(
        nodos=["EjecucionPrediccion", "Prediccion", "Recomendacion"],
        refs=["Producto", "Sede", "Traslado"],
        rel=[("EjecucionPrediccion", "Prediccion"), ("EjecucionPrediccion", "Recomendacion"), ("Prediccion", "Producto"),
             ("Recomendacion", "Traslado"), ("Prediccion", "Sede"), ("Recomendacion", "Sede"), ("Recomendacion", "Producto")]),
}
for nombre, d in DIAGRAMAS.items():
    dot = ['digraph G {', f'graph [rankdir={d.get("direccion", "TB")}, splines=true, nodesep=0.6, ranksep={d.get("ranksep", 1.3)}, pad=0.3, fontname="Inter"];',
           'node [shape=plain, fontname="Inter"];', 'edge [fontname="Inter", fontsize=9, color="#52514e", arrowhead=none, labelfontsize=9, labeldistance=1.7, labelangle=25];']
    dot += [nodo(n) for n in d["nodos"]] + [referencia(n) for n in d["refs"]]
    for fila in d.get("filas", []):
        dot.append("{rank=same; " + "; ".join(fila) + "}")
    usados = set(d["nodos"]) | set(d["refs"])
    for a, b, et, ma, mb in RELACIONES:
        if (a, b) in d["rel"] or (b, a) in d["rel"]:
            dot.append(f'{a} -> {b} [label="{et}", taillabel="{ma}", headlabel="{mb}", fontcolor="#52514e", labelfontcolor="#0b0b0b"];')
    dot.append("}")
    Path(f"{nombre}.dot").write_text("\n".join(dot), encoding="utf-8")
    subprocess.run(["dot", "-Tpng", "-Gdpi=170", f"{nombre}.dot", "-o", f"{nombre}.png"], check=True)
    print(nombre)
