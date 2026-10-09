from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.catalogo import ProductoResumen
from app.schemas.comunes import Dinero, EsquemaBase, Numero, TextoOpcional, Texto
from app.schemas.sede import SedeResumen

MotivoEntradaT = Literal["compra", "devolucion_cliente", "inventario_inicial", "produccion", "otro"]
MotivoSalidaT = Literal["perdida", "deterioro", "consumo_interno", "devolucion_proveedor", "otro"]
MotivoAjusteT = Literal["conteo_fisico", "correccion", "otro"]
EstadoStockT = Literal["agotado", "bajo", "normal", "excesivo"]


class ItemCantidad(EsquemaBase):
    producto_id: int = Field(gt=0)
    cantidad: int = Field(gt=0, le=10_000_000, description="Unidades enteras, mayor que cero")


def _sin_repetidos(items: list[ItemCantidad]) -> list[ItemCantidad]:
    ids = [i.producto_id for i in items]
    if len(ids) != len(set(ids)):
        raise ValueError("No repitas el mismo producto en una operación: suma las cantidades en una sola línea")
    return items


class EntradaCrear(EsquemaBase):
    sede_id: int = Field(gt=0)
    motivo: MotivoEntradaT = "compra"
    observacion: TextoOpcional(500)
    items: list[ItemCantidad] = Field(min_length=1, max_length=200)

    @field_validator("items")
    @classmethod
    def _unicos(cls, items):
        return _sin_repetidos(items)


class SalidaCrear(EsquemaBase):
    sede_id: int = Field(gt=0)
    motivo: MotivoSalidaT
    observacion: TextoOpcional(500)
    items: list[ItemCantidad] = Field(min_length=1, max_length=200)

    @field_validator("items")
    @classmethod
    def _unicos(cls, items):
        return _sin_repetidos(items)

    @model_validator(mode="after")
    def _exigir_detalle(self):
        if self.motivo == "otro" and not self.observacion:
            raise ValueError("Cuando el motivo es «otro» debes explicarlo en la observación")
        return self


class AjusteCrear(EsquemaBase):
    sede_id: int = Field(gt=0)
    producto_id: int = Field(gt=0)
    cantidad_real: int = Field(ge=0, le=100_000_000, description="Existencias contadas físicamente")
    motivo: MotivoAjusteT = "conteo_fisico"
    observacion: Texto(5, 500)  # un ajuste siempre debe justificarse


class NivelesActualizar(EsquemaBase):
    sede_id: int = Field(gt=0)
    producto_id: int = Field(gt=0)
    stock_minimo: int = Field(ge=0, le=100_000_000)
    stock_maximo: int | None = Field(default=None, ge=0, le=100_000_000)

    @model_validator(mode="after")
    def _coherentes(self):
        if self.stock_maximo is not None and self.stock_maximo < self.stock_minimo:
            raise ValueError("El stock máximo no puede ser menor que el mínimo")
        return self


class MovimientoSalida(BaseModel):
    id: int
    fecha: datetime
    tipo: str
    motivo: str | None
    delta: int
    saldo_anterior: int
    saldo_posterior: int
    observacion: str | None
    producto: ProductoResumen
    sede: SedeResumen
    sede_contraparte: SedeResumen | None = None
    usuario_id: int
    usuario_nombre: str | None = None
    venta_id: int | None = None
    venta_numero: int | None = None
    traslado_id: int | None = None
    traslado_numero: int | None = None
    entrada_id: int | None = None  # solo en entradas registradas desde la versión 1.1
    entrada_numero: int | None = None


class ResultadoOperacion(BaseModel):
    mensaje: str
    movimientos: list[MovimientoSalida]
    alertas_abiertas: int = 0
    alertas_resueltas: int = 0
    entrada_id: int | None = None
    entrada_numero: int | None = None


class InventarioFila(BaseModel):
    producto: ProductoResumen
    categoria: str
    producto_activo: bool
    cantidad: int
    stock_minimo: int
    stock_maximo: int | None
    estado: EstadoStockT
    costo: Dinero | None
    valor: Numero | None
    actualizado_en: datetime | None


class DesgloseSede(BaseModel):
    sede_id: int
    sede: str
    cantidad: int
    stock_minimo: int
    stock_maximo: int | None
    estado: EstadoStockT


class ConsolidadoFila(BaseModel):
    producto: ProductoResumen
    categoria: str
    producto_activo: bool
    total: int
    costo: Dinero | None
    valor: Numero | None
    sedes_en_alerta: int
    sedes: list[DesgloseSede]


class FiltroFechas(BaseModel):
    desde: date | None = None
    hasta: date | None = None


# ---------------- Entradas de mercancía y sus observaciones ----------------
class EntradaObservacionCrear(EsquemaBase):
    contenido: Texto(3, 1000)
    producto_id: int | None = Field(default=None, gt=0, description="Línea de la entrada a la que se refiere (opcional)")


class NoConformidadVinculo(BaseModel):
    id: int
    numero: int
    estado: str


class EntradaObservacionSalida(BaseModel):
    id: int
    fecha: datetime
    usuario_id: int
    usuario_nombre: str | None = None
    contenido: str
    producto: ProductoResumen | None = None
    # No conformidades que ya se abrieron a partir de esta observación (evita registrarla dos veces).
    no_conformidades: list[NoConformidadVinculo] = []


class EntradaLinea(BaseModel):
    producto: ProductoResumen
    cantidad: int
    saldo_posterior: int


class EntradaResumen(BaseModel):
    id: int
    numero: int
    fecha: datetime
    motivo: str
    sede: SedeResumen
    usuario_id: int
    usuario_nombre: str | None = None
    unidades: int
    lineas: int
    observaciones: int
    no_conformidades: int


class EntradaDetalle(EntradaResumen):
    detalle_lineas: list[EntradaLinea]
    historial_observaciones: list[EntradaObservacionSalida]
    no_conformidades_vinculadas: list[NoConformidadVinculo]
    puede_observar: bool = False
    puede_reportar_calidad: bool = False
