"""Validación temporal (nunca se mezcla el futuro con el pasado) y métricas de error."""

from dataclasses import dataclass, field

import numpy as np

from app.ml.modelos import Candidato

ENTRENAMIENTO_MINIMO = 21  # días de historia mínimos antes del primer corte de validación


@dataclass
class Metricas:
    wape: float | None  # Σ|error| / Σ real  (None si en la validación no hubo ventas)
    mae: float  # error absoluto medio por día, en unidades
    sesgo: float | None  # Σ(pronóstico − real) / Σ real; > 0 sobrestima
    n_pliegues: int
    n_dias_validados: int
    suma_error_abs: float = 0.0  # Σ|pronóstico − real| de todos los pliegues (para el WAPE global)
    suma_real: float = 0.0  # Σ real de todos los pliegues
    residuos: list[float] = field(default_factory=list)  # real − pronóstico por día


def plan_de_pliegues(n: int, horizonte: int) -> tuple[int, int]:
    """Devuelve (días por pliegue, número de pliegues). Hasta 3 cortes, el último pegado al presente."""
    por_pliegue = max(7, min(14, horizonte))
    por_pliegue = min(por_pliegue, max(n - ENTRENAMIENTO_MINIMO, 0))
    if por_pliegue < 7:
        return 0, 0
    pliegues = min(3, (n - ENTRENAMIENTO_MINIMO) // por_pliegue)
    return por_pliegue, pliegues


def validar(candidato: Candidato, y: np.ndarray, horizonte: int, dia_semana_inicio: int) -> Metricas | None:
    """Rolling origin: se entrena con y[:corte] y se evalúa en y[corte:corte+k]. Devuelve ``None`` si el
    modelo no aplica a la serie (p. ej. historia insuficiente) o no hay base para validar."""
    n = len(y)
    k, pliegues = plan_de_pliegues(n, horizonte)
    if pliegues == 0:
        return None
    errores_abs, reales, sesgos, residuos = 0.0, 0.0, 0.0, []
    for i in range(pliegues):
        corte = n - k * (pliegues - i)
        try:
            pronostico = candidato.funcion(y[:corte], k, dia_semana_inicio)
        except Exception:  # noqa: BLE001 - un modelo que no converge simplemente no compite en esta serie
            return None
        real = y[corte : corte + k]
        diferencia = pronostico - real
        errores_abs += float(np.abs(diferencia).sum())
        sesgos += float(diferencia.sum())
        reales += float(real.sum())
        residuos.extend((-diferencia).tolist())
    dias = k * pliegues
    return Metricas(
        wape=(errores_abs / reales) if reales > 0 else None,
        mae=errores_abs / dias,
        sesgo=(sesgos / reales) if reales > 0 else None,
        n_pliegues=pliegues,
        n_dias_validados=dias,
        suma_error_abs=errores_abs,
        suma_real=reales,
        residuos=residuos,
    )
