"""Experimento reproducible: compara los modelos de pronóstico de Inventia contra la línea base.

    cd backend
    python ../ml/evaluar_modelos.py [--series 40] [--dias 180] [--horizonte 14] [--semilla 7] [--csv salida.csv]

Genera series sintéticas de demanda diaria con comportamientos distintos (estable, estacional, con tendencia,
intermitente y ruidosa) y las evalúa con la MISMA validación temporal que usa el sistema (varios cortes en el
tiempo, nunca se mezcla el futuro con el pasado). Muestra, por tipo de serie, el error de cada modelo (WAPE,
MAE, RMSE y MAPE) y cuántas veces gana frente a la línea base «promedio de 28 días». Con ``--csv ruta.csv`` guarda
la tabla completa para usarla en informes.

Con menos de 132 días de historia el gradient boosting (que exige 90 días de entrenamiento en el primer corte)
no puede validarse y aparece con «—»; por eso el valor por defecto es 180 días.

Las series son sintéticas a propósito: sirven para verificar que cada modelo hace lo que promete (p. ej. que el
modelo estacional gana en series estacionales y que ninguno «inventa» mejoras donde no las hay). Con datos reales,
use el módulo de predicción del sistema, que aplica exactamente este procedimiento sobre el historial de ventas.
"""

import argparse
import csv
import math
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
    ap.add_argument("--dias", type=int, default=180, help="el gradient boosting solo compite con 132 días o más")
    ap.add_argument("--horizonte", type=int, default=14)
    ap.add_argument("--semilla", type=int, default=7)
    ap.add_argument("--csv", type=Path, default=None, help="guarda la tabla de errores por tipo y modelo")
    args = ap.parse_args()

    rng = np.random.default_rng(args.semilla)
    tipos = ["estable", "estacional", "tendencia", "intermitente", "ruidosa"]
    # tipo -> modelo -> acumulados: Σ|e|, Σreal, Σe², días validados, Σ|e|/real, días con ventas, series
    error = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0, 0.0, 0, 0.0, 0, 0]))
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
                    acc[2] += m.suma_error_cuad
                    acc[3] += m.n_dias_validados
                    acc[4] += m.suma_error_pct
                    acc[5] += m.n_dias_con_ventas
                    acc[6] += 1
            base = resultados.get(modelos.LINEA_BASE)
            if base is None:
                continue
            for nombre, m in resultados.items():
                if nombre != modelos.LINEA_BASE and m.suma_error_abs < base.suma_error_abs * 0.97:
                    victorias[tipo][nombre] += 1

    nombres = [c.nombre for c in modelos.CANDIDATOS]

    def valor(metrica: str, tipo: str, nombre: str) -> float | None:
        e, real, cuad, dias, pct, dias_pct, k = error[tipo][nombre]
        if not k:
            return None
        if metrica == "WAPE":
            return e / real if real else None
        if metrica == "MAE":
            return e / dias if dias else None
        if metrica == "RMSE":
            return math.sqrt(cuad / dias) if dias else None
        return pct / dias_pct if dias_pct else None  # MAPE: solo días con ventas

    tabla = []
    for metrica, unidad in (("WAPE", "%"), ("MAE", "u./día"), ("RMSE", "u./día"), ("MAPE", "%")):
        print(f"\n{metrica} por tipo de serie ({args.series} series × {args.dias} días, horizonte {args.horizonte}); menor es mejor")
        if metrica == "MAPE":
            print("(el MAPE solo cuenta los días con ventas; con ventas en cero el cociente no existe)")
        print(f"\n{'tipo':14}" + "".join(f"{n:>14}" for n in nombres))
        for tipo in tipos:
            fila = f"{tipo:14}"
            for n in nombres:
                v = valor(metrica, tipo, n)
                tabla.append({"metrica": metrica, "tipo_serie": tipo, "modelo": n, "valor": "" if v is None else round(v, 6), "unidad": unidad})
                if v is None:
                    fila += f"{'—':>14}"
                else:
                    fila += f"{100 * v:>13.1f}%" if unidad == "%" else f"{v:>14.2f}"
            print(fila)
    print("\nSeries donde el modelo mejora ≥ 3 % a la línea base (criterio de selección del sistema)\n")
    print(f"{'tipo':14}" + "".join(f"{n:>14}" for n in nombres if n != modelos.LINEA_BASE))
    for tipo in tipos:
        print(f"{tipo:14}" + "".join(f"{victorias[tipo][n]:>14}" for n in nombres if n != modelos.LINEA_BASE))
    if args.csv:
        with args.csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["metrica", "tipo_serie", "modelo", "valor", "unidad"])
            w.writeheader()
            w.writerows(tabla)
        print(f"\nTabla guardada en {args.csv}")


if __name__ == "__main__":
    main()
