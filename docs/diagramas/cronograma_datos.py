"""Plan de referencia por semanas relativas (no son fechas de calendario): el equipo debe confirmar las fechas reales."""
SEMANAS = 28

# (objetivo, actividad, semana inicial, semana final)
ACTIVIDADES = [
    ("OE1", "Revisión de literatura y antecedentes", 1, 3),
    ("OE1", "Caso de estudio e instrumentos de diagnóstico", 2, 4),
    ("OE1", "Análisis exploratorio de los datos de ventas", 3, 5),
    ("OE1", "Procesos AS-IS y TO-BE", 4, 5),
    ("OE2", "Requisitos de negocio y de usuario", 4, 6),
    ("OE2", "Requisitos funcionales y no funcionales, prioridad y criterios", 5, 8),
    ("OE2", "Riesgos (ISO 31000) y matriz de trazabilidad", 6, 9),
    ("OE3", "Arquitectura y despliegue", 8, 10),
    ("OE3", "Modelo de datos", 8, 11),
    ("OE3", "Interfaz: navegación, guía de estilo y prototipos", 9, 12),
    ("OE3", "Modelo predictivo (CRISP-DM)", 10, 13),
    ("OE4", "Seguridad y control de acceso", 11, 14),
    ("OE4", "Catálogo e inventario multisede", 12, 16),
    ("OE4", "Ventas, traslados y alertas", 14, 18),
    ("OE4", "Predicción y recomendaciones", 15, 20),
    ("OE4", "Reportes, auditoría y módulo SIG", 18, 23),
    ("OE5", "Pruebas funcionales y de integración", 16, 23),
    ("OE5", "Pruebas de seguridad (OWASP y fuzzing)", 20, 24),
    ("OE5", "Pruebas de rendimiento y de escala", 21, 25),
    ("OE5", "Evaluación del modelo y de las recomendaciones", 22, 26),
    ("OE5", "Usabilidad (SUS) y validación con el caso de estudio", 24, 27),
    ("Doc.", "Redacción del documento y cierre", 1, 28),
]
HITOS = [(5, "Diagnóstico"), (9, "Requisitos"), (13, "Diseño"), (20, "Versión 1.0.0"), (24, "Versión 1.1.0"), (28, "Entrega")]
OBJETIVOS = {"OE1": "OE1 Diagnóstico", "OE2": "OE2 Requisitos", "OE3": "OE3 Diseño", "OE4": "OE4 Desarrollo", "OE5": "OE5 Pruebas y cierre", "Doc.": "Documento"}
