"""Utilidades mínimas para dibujar diagramas de cajas y flechas con matplotlib (estilo común de las figuras)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

AZUL, AZUL_CL, AZUL_OSC = "#3b5bf0", "#eef1ff", "#184f95"
NARANJA, NARANJA_CL = "#eb6834", "#fff1e8"
VERDE, VERDE_CL = "#1baf7a", "#e8f7f0"
AMARILLO, AMARILLO_CL = "#eda100", "#fff6e0"
GRIS, GRIS_CL, GRIS_MED, TEXTO = "#52514e", "#f3f2ee", "#b9b8b2", "#0b0b0b"

ESTILOS = {
    "azul": (AZUL_CL, AZUL), "naranja": (NARANJA_CL, NARANJA), "verde": (VERDE_CL, VERDE),
    "amarillo": (AMARILLO_CL, AMARILLO), "gris": (GRIS_CL, GRIS),
}


def lienzo(ancho, alto, xlim, ylim):
    fig, ax = plt.subplots(figsize=(ancho, alto))
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.axis("off")
    ax.set_aspect("auto")
    return fig, ax


def grupo(ax, x, y, w, h, titulo, color=GRIS_MED, texto=GRIS, estilo="-", lw=1.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.25", fc="none", ec=color, lw=lw, ls=estilo, zorder=1))
    ax.text(x + 0.2, y + h - 0.2, titulo, ha="left", va="top", fontsize=9, color=texto, fontweight="bold", zorder=2)


def caja(ax, x, y, w, h, titulo, detalle="", estilo="azul", tam=8.5):
    fc, ec = ESTILOS[estilo]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.2", fc=fc, ec=ec, lw=1.3, zorder=3))
    if detalle:
        ax.text(x + w / 2, y + h * 0.66, titulo, ha="center", va="center", fontsize=tam, fontweight="bold", color=TEXTO, zorder=4)
        ax.text(x + w / 2, y + h * 0.30, detalle, ha="center", va="center", fontsize=tam - 1.2, color=GRIS, zorder=4, linespacing=1.25)
    else:
        ax.text(x + w / 2, y + h / 2, titulo, ha="center", va="center", fontsize=tam, fontweight="bold", color=TEXTO, zorder=4)
    return (x, y, w, h)


def centro(c, lado):
    x, y, w, h = c
    return {"s": (x + w / 2, y), "n": (x + w / 2, y + h), "o": (x, y + h / 2), "e": (x + w, y + h / 2)}[lado]


def flecha(ax, p, q, etiqueta="", color=GRIS, estilo="-", curva=0.0, desplaza=(0, 0), ambos=False, tam=7.5):
    a = FancyArrowPatch(p, q, arrowstyle="<|-|>" if ambos else "-|>", mutation_scale=11, lw=1.2, color=color, ls=estilo,
                        connectionstyle=f"arc3,rad={curva}", zorder=2, shrinkA=0, shrinkB=0)
    ax.add_patch(a)
    if etiqueta:
        ax.text((p[0] + q[0]) / 2 + desplaza[0], (p[1] + q[1]) / 2 + desplaza[1], etiqueta, ha="center", va="center", fontsize=tam,
                color=GRIS, zorder=5, bbox=dict(fc="white", ec="none", pad=1.2))


def guardar(fig, ruta):
    fig.savefig(ruta, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(ruta)
