"""Simulación del efecto de las recomendaciones sobre los quiebres de stock (validación del módulo de recomendaciones).

    cd backend
    export DATABASE_URL=postgresql+asyncpg://usuario:clave@localhost:5432/base   # base de DEMOSTRACIÓN o de prueba
    export SECRET_KEY=una-clave-cualquiera-de-al-menos-32-caracteres
    python ../ml/simular_recomendaciones.py --salida ../ml/resultados [--ventana 56] [--revision 7] [--transito 2]

Qué responde. ¿Habrían sido menores los quiebres de stock si la empresa hubiera seguido las recomendaciones del sistema?
Se «repite» un período reciente (por defecto las últimas 8 semanas) con la demanda que realmente ocurrió en la base y se
compara cómo evolucionan las existencias de cada producto en cada sede bajo cuatro políticas de reposición:

  A  Sin reposición            No se pide nada: referencia de lo que pasa si nadie actúa.
  B  Mínimos y máximos fijos   Reglas habituales de una pyme: se pide cuando las existencias bajan del mínimo configurado
                               en la sede y se repone hasta el máximo configurado. Los niveles no se adaptan a la demanda.
  C  Reglas de Inventia con    Mismas reglas que el módulo de recomendaciones (punto de reposición, nivel objetivo,
     promedio de 28 días       traslados antes que compras), pero con la demanda estimada como el promedio de 28 días.
  D  Inventia completo         Las mismas reglas con el pronóstico del pipeline (el modelo que elige el sistema).

Las reglas de C y D son las del servicio real (``recomendaciones_service._calcular``): no se reimplementan. El pronóstico de
cada semana usa solo las ventas anteriores a ese día. Para B, C y D también se simula que solo una parte de las sugerencias se
acepta (``--aceptacion``): cada sugerencia se acepta o no al azar.

Supuestos (declarados porque condicionan el resultado):
  * La demanda es la venta observada; cuando hubo quiebres reales, la demanda verdadera pudo ser mayor.
  * Los pedidos llegan exactamente ``plazo_entrega_dias`` después y los traslados ``--transito`` días después; no hay
    cantidades mínimas de compra, descuentos, capital limitado ni espacio limitado.
  * Se revisa una vez por semana (``--revision``), igual para todas las políticas con reposición.
  * La venta no atendida se pierde (no queda pendiente).
  * Los datos de demostración son sintéticos y se generaron con un proceso parecido al que el pronóstico supone: el
    resultado ilustra el mecanismo, no mide el beneficio que tendría una empresa real.

Solo lee la base de datos. Escribe ``simulacion_resumen.json`` y ``simulacion_series.csv`` en la carpeta de salida.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))  # permite ejecutarlo desde cualquier carpeta

from app.config.database import AsyncSessionLocal  # noqa: E402
from app.ml.datos import cargar_series  # noqa: E402
from app.ml.modelos import media_movil  # noqa: E402
from app.ml.pipeline import SerieEntrada, imputar_dias_sin_existencias, limitar_picos, pronosticar_serie  # noqa: E402
from app.model.empresa import Empresa  # noqa: E402
from app.service.recomendaciones_service import PRIORIDAD_ORDEN, _calcular, _Serie  # reglas reales del sistema  # noqa: E402
from app.util.tiempo import hoy_local, inicio_de_dia_utc  # noqa: E402

POLITICAS = ("A", "B", "C", "D")
NOMBRES = {
    "A": "Sin reposición", "B": "Mínimos y máximos fijos", "C": "Reglas de Inventia con promedio de 28 días",
    "D": "Inventia completo (pronóstico del sistema)",
}


# ---------------------------------------------------------------------------------- pronósticos (en procesos aparte)
def _pronosticar(args: tuple) -> tuple:
    clave, dia, sede, producto, inicio, unidades, sin_stock, horizonte = args
    entrada = SerieEntrada(sede, producto, inicio, np.asarray(unidades, float), np.asarray(sin_stock, bool))
    r = pronosticar_serie(entrada, horizonte)
    y, _ = imputar_dias_sin_existencias(entrada.unidades, entrada.sin_existencias)
    y, _ = limitar_picos(y)
    base = float(np.mean(media_movil(y, horizonte, 28))) if len(y) else 0.0
    if r.omitida:
        return clave, dia, None, base
    return clave, dia, {"demanda": r.demanda_total / horizonte, "confianza": r.confianza, "modelo": r.modelo}, base


# ---------------------------------------------------------------------------------- simulación
class Mundo:
    """Datos fijos de la simulación: demanda real de la ventana, existencias iniciales y pronósticos por semana."""

    def __init__(self, claves, demanda, inicial, minimo, maximo, previsiones, base28, plazo, seguridad, cobertura, ventana, revision, transito):
        self.claves, self.demanda, self.inicial, self.minimo, self.maximo = claves, demanda, inicial, minimo, maximo
        self.previsiones, self.base28 = previsiones, base28
        self.plazo, self.seguridad, self.cobertura = plazo, seguridad, cobertura
        self.ventana, self.revision, self.transito = ventana, revision, transito
        self.con_pronostico = {k for k in claves if previsiones.get((k, 0)) is not None}


def _recomendaciones(mundo: Mundo, politica: str, dia: int, stock: dict, en_camino: dict) -> list[tuple]:
    """Lista de (tipo, sede_destino, producto, cantidad, sede_origen) que la política sugeriría hoy."""
    if politica == "A":
        return []
    if politica == "B":
        pedidos = []
        for k in mundo.claves:
            minimo, maximo = mundo.minimo[k], mundo.maximo[k]
            if maximo is None:
                continue
            disponible = stock[k] + en_camino[k]
            if disponible <= minimo:
                cantidad = maximo - disponible
                if cantidad > 0:
                    pedidos.append(("compra", k[0], k[1], cantidad, None))
        return pedidos

    series: dict[tuple[int, int], _Serie] = {}
    for k in mundo.claves:
        if k not in mundo.con_pronostico:
            continue
        p = mundo.previsiones.get((k, dia))
        if p is None:
            continue
        if politica == "C":
            demanda, confianza, modelo = mundo.base28[(k, dia)], "media", "media_28"
        else:
            demanda, confianza, modelo = p["demanda"], p["confianza"], p["modelo"]
        s = _Serie(
            sede_id=k[0], producto_id=k[1], cantidad=stock[k], minimo=mundo.minimo[k], maximo=mundo.maximo[k], demanda=demanda,
            confianza=confianza, modelo=modelo, demanda_horizonte=demanda * 14, horizonte=14, en_camino=en_camino[k],
        )
        _calcular(s, mundo.plazo, mundo.seguridad, mundo.cobertura)
        series[k] = s

    resultado = []
    necesitan = sorted(
        (s for s in series.values() if s.necesidad),
        key=lambda s: (PRIORIDAD_ORDEN[s.prioridad], s.cobertura if s.cobertura is not None else 1e9, s.sede_id),
    )
    for s in necesitan:
        restante = s.necesidad
        donantes = sorted(
            ((k[0], x.excedente) for k, x in series.items() if k[1] == s.producto_id and k[0] != s.sede_id and x.excedente > 0),
            key=lambda d: (-d[1], d[0]),
        )
        for origen, excedente in donantes:
            if restante <= 0:
                break
            cantidad = min(restante, excedente)
            if cantidad < 1:
                continue
            series[(origen, s.producto_id)].excedente -= cantidad
            restante -= cantidad
            resultado.append(("traslado", s.sede_id, s.producto_id, cantidad, origen))
        if restante > 0:
            resultado.append(("compra", s.sede_id, s.producto_id, restante, None))
    return resultado


def simular(mundo: Mundo, politica: str, aceptacion: float = 1.0, rng: np.random.Generator | None = None) -> dict:
    stock = {k: int(mundo.inicial[k]) for k in mundo.claves}
    en_camino = {k: 0 for k in mundo.claves}
    llegadas: dict[int, list[tuple]] = defaultdict(list)  # día -> [(clave, cantidad)]
    perdidas = {k: 0 for k in mundo.claves}
    atendidas = {k: 0 for k in mundo.claves}
    dias_quiebre = {k: 0 for k in mundo.claves}
    inventario_total = 0
    stats = {"compras": 0, "unidades_compradas": 0, "traslados": 0, "unidades_trasladadas": 0, "recomendaciones": 0, "aceptadas": 0}
    perdidas_semana = np.zeros(mundo.ventana // mundo.revision + 1)

    for dia in range(mundo.ventana):
        for clave, cantidad in llegadas.pop(dia, []):
            stock[clave] += cantidad
            en_camino[clave] -= cantidad
        if dia % mundo.revision == 0:
            for tipo, destino, producto, cantidad, origen in _recomendaciones(mundo, politica, dia, stock, en_camino):
                stats["recomendaciones"] += 1
                if aceptacion < 1.0 and rng is not None and rng.random() > aceptacion:
                    continue
                stats["aceptadas"] += 1
                k = (destino, producto)
                if tipo == "traslado":
                    cantidad = min(cantidad, stock[(origen, producto)])  # no se puede enviar lo que ya no está
                    if cantidad < 1:
                        continue
                    stock[(origen, producto)] -= cantidad
                    llegadas[dia + mundo.transito].append((k, cantidad))
                    stats["traslados"] += 1
                    stats["unidades_trasladadas"] += cantidad
                else:
                    llegadas[dia + mundo.plazo].append((k, cantidad))
                    stats["compras"] += 1
                    stats["unidades_compradas"] += cantidad
                en_camino[k] += cantidad
        for k in mundo.claves:
            d = int(mundo.demanda[k][dia])
            vendida = min(stock[k], d)
            stock[k] -= vendida
            atendidas[k] += vendida
            if vendida < d:
                perdidas[k] += d - vendida
                dias_quiebre[k] += 1
                perdidas_semana[dia // mundo.revision] += d - vendida
            inventario_total += stock[k]

    demanda_total = sum(atendidas.values()) + sum(perdidas.values())
    n = len(mundo.claves)
    return {
        "demanda_total": demanda_total, "ventas_atendidas": sum(atendidas.values()), "ventas_perdidas": sum(perdidas.values()),
        "nivel_de_servicio": sum(atendidas.values()) / demanda_total if demanda_total else None,
        "dias_con_quiebre": sum(dias_quiebre.values()), "dias_serie": n * mundo.ventana,
        "fraccion_dias_con_quiebre": sum(dias_quiebre.values()) / (n * mundo.ventana),
        "series_con_quiebre": sum(1 for v in dias_quiebre.values() if v), "series": n,
        "inventario_promedio_unidades": inventario_total / mundo.ventana,
        "dias_de_inventario": (inventario_total / mundo.ventana) / (demanda_total / mundo.ventana) if demanda_total else None,
        "perdidas_por_semana": [float(x) for x in perdidas_semana[: mundo.ventana // mundo.revision]],
        **stats,
        "_perdidas_por_serie": perdidas, "_atendidas_por_serie": atendidas,
    }


# ---------------------------------------------------------------------------------- preparación
async def preparar(empresa_id: int | None, ventana: int, revision: int, transito: int, historia: int, workers: int) -> Mundo:
    async with AsyncSessionLocal() as db:
        if empresa_id is None:
            empresa_id = (await db.execute(text("select id from empresas order by id limit 1"))).scalar_one()
        empresa = await db.get(Empresa, empresa_id)
        cfg = empresa.parametros()
        corte = hoy_local() - timedelta(days=1)
        series, _ = await cargar_series(db, empresa_id, corte, historia_max_dias=historia, limite_series=5000)
        inicio_ventana = corte - timedelta(days=ventana - 1)
        t0 = inicio_de_dia_utc(inicio_ventana)
        filas = (await db.execute(text("""
            select distinct on (sede_id, producto_id) sede_id, producto_id, saldo_posterior
            from movimientos where empresa_id = :e and fecha < :t0
            order by sede_id, producto_id, fecha desc, id desc"""), {"e": empresa_id, "t0": t0})).all()
        saldos = {(r[0], r[1]): int(r[2]) for r in filas}
        niveles = {
            (r[0], r[1]): (int(r[2]), int(r[3]) if r[3] is not None else None)
            for r in (await db.execute(text("select sede_id, producto_id, stock_minimo, stock_maximo from inventario_sede where empresa_id = :e"), {"e": empresa_id})).all()
        }

    horizonte = int(cfg["horizonte_dias"])
    claves, demanda, inicial, minimo, maximo, trabajos = [], {}, {}, {}, {}, []
    for s in series:
        k = (s.sede_id, s.producto_id)
        indice_ventana = (inicio_ventana - s.inicio).days
        if indice_ventana < 0 or len(s.unidades) - indice_ventana < ventana:
            continue
        claves.append(k)
        demanda[k] = np.asarray(s.unidades[indice_ventana: indice_ventana + ventana], dtype=int)
        inicial[k] = saldos.get(k, 0)
        minimo[k], maximo[k] = niveles.get(k, (0, None))
        for dia in range(0, ventana, revision):
            corte_i = indice_ventana + dia
            trabajos.append((k, dia, s.sede_id, s.producto_id, s.inicio, s.unidades[:corte_i].tolist(), s.sin_existencias[:corte_i].tolist(), horizonte))

    previsiones, base28 = {}, {}
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for clave, dia, pron, base in pool.map(_pronosticar, trabajos, chunksize=8):
            previsiones[(clave, dia)] = pron
            base28[(clave, dia)] = base
    return Mundo(sorted(claves), demanda, inicial, minimo, maximo, previsiones, base28, int(cfg["plazo_entrega_dias"]),
                 int(cfg["dias_seguridad"]), int(cfg["dias_cobertura_objetivo"]), ventana, revision, transito)


def _limpio(r: dict) -> dict:
    return {k: v for k, v in r.items() if not k.startswith("_")}


def _bootstrap_diferencia(mundo: Mundo, a: dict, b: dict, repeticiones: int = 5000, semilla: int = 7) -> dict:
    """IC 95 % de la reducción del nivel de servicio perdido: (perdidas_a − perdidas_b) / demanda, remuestreando series."""
    claves = mundo.claves
    pa = np.array([a["_perdidas_por_serie"][k] for k in claves], float)
    pb = np.array([b["_perdidas_por_serie"][k] for k in claves], float)
    dem = np.array([a["_perdidas_por_serie"][k] + a["_atendidas_por_serie"][k] for k in claves], float)
    rng = np.random.default_rng(semilla)
    muestras = []
    for _ in range(repeticiones):
        idx = rng.integers(0, len(claves), len(claves))
        muestras.append((pa[idx].sum() - pb[idx].sum()) / dem[idx].sum())
    return {"estimado": float((pa.sum() - pb.sum()) / dem.sum()), "ic95": [float(np.percentile(muestras, 2.5)), float(np.percentile(muestras, 97.5))]}


async def principal(a: argparse.Namespace) -> None:
    a.salida.mkdir(parents=True, exist_ok=True)
    mundo = await preparar(a.empresa_id, a.ventana, a.revision, a.transito, a.historia, a.workers)
    resultados = {p: simular(mundo, p) for p in POLITICAS}
    sensibilidad = []
    for p_acept in a.aceptacion:
        for politica in ("B", "C", "D"):  # A no pide nada; B, C y D dependen de que las sugerencias se acepten
            rng = np.random.default_rng(2026)
            corridas = [simular(mundo, politica, p_acept, rng) for _ in range(a.repeticiones if p_acept < 1.0 else 1)]
            nivel = [c["nivel_de_servicio"] for c in corridas]
            sensibilidad.append({
                "politica": politica, "aceptacion": p_acept, "corridas": len(corridas), "nivel_de_servicio_medio": float(np.mean(nivel)),
                "nivel_de_servicio_min": float(np.min(nivel)), "nivel_de_servicio_max": float(np.max(nivel)),
                "ventas_perdidas_medias": float(np.mean([c["ventas_perdidas"] for c in corridas])),
                "fraccion_dias_con_quiebre_media": float(np.mean([c["fraccion_dias_con_quiebre"] for c in corridas])),
            })
    resumen = {
        "ventana_dias": a.ventana, "revision_dias": a.revision, "transito_traslado_dias": a.transito, "plazo_entrega_dias": mundo.plazo,
        "dias_seguridad": mundo.seguridad, "dias_cobertura_objetivo": mundo.cobertura, "series": len(mundo.claves),
        "series_con_pronostico": len(mundo.con_pronostico), "politicas": {p: {"nombre": NOMBRES[p], **_limpio(resultados[p])} for p in POLITICAS},
        "reduccion_de_ventas_perdidas_vs": {
            "A": _bootstrap_diferencia(mundo, resultados["A"], resultados["D"]),
            "B": _bootstrap_diferencia(mundo, resultados["B"], resultados["D"]),
            "C": _bootstrap_diferencia(mundo, resultados["C"], resultados["D"]),
        },
        "sensibilidad_a_la_aceptacion": sensibilidad,
    }
    (a.salida / "simulacion_resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(a.salida / "simulacion_series.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sede_id", "producto_id", "existencia_inicial", "stock_minimo", "stock_maximo", "demanda_ventana"]
                   + [f"perdidas_{p}" for p in POLITICAS])
        for k in mundo.claves:
            w.writerow([k[0], k[1], mundo.inicial[k], mundo.minimo[k], mundo.maximo[k], int(mundo.demanda[k].sum())]
                       + [resultados[p]["_perdidas_por_serie"][k] for p in POLITICAS])
    imprimir(resumen)


def imprimir(r: dict) -> None:
    print(f"Ventana de {r['ventana_dias']} días · revisión cada {r['revision_dias']} · {r['series']} series ({r['series_con_pronostico']} con pronóstico)")
    print(f"{'Política':<46}{'Servicio':>9}{'Perdidas':>10}{'Días c/quiebre':>16}{'Inv. prom.':>11}{'Días inv.':>10}{'Compras':>9}{'Traslados':>10}")
    for p in POLITICAS:
        x = r["politicas"][p]
        print(f"{p + ' ' + x['nombre']:<46}{x['nivel_de_servicio'] * 100:8.1f}%{x['ventas_perdidas']:>10}{x['fraccion_dias_con_quiebre'] * 100:15.1f}%"
              f"{x['inventario_promedio_unidades']:>11.0f}{x['dias_de_inventario']:>10.1f}{x['compras']:>9}{x['traslados']:>10}")
    for p, d in r["reduccion_de_ventas_perdidas_vs"].items():
        print(f"Ventas perdidas de {p} menos las de D, como % de la demanda: {d['estimado'] * 100:.1f} pts (IC 95 % {d['ic95'][0] * 100:.1f} a {d['ic95'][1] * 100:.1f})")
    for s in r["sensibilidad_a_la_aceptacion"]:
        print(f"Aceptación {s['aceptacion'] * 100:3.0f} % · política {s['politica']}: nivel de servicio {s['nivel_de_servicio_medio'] * 100:.1f} % "
              f"(rango {s['nivel_de_servicio_min'] * 100:.1f} a {s['nivel_de_servicio_max'] * 100:.1f}), {s['ventas_perdidas_medias']:.0f} unidades perdidas")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--salida", type=Path, required=True)
    ap.add_argument("--ventana", type=int, default=56, help="días simulados (múltiplo de la revisión)")
    ap.add_argument("--revision", type=int, default=7, help="cada cuántos días se revisan las existencias")
    ap.add_argument("--transito", type=int, default=2, help="días que tarda un traslado entre sedes")
    ap.add_argument("--historia", type=int, default=200)
    ap.add_argument("--aceptacion", type=lambda s: [float(x) for x in s.split(",")], default=[1.0, 0.7, 0.4])
    ap.add_argument("--repeticiones", type=int, default=30, help="repeticiones por cada nivel de aceptación menor que 1")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--empresa-id", type=int, default=None)
    a = ap.parse_args()
    if a.ventana % a.revision:
        ap.error("--ventana debe ser múltiplo de --revision")
    asyncio.run(principal(a))


if __name__ == "__main__":
    main()
