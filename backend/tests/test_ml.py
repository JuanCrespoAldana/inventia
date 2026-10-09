"""Modelos de pronóstico, validación temporal y reglas de calidad (sin base de datos)."""

from datetime import date, timedelta

import numpy as np
import pytest

from app.ml import evaluacion, modelos, pipeline
from app.ml.modelos import Candidato
from app.ml.pipeline import SerieEntrada, pronosticar_serie

LUNES = date(2026, 1, 5)  # lunes


def serie(valores, *, sin_stock=None, inicio=LUNES) -> SerieEntrada:
    y = np.asarray(valores, dtype=float)
    return SerieEntrada(1, 1, inicio, y, np.zeros(len(y), bool) if sin_stock is None else np.asarray(sin_stock, bool))


def semanal(n=120, base=3, pico=8, semilla=3):
    rng = np.random.default_rng(semilla)
    return [rng.poisson(base + (pico if i % 7 in (4, 5) else 0)) for i in range(n)]


# ------------------------------------------------------------------------------ modelos
def test_todos_los_modelos_devuelven_h_valores_no_negativos():
    y = np.asarray(semanal(), dtype=float)
    for c in modelos.CANDIDATOS:
        p = c.funcion(y, 14, 0)
        assert p.shape == (14,), c.nombre
        assert (p >= 0).all() and np.isfinite(p).all(), c.nombre


def test_estacional_aprende_el_perfil_semanal_y_la_media_no():
    y = np.asarray(semanal(n=84), dtype=float)  # 84 días = 12 semanas exactas, empieza en lunes
    est = modelos.estacional_semanal(y, 7)
    plano = modelos.media_movil(y, 7, 28)
    assert est[4] > est[0] * 1.8  # viernes mucho más que lunes
    assert np.ptp(plano) == 0


def test_croston_sobre_demanda_esporadica_no_supera_la_demanda_media():
    y = np.zeros(100)
    y[::10] = 5
    p = modelos.croston_sba(y, 7)
    assert 0 < p[0] < 1.0  # ~0,5 unidades por día
    assert modelos.croston_sba(np.zeros(30), 3).sum() == 0


def test_modelos_avanzados_rechazan_series_demasiado_cortas():
    with pytest.raises(ValueError):
        modelos.gbr_rezagos(np.ones(40), 7, 0)
    with pytest.raises(ValueError):
        modelos.ets_semanal(np.ones(20), 7)


# ------------------------------------------------------------------------------ validación
def test_plan_de_pliegues():
    assert evaluacion.plan_de_pliegues(27, 14) == (0, 0)  # no alcanza para validar
    assert evaluacion.plan_de_pliegues(28, 14) == (7, 1)
    k, n = evaluacion.plan_de_pliegues(200, 14)
    assert (k, n) == (14, 3)


def test_la_validacion_nunca_entrena_con_datos_del_futuro():
    y = np.arange(100, dtype=float)
    vistos = []

    def espia(historia, h, d):
        vistos.append((len(historia), h, float(historia[-1])))
        return np.full(h, float(historia[-1]))  # pronóstico: último valor visto

    m = evaluacion.validar(Candidato("espia", espia, False, ""), y, 14, 0)
    assert m is not None and m.n_pliegues == 3
    assert [v[0] for v in vistos] == [58, 72, 86]  # cortes crecientes, siempre dejando días sin ver
    for largo, h, ultimo in vistos:
        assert ultimo == largo - 1 and largo + h <= 100  # lo último que vio es anterior al periodo evaluado
    assert m.sesgo is not None and m.sesgo < 0  # en una serie creciente, repetir el último valor subestima


def test_wape_y_mae_se_calculan_sobre_el_total():
    y = np.array([10.0] * 35 + [20.0] * 7)  # el último tramo de 7 días vale el doble de lo aprendido
    m = evaluacion.validar(modelos.POR_NOMBRE["media_7"], y, 7, 0)
    assert m.n_pliegues == 3 and m.n_dias_validados == 21
    # pliegos 1 y 2 acierta (10 vs 10); el 3.º predice 10 y ocurre 20 -> error 70 sobre real 70+70+140
    assert m.suma_error_abs == pytest.approx(70.0) and m.suma_real == pytest.approx(280.0)
    assert m.wape == pytest.approx(0.25) and m.mae == pytest.approx(70 / 21)
    assert m.sesgo == pytest.approx(-0.25)  # subestimó


def test_sin_ventas_en_la_validacion_el_wape_no_existe_pero_si_el_mae():
    y = np.array([10.0] * 21 + [0.0] * 14)
    m = evaluacion.validar(modelos.POR_NOMBRE["media_28"], y, 7, 0)
    assert m.wape is None and m.sesgo is None and m.mae > 0


# ------------------------------------------------------------------------------ calidad de datos
def test_historia_insuficiente_se_omite_con_motivo():
    r = pronosticar_serie(serie(semanal(n=20)), 14)
    assert r.omitida and "Historial insuficiente" in r.omitida and r.modelo is None


