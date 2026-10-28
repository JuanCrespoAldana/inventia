"""Mapper de agentes: convierte la entidad ApiKey en su DTO de salida (nunca expone la llave completa)."""

from app.dto.prediccion_dto import LlaveSalida
from app.model.auditoria import ApiKey


def a_llave_salida(k: ApiKey) -> LlaveSalida:
    return LlaveSalida(
        id=k.id, nombre=k.nombre, prefijo=k.prefijo, alcances=list(k.alcances or []), sede_id=k.sede_id, activa=k.activa,
        creada_en=k.creada_en, expira_en=k.expira_en, ultimo_uso_en=k.ultimo_uso_en,
    )
