"""Mapper ambiental: convierte la configuración del factor de red en su DTO de salida."""

from app.dto.ambiental_dto import FactorRedSalida
from app.model.ambiental import AmbConfiguracion


def a_factor_red_salida(cfg: AmbConfiguracion | None) -> FactorRedSalida:
    if cfg is None:
        return FactorRedSalida(valor=None, anio=None, fuente=None)
    return FactorRedSalida(valor=cfg.factor_red_kgco2_kwh, anio=cfg.factor_red_anio, fuente=cfg.factor_red_fuente)
