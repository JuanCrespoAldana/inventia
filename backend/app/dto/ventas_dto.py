from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.dto.catalogo_dto import ProductoResumen
from app.dto.comunes_dto import Dinero, EsquemaBase, Texto, TextoOpcional
from app.dto.sede_dto import SedeResumen


class VentaItemCrear(EsquemaBase):
    producto_id: int = Field(gt=0)
    cantidad: int = Field(gt=0, le=1_000_000)
    precio_unitario: Dinero | None = Field(default=None, description="Si se omite, se usa el precio de venta del producto")


class VentaCrear(EsquemaBase):
    sede_id: int = Field(gt=0)
    observacion: TextoOpcional(500)
    items: list[VentaItemCrear] = Field(min_length=1, max_length=200)

    @field_validator("items")
    @classmethod
    def _unicos(cls, items):
        ids = [i.producto_id for i in items]
        if len(ids) != len(set(ids)):
            raise ValueError("No repitas el mismo producto en una venta: suma las cantidades en una sola línea")
        return items


class VentaAnular(EsquemaBase):
    motivo: Texto(5, 500)


class VentaItemSalida(BaseModel):
    producto: ProductoResumen
    cantidad: int
    precio_unitario: Dinero
    subtotal: Dinero


class VentaResumen(BaseModel):
    id: int
    numero: int
    fecha: datetime
    fecha_dia: date
    sede: SedeResumen
    usuario_nombre: str | None
    total: Dinero
    unidades: int
    lineas: int
    estado: str
    observacion: str | None


class VentaDetalle(VentaResumen):
    items: list[VentaItemSalida]
    anulada_por_nombre: str | None = None
    anulada_en: datetime | None = None
    motivo_anulacion: str | None = None
    puede_anularse: bool = False
