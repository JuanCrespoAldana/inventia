# Módulo de predicción: experimentos

El código de predicción de Inventia vive en [`backend/app/ml/`](../backend/app/ml/) porque lo usa la API. Esta
carpeta contiene lo que sirve para **estudiarlo y repetir la evaluación** sin tocar ninguna base de datos.

La explicación completa del método (calidad de datos, modelos, validación temporal, intervalos, confianza y
recomendaciones) está en [`docs/PREDICCION.md`](../docs/PREDICCION.md).

## `evaluar_modelos.py`

Genera series **sintéticas** de demanda diaria con cinco comportamientos —estable, estacional, con tendencia,
intermitente y ruidosa— y las pasa por la misma validación temporal que usa el sistema (varios cortes en el tiempo;
nunca se entrena con datos posteriores al corte). Para cada tipo de serie muestra:

1. El **WAPE** de cada modelo (menor es mejor).
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
de esa empresa: el sistema lo hace en cada ejecución y deja WAPE, MAE y la mejora frente a la línea base guardados
en cada predicción (pantalla *Predicción de demanda*, y reporte de predicciones).

## Evaluar con datos reales

1. Cargue las ventas reales en Inventia (ventas registradas o migradas).
2. Genere una predicción desde la interfaz o con `python -m app.cli predecir`.
3. Revise en *Predicción de demanda* el **WAPE global**, la **mejora frente a la línea base** y las series omitidas
   con su motivo.

Una mejora cercana a cero o negativa es información valiosa: indica que, con esos datos, el promedio simple es
tan bueno como los modelos complejos, y el sistema ya lo usará automáticamente.
