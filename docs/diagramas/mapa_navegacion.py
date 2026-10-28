"""Mapa de navegación de Inventia, tomado de frontend/src/components/layout/navegacion.ts y App.tsx."""
from dibujo import *

fig, ax = lienzo(16, 8.1, (0, 16), (1.7, 9.8))

def nodo(x, y, w, h, txt, estilo="azul", tam=8.2, negrita=False):
    fc, ec = ESTILOS[estilo]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.12", fc=fc, ec=ec, lw=1.2, zorder=3))
    ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=tam, color=TEXTO, zorder=4,
            fontweight="bold" if negrita else "normal", linespacing=1.25)
    return (x, y, w, h)

def linea(pts, color=GRIS_MED, flecha_final=True):
    for p, q in zip(pts[:-2], pts[1:-1]):
        ax.plot([p[0], q[0]], [p[1], q[1]], color=color, lw=1.3, zorder=2, solid_capstyle="round")
    if flecha_final:
        flecha(ax, pts[-2], pts[-1], color=color)
    else:
        ax.plot([pts[-2][0], pts[-1][0]], [pts[-2][1], pts[-1][1]], color=color, lw=1.3, zorder=2)

# Zona de acceso (pantallas públicas y de sesión)
ax.add_patch(FancyBboxPatch((0.1, 8.0), 9.0, 1.75, boxstyle="round,pad=0,rounding_size=0.15", fc="none", ec=GRIS_MED, lw=1, ls=(0, (4, 3))))
ax.text(0.3, 9.6, "ACCESO", va="top", fontsize=8.6, color=GRIS, fontweight="bold")
login = nodo(0.3, 8.5, 1.95, 0.75, "Ingreso\n/login", "gris", negrita=True)
rec = nodo(2.4, 8.5, 1.95, 0.75, "Recuperar contraseña\n/recuperar", "gris")
conf = nodo(4.5, 8.5, 2.1, 0.75, "Configuración inicial\n/configuracion-inicial", "gris")
camb = nodo(6.75, 8.5, 2.1, 0.75, "Cambiar contraseña\n/cambiar-password", "gris")
for x, t in [(3.375, "Si olvidó su contraseña"), (5.55, "Primer uso (una sola vez)"), (7.8, "Cambio obligatorio")]:
    ax.text(x, 8.25, t, ha="center", va="center", fontsize=7.2, color=GRIS)

# Panel y encabezado
panel = nodo(5.9, 6.55, 2.2, 0.8, "Panel de control\n/", "azul", negrita=True)
linea([(1.275, 8.5), (1.275, 6.95), (5.9, 6.95)], color=AZUL)
ax.text(3.0, 7.08, "sesión iniciada", fontsize=7.4, color=AZUL, ha="center")
ax.add_patch(FancyBboxPatch((9.6, 6.9), 6.2, 2.85, boxstyle="round,pad=0,rounding_size=0.15", fc="none", ec=GRIS_MED, lw=1, ls=(0, (4, 3))))
ax.text(9.8, 9.6, "ENCABEZADO DE LA APLICACIÓN", va="top", fontsize=8.6, color=GRIS, fontweight="bold")
nodo(9.85, 8.5, 2.7, 0.75, "Perfil  /perfil\nDatos propios y contraseña", "azul", tam=7.8)
nodo(12.85, 8.5, 2.7, 0.75, "Salir\nCierra la sesión y vuelve a /login", "azul", tam=7.8)
ax.text(9.85, 8.15, "Visibilidad por permisos: cada opción del menú aparece solo si el rol\ntiene el permiso de la pantalla, y el servidor lo valida en cada solicitud.\nSin permiso se muestra «No tiene acceso a esta sección».\nEn móvil, el menú lateral se abre desde el encabezado.",
        fontsize=7.4, color=GRIS, va="top", linespacing=1.45)

# Menú lateral: bus y grupos
ax.text(0.15, 6.2, "MENÚ LATERAL", fontsize=8.6, color=GRIS, fontweight="bold", va="center")
GRUPOS = [
    ("INVENTARIO", "azul", [("Existencias", "/inventario"), ("Consolidado", "/inventario/consolidado"), ("Movimientos", "/movimientos"), ("Productos", "/productos"), ("Categorías", "/categorias")]),
    ("OPERACIÓN", "verde", [("Ventas", "/ventas  ▸  /ventas/nueva · /ventas/:id"), ("Traslados", "/traslados  ▸  /traslados/nuevo · /traslados/:id"), ("Alertas", "/alertas")]),
    ("INTELIGENCIA", "naranja", [("Predicción de demanda", "/predicciones"), ("Recomendaciones", "/recomendaciones"), ("Reportes", "/reportes")]),
    ("SIG", "amarillo", [("PQRS y sugerencias", "/sig/pqrs"), ("Seguridad y Salud en el Trabajo", "/sig/sst"), ("Calidad", "/sig/calidad"), ("Gestión ambiental", "/sig/ambiental")]),
    ("ADMINISTRACIÓN", "gris", [("Empresa", "/empresa"), ("Sedes", "/sedes"), ("Usuarios", "/usuarios"), ("Roles y permisos", "/roles"), ("Auditoría", "/auditoria"), ("Agentes de IA", "/integraciones")]),
]
W, GAP, TOP = 2.95, 0.12, 5.6
centros = []
for k, (nombre, estilo, items) in enumerate(GRUPOS):
    x = 0.2 + k * (W + GAP)
    alto = 0.5 + len(items) * 0.52
    fc, ec = ESTILOS[estilo]
    ax.add_patch(FancyBboxPatch((x, TOP - alto), W, alto, boxstyle="round,pad=0,rounding_size=0.15", fc="white", ec=ec, lw=1.4, zorder=2))
    ax.add_patch(FancyBboxPatch((x, TOP - 0.45), W, 0.45, boxstyle="round,pad=0,rounding_size=0.15", fc=fc, ec=ec, lw=1.4, zorder=3))
    ax.text(x + W / 2, TOP - 0.225, nombre, ha="center", va="center", fontsize=8.6, fontweight="bold", color=TEXTO, zorder=4)
    for j, (et, ruta) in enumerate(items):
        y = TOP - 0.45 - 0.52 * (j + 1) + 0.12
        ax.text(x + 0.14, y + 0.27, et, fontsize=8, va="center", color=TEXTO, zorder=4)
        ax.text(x + 0.14, y + 0.07, ruta, fontsize=6.7, va="center", color=GRIS, zorder=4)
    centros.append(x + W / 2)
BUS = 6.0
ax.plot([centros[0], centros[-1]], [BUS, BUS], color=GRIS_MED, lw=1.3, zorder=2)
ax.plot([7.0, 7.0], [6.55, BUS], color=GRIS_MED, lw=1.3, zorder=2)
for c in centros:
    flecha(ax, (c, BUS), (c, TOP), color=GRIS_MED)
guardar(fig, "mapa_navegacion.png")
