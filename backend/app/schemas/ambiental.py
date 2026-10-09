"""Esquemas de gestión ambiental."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.catalogo import ProductoResumen
from app.schemas.comunes import EsquemaBase, Numero, Texto, TextoOpcional
from app.schemas.sede import SedeResumen

TipoVehiculoT = Literal["bicicleta_electrica", "patineta_electrica", "motocicleta_electrica", "otro"]
PropulsionT = Literal["electrica", "asistida_pedaleo"]
EstadoParametrizacionT = Literal["completa", "parcial", "pendiente", "sin_categorias"]

# Entradas decimales con límites razonables (se entregan al navegador como números).
_Decimal = lambda **kw: Annotated[Decimal, Field(**kw)]  # noqa: E731


class FactorRedActualizar(EsquemaBase):
    valor: _Decimal(gt=0, le=5, max_digits=8, decimal_places=5)  # kg CO₂e por kWh
    anio: int = Field(ge=2000, le=2100)
    fuente: Texto(5, 500)


class CategoriaAmbientalActualizar(EsquemaBase):
    tipo_vehiculo: TipoVehiculoT
    propulsion: PropulsionT
    distancia_anual_km: _Decimal(gt=0, le=200000, max_digits=10, decimal_places=1) | None = None
    consumo_kwh_100km: _Decimal(ge=0, le=100, max_digits=8, decimal_places=3) | None = None
    vehiculo_referencia: TextoOpcional(200)
    emision_referencia_gco2_km: _Decimal(ge=0, le=2000, max_digits=8, decimal_places=2) | None = None
    horizonte_anios: int = Field(default=1, ge=1, le=30)
    fuente: TextoOpcional(500)
    activa: bool = True

    @model_validator(mode="after")
    def _documentar(self):
        completos = None not in (self.distancia_anual_km, self.consumo_kwh_100km, self.emision_referencia_gco2_km)
        if completos and not self.fuente:
            raise ValueError("Documenta la fuente de los valores (ficha técnica, estudio o norma)")
        return self


class FactorRedSalida(BaseModel):
    valor: Numero | None
    anio: int | None
    fuente: str | None


class CategoriaAmbientalSalida(BaseModel):
    categoria_id: int
    categoria_nombre: str
    es_vehiculo: bool  # tiene configuración
    activa: bool = False
    tipo_vehiculo: str | None = None
    propulsion: str | None = None
    distancia_anual_km: Numero | None = None
    consumo_kwh_100km: Numero | None = None
    vehiculo_referencia: str | None = None
    emision_referencia_gco2_km: Numero | None = None
    horizonte_anios: int = 1
    fuente: str | None = None
    parametros_completos: bool = False
    co2_por_unidad_kg: Numero | None = None  # resultado de la fórmula con los parámetros actuales
    unidades_vendidas: int = 0
    unidades_sin_parametrizar: int = 0


class ConfiguracionAmbiental(BaseModel):
    factor_red: FactorRedSalida
    categorias: list[CategoriaAmbientalSalida]
    puede_configurar: bool = False


class ResultadoSincronizacion(BaseModel):
    incorporados: int  # líneas de ventas anteriores que se empezaron a contar
    calculados: int  # registros que estaban pendientes y ya tienen CO₂ estimado


class Parametrizacion(BaseModel):
    estado: EstadoParametrizacionT
    mensaje: str
    categorias_vehiculo: int
    categorias_parametrizadas: int
    factor_red_definido: bool


class Cifras(BaseModel):
    """``unidades`` es un dato REAL (ventas confirmadas). ``co2_estimado_kg`` es una ESTIMACIÓN que solo
    suma los registros ya parametrizados; ``unidades_sin_parametrizar`` quedan fuera de la estimación."""

    unidades: int
    co2_estimado_kg: Numero
    unidades_sin_parametrizar: int


class CifrasMes(Cifras):
    mes: int


class CifrasAnio(Cifras):
    anio: int


class CifrasTipo(Cifras):
    tipo_vehiculo: str


class ResumenAmbiental(BaseModel):
    anio: int
    parametrizacion: Parametrizacion
    mes_actual: Cifras
    anio_seleccionado: Cifras
    acumulado: Cifras
    meses: list[CifrasMes]
    anios: list[CifrasAnio]
    por_tipo: list[CifrasTipo]
    anios_disponibles: list[int]


class RegistroAmbiental(BaseModel):
    id: int
    fecha: date
    venta_id: int
    venta_numero: int | None = None
    sede: SedeResumen
    producto: ProductoResumen
    categoria: str | None = None
    tipo_vehiculo: str
    propulsion: str
    unidades: int
    estado: str  # activo | anulado
    parametrizado: bool
    co2_estimado_kg: Numero | None
    anulado_en: datetime | None
