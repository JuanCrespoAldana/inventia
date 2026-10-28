"""Mapper de SST: convierte las entidades de pausas activas en sus DTO de salida."""

from app.dto.sst_dto import ActividadSalida, ConfiguracionSst, PausaMostrada
from app.model.sst import SstActividad, SstConfiguracion, SstPausa


def a_configuracion_sst(cfg: SstConfiguracion) -> ConfiguracionSst:
    return ConfiguracionSst(pausas_activas=cfg.pausas_activas, intervalo_minutos=cfg.intervalo_minutos)


def a_pausa_mostrada(p: SstPausa, actividades: dict[int, SstActividad]) -> PausaMostrada:
    a = actividades.get(p.actividad_id) if p.actividad_id else None
    return PausaMostrada(id=p.id, mostrada_en=p.mostrada_en, actividad=ActividadSalida.model_validate(a) if a else None)
