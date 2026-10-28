from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.dto.catalogo_dto import ProductoResumen
from app.dto.comunes_dto import EsquemaBase, Texto, TextoOpcional
from app.dto.inventario_dto import ItemCantidad
from app.dto.sede_dto import SedeResumen


class TrasladoCrear(EsquemaBase):
    sede_origen_id: int = Field(gt=0)
    sede_destino_id: int = Field(gt=0)
    observacion: TextoOpcional(500)
    items: list[ItemCantidad] = Field(min_length=1, max_length=200)

    @field_validator("items")
    @classmethod
    def _unicos(cls, items):
        ids = [i.producto_id for i in items]
        if len(ids) != len(set(ids)):
            raise ValueError("No repitas el mismo producto en un traslado: suma las cantidades en una sola línea")
        return items

    @model_validator(mode="after")
    def _sedes_distintas(self):
        if self.sede_origen_id == self.sede_destino_id:
            raise ValueError("La sede de origen y la de destino deben ser distintas")
        return self


class TrasladoMotivo(EsquemaBase):
    motivo: Texto(5, 500)


class TrasladoItemSalida(BaseModel):
    producto: ProductoResumen
    cantidad: int
    existencias_origen: int  # lo que hay HOY en la sede de origen (ayuda a decidir)
    existencias_destino: int


class TrasladoResumen(BaseModel):
    id: int
    numero: int
    estado: str
    origen: SedeResumen
    destino: SedeResumen
    unidades: int
    lineas: int
    observacion: str | None
    solicitado_en: datetime
    solicitado_por_nombre: str | None
    recomendacion_id: int | None


class TrasladoDetalle(TrasladoResumen):
    items: list[TrasladoItemSalida]
    aprobado_por_nombre: str | None = None
    aprobado_en: datetime | None = None
    confirmado_por_nombre: str | None = None
    confirmado_en: datetime | None = None
    cerrado_por_nombre: str | None = None
    cerrado_en: datetime | None = None
    motivo_cierre: str | None = None
    acciones: list[str] = []  # acciones que el usuario actual puede realizar ahora

