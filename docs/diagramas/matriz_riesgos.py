"""Matriz de calor de riesgos (probabilidad × impacto) a partir de riesgos_datos.py."""
import sys
sys.path.insert(0, "/tmp/claude-0/-home-claude/96d2aac8-ceba-5071-b3a2-b1a2b6db9c4d/scratchpad")
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch
from estilo_fig import *  # fuente Inter y colores
from riesgos_datos import RIESGOS, nivel

FONDO = {"Bajo": "#e3f3ec", "Medio": "#fdf0cf", "Alto": "#fbdcdb"}
BORDE = {"Bajo": "#1baf7a", "Medio": "#eda100", "Alto": "#e34948"}
CAT = {"RT": AZUL, "RC": NARANJA, "RP": VIOLETA, "RD": AQUA}

celdas = defaultdict(list)
for r in RIESGOS:
    celdas[(r[2], r[3])].append(r[0])

fig, ax = plt.subplots(figsize=(14.5, 9.2))
ax.set_xlim(0, 5); ax.set_ylim(0, 5); ax.axis("off"); ax.grid(False)
for p in range(1, 6):
    for i in range(1, 6):
        n = nivel(p, i)
        ax.add_patch(Rectangle((i - 1, p - 1), 1, 1, fc=FONDO[n], ec="white", lw=3, zorder=1))
        ax.text(i - 0.95, p - 0.07, str(p * i), fontsize=7.5, color=BORDE[n], va="top", ha="left", fontweight="bold", zorder=2)
        ids = celdas.get((p, i), [])
        # hasta 3 por fila, centrados
        filas = [ids[k:k + 3] for k in range(0, len(ids), 3)]
        alto = len(filas)
        for f, fila in enumerate(filas):
            y = p - 0.5 + (alto - 1) / 2 * 0.2 - f * 0.2
            for k, rid in enumerate(fila):
                x = i - 0.5 + (k - (len(fila) - 1) / 2) * 0.32
                ax.add_patch(FancyBboxPatch((x - 0.145, y - 0.075), 0.29, 0.15, boxstyle="round,pad=0,rounding_size=0.04",
                                            fc="white", ec=CAT[rid[:2]], lw=1.4, zorder=3))
                ax.text(x, y, rid, ha="center", va="center", fontsize=7.2, color=TEXTO, zorder=4)
for k, et in enumerate(["Muy bajo", "Bajo", "Moderado", "Alto", "Muy alto"], 1):
    ax.text(k - 0.5, -0.1, f"{k}\n{et}", ha="center", va="top", fontsize=8.5, color=TEXTO2)
for k, et in enumerate(["Muy baja", "Baja", "Media", "Alta", "Muy alta"], 1):
    ax.text(-0.08, k - 0.5, f"{et}  {k}", ha="right", va="center", fontsize=8.5, color=TEXTO2)
ax.text(2.5, -0.62, "Impacto", ha="center", fontsize=10, fontweight="bold", color=TEXTO)
ax.text(-0.95, 2.5, "Probabilidad", ha="center", va="center", rotation=90, fontsize=10, fontweight="bold", color=TEXTO)

# leyendas
nn = {n: sum(1 for r in RIESGOS if nivel(r[2], r[3]) == n) for n in FONDO}
x0 = 5.25
ax.text(x0, 4.95, "Nivel de riesgo (P × I)", fontsize=9.5, fontweight="bold", va="top")
for k, (n, rango) in enumerate([("Alto", "12 a 25"), ("Medio", "6 a 11"), ("Bajo", "1 a 5")]):
    y = 4.5 - k * 0.42
    ax.add_patch(Rectangle((x0, y - 0.13), 0.3, 0.26, fc=FONDO[n], ec=BORDE[n], lw=1.4, clip_on=False))
    ax.text(x0 + 0.42, y, f"{n}  ({rango}):  {nn[n]} " + ("riesgo" if nn[n] == 1 else "riesgos"), fontsize=8.8, va="center", color=TEXTO)
ax.text(x0, 3.1, "Categoría (borde del ID)", fontsize=9.5, fontweight="bold", va="top")
for k, (c, nombre) in enumerate([("RT", "RT  Tecnológicos"), ("RC", "RC  Del cliente o usuario"), ("RP", "RP  Del proceso"), ("RD", "RD  Del producto")]):
    y = 2.7 - k * 0.42
    ax.add_patch(FancyBboxPatch((x0, y - 0.1), 0.34, 0.2, boxstyle="round,pad=0,rounding_size=0.04", fc="white", ec=CAT[c], lw=1.6, clip_on=False))
    ax.text(x0 + 0.46, y, nombre, fontsize=8.8, va="center", color=TEXTO)
ax.text(x0, 0.95, "Escala de 1 a 5 en probabilidad e impacto.\nValoración del equipo sobre el riesgo\ninherente (antes de la mitigación);\nes un juicio informado, no una medición.", fontsize=8, color=TEXTO2, va="top", linespacing=1.4)
ax.set_xlim(-1.1, 7.4); ax.set_ylim(-0.95, 5.05)
fig.savefig("matriz_riesgos.png", dpi=200, bbox_inches="tight", facecolor="white")
print(nn)