def test_pocas_ventas_se_omite_aunque_haya_historia():
    y = [0] * 60
    y[10] = y[30] = 4
    r = pronosticar_serie(serie(y), 14)
    assert r.omitida and "Pocas ventas" in r.omitida


def test_mas_de_la_mitad_sin_existencias_se_omite():
    y = semanal(n=60)
    r = pronosticar_serie(serie(y, sin_stock=[True] * 40 + [False] * 20), 14)
    assert r.omitida and "sin existencias" in r.omitida


def test_dias_sin_existencias_se_imputan_y_se_advierte():
    y = np.array(semanal(n=60), dtype=float)
    y[20:24] = 0
    limpio, n = pipeline.imputar_dias_sin_existencias(y, np.isin(np.arange(60), range(20, 24)))
    assert n == 4 and (limpio[20:24] > 0).all()
    r = pronosticar_serie(serie(y, sin_stock=np.isin(np.arange(60), range(20, 24))), 14)
    assert r.omitida is None and any("sin existencias" in a for a in r.advertencias)


def test_picos_extremos_se_limitan():
    y = np.array(semanal(n=90), dtype=float)
    y[45] = 5000
    limpio, n = pipeline.limitar_picos(y)
    assert n == 1 and limpio[45] < 100
    r = pronosticar_serie(serie(y), 14)
    assert r.demanda_total < 400  # un pico aislado no dispara el pronóstico


# ------------------------------------------------------------------------------ selección
def test_con_estacionalidad_gana_un_modelo_mejor_que_la_linea_base():
    r = pronosticar_serie(serie(semanal()), 14)
    assert r.omitida is None
    assert r.modelo != modelos.LINEA_BASE and not r.es_linea_base
    m = r.metricas
    assert m["wape"] < m["wape_linea_base"] and m["mejora_vs_linea_base_pct"] > 5
    assert m["n_pliegues"] >= 2 and r.confianza in ("media", "alta")
    # El intervalo de 80 % rodea el pronóstico y nunca es negativo
    assert 0 <= r.limite_inferior <= r.demanda_total <= r.limite_superior
    assert len(r.pronostico) == 14 and r.fecha_inicio == LUNES + timedelta(days=120)  # al día siguiente del último dato


def test_el_modelo_avanzado_solo_gana_si_supera_a_los_simples_por_el_margen(monkeypatch):
    y = serie([5.0 + (i % 2) for i in range(80)])
    # Errores (WAPE) controlados: la línea base predice 5,5; el «avanzado» se acerca más o menos.
    def base(yy, h, d):
        return np.full(h, 5.5)

    def avanzado_1_pct(yy, h, d):
        return np.full(h, 5.5 + 0.02)  # error casi idéntico

    def avanzado_bueno(yy, h, d):
        return np.array([5.0 if (len(yy) + k) % 2 == 0 else 6.0 for k in range(h)])  # acierta la alternancia

    for avanzado, espera_avanzado in ((avanzado_1_pct, False), (avanzado_bueno, True)):
        monkeypatch.setattr(pipeline, "CANDIDATOS", (Candidato("media_28", base, False, ""), Candidato("x", avanzado, True, "")))
        monkeypatch.setitem(pipeline.POR_NOMBRE, "x", Candidato("x", avanzado, True, ""))
        monkeypatch.setitem(pipeline.POR_NOMBRE, "media_28", Candidato("media_28", base, False, ""))
        r = pronosticar_serie(y, 14)
        assert (r.modelo == "x") is espera_avanzado, r.metricas["candidatos"]


def test_resumen_global_pondera_por_volumen_y_cuenta_omitidas():
    buenas = [pronosticar_serie(serie(semanal(semilla=s)), 14) for s in (1, 2)]
    omitida = pronosticar_serie(serie(semanal(n=10)), 14)
    resumen = pipeline.resumir(buenas + [omitida])
    assert resumen["series_total"] == 3 and resumen["series_con_prediccion"] == 2 and resumen["series_omitidas"] == 1
    assert resumen["motivos_omision"] == {"Historial insuficiente": 1}
    err = sum(r.metricas["suma_error_abs"] for r in buenas)
    real = sum(r.metricas["suma_real"] for r in buenas)
    assert resumen["wape_global"] == pytest.approx(err / real, abs=1e-4)
    assert resumen["wape_global"] < resumen["wape_linea_base_global"]


def test_sin_tiempo_solo_se_comparan_modelos_simples_y_se_advierte(monkeypatch):
    reloj = iter([0.0, 5.0, 5.0, 5.0])  # al llegar a la serie ya pasó el tiempo asignado

    class RelojFalso:
        monotonic = staticmethod(lambda: next(reloj))

    monkeypatch.setattr(pipeline, "time", RelojFalso)
    r = pipeline.pronosticar_lote([serie(semanal())], 14, tiempo_maximo_s=1.0)[0]
    assert r.omitida is None
    assert all(not modelos.POR_NOMBRE[c["modelo"]].avanzado for c in r.metricas["candidatos"])
    assert any("tiempo" in a for a in r.advertencias)
