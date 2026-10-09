"""Pronóstico de una serie (sede, producto) y resumen de una ejecución completa.

Todo aquí es cálculo puro (sin base de datos), de modo que se puede probar y repetir:

1. Control de calidad: una serie con menos de 28 días de historia o menos de 5 días con ventas NO se
   pronostica; se informa como «datos insuficientes» en lugar de inventar un número.
2. Preparación: los días en que no hubo existencias (la demanda no se pudo observar) se sustituyen por
   el promedio reciente y los picos extremos se limitan (winsorización), para no aprender de ruido.
3. Validación temporal (rolling origin, hasta 3 cortes): cada modelo se entrena solo con el pasado y se
   evalúa en los días siguientes. Se mide WAPE y MAE.
4. Selección: un modelo avanzado solo reemplaza al mejor modelo simple si lo supera por al menos 3 %
   de WAPE; la línea base (promedio de 28 días) queda siempre como referencia.
5. Intervalo de 80 % a partir de la dispersión de los errores de validación y confianza alta/media/baja.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np

from app.ml.evaluacion import Metricas, validar
from app.ml.modelos import CANDIDATOS, LINEA_BASE, POR_NOMBRE

MIN_DIAS_HISTORIA = 28
MIN_DIAS_CON_VENTAS = 5
MEJORA_MINIMA_AVANZADO = 0.03  # el modelo avanzado debe ganar al simple por ≥ 3 % de error
Z_80 = 1.2816  # cuantil normal para un intervalo de 80 %
MAX_FRACCION_CENSURADA = 0.5


@dataclass
class SerieEntrada:
    """Ventas diarias netas de un producto en una sede, sin huecos, desde ``inicio`` hasta el día de corte."""

    sede_id: int
    producto_id: int
    inicio: date
    unidades: np.ndarray
    sin_existencias: np.ndarray  # True = ese día no había stock (la venta pudo estar limitada)

    @property
    def fin(self) -> date:
        return self.inicio + timedelta(days=len(self.unidades) - 1)


@dataclass
class ResultadoSerie:
    sede_id: int
    producto_id: int
    omitida: str | None = None  # motivo si no se pudo pronosticar
    modelo: str | None = None
    es_linea_base: bool = False
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    pronostico: list[float] = field(default_factory=list)
    demanda_total: float = 0.0
    limite_inferior: float | None = None
    limite_superior: float | None = None
    confianza: str = "baja"
    metricas: dict = field(default_factory=dict)
    advertencias: list[str] = field(default_factory=list)
    # Detalle de diagnóstico de la serie omitida
    dias_historia: int = 0
    dias_con_ventas: int = 0


# ---------------------------------------------------------------------------------------------
# Preparación
# ---------------------------------------------------------------------------------------------
def imputar_dias_sin_existencias(y: np.ndarray, censurado: np.ndarray) -> tuple[np.ndarray, int]:
    """Sustituye los días con existencias en cero (demanda no observable) por el promedio de los 28
    días observables anteriores (o el promedio general si aún no hay días anteriores)."""
    limpio = y.astype(float).copy()
    marcados = np.flatnonzero(censurado)
    if len(marcados) == 0:
        return limpio, 0
    observables = ~censurado
    if not observables.any():
        return limpio, 0
    general = float(y[observables].mean())
    for i in marcados:
        previos = y[max(0, i - 28) : i][observables[max(0, i - 28) : i]]
        limpio[i] = float(previos.mean()) if len(previos) else general
    return limpio, int(len(marcados))


def limitar_picos(y: np.ndarray) -> tuple[np.ndarray, int]:
    """Limita valores extremos a Q3 + 3·IQR calculado sobre los días con ventas."""
    positivos = y[y > 0]
    if len(positivos) < 8:
        return y, 0
    q1, q3 = np.percentile(positivos, [25, 75])
    tope = float(q3 + 3.0 * (q3 - q1))
    if tope <= 0:
        return y, 0
    n = int((y > tope).sum())
    return (np.minimum(y, tope), n) if n else (y, 0)


# ---------------------------------------------------------------------------------------------
# Una serie
# ---------------------------------------------------------------------------------------------
def _error(m: Metricas) -> float:
    """Criterio de comparación: WAPE; si en la validación no hubo ventas, MAE."""
    return m.wape if m.wape is not None else m.mae


def _confianza(wape: float | None, m: Metricas, dias_historia: int, dias_con_ventas: int) -> str:
    if wape is None or m.n_pliegues < 1:
        return "baja"
    if wape <= 0.35 and dias_historia >= 56 and dias_con_ventas >= 20 and m.n_pliegues >= 2:
        return "alta"
    if wape <= 0.70 and dias_con_ventas >= 10:
        return "media"
    return "baja"


def pronosticar_serie(serie: SerieEntrada, horizonte: int, *, solo_modelos_simples: bool = False) -> ResultadoSerie:
    y_bruta = np.asarray(serie.unidades, dtype=float)
    n = len(y_bruta)
    dias_con_ventas = int((y_bruta > 0).sum())
    base = ResultadoSerie(
        sede_id=serie.sede_id, producto_id=serie.producto_id, dias_historia=n, dias_con_ventas=dias_con_ventas
    )
    if n < MIN_DIAS_HISTORIA:
        base.omitida = f"Historial insuficiente: {n} días (se requieren al menos {MIN_DIAS_HISTORIA})"
        return base
    if dias_con_ventas < MIN_DIAS_CON_VENTAS:
        base.omitida = (
            f"Pocas ventas: {dias_con_ventas} días con ventas en {n} (se requieren al menos {MIN_DIAS_CON_VENTAS})"
        )
        return base
    if float(serie.sin_existencias.mean()) > MAX_FRACCION_CENSURADA:
        base.omitida = "Más de la mitad del historial sin existencias: la demanda real no es observable"
        return base

    advertencias: list[str] = []
    y, imputados = imputar_dias_sin_existencias(y_bruta, np.asarray(serie.sin_existencias, dtype=bool))
    if imputados:
        advertencias.append(f"{imputados} días sin existencias se reemplazaron por la demanda reciente")
    y, limitados = limitar_picos(y)
    if limitados:
        advertencias.append(f"{limitados} valores extremos se limitaron para no distorsionar el pronóstico")
    if n < 56:
        advertencias.append(f"Historial corto ({n} días): la estimación es menos estable")
    ceros = 1.0 - dias_con_ventas / n
    if ceros > 0.6:
        advertencias.append(f"Demanda intermitente: {ceros:.0%} de los días sin ventas")

    dia_semana_inicio = serie.inicio.weekday()
    evaluados: dict[str, Metricas] = {}
    for candidato in CANDIDATOS:
        if solo_modelos_simples and candidato.avanzado:
            continue
        m = validar(candidato, y, horizonte, dia_semana_inicio)
        if m is not None:
            evaluados[candidato.nombre] = m
    if LINEA_BASE not in evaluados:
        base.omitida = "No hay suficiente historial para validar el modelo"
        return base

    simples = {k: m for k, m in evaluados.items() if not POR_NOMBRE[k].avanzado}
    avanzados = {k: m for k, m in evaluados.items() if POR_NOMBRE[k].avanzado}
    mejor_simple = min(simples, key=lambda k: (_error(simples[k]), k != LINEA_BASE, k))
    elegido = mejor_simple
    if avanzados:
        mejor_avanzado = min(avanzados, key=lambda k: (_error(avanzados[k]), k))
        if _error(avanzados[mejor_avanzado]) <= _error(simples[mejor_simple]) * (1.0 - MEJORA_MINIMA_AVANZADO):
            elegido = mejor_avanzado

    metricas = evaluados[elegido]
    linea_base = evaluados[LINEA_BASE]
    try:
        punto = POR_NOMBRE[elegido].funcion(y, horizonte, dia_semana_inicio)
    except Exception:  # noqa: BLE001 - si el modelo falla al ajustar con todos los datos, se vuelve a la línea base
        elegido, metricas = LINEA_BASE, linea_base
        punto = POR_NOMBRE[LINEA_BASE].funcion(y, horizonte, dia_semana_inicio)
        advertencias.append("El modelo elegido no pudo ajustarse con todo el historial; se usó la línea base")
    punto = np.clip(np.asarray(punto, dtype=float), 0.0, None)

    sigma = float(np.std(metricas.residuos)) if metricas.residuos else 0.0
    total = float(punto.sum())
    margen = Z_80 * sigma * math.sqrt(horizonte)
    mejora = None
    if linea_base.wape is not None and metricas.wape is not None and linea_base.wape > 0:
        mejora = (linea_base.wape - metricas.wape) / linea_base.wape * 100.0

    base.modelo = elegido
    base.es_linea_base = elegido == LINEA_BASE
    base.fecha_inicio = serie.fin + timedelta(days=1)
    base.fecha_fin = serie.fin + timedelta(days=horizonte)
    base.pronostico = [round(float(v), 3) for v in punto]
    base.demanda_total = round(total, 2)
    base.limite_inferior = round(max(0.0, total - margen), 2)
    base.limite_superior = round(total + margen, 2)
    base.confianza = _confianza(metricas.wape, metricas, n, dias_con_ventas)
    base.advertencias = advertencias
    base.metricas = {
        "wape": _r(metricas.wape), "mae": _r(metricas.mae), "sesgo": _r(metricas.sesgo),
        "wape_linea_base": _r(linea_base.wape), "mae_linea_base": _r(linea_base.mae),
        "mejora_vs_linea_base_pct": _r(mejora, 1),
        "n_pliegues": metricas.n_pliegues, "dias_validados": metricas.n_dias_validados,
        "dias_historia": n, "dias_con_ventas": dias_con_ventas,
        "suma_error_abs": _r(metricas.suma_error_abs), "suma_real": _r(metricas.suma_real),
        "suma_error_abs_base": _r(linea_base.suma_error_abs), "suma_real_base": _r(linea_base.suma_real),
        "candidatos": [
            {"modelo": k, "avanzado": POR_NOMBRE[k].avanzado, "wape": _r(m.wape), "mae": _r(m.mae)}
            for k, m in sorted(evaluados.items(), key=lambda kv: _error(kv[1]))
        ],
    }
    return base


def _r(valor: float | None, decimales: int = 4) -> float | None:
    return None if valor is None else round(float(valor), decimales)


# ---------------------------------------------------------------------------------------------
# Una ejecución completa
# ---------------------------------------------------------------------------------------------
def pronosticar_lote(
    series: list[SerieEntrada], horizonte: int, *, tiempo_maximo_s: float | None = None
) -> list[ResultadoSerie]:
    """Pronostica todas las series. Si se agota el tiempo asignado, las series restantes solo usan
    modelos simples (más rápidos) y lo advierten, en lugar de abortar la ejecución."""
    limite = time.monotonic() + tiempo_maximo_s if tiempo_maximo_s else None
    resultados: list[ResultadoSerie] = []
    for serie in series:
        rapido = limite is not None and time.monotonic() > limite
        r = pronosticar_serie(serie, horizonte, solo_modelos_simples=rapido)
        if rapido and r.omitida is None:
            r.advertencias.append("Se agotó el tiempo de la ejecución: solo se compararon modelos simples")
        resultados.append(r)
    return resultados


def resumir(resultados: list[ResultadoSerie]) -> dict:
    """Métricas globales de la ejecución: error del modelo elegido frente a la línea base (RNF-030)."""
    hechos = [r for r in resultados if r.omitida is None]
    omitidas = [r for r in resultados if r.omitida is not None]
    err = sum(r.metricas.get("suma_error_abs") or 0.0 for r in hechos)
    real = sum(r.metricas.get("suma_real") or 0.0 for r in hechos)
    err_b = sum(r.metricas.get("suma_error_abs_base") or 0.0 for r in hechos)
    real_b = sum(r.metricas.get("suma_real_base") or 0.0 for r in hechos)
    wape = err / real if real > 0 else None
    wape_base = err_b / real_b if real_b > 0 else None
    mejora = (wape_base - wape) / wape_base * 100.0 if wape is not None and wape_base else None
    por_modelo: dict[str, int] = {}
    for r in hechos:
        por_modelo[r.modelo or "?"] = por_modelo.get(r.modelo or "?", 0) + 1
    por_confianza = {c: sum(1 for r in hechos if r.confianza == c) for c in ("alta", "media", "baja")}
    motivos: dict[str, int] = {}
    for r in omitidas:
        clave = r.omitida.split(":")[0] if r.omitida else "otro"
        motivos[clave] = motivos.get(clave, 0) + 1
    return {
        "series_total": len(resultados),
        "series_con_prediccion": len(hechos),
        "series_omitidas": len(omitidas),
        "motivos_omision": motivos,
        "wape_global": _r(wape),
        "wape_linea_base_global": _r(wape_base),
        "mejora_vs_linea_base_pct": _r(mejora, 1),
        "modelos_elegidos": por_modelo,
        "series_por_confianza": por_confianza,
        "series_mejor_que_linea_base": sum(1 for r in hechos if not r.es_linea_base),
    }
