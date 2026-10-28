"""Diagrama de Gantt del plan de referencia (cronograma_datos.py)."""
import sys
sys.path.insert(0, "/tmp/claude-0/-home-claude/96d2aac8-ceba-5071-b3a2-b1a2b6db9c4d/scratchpad")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from estilo_fig import *
from cronograma_datos import ACTIVIDADES, HITOS, OBJETIVOS, SEMANAS

COLOR = {"OE1": AZUL, "OE2": NARANJA, "OE3": AQUA, "OE4": VIOLETA, "OE5": AMARILLO, "Doc.": GRIS}
n = len(ACTIVIDADES)
fig, ax = plt.subplots(figsize=(13.5, 8.2))
ax.set_xlim(0.5, SEMANAS + 0.5); ax.set_ylim(n + 0.6, -1.2)
for i, (oe, act, a, b) in enumerate(ACTIVIDADES):
    ax.barh(i, b - a + 1, left=a - 0.5, height=0.58, color=COLOR[oe], edgecolor="white", linewidth=1.2, zorder=3)
    ax.text(a - 0.5 + (b - a + 1) + 0.12, i, f"S{a}–S{b}", va="center", ha="left", fontsize=7.6, color=TEXTO2)
ax.set_yticks(range(n)); ax.set_yticklabels([a[1] for a in ACTIVIDADES], fontsize=8.6)
ax.set_xticks(range(1, SEMANAS + 1)); ax.set_xticklabels([f"{k}" for k in range(1, SEMANAS + 1)], fontsize=8)
ax.set_xlabel("Semana del proyecto (referencia relativa)", fontsize=9.5)
ax.grid(axis="x", color=GRIS_CLARO, lw=0.6); ax.grid(axis="y", visible=False)
ax.tick_params(axis="y", length=0)
for s in ("left", "bottom"):
    ax.spines[s].set_color(GRIS)
# hitos
for s, nombre in HITOS:
    ax.axvline(s + 0.5, color=ROJO, lw=1.1, ls=(0, (4, 3)), zorder=2, ymin=0, ymax=0.97)
    ax.text(s + 0.5, -0.85, nombre, ha="center", va="bottom", fontsize=8, color=ROJO, fontweight="bold", rotation=0)
ax.legend(handles=[Patch(color=COLOR[k], label=OBJETIVOS[k]) for k in COLOR], loc="lower left", bbox_to_anchor=(0.0, -0.20), ncol=6, fontsize=8.6, handlelength=1.2)
ax.set_title("")
fig.savefig("cronograma.png", dpi=200, bbox_inches="tight", facecolor="white")
print("cronograma.png")
