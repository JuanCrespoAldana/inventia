"""Árbol de problemas (causas y efectos) del planteamiento del problema de Inventia."""
from dibujo import *

fig, ax = lienzo(15.9, 10.2, (-0.9, 15), (0, 10.2))
W, H = 3.35, 1.05
xs = [0.2 + k * 3.72 for k in range(4)]

def texto_caja(x, y, w, h, txt, estilo, tam=8.6):
    fc, ec = ESTILOS[estilo]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.18", fc=fc, ec=ec, lw=1.4, zorder=3))
    ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=tam, color=TEXTO, zorder=4, linespacing=1.3)
    return (x, y, w, h)

def banda(y, h, txt):
    ax.add_patch(FancyBboxPatch((-0.9, y), 15.9, h, boxstyle="round,pad=0,rounding_size=0.15", fc="none", ec=GRIS_MED, lw=0.8, ls=(0, (4, 3)), zorder=1))
    ax.text(-0.55, y + h / 2, txt, ha="center", va="center", rotation=90, fontsize=9, color=GRIS, fontweight="bold", zorder=2)

# Efectos
banda(6.6, 3.55, "EFECTOS")
banda(4.5, 1.85, "PROBLEMA CENTRAL")
final = texto_caja(3.45, 8.85, 8.1, 1.0, "Menor eficiencia operativa y competitividad de la PyME multisede:\ndecisiones de compra y distribución poco oportunas", "naranja", 9.2)
efectos = [
    "Datos de inventario poco confiables;\nrevisiones físicas frecuentes",
    "Desabastecimiento: retrasos en la\natención y ventas perdidas",
    "Exceso de productos de baja rotación:\ncostos de almacenamiento y obsolescencia",
    "Existencias de una sede sin aprovechar\nen otra; compras evitables",
]
ce = [texto_caja(x, 7.1, W, H, t, "naranja") for x, t in zip(xs, efectos)]
for c in ce:
    flecha(ax, centro(c, "n"), (centro(c, "n")[0] * 0.55 + 7.5 * 0.45, 8.85), color=NARANJA)

# Problema central
central = texto_caja(0.2, 4.75, 14.6, 1.35,
    "Ausencia de un sistema centralizado e inteligente que permita a las PyMEs con varias sedes\n"
    "gestionar sus inventarios, consultar la disponibilidad de los productos\ny anticipar sus necesidades de reabastecimiento",
    "azul", 10)
ax.patches[-1].set_linewidth(2.2)
for c, x in zip(ce, xs):
    flecha(ax, (x + W / 2 * 0.0 + W / 2, 6.1), (x + W / 2, 7.1), color=NARANJA)

# Causas
banda(0.1, 4.25, "CAUSAS")
directas = [
    "Registros manuales y hojas de cálculo\ndesconectadas entre sí",
    "Cada sede administra su inventario\npor separado, sin visión consolidada",
    "Compras y reposición decididas por\nexperiencia, sin pronósticos de la demanda",
    "Poca trazabilidad de los movimientos\ny de los responsables de cada operación",
]
raices = [
    "Falta de una herramienta integrada\ny accesible para la PyME",
    "Información sin una base de datos\ncentralizada por empresa",
    "Historial de ventas no consolidado\nni analizado de forma sistemática",
    "Sin control de acceso por rol\ny sede ni registro de auditoría",
]
cd = [texto_caja(x, 3.0, W, H, t, "verde") for x, t in zip(xs, directas)]
cr = [texto_caja(x, 0.55, W, H, t, "gris") for x, t in zip(xs, raices)]
for a, b, x in zip(cd, cr, xs):
    flecha(ax, (x + W / 2, 1.6), (x + W / 2, 3.0), color=GRIS)
    flecha(ax, (x + W / 2, 4.05), (x + W / 2, 4.75), color=VERDE)
guardar(fig, "arbol_problemas.png")
