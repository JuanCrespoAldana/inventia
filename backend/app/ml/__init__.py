"""Módulo de inteligencia artificial: predicción de demanda por sede y producto.

Capas (de la más pura a la más acoplada):
 * ``modelos``     — pronosticadores matemáticos (numpy/statsmodels/scikit-learn), sin base de datos.
 * ``evaluacion``  — validación temporal (rolling origin) y métricas WAPE / MAE / RMSE / MAPE / sesgo.
 * ``pipeline``    — preparación de la serie, calidad de datos, selección de modelo e intervalos.
 * ``datos``       — extracción de series reales desde la base de datos.
Ver docs/PREDICCION.md para el diseño, las decisiones y las limitaciones.
"""
