"""Asistente de consultas de Inventia: entiende preguntas en español sobre el inventario y responde con datos reales.

Es de SOLO LECTURA y determinista (no usa un modelo de lenguaje): clasifica la pregunta por intención, resuelve las
sedes, productos, categorías y fechas que menciona, y consulta la base de datos respetando los permisos y la sede
de quien pregunta. Módulos:

* ``catalogo``   intenciones, señales de lenguaje, ejemplos y rutas de las pantallas.
* ``entidades``  sedes, categorías, productos, periodos y filtros que aparecen en la frase.
* ``bloques``    estructuras de respuesta (métricas, tablas, barras, listas) y formatos.
* ``datos``      consultas a la base de datos compartidas por las respuestas.
* ``respuestas_*`` una respuesta por intención, agrupadas por tema.
* ``motor``      orquesta todo: interpreta, comprueba permisos, responde y recuerda el contexto.
"""
