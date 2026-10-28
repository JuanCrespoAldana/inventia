"""Figuras: procesos de gestión de inventario en notación BPMN simplificada (carriles verticales).

    python bpmn.py   # escribe bpmn_as_is.png y bpmn_to_be.png junto a este archivo

El proceso AS-IS es un proceso de REFERENCIA construido a partir de la descripción del problema y de prácticas habituales en
PyMEs multisede; debe validarse con el caso de estudio real (instrumentos del Anexo C) antes de presentarse como diagnóstico.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle

AZUL, AZUL_CL, GRIS, GRIS_CL, TEXTO = "#3b5bf0", "#eef1ff", "#52514e", "#f3f2ee", "#0b0b0b"
ROJO, VERDE, NARANJA, NARANJA_CL = "#e34948", "#1baf7a", "#eb6834", "#fff1e8"
ANCHO_CARRIL, PASO = 4.7, 2.15


class Diagrama:
    def __init__(self, carriles, filas, titulo_alto=0.9):
        self.carriles, self.filas, self.t = carriles, filas, titulo_alto
        self.fig, self.ax = plt.subplots(figsize=(len(carriles) * 4.1, (filas * PASO + titulo_alto + 0.6) * 0.84))
        self.ax.set_xlim(0, len(carriles) * ANCHO_CARRIL)
        self.ax.set_ylim(filas * PASO + titulo_alto + 0.4, 0)
        self.ax.axis("off")
        for i, nombre in enumerate(carriles):
            x0 = i * ANCHO_CARRIL
            self.ax.add_patch(Rectangle((x0, 0), ANCHO_CARRIL, filas * PASO + titulo_alto + 0.4, fc="white" if i % 2 else "#fafaf8", ec="#b9b8b2", lw=1.2, zorder=0))
            self.ax.add_patch(Rectangle((x0, 0), ANCHO_CARRIL, titulo_alto, fc=GRIS_CL, ec="#b9b8b2", lw=1.2, zorder=1))
            self.ax.text(x0 + ANCHO_CARRIL / 2, titulo_alto / 2, nombre, ha="center", va="center", fontsize=10, fontweight="bold", color=TEXTO, zorder=2)

    def pos(self, carril, fila):
        return carril * ANCHO_CARRIL + ANCHO_CARRIL / 2, self.t + 0.55 + fila * PASO

    def tarea(self, carril, fila, texto, dx=0, color=AZUL, relleno=AZUL_CL, ancho=3.7, alto=1.15):
        x, y = self.pos(carril, fila)
        x += dx
        self.ax.add_patch(FancyBboxPatch((x - ancho / 2, y - alto / 2), ancho, alto, boxstyle="round,pad=0,rounding_size=0.18", fc=relleno, ec=color, lw=1.4, zorder=3))
        self.ax.text(x, y, texto, ha="center", va="center", fontsize=8.3, color=TEXTO, zorder=4, linespacing=1.25)
        return x, y

    def evento(self, carril, fila, tipo, texto="", dx=0, lado="abajo"):
        """Evento BPMN (inicio, fin o temporizador). El texto va debajo del círculo o a su derecha."""
        x, y = self.pos(carril, fila)
        x += dx
        color = {"inicio": VERDE, "fin": ROJO, "tiempo": NARANJA}[tipo]
        self.ax.add_patch(Circle((x, y), 0.32, fc="white", ec=color, lw=3.2 if tipo == "fin" else 1.6, zorder=3))
        if tipo == "tiempo":
            self.ax.plot([x, x], [y, y - 0.17], color=color, lw=1.2, zorder=4)
            self.ax.plot([x, x + 0.12], [y, y + 0.06], color=color, lw=1.2, zorder=4)
        if texto:
            if lado == "abajo":
                self.ax.text(x, y + 0.5, texto, ha="center", va="top", fontsize=7.8, color=TEXTO, zorder=4, linespacing=1.2)
            else:
                self.ax.text(x + 0.5, y, texto, ha="left", va="center", fontsize=7.8, color=TEXTO, zorder=4, linespacing=1.2)
        return x, y

    def compuerta(self, carril, fila, texto, dx=0, ancho=3.0, alto=1.55):
        x, y = self.pos(carril, fila)
        x += dx
        self.ax.add_patch(Polygon([[x, y - alto / 2], [x + ancho / 2, y], [x, y + alto / 2], [x - ancho / 2, y]], closed=True, fc="#fff6e0", ec="#eda100", lw=1.5, zorder=3))
        self.ax.text(x, y, texto, ha="center", va="center", fontsize=7.8, color=TEXTO, zorder=4, linespacing=1.2)
        return x, y

    def flujo(self, puntos, etiqueta="", color=GRIS, estilo="-", segmento=0, posicion=0.5, desplaza=(0.0, 0.0)):
        """Polilínea ortogonal con flecha en el último tramo. La etiqueta se ancla en el ``segmento`` indicado."""
        for a, b in zip(puntos[:-2], puntos[1:-1]):
            self.ax.plot([a[0], b[0]], [a[1], b[1]], color=color, lw=1.3, ls=estilo, zorder=2)
        a, b = puntos[-2], puntos[-1]
        self.ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=11, lw=1.3, color=color, ls=estilo, zorder=2, shrinkA=0, shrinkB=0))
        if etiqueta:
            p, q = puntos[segmento], puntos[segmento + 1]
            self.ax.text(p[0] + (q[0] - p[0]) * posicion + desplaza[0], p[1] + (q[1] - p[1]) * posicion + desplaza[1], etiqueta, ha="center", va="center",
                         fontsize=8, fontweight="bold", color=GRIS, zorder=5, bbox=dict(fc="white", ec="none", pad=0.8))

    def dolor(self, x, y, n):
        self.ax.add_patch(Circle((x, y), 0.22, fc=ROJO, ec="white", lw=1, zorder=6))
        self.ax.text(x, y, str(n), ha="center", va="center", fontsize=8, fontweight="bold", color="white", zorder=7)

    def guardar(self, nombre, pie=""):
        if pie:
            self.ax.text(0.1, self.filas * PASO + self.t + 0.25, pie, ha="left", va="center", fontsize=7.8, color=GRIS, linespacing=1.4, zorder=5)
        self.fig.savefig(Path(__file__).with_name(nombre), dpi=200, bbox_inches="tight", facecolor="white")
        plt.close(self.fig)
        print(nombre)


# ------------------------------------------------------------------------------------------------ AS-IS
H = 0.575  # mitad de la altura de una tarea
d = Diagrama(["Encargado de sede", "Administración", "Proveedor"], 10)
cx = lambda c: c * ANCHO_CARRIL + ANCHO_CARRIL / 2
y = lambda f: d.t + 0.55 + f * PASO
d.evento(0, 0, "inicio", "Se vende o recibe mercancía", lado="derecha")
d.tarea(0, 1, "Anota la operación en un cuaderno\no en una hoja propia de la sede")
d.tarea(0, 2, "Cuenta la mercancía y compara\n(de forma periódica)")
d.compuerta(0, 3, "¿Existencias\nbajas?")
d.tarea(0, 4, "Avisa por llamada, WhatsApp\no correo")
d.tarea(1, 4, "Recibe avisos y hojas\nde cada sede")
d.tarea(1, 5, "Consolida a mano en una\nhoja de cálculo")
d.tarea(1, 6, "Decide con su experiencia\nqué pedir o mover")
d.compuerta(1, 7, "¿Otra sede tiene\nsobrante?")
d.tarea(1, 8, "Coordina el traslado\npor llamada", dx=-1.25, ancho=2.1)
d.tarea(1, 8, "Pide la compra\nal proveedor", dx=1.25, ancho=2.1)
d.tarea(2, 8, "Entrega la mercancía", ancho=3.0)
d.tarea(0, 8, "Envía o recibe la mercancía\ny la anota a mano")
d.evento(0, 9, "fin", "Inventario actualizado solo\nen el cuaderno de la sede", dx=0.0)
d.flujo([(cx(0), y(0) + 0.32), (cx(0), y(1) - H)])
d.flujo([(cx(0), y(1) + H), (cx(0), y(2) - H)])
d.flujo([(cx(0), y(2) + H), (cx(0), y(3) - 0.775)])
d.flujo([(cx(0), y(3) + 0.775), (cx(0), y(4) - H)], "Sí", posicion=0.5)
d.flujo([(cx(0) - 1.5, y(3)), (cx(0) - 2.1, y(3)), (cx(0) - 2.1, y(1)), (cx(0) - 1.85, y(1))], "No", segmento=0, posicion=0.5, desplaza=(0.0, -0.2), estilo="--")
d.flujo([(cx(0) + 1.85, y(4)), (cx(1) - 1.85, y(4))])
d.flujo([(cx(1), y(4) + H), (cx(1), y(5) - H)])
d.flujo([(cx(1), y(5) + H), (cx(1), y(6) - H)])
d.flujo([(cx(1), y(6) + H), (cx(1), y(7) - 0.775)])
d.flujo([(cx(1) - 1.5, y(7)), (cx(1) - 1.25, y(7)), (cx(1) - 1.25, y(8) - H)], "Sí", segmento=0, posicion=0.4, desplaza=(0.0, -0.22))
d.flujo([(cx(1) + 1.5, y(7)), (cx(1) + 1.25, y(7)), (cx(1) + 1.25, y(8) - H)], "No", segmento=0, posicion=0.4, desplaza=(0.0, -0.22))
d.flujo([(cx(1) - 1.25 - 1.05, y(8)), (cx(0) + 1.85, y(8))])
d.flujo([(cx(1) + 1.25 + 1.05, y(8)), (cx(2) - 1.5, y(8))])
d.flujo([(cx(2), y(8) + H), (cx(2), y(8) + 1.0), (cx(0) + 1.0, y(8) + 1.0), (cx(0) + 1.0, y(8) + H)], "llega a la sede", segmento=1, posicion=0.5)
d.flujo([(cx(0), y(8) + H), (cx(0), y(9) - 0.32)])
for n, (px, py) in enumerate([(cx(0) + 1.85, y(1) - 0.45), (cx(0) + 1.85, y(2) - 0.45), (cx(1) + 1.85, y(5) - 0.45), (cx(1) + 1.85, y(6) - 0.45)], 1):
    d.dolor(px, py, n)
d.guardar("bpmn_as_is.png",
          "Puntos débiles:  ① datos dispersos en cuadernos y hojas por sede   ② los quiebres se descubren tarde, al contar\n"
          "③ la consolidación manual es lenta y propensa a errores   ④ la decisión no usa un pronóstico de la demanda\n"
          "Proceso de referencia: debe validarse con el caso de estudio (entrevistas y observación).")

# ------------------------------------------------------------------------------------------------ TO-BE
d = Diagrama(["Usuario de sede", "Inventia (sistema e IA)", "Analista de compras o gerente"], 11)
cx = lambda c: c * ANCHO_CARRIL + ANCHO_CARRIL / 2
y = lambda f: d.t + 0.55 + f * PASO
d.evento(0, 0, "inicio", "Se vende o recibe mercancía", lado="derecha")
d.tarea(0, 1, "Registra la venta o la entrada\nen Inventia")
d.tarea(1, 2, "Valida y actualiza existencias,\nmovimientos y alertas\n(una sola transacción)", alto=1.3)
d.evento(1, 3, "tiempo", "Predicción programada o solicitada", lado="derecha")
d.tarea(1, 4, "Pronostica la demanda por sede\ny producto (6 modelos, validación\ntemporal y línea base)", alto=1.3)
d.tarea(1, 5, "Genera recomendaciones: traslado\nantes que compra, con justificación", alto=1.3)
d.tarea(2, 6, "Revisa la recomendación\ny su justificación")
d.compuerta(2, 7, "¿Aprueba?", ancho=2.4)
d.evento(2, 7, "fin", "Rechazada:\nqueda en el\nhistorial", dx=-1.95)
d.compuerta(2, 8, "¿Es un\ntraslado?", ancho=2.4, alto=1.4)
d.tarea(0, 9, "Sede origen aprueba y sede\ndestino confirma la recepción")
d.tarea(1, 9, "Mueve las existencias en una\nsola transacción y audita", alto=1.3)
d.tarea(2, 9, "Compra fuera de Inventia y\nmarca la recomendación ejecutada")
d.tarea(0, 10, "Registra la entrada de\nmercancía comprada")
d.evento(1, 10, "fin", "Existencias y alertas\nactualizadas", lado="derecha")
d.flujo([(cx(0), y(0) + 0.32), (cx(0), y(1) - H)])
d.flujo([(cx(0) + 1.85, y(1)), (cx(1), y(1)), (cx(1), y(2) - 0.65)])
d.flujo([(cx(1) - 1.85, y(2)), (cx(0) + 1.1, y(2)), (cx(0) + 1.1, y(1) + H)], "alertas para\nla sede", segmento=0, posicion=0.5, estilo="--")
d.flujo([(cx(1), y(3) + 0.32), (cx(1), y(4) - 0.65)])
d.flujo([(cx(1), y(4) + 0.65), (cx(1), y(5) - 0.65)])
d.flujo([(cx(1) + 1.85, y(5)), (cx(2), y(5)), (cx(2), y(6) - H)])
d.flujo([(cx(2), y(6) + H), (cx(2), y(7) - 0.775)])
d.flujo([(cx(2) - 1.2, y(7)), (cx(2) - 1.95 + 0.32, y(7))], "No", segmento=0, posicion=0.5, desplaza=(0.0, -0.22))
d.flujo([(cx(2), y(7) + 0.775), (cx(2), y(8) - 0.7)], "Sí", posicion=0.5, desplaza=(0.22, 0.0))
d.flujo([(cx(2) - 1.2, y(8)), (cx(0), y(8)), (cx(0), y(9) - H)], "Sí", segmento=0, posicion=0.08, desplaza=(0.0, -0.22))
d.flujo([(cx(2), y(8) + 0.7), (cx(2), y(9) - H)], "No", posicion=0.5, desplaza=(0.22, 0.0))
d.flujo([(cx(0) + 1.85, y(9)), (cx(1) - 1.85, y(9))])
d.flujo([(cx(1), y(9) + 0.65), (cx(1), y(10) - 0.32)])
d.flujo([(cx(2), y(9) + H), (cx(2), y(10) + 0.85), (cx(0), y(10) + 0.85), (cx(0), y(10) + H)])
d.flujo([(cx(0) + 1.85, y(10)), (cx(1) - 0.32, y(10))])
d.guardar("bpmn_to_be.png",
          "Cada etapa deja registro en la auditoría. Inventia no emite órdenes de compra: la compra se gestiona fuera del sistema.")
