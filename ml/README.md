# Módulo de predicción: experimentos

El código de predicción de Inventia vive en [`backend/app/ml/`](../backend/app/ml/) porque lo usa la API. Esta
carpeta contiene lo que sirve para **estudiarlo y repetir la evaluación** sin tocar ninguna base de datos.

La explicación completa del método (calidad de datos, modelos, validación temporal, intervalos, confianza y
recomendaciones) está en [`docs/PREDICCION.md`](../docs/PREDICCION.md).

## `evaluar_modelos.py`

Genera series **sintéticas** de demanda diaria con cinco comportamientos —estable, estacional, con tendencia,
intermitente y ruidosa— y las pasa por la misma validación temporal que usa el sistema (varios cortes en el tiempo;
nunca se entrena con datos posteriores al corte). Para cada tipo de serie muestra:

1. El **WAPE**, **MAE**, **RMSE** y **MAPE** de cada modelo (menor es mejor). El MAPE solo cuenta los días con ventas.
2. En cuántas series cada modelo supera a la línea base («promedio de 28 días») por el margen mínimo de 3 % que el
   sistema exige para preferir un modelo avanzado.

```bash
cd backend
python ../ml/evaluar_modelos.py --series 40 --dias 120 --horizonte 14 --semilla 7
```

| Opción | Por defecto | Significado |
|---|---|---|
| `--series` | 40 | Series generadas por cada tipo |
| `--dias` | 120 | Largo de cada serie |
| `--horizonte` | 14 | Días que se pronostican en cada corte |
| `--semilla` | 7 | Semilla del generador (mismo valor → mismo resultado) |

Requiere las dependencias del backend (`pip install -r backend/requirements.txt`).

### Cómo interpretarlo

Las series son sintéticas **a propósito**: se conoce el proceso que las genera, así que se puede comprobar que cada
modelo hace lo que promete —el estacional gana en series con ciclo semanal, Croston en demanda intermitente— y que
ninguno «inventa» mejoras donde no las hay.

**No son una medida del desempeño en una empresa real.** Ese desempeño solo se conoce midiéndolo sobre las ventas
de esa empresa: el sistema lo hace en cada ejecución y deja WAPE, MAE, RMSE, MAPE y la mejora frente a la línea base guardados
en cada predicción (pantalla *Predicción de demanda*, y reporte de predicciones).

## `evaluar_fuera_de_muestra.py`

Mide el sistema sobre las ventas de una base de datos (la de demostración o cualquier base de **pruebas**; solo lee).
Oculta los últimos *h* días de cada serie, deja que el pipeline elija modelo y pronostique con el resto y compara con lo que
realmente ocurrió, frente a la línea base «promedio de 28 días». Con `--ventanas N` lo repite en N ventanas consecutivas hacia
atrás. También mide en qué fracción de los casos la demanda real cayó dentro del intervalo de 80 % que muestra la interfaz.

```bash
cd backend
export DATABASE_URL=postgresql+asyncpg://usuario:clave@localhost:5432/base_de_pruebas SECRET_KEY=una-clave-de-32-caracteres-o-mas
python ../ml/evaluar_fuera_de_muestra.py --salida ../ml/resultados --horizonte 14 --ventanas 3
```

Escribe `holdout_resumen.json` y `holdout_series.json` en la carpeta indicada. Los resultados con la base de demostración
están comentados en [`docs/PREDICCION.md` §11](../docs/PREDICCION.md).

## `simular_recomendaciones.py`

Responde si los quiebres de stock habrían sido menores de haber seguido las recomendaciones. Repite las últimas 8 semanas de una
base de **pruebas** (solo lee) con la demanda que realmente ocurrió y compara cuatro políticas: sin reposición, mínimos y máximos
fijos, las reglas de Inventia con promedio de 28 días y Inventia completo (con el pronóstico del sistema). Las reglas son las del
servicio real (`recomendaciones_service._calcular`). Con `--aceptacion` simula que solo una parte de las sugerencias se acepta.

```bash
cd backend
export DATABASE_URL=postgresql+asyncpg://usuario:clave@localhost:5432/base_de_pruebas SECRET_KEY=una-clave-de-32-caracteres-o-mas
python ../ml/simular_recomendaciones.py --salida ../ml/resultados --ventana 56 --revision 7 --transito 2 --aceptacion 1.0,0.7,0.4
```

Escribe `simulacion_resumen.json` y `simulacion_series.csv`. Tarda unos minutos (calcula un pronóstico por serie y semana).
Los resultados con la base de demostración y los supuestos están en [`docs/PREDICCION.md` §12](../docs/PREDICCION.md).

## Evaluar con datos reales

1. Cargue las ventas reales en Inventia (ventas registradas o migradas).
2. Genere una predicción desde la interfaz o con `python -m app.cli predecir`.
3. Revise en *Predicción de demanda* el **WAPE global**, la **mejora frente a la línea base** y las series omitidas
   con su motivo.

Una mejora cercana a cero o negativa es información valiosa: indica que, con esos datos, el promedio simple es
tan bueno como los modelos complejos, y el sistema ya lo usará automáticamente.
