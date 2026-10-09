"""Modelos de pronóstico de demanda diaria. Todos reciben la serie histórica ``y`` (unidades por día,
numpy 1-D, sin huecos) y el horizonte ``h`` en días, y devuelven un arreglo de ``h`` valores >= 0.

Línea base (referencia contra la que debe ganar cualquier modelo avanzado):
    ``media_28``     promedio de los últimos 28 días.
Modelos simples:
    ``media_7``      promedio de los últimos 7 días (reacciona rápido).
    ``estacional_7`` perfil semanal: promedio de los últimos días de la semana equivalentes.
Modelos avanzados:
    ``croston_sba``  demanda intermitente (muchos días sin ventas), corrección Syntetos-Boylan.
    ``ets_semanal``  suavizado exponencial Holt-Winters con tendencia amortiguada y estacionalidad semanal.
    ``gbr_rezagos``  gradient boosting sobre rezagos, medias móviles y día de la semana.
"""

import warnings
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

LINEA_BASE = "media_28"


def _no_negativo(x: np.ndarray) -> np.ndarray:
    return np.clip(np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0), 0.0, None)


def media_movil(y: np.ndarray, h: int, ventana: int) -> np.ndarray:
    base = y[-ventana:] if len(y) else np.zeros(1)
    return np.full(h, float(base.mean()))


def estacional_semanal(y: np.ndarray, h: int, semanas: int = 4) -> np.ndarray:
    n = len(y)
    if n < 14:
        return media_movil(y, h, 7)
    salida = np.empty(h)
    for k in range(h):
        j0 = k // 7 + 1  # primer salto de 7 días que cae dentro de la historia
        indices = [n + k - 7 * j for j in range(j0, j0 + semanas)]
        valores = [y[i] for i in indices if 0 <= i < n]
        salida[k] = np.mean(valores) if valores else y[-28:].mean()
    return _no_negativo(salida)


def croston_sba(y: np.ndarray, h: int, alfa: float = 0.1) -> np.ndarray:
    posiciones = np.flatnonzero(y > 0)
    if len(posiciones) == 0:
        return np.zeros(h)
    z = float(y[posiciones[0]])  # tamaño medio de la demanda
    p = float(posiciones[0] + 1)  # intervalo medio entre demandas
    q = 1
    for t in range(posiciones[0] + 1, len(y)):
        if y[t] > 0:
            z += alfa * (y[t] - z)
            p += alfa * (q - p)
            q = 1
        else:
            q += 1
    return np.full(h, (z / p) * (1 - alfa / 2))


def ets_semanal(y: np.ndarray, h: int) -> np.ndarray:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    if len(y) < 28 or np.count_nonzero(y) < 10:
        raise ValueError("historia insuficiente para suavizado estacional")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        modelo = ExponentialSmoothing(
            y.astype(float), trend="add", damped_trend=True, seasonal="add", seasonal_periods=7,
            initialization_method="estimated",
        ).fit(optimized=True)
        return _no_negativo(np.asarray(modelo.forecast(h)))


def _caracteristicas(historia: np.ndarray, t: int, dia_semana: int) -> list[float]:
    previo = lambda k: historia[t - k] if t - k >= 0 else historia[max(t - 1, 0)]  # noqa: E731
    fila = [previo(k) for k in range(1, 8)] + [previo(14), previo(21), previo(28)]
    fila += [historia[max(0, t - 7):t].mean(), historia[max(0, t - 28):t].mean()]
    fila += [1.0 if dia_semana == d else 0.0 for d in range(7)]
    return fila


def gbr_rezagos(y: np.ndarray, h: int, dia_semana_inicio: int = 0) -> np.ndarray:
    """``dia_semana_inicio`` es el día de la semana (lunes = 0) del primer día de ``y``."""
    from sklearn.ensemble import GradientBoostingRegressor

    n = len(y)
    if n < 90:
        raise ValueError("historia insuficiente para regresión con rezagos")
    filas, objetivo = [], []
    for t in range(28, n):
        filas.append(_caracteristicas(y, t, (dia_semana_inicio + t) % 7))
        objetivo.append(y[t])
    modelo = GradientBoostingRegressor(
        n_estimators=120, max_depth=3, learning_rate=0.05, subsample=0.8, min_samples_leaf=5, random_state=42
    )
    modelo.fit(np.asarray(filas), np.asarray(objetivo))
    historia = list(y.astype(float))
    for k in range(h):
        t = n + k
        x = np.asarray([_caracteristicas(np.asarray(historia), t, (dia_semana_inicio + t) % 7)])
        historia.append(float(max(modelo.predict(x)[0], 0.0)))
    return _no_negativo(np.asarray(historia[n:]))


@dataclass(frozen=True)
class Candidato:
    nombre: str
    funcion: Callable  # (y, h, dia_semana_inicio) -> np.ndarray
    avanzado: bool
    descripcion: str


CANDIDATOS: tuple[Candidato, ...] = (
    Candidato("media_28", lambda y, h, d: media_movil(y, h, 28), False, "Promedio de los últimos 28 días (línea base)"),
    Candidato("media_7", lambda y, h, d: media_movil(y, h, 7), False, "Promedio de los últimos 7 días"),
    Candidato("estacional_7", lambda y, h, d: estacional_semanal(y, h), False, "Perfil semanal de las últimas 4 semanas"),
    Candidato("croston_sba", lambda y, h, d: croston_sba(y, h), True, "Demanda intermitente (Croston, variante SBA)"),
    Candidato("ets_semanal", lambda y, h, d: ets_semanal(y, h), True, "Holt-Winters con estacionalidad semanal"),
    Candidato("gbr_rezagos", lambda y, h, d: gbr_rezagos(y, h, d), True, "Gradient boosting sobre rezagos"),
)
POR_NOMBRE = {c.nombre: c for c in CANDIDATOS}
