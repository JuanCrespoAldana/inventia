"""Figura: flujo de una ejecución de predicción y recomendaciones (ver docs/PREDICCION.md)."""
from pathlib import Path
from dibujo import *

fig, ax = lienzo(10.8, 7.4, (0, 11.2), (0.3, 9.2))
W, H = 2.3, 1.15
X = [0.3, 3.15, 6.0, 8.85]
f1, f2, f3, f4 = 6.6, 4.5, 2.4, 0.5

A = caja(ax, X[0], f1, W, H, "Ventas y movimientos", "por sede y producto")
B = caja(ax, X[1], f1, W, H, "Serie diaria", "unidades vendidas por día,\nsin huecos")
C = caja(ax, X[2], f1, W, H, "¿Cumple los mínimos?", "28 días · 5 días con ventas\n≤ 50 % sin existencias", "amarillo")
D = caja(ax, X[2], 8.0, W, 0.95, "Se omite la serie", "y se explica el motivo", "gris")
E = caja(ax, X[3], f1, W, H, "Preparar la serie", "imputa días sin stock\nlimita picos extremos")
F = caja(ax, X[3], f2, W, H, "Validación temporal", "origen móvil, hasta 3 cortes")
G = caja(ax, X[2], f2, W, H, "Comparar 6 modelos", "frente a la línea base\n(promedio de 28 días)", "naranja")
Hh = caja(ax, X[1], f2, W, H, "Elegir el modelo", "mejor simple vs. mejor avanzado\ncon mejora mínima de 3 %", "naranja")
I = caja(ax, X[0], f2, W, H, "Pronóstico", "intervalo de 80 %, confianza\ny advertencias")
J = caja(ax, X[0], f3, W, H, "Predicciones", "se guardan; no mezclan\ncon ventas reales", "verde")
K = caja(ax, X[1], f3, W, H, "Alertas de riesgo", "cobertura frente al plazo\nde entrega", "verde")
L = caja(ax, X[2], f3, W, H, "Recomendaciones", "reposición y traslado,\nsiempre pendientes", "verde")
M = caja(ax, X[3], f3, W, H, "Aprobación humana", "aprobar, rechazar\no marcar ejecutada", "azul")

flecha(ax, centro(A, "e"), centro(B, "o"))
flecha(ax, centro(B, "e"), centro(C, "o"))
flecha(ax, centro(C, "n"), centro(D, "s"), "No", desplaza=(0.3, 0))
flecha(ax, centro(C, "e"), centro(E, "o"), "Sí", desplaza=(0, 0.28))
flecha(ax, centro(E, "s"), centro(F, "n"))
flecha(ax, centro(F, "o"), centro(G, "e"))
flecha(ax, centro(G, "o"), centro(Hh, "e"))
flecha(ax, centro(Hh, "o"), centro(I, "e"))
flecha(ax, centro(I, "s"), centro(J, "n"))
flecha(ax, centro(J, "e"), centro(K, "o"))
flecha(ax, centro(J, "s"), centro(L, "s"), curva=0.28)
flecha(ax, centro(L, "e"), centro(M, "o"))
guardar(fig, Path(__file__).with_name("flujo_prediccion.png"))
