"""Figuras de resultados: simulación de políticas de reposición (ml/resultados) y pruebas de carga (docs/RENDIMIENTO.md)."""
import json
import sys
from pathlib import Path
sys.path.insert(0, "/tmp/claude-0/-home-claude/96d2aac8-ceba-5071-b3a2-b1a2b6db9c4d/scratchpad")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
from estilo_fig import *

RAIZ = Path(__file__).resolve().parents[2]
sim = json.loads((RAIZ / "ml" / "resultados" / "simulacion_resumen.json").read_text(encoding="utf-8"))["politicas"]
ETQ = {"A": "A  Sin reposición", "B": "B  Mínimos y\nmáximos fijos", "C": "C  Reglas de Inventia,\npromedio de 28 días", "D": "D  Reglas de Inventia,\npronóstico del sistema"}
COL = {"A": GRIS, "B": NARANJA, "C": AQUA, "D": AZUL}

# ------------------------------------------------------------------ Simulación: servicio e inventario
fig, axs = plt.subplots(1, 2, figsize=(12, 4.6))
claves = list(sim)
for ax, campo, titulo, fmt in [
    (axs[0], "nivel_de_servicio", "Nivel de servicio (% de la demanda atendida)", lambda v: f"{v*100:.1f}".replace(".", ",") + " %"),
    (axs[1], "dias_de_inventario", "Inventario promedio (días de venta cubiertos)", lambda v: f"{v:.1f}".replace(".", ",")),
]:
    vals = [sim[k][campo] for k in claves]
    barras = ax.bar(range(4), vals, color=[COL[k] for k in claves], width=0.62)
    for r, v in zip(barras, vals):
        ax.text(r.get_x() + r.get_width() / 2, v, fmt(v), ha="center", va="bottom", fontsize=9, color=TEXTO)
    ax.set_xticks(range(4)); ax.set_xticklabels([ETQ[k] for k in claves], fontsize=8.2)
    ax.set_title(titulo, fontsize=10.5, pad=10)
    ax.grid(axis="x", visible=False); ax.tick_params(axis="x", length=0)
    ax.set_ylim(0, max(vals) * 1.15)
axs[0].set_yticks([0, 0.25, 0.5, 0.75, 1.0]); axs[0].set_yticklabels(["0", "25", "50", "75", "100"]); axs[0].set_ylim(0, 1.1)
axs[1].set_ylabel("días")
fig.tight_layout()
fig.savefig("res_simulacion_politicas.png", dpi=200, bbox_inches="tight", facecolor="white"); plt.close(fig)

# ------------------------------------------------------------------ Simulación: ventas perdidas por semana
fig, ax = plt.subplots(figsize=(10, 4.4))
sem = range(1, 9)
for k in ["A", "B", "C", "D"]:
    y = sim[k]["perdidas_por_semana"]
    ax.plot(sem, y, color=COL[k], lw=2, marker="o", ms=4.5, label=ETQ[k].replace("\n", " "), zorder=3 if k in "CD" else 2)
ax.set_xlabel("Semana de la simulación"); ax.set_ylabel("Unidades de demanda no atendidas")
ax.set_xticks(list(sem)); ax.grid(axis="x", visible=False)
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(miles))
ax.legend(loc="upper left", fontsize=8.6, ncol=1)
fig.savefig("res_simulacion_semanal.png", dpi=200, bbox_inches="tight", facecolor="white"); plt.close(fig)

# ------------------------------------------------------------------ Carga: usuarios simultáneos y volumen de datos
fig, axs = plt.subplots(1, 2, figsize=(12.2, 4.6))
usuarios = [5, 20, 50]
med = [16, 18, 23]; p95 = [45, 56, 100]
x = range(3)
a = axs[0]
a.bar([i - 0.19 for i in x], med, width=0.36, color=AZUL, label="Mediana")
a.bar([i + 0.19 for i in x], p95, width=0.36, color=NARANJA, label="Percentil 95")
for i in x:
    a.text(i - 0.19, med[i], str(med[i]), ha="center", va="bottom", fontsize=9)
    a.text(i + 0.19, p95[i], str(p95[i]), ha="center", va="bottom", fontsize=9)
a.set_xticks(list(x)); a.set_xticklabels([f"{u} usuarios" for u in usuarios])
a.set_ylabel("Tiempo de respuesta (ms)"); a.set_ylim(0, 125)
a.set_title("Usuarios simultáneos (0 peticiones fallidas)", fontsize=10.5, pad=10)
a.legend(loc="upper left", fontsize=8.6); a.grid(axis="x", visible=False); a.tick_params(axis="x", length=0)

b = axs[1]
escala = [1, 10, 50]
series = [
    ("Panel (30 días)", [39, 67, 86], AZUL),
    ("Existencias consolidadas", [13, 16, 12], AQUA),
    ("Ventas, última página", [11, 33, 141], VIOLETA),
    ("Movimientos, última página", [21, 103, 441], NARANJA),
]
for nombre, v, c in series:
    b.plot(escala, v, color=c, lw=2, marker="o", ms=5, label=nombre)
    b.text(50 * 1.07, v[-1], str(v[-1]), va="center", fontsize=8.6, color=TEXTO2)
b.axhline(3000, color=ROJO, lw=1.2, ls=(0, (4, 3)))
b.text(1.0, 3000 * 1.12, "Límite de RNF-011: 3 s", color=ROJO, fontsize=8.8, va="bottom")
b.set_xscale("log"); b.set_yscale("log"); b.set_xticks(escala); b.set_xticklabels(["×1", "×10", "×50"])
b.set_xlim(0.85, 70); b.set_ylim(6, 6000)
b.set_yticks([10, 100, 1000]); b.set_yticklabels(["10", "100", "1.000"])
b.minorticks_off()
b.set_xlabel("Volumen de datos respecto de la base de demostración"); b.set_ylabel("Mediana (ms, escala logarítmica)")
b.set_title("Un usuario y volumen de datos creciente", fontsize=10.5, pad=10)
b.legend(loc="upper center", fontsize=8.4, bbox_to_anchor=(0.5, -0.22), ncol=2)
fig.tight_layout()
fig.savefig("res_carga.png", dpi=200, bbox_inches="tight", facecolor="white"); plt.close(fig)
print("ok")
