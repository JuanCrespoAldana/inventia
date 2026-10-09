from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.catalogo import ProductoResumen
from app.schemas.comunes import EsquemaBase, Texto, TextoOpcional
from app.schemas.sede import SedeResumen


class EjecutarPrediccion(EsquemaBase):
    horizonte_dias: int | None = Field(default=None, ge=1, le=90, description="Vacío = parámetro de la empresa")


class EjecucionSalida(BaseModel):
    id: int
    estado: str
    horizonte_dias: int
    fecha_corte: date | None
    parametros: dict
    resumen: dict
    error: str | None
    creada_en: datetime
    iniciada_en: datetime | None
    finalizada_en: datetime | None
    solicitada_por: str | None = None


class PrediccionSalida(BaseModel):
    id: int
    ejecucion_id: int
    producto: ProductoResumen
    sede: SedeResumen
    fecha_inicio: date
    fecha_fin: date
    demanda_estimada: float
    demanda_diaria: float
    limite_inferior: float | None
    limite_superior: float | None
    modelo: str
    modelo_descripcion: str
    es_linea_base: bool
    confianza: str
    metricas: dict
    advertencias: list[str]
    existencias_actuales: int | None
    cobertura_dias: float | None
    generada_en: datetime


class SerieDemanda(BaseModel):
    producto: ProductoResumen
    sede: SedeResumen
    ejecucion_id: int | None
    historial: list[tuple[date, float]]  # ventas reales
    pronostico: list[tuple[date, float]]  # estimación (nunca se mezcla con lo real)
    modelo: str | None
    confianza: str | None
    demanda_estimada: float | None
    limite_inferior: float | None
    limite_superior: float | None
    metricas: dict
    advertencias: list[str]
    motivo_sin_prediccion: str | None


class LlaveCrear(EsquemaBase):
    nombre: Texto(3, 100)
    alcances: list[str] = Field(min_length=1, max_length=10)
    sede_id: int | None = Field(default=None, gt=0)
    dias_vigencia: int | None = Field(default=90, ge=1, le=730)


class LlaveSalida(BaseModel):
    id: int
    nombre: str
    prefijo: str
    alcances: list[str]
    sede_id: int | None
    activa: bool
    creada_en: datetime
    expira_en: datetime | None
    ultimo_uso_en: datetime | None


class LlaveCreada(LlaveSalida):
    llave: str  # se muestra UNA sola vez


class RecomendacionSalida(BaseModel):
    id: int
    tipo: str
    prioridad: str
    estado: str
    producto: ProductoResumen
    sede: SedeResumen
    sede_origen: SedeResumen | None
    cantidad_sugerida: int
    resumen: str
    justificacion: dict
    ejecucion_id: int | None
    generada_en: datetime
    revisada_por_nombre: str | None
    revisada_en: datetime | None
    comentario_revision: str | None
    traslado_id: int | None = None
    traslado_numero: int | None = None
    acciones: list[str] = []


class RevisionRecomendacion(EsquemaBase):
    comentario: TextoOpcional(500)
