"""Figura: diagrama general de casos de uso (UML) de Inventia. Se dibuja a mano para controlar el trazado.

    python casos_de_uso.py        # escribe casos_de_uso.png junto a este archivo
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Polygon, Rectangle, FancyBboxPatch

AZUL, AZUL_CL, GRIS, TEXTO, NARANJA = "#3b5bf0", "#eef1ff", "#52514e", "#0b0b0b", "#eb6834"

CASOS = [  # (id, texto, actores)
    ("CU-03", "Gestionar empresa, sedes, usuarios y roles", ["adm"]),
    ("CU-04", "Gestionar categorías y productos", ["adm"]),
    ("CU-15", "Gestionar llaves de agentes de IA", ["adm"]),
    ("CU-17", "Configurar niveles mínimo y máximo", ["enc"]),
    ("CU-05", "Registrar entradas, salidas y ajustes", ["usu", "enc"]),
    ("CU-06", "Registrar y anular ventas", ["usu", "enc"]),
    ("CU-08", "Solicitar, aprobar y confirmar traslados", ["usu", "enc"]),
    ("CU-10", "Generar predicción de demanda", ["ana", "ia"]),
    ("CU-11", "Generar recomendaciones", ["ana", "ia"]),
    ("CU-12", "Aprobar o rechazar recomendaciones", ["enc", "ana", "ger"]),
    ("CU-13", "Generar y exportar reportes (pantalla, CSV, Excel, PDF)", ["usu", "enc", "ana", "ger"]),
    ("CU-14", "Consultar auditoría", ["enc", "ger"]),
    ("CU-01", "Iniciar y cerrar sesión", ["aut"]),
    ("CU-02", "Recuperar contraseña", ["aut"]),
    ("CU-07", "Consultar inventario por sede y consolidado (según permiso)", ["aut"]),
    ("CU-09", "Consultar alertas de inventario", ["aut"]),
    ("CU-16", "Usar el SIG (PQRS, SST, calidad, gestión ambiental)", ["aut"]),
]
ACTORES = {  # clave: (x, y, etiqueta)
    "adm": (1.2, 1.0, "Administrador\n(todos los permisos)"),
    "usu": (1.2, 3.9, "Usuario de\ninventario"),
    "enc": (1.2, 6.7, "Encargado\nde sede"),
    "ana": (1.2, 9.2, "Analista\nde compras"),
    "ger": (1.2, 11.6, "Gerente"),
    "aut": (1.2, 14.6, "Usuario autenticado\n(actor abstracto)"),
    "ia": (11.6, 7.5, "Sistema de IA\n(actor secundario)"),
}
X_CU, ANCHO, ALTO, PASO = 6.9, 6.0, 0.62, 1.0

fig, ax = plt.subplots(figsize=(11.5, 9.6))
ax.set_xlim(-0.8, 13.0); ax.set_ylim(17.4, -1.4); ax.axis("off")
ax.add_patch(FancyBboxPatch((3.7, -0.9), 6.4, 17.3, boxstyle="round,pad=0.02,rounding_size=0.3", fc="none", ec=AZUL, lw=1.4))
ax.text(3.95, -0.55, "Sistema Inventia", color="#184f95", fontsize=11, fontweight="bold", va="center")

y_cu = {}
for i, (cid, txt, _) in enumerate(CASOS):
    y = 0.55 + i * 0.97
    y_cu[cid] = y
    ax.add_patch(Ellipse((X_CU, y), ANCHO, ALTO + 0.1, fc=AZUL_CL, ec=AZUL, lw=1.1, zorder=3))
    ax.text(X_CU, y, f"{cid}  {txt}", ha="center", va="center", fontsize=7.4, color=TEXTO, zorder=4)

def actor(clave):
    x, y, etiqueta = ACTORES[clave]
    color = NARANJA if clave == "ia" else GRIS
    ax.add_patch(plt.Circle((x, y - 0.55), 0.17, fc="white", ec=color, lw=1.4, zorder=5))
    ax.plot([x, x], [y - 0.38, y + 0.12], color=color, lw=1.4, zorder=5)
    ax.plot([x - 0.3, x + 0.3], [y - 0.22, y - 0.22], color=color, lw=1.4, zorder=5)
    ax.plot([x, x - 0.25], [y + 0.12, y + 0.48], color=color, lw=1.4, zorder=5)
    ax.plot([x, x + 0.25], [y + 0.12, y + 0.48], color=color, lw=1.4, zorder=5)
    ax.text(x, y + 0.78, etiqueta, ha="center", va="top", fontsize=7.8, color=TEXTO, fontweight="bold", zorder=5)
for k in ACTORES:
    actor(k)

# asociaciones
for cid, _, acts in CASOS:
    for a in acts:
        ax_, ay_, _ = ACTORES[a]
        if a == "ia":
            ax.plot([X_CU + ANCHO / 2, ax_ - 0.3], [y_cu[cid], ay_ - 0.1], color=NARANJA, lw=0.9, zorder=1)
        else:
            ax.plot([ax_ + 0.35, X_CU - ANCHO / 2], [ay_ - 0.1, y_cu[cid]], color=GRIS, lw=0.8, zorder=1)

# generalización: roles -> usuario autenticado (codo por el borde izquierdo)
xg = -0.2
yaut = ACTORES["aut"][1] - 0.5
for r in ("adm", "usu", "enc", "ana", "ger"):
    x, y, _ = ACTORES[r]
    ax.plot([x - 0.55, xg], [y - 0.1, y - 0.1], color="#9a9890", lw=1, ls="--", zorder=1)
ax.plot([xg, xg], [ACTORES["adm"][1] - 0.1, yaut - 0.5], color="#9a9890", lw=1, ls="--", zorder=1)
ax.plot([xg, ACTORES["aut"][0]], [yaut - 0.5, yaut - 0.5], color="#9a9890", lw=1, ls="--", zorder=1)
ax.add_patch(Polygon([[ACTORES["aut"][0] - 0.45, yaut - 0.5], [ACTORES["aut"][0] - 0.2, yaut - 0.7], [ACTORES["aut"][0] - 0.2, yaut - 0.3]],
                     closed=True, fc="white", ec="#9a9890", lw=1, zorder=2))
ax.text(xg - 0.1, 7.0, "es un", rotation=90, ha="right", va="center", fontsize=7.5, color="#52514e")

out = Path(__file__).with_name("casos_de_uso.png")
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
print(out)
