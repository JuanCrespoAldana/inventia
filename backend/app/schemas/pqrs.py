"""Esquemas de PQRS."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.adjunto import AdjuntoSalida
from app.schemas.comunes import EsquemaBase, Texto, TextoOpcional
from app.schemas.sede import SedeResumen

TipoPqrsT = Literal["peticion", "queja", "reclamo", "sugerencia"]
EstadoPqrsT = Literal["pendiente", "en_revision", "en_proceso", "resuelta"]
AmbitoPqrsT = Literal["mias", "todas"]


class PqrsCrear(EsquemaBase):
    tipo: TipoPqrsT
    asunto: Texto(5, 200)
    descripcion: Texto(10, 4000)


class PqrsGestionar(EsquemaBase):
    """Cambia el estado y/o registra la respuesta administrativa. Debe traer al menos uno de los dos."""

    estado: EstadoPqrsT | None = None
    respuesta: TextoOpcional(4000)

    @model_validator(mode="after")
    def _algo_que_hacer(self):
        if self.estado is None and not self.respuesta:
            raise ValueError("Indica el nuevo estado o escribe una respuesta")
        if self.respuesta is not None and len(self.respuesta) < 3:
            raise ValueError("La respuesta debe tener al menos 3 caracteres")
        return self


class PqrsEvento(BaseModel):
    id: int
    fecha: datetime
    usuario_id: int
    usuario_nombre: str | None = None
    evento: str
    estado_anterior: str | None
    estado_nuevo: str | None
    comentario: str | None


class PqrsResumen(BaseModel):
    id: int
    numero: int
    tipo: str
    asunto: str
    estado: str
    usuario_id: int
    usuario_nombre: str | None = None
    sede: SedeResumen | None = None
    created_at: datetime
    updated_at: datetime
    respondida: bool
    adjuntos: int = 0


class PqrsDetalle(PqrsResumen):
    descripcion: str
    respuesta: str | None
    respondida_por_nombre: str | None = None
    respondida_en: datetime | None = None
    historial: list[PqrsEvento]
    archivos: list[AdjuntoSalida]
    puede_gestionar: bool = False
    puede_adjuntar: bool = False


class PqrsConteo(BaseModel):
    total: int
    pendiente: int
    en_revision: int
    en_proceso: int
    resuelta: int


class FiltrosPqrs(BaseModel):
    ambito: AmbitoPqrsT = "mias"
    tipo: TipoPqrsT | None = None
    estado: EstadoPqrsT | None = None
    usuario_id: int | None = Field(default=None, gt=0)
    desde: date | None = None
    hasta: date | None = None
    q: str | None = None
