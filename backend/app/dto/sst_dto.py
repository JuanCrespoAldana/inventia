"""Esquemas de Seguridad y Salud en el Trabajo (pausas activas)."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, computed_field, model_validator

from app.dto.comunes_dto import EsquemaBase, Texto, TextoOpcional

AreaPausaT = Literal["cuello", "hombros", "espalda", "manos_munecas", "ojos", "piernas", "respiracion"]
ResultadoPausaT = Literal["realizada", "omitida"]
EstadoPausaT = Literal["mostrada", "realizada", "omitida"]


class ActividadCrear(EsquemaBase):
    titulo: Texto(3, 120)
    area: AreaPausaT
    mensaje: Texto(5, 300)
    instrucciones: Texto(10, 2000)  # un paso por línea
    duracion_segundos: int = Field(ge=10, le=900)
    recomendaciones: TextoOpcional(1500)  # un consejo por línea (postura, ojos, manos, forma de sentarse)
    orden: int = Field(default=0, ge=0, le=999)
    activa: bool = True


class ActividadActualizar(EsquemaBase):
    titulo: Texto(3, 120) | None = None
    area: AreaPausaT | None = None
    mensaje: Texto(5, 300) | None = None
    instrucciones: Texto(10, 2000) | None = None
    duracion_segundos: int | None = Field(default=None, ge=10, le=900)
    recomendaciones: TextoOpcional(1500)
    orden: int | None = Field(default=None, ge=0, le=999)
    activa: bool | None = None

    @model_validator(mode="after")
    def _algo_que_hacer(self):
        if not self.model_fields_set:
            raise ValueError("Indica al menos un cambio")
        return self


def _lineas(texto: str | None) -> list[str]:
    return [linea.strip() for linea in (texto or "").splitlines() if linea.strip()]


class ActividadSalida(BaseModel):
    id: int
    titulo: str
    area: str
    mensaje: str
    instrucciones: str
    duracion_segundos: int
    recomendaciones: str | None
    orden: int
    activa: bool

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pasos(self) -> list[str]:
        return _lineas(self.instrucciones)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def consejos(self) -> list[str]:
        return _lineas(self.recomendaciones)

    model_config = {"from_attributes": True}


class ConfiguracionSst(BaseModel):
    pausas_activas: bool
    intervalo_minutos: int


class ConfiguracionSstActualizar(EsquemaBase):
    pausas_activas: bool | None = None
    intervalo_minutos: int | None = Field(default=None, ge=1, le=480)

    @model_validator(mode="after")
    def _algo_que_hacer(self):
        if not self.model_fields_set:
            raise ValueError("Indica al menos un cambio")
        return self


class PausaMostrada(BaseModel):
    id: int
    mostrada_en: datetime
    actividad: ActividadSalida | None


class PausaEstado(BaseModel):
    aplica: bool  # false para quien administra el SST: no recibe pausas automáticas
    activo: bool
    intervalo_minutos: int
    ahora: datetime
    ultima_pausa_en: datetime | None
    pendiente: PausaMostrada | None


class PausaIniciada(BaseModel):
    mostrar: bool
    pausa: PausaMostrada | None = None
    proxima_en: datetime | None = None
    motivo: str | None = None  # excluido | desactivadas | sin_actividades | muy_pronto


class PausaCerrar(EsquemaBase):
    resultado: ResultadoPausaT
    duracion_segundos: int | None = Field(default=None, ge=0, le=3600)


class PausaRegistro(BaseModel):
    id: int
    usuario_id: int
    usuario_nombre: str | None = None
    actividad_titulo: str
    mostrada_en: datetime
    estado: str
    cerrada_en: datetime | None
    duracion_segundos: int | None


class ResumenUsuarioSst(BaseModel):
    usuario_id: int
    usuario_nombre: str | None
    mostradas: int
    realizadas: int
    omitidas: int


class ResumenSst(BaseModel):
    desde: date
    mostradas: int
    realizadas: int
    omitidas: int
    sin_responder: int
    cumplimiento: float | None  # realizadas / (realizadas + omitidas + sin responder), en %
    por_usuario: list[ResumenUsuarioSst]
