"""Experimento reproducible: compara los modelos de pronóstico de Inventia contra la línea base.

    cd backend
    python ../ml/evaluar_modelos.py [--series 40] [--dias 120] [--horizonte 14] [--semilla 7]

Genera series sintéticas de demanda diaria con comportamientos distintos (estable, estacional, con tendencia,
intermitente y ruidosa) y las evalúa con la MISMA validación temporal que usa el sistema (varios cortes en el
tiempo, nunca se mezcla el futuro con el pasado). Muestra, por tipo de serie, el error de cada modelo (WAPE y
MAE) y cuántas veces gana frente a la línea base «promedio de 28 días».

Las series son sintéticas a propósito: sirven para verificar que cada modelo hace lo que promete (p. ej. que el
modelo estacional gana en series estacionales y que ninguno «inventa» mejoras donde no las hay). Con datos reales,
use el módulo de predicción del sistema, que aplica exactamente este procedimiento sobre el historial de ventas.
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.ml import evaluacion, modelos  # noqa: E402


def generar(tipo: str, dias: int, rng: np.random.Generator) -> np.ndarray:
    t = np.arange(dias)
    if tipo == "estable":
        lam = np.full(dias, 12.0)
    elif tipo == "estacional":
        lam = 8 + 10 * np.isin(t % 7, (4, 5)) + 2 * np.sin(t / 30)
    elif tipo == "tendencia":
        lam = 6 + 0.08 * t + 3 * np.isin(t % 7, (5, 6))
    elif tipo == "intermitente":
        lam = np.where(rng.random(dias) < 0.25, 6.0, 0.0)
    else:  # ruidosa: media estable con sobredispersión
        lam = rng.gamma(2.0, 5.0, size=dias)
    return rng.poisson(lam).astype(float)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--series", type=int, default=40, help="series por tipo")
    ap.add_argument("--dias", type=int, default=120)
    ap.add_argument("--horizonte", type=int, default=14)
    ap.add_argument("--semilla", type=int, default=7)
    args = ap.parse_args()

    rng = np.random.default_rng(args.semilla)
    tipos = ["estable", "estacional", "tendencia", "intermitente", "ruidosa"]
    error = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0, 0.0, 0]))  # tipo -> modelo -> [Σ|e|, Σreal, ΣMAE, n]
    victorias = defaultdict(lambda: defaultdict(int))

    for tipo in tipos:
        for _ in range(args.series):
            y = generar(tipo, args.dias, rng)
            resultados = {}
            for c in modelos.CANDIDATOS:
                try:
                    m = evaluacion.validar(c, y, args.horizonte, 0)
                except ValueError:
                    m = None
                if m is not None:
                    resultados[c.nombre] = m
                    acc = error[tipo][c.nombre]
                    acc[0] += m.suma_error_abs
                    acc[1] += m.suma_real
                    acc[2] += m.mae
                    acc[3] += 1
            base = resultados.get(modelos.LINEA_BASE)
            if base is None:
                continue
            for nombre, m in resultados.items():
                if nombre != modelos.LINEA_BASE and m.suma_error_abs < base.suma_error_abs * 0.97:
                    victorias[tipo][nombre] += 1

    print(f"\nWAPE por tipo de serie ({args.series} series × {args.dias} días, horizonte {args.horizonte}); menor es mejor\n")
    nombres = [c.nombre for c in modelos.CANDIDATOS]
    print(f"{'tipo':14}" + "".join(f"{n:>14}" for n in nombres))
    for tipo in tipos:
        fila = f"{tipo:14}"
        for n in nombres:
            e, real, _, k = error[tipo][n]
            fila += f"{(100 * e / real):>13.1f}%" if k and real else f"{'—':>14}"
        print(fila)
    print("\nSeries donde el modelo mejora ≥ 3 % a la línea base (criterio de selección del sistema)\n")
    print(f"{'tipo':14}" + "".join(f"{n:>14}" for n in nombres if n != modelos.LINEA_BASE))
    for tipo in tipos:
        print(f"{tipo:14}" + "".join(f"{victorias[tipo][n]:>14}" for n in nombres if n != modelos.LINEA_BASE))


if __name__ == "__main__":
    main()
