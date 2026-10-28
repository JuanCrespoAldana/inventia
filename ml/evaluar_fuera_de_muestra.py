"""Prueba fuera de muestra («holdout») del módulo de predicción sobre las ventas de una base de datos.

    cd backend
    export DATABASE_URL=postgresql+asyncpg://usuario:clave@localhost:5432/base   # base de DEMOSTRACIÓN o de prueba
    export SECRET_KEY=una-clave-cualquiera-de-al-menos-32-caracteres
    python ../ml/evaluar_fuera_de_muestra.py --salida ../ml/resultados [--horizonte 14] [--ventanas 3] [--empresa-id 1]

Para cada serie (sede, producto) se ocultan los últimos ``horizonte`` días —que ni se usan para entrenar ni para
elegir el modelo—, se ejecuta el pipeline del sistema con el resto de la historia y se compara el pronóstico con lo que
realmente ocurrió. Con ``--ventanas N`` se repite con N ventanas de prueba consecutivas hacia atrás en el tiempo
(origen móvil externo). La referencia es la línea base «promedio de 28 días» entrenada con los mismos datos.

Por qué existe: la validación interna del sistema (rolling origin dentro del historial) también SIRVE para elegir el
modelo, así que su error es algo optimista. Esta prueba mide el error en datos que ninguna decisión del sistema vio.
También mide qué fracción de los períodos reales cayó dentro del intervalo de 80 % que muestra la interfaz.

Escribe ``holdout_resumen.json`` (métricas globales, por ventana y por modelo elegido) y ``holdout_series.json``
(pronóstico y real de cada serie, útil para graficar). Solo lee la base de datos; no modifica nada.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))  # permite ejecutarlo desde cualquier carpeta

from app.config.database import AsyncSessionLocal  # noqa: E402
from app.ml.datos import cargar_series  # noqa: E402
from app.ml.modelos import media_movil  # noqa: E402
from app.ml.pipeline import SerieEntrada, imputar_dias_sin_existencias, limitar_picos, pronosticar_serie  # noqa: E402
from app.model.empresa import Empresa  # noqa: E402
from app.util.tiempo import hoy_local  # noqa: E402


def _metricas(real: np.ndarray, pron: np.ndarray) -> dict:
    e = pron - real
    con_ventas = real > 0
    return {
        "abs": float(np.abs(e).sum()), "real": float(real.sum()), "cuad": float((e**2).sum()), "dias": int(len(real)),
        "pct": float((np.abs(e[con_ventas]) / real[con_ventas]).sum()), "dias_con_ventas": int(con_ventas.sum()),
        "sesgo_num": float(e.sum()),
    }


def _acumular(acumulado: dict, m: dict) -> None:
    for clave, valor in m.items():
        acumulado[clave] = acumulado.get(clave, 0.0) + valor


def _resumir(a: dict) -> dict:
    return {
        "wape": a["abs"] / a["real"] if a["real"] else None,
        "mae": a["abs"] / a["dias"],
        "rmse": float(np.sqrt(a["cuad"] / a["dias"])),
        "mape": a["pct"] / a["dias_con_ventas"] if a["dias_con_ventas"] else None,
        "sesgo": a["sesgo_num"] / a["real"] if a["real"] else None,
    }


async def evaluar(salida: Path, horizonte: int, historia: int, ventanas: int, empresa_id: int | None) -> dict:
    salida.mkdir(parents=True, exist_ok=True)
    async with AsyncSessionLocal() as db:
        if empresa_id is None:
            empresa_id = (await db.execute(select(Empresa.id).order_by(Empresa.id).limit(1))).scalar_one()
        corte = hoy_local() - timedelta(days=1)  # igual que el sistema: hasta el día anterior
        series, _ = await cargar_series(db, empresa_id, corte, historia_max_dias=historia, limite_series=5000)

    sistema: dict = {}
    base: dict = {}
    por_modelo: dict[str, dict] = {}
    por_ventana = []
    detalle = []
    mejoran = iguales = empeoran = omitidas = 0

    for v in range(ventanas):
        desplazamiento = v * horizonte  # ventana 0: los últimos días; ventana 1: los días anteriores; ...
        sis_v: dict = {}
        base_v: dict = {}
        for s in series:
            n = len(s.unidades) - desplazamiento
            if n < 28 + horizonte:
                omitidas += 1
                continue
            unidades, sin_existencias = s.unidades[:n], s.sin_existencias[:n]
            entrenamiento = SerieEntrada(s.sede_id, s.producto_id, s.inicio, unidades[:-horizonte], sin_existencias[:-horizonte])
            r = pronosticar_serie(entrenamiento, horizonte)
            if r.omitida:
                omitidas += 1
                continue
            real = np.asarray(unidades[-horizonte:], dtype=float)
            y, _ = imputar_dias_sin_existencias(np.asarray(entrenamiento.unidades, float), np.asarray(entrenamiento.sin_existencias, bool))
            y, _ = limitar_picos(y)
            p_base = media_movil(y, horizonte, 28)
            p_sis = np.asarray(r.pronostico, float)
            m_sis, m_base = _metricas(real, p_sis), _metricas(real, p_base)
            for destino, m in ((sistema, m_sis), (base, m_base), (sis_v, m_sis), (base_v, m_base), (por_modelo.setdefault(r.modelo, {}), m_sis)):
                _acumular(destino, m)
            w_sis = m_sis["abs"] / m_sis["real"] if m_sis["real"] else None
            w_base = m_base["abs"] / m_base["real"] if m_base["real"] else None
            if w_sis is None or w_base is None or abs(w_sis - w_base) < 1e-9:
                iguales += 1
            elif w_sis < w_base:
                mejoran += 1
            else:
                empeoran += 1
            detalle.append({
                "ventana": v, "sede": s.sede_id, "producto": s.producto_id, "modelo": r.modelo,
                "wape_sistema": w_sis, "wape_base": w_base, "real": real.tolist(),
                "pronostico": [round(float(x), 3) for x in p_sis], "base": [round(float(x), 3) for x in p_base],
                "historia": np.asarray(unidades[-(horizonte + 42):-horizonte], float).tolist(),
                "inicio_prueba": str(s.inicio + timedelta(days=n - horizonte)),
                "intervalo_total": [r.limite_inferior, r.limite_superior],
                "demanda_total_pronosticada": r.demanda_total, "demanda_total_real": float(real.sum()),
            })
        por_ventana.append({"ventana": v, "desplazamiento_dias": desplazamiento, "sistema": _resumir(sis_v), "linea_base_media_28": _resumir(base_v)})

    dentro = sum(1 for e in detalle if e["intervalo_total"][0] is not None and e["intervalo_total"][0] <= e["demanda_total_real"] <= e["intervalo_total"][1])
    resumen = {
        "corte": str(corte), "horizonte": horizonte, "ventanas": ventanas, "por_ventana": por_ventana,
        "series_evaluadas": len(detalle), "series_omitidas": omitidas,
        "sistema": _resumir(sistema), "linea_base_media_28": _resumir(base),
        "series_mejoran": mejoran, "series_iguales": iguales, "series_empeoran": empeoran,
        "cobertura_intervalo_80_sobre_total": dentro / len(detalle) if detalle else None,
        "por_modelo_elegido": {k: {"series": sum(1 for e in detalle if e["modelo"] == k), **_resumir(a)} for k, a in por_modelo.items()},
    }
    (salida / "holdout_resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    (salida / "holdout_series.json").write_text(json.dumps(detalle, ensure_ascii=False), encoding="utf-8")
    return resumen


def imprimir(r: dict) -> None:
    s, b = r["sistema"], r["linea_base_media_28"]
    print(f"Horizonte {r['horizonte']} días · {r['ventanas']} ventana(s) · {r['series_evaluadas']} series-ventana (omitidas: {r['series_omitidas']})")
    print(f"{'':22}{'WAPE':>8}{'MAE':>8}{'RMSE':>8}{'MAPE':>8}{'sesgo':>8}")
    for nombre, m in (("Sistema", s), ("Línea base (media 28)", b)):
        mape = f"{m['mape'] * 100:7.1f}%" if m["mape"] is not None else "      —"
        print(f"{nombre:22}{m['wape'] * 100:7.1f}%{m['mae']:8.3f}{m['rmse']:8.3f}{mape}{m['sesgo'] * 100:7.1f}%")
    print(f"Series donde el sistema mejora / iguala / empeora a la línea base: {r['series_mejoran']} / {r['series_iguales']} / {r['series_empeoran']}")
    print(f"Cobertura del intervalo de 80 % sobre la demanda total del período: {r['cobertura_intervalo_80_sobre_total'] * 100:.1f} %")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--salida", type=Path, required=True, help="carpeta donde se guardan los resultados")
    ap.add_argument("--horizonte", type=int, default=14, help="días ocultos y pronosticados (7, 14, 28...)")
    ap.add_argument("--ventanas", type=int, default=3, help="ventanas de prueba consecutivas hacia atrás")
    ap.add_argument("--historia", type=int, default=200, help="días máximos de historia que se cargan")
    ap.add_argument("--empresa-id", type=int, default=None)
    a = ap.parse_args()
    imprimir(asyncio.run(evaluar(a.salida, a.horizonte, a.historia, a.ventanas, a.empresa_id)))


if __name__ == "__main__":
    main()
