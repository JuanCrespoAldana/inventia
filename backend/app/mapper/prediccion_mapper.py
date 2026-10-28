"""Mapper de predicciones: convierte una predicción con su producto, sede y existencias en su DTO de salida."""

from app.dto.catalogo_dto import ProductoResumen
from app.dto.prediccion_dto import PrediccionSalida
from app.dto.sede_dto import SedeResumen
from app.ml.modelos import POR_NOMBRE
from app.model.catalogo import Producto
from app.model.prediccion import Prediccion
from app.model.sede import Sede


def descripcion_modelo(nombre: str) -> str:
    c = POR_NOMBRE.get(nombre)
    return c.descripcion if c else nombre


def a_prediccion_salida(p: Prediccion, producto: Producto, sede: Sede, existencias: int | None) -> PrediccionSalida:
    dias = max((p.fecha_fin - p.fecha_inicio).days + 1, 1)
    diaria = float(p.demanda_estimada) / dias
    return PrediccionSalida(
        id=p.id, ejecucion_id=p.ejecucion_id, producto=ProductoResumen.model_validate(producto),
        sede=SedeResumen.model_validate(sede), fecha_inicio=p.fecha_inicio, fecha_fin=p.fecha_fin,
        demanda_estimada=float(p.demanda_estimada), demanda_diaria=round(diaria, 3),
        limite_inferior=None if p.limite_inferior is None else float(p.limite_inferior),
        limite_superior=None if p.limite_superior is None else float(p.limite_superior),
        modelo=p.modelo, modelo_descripcion=descripcion_modelo(p.modelo), es_linea_base=p.es_linea_base,
        confianza=p.confianza, metricas=p.metricas or {}, advertencias=list(p.advertencias or []),
        existencias_actuales=existencias,
        cobertura_dias=round(existencias / diaria, 1) if existencias is not None and diaria > 0 else None,
        generada_en=p.generada_en,
    )
