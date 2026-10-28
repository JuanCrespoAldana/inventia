"""Esquemas de calidad: no conformidades y garantías."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.dto.adjunto_dto import AdjuntoSalida
from app.dto.catalogo_dto import ProductoResumen
from app.dto.comunes_dto import EsquemaBase, Texto, TextoOpcional
from app.dto.sede_dto import SedeResumen
from app.util.tiempo import hoy_local

TipoNcT = Literal[
    "defecto_de_fabrica", "dano_en_transporte", "producto_equivocado", "cantidad_incorrecta",
    "empaque_deteriorado", "no_cumple_especificacion", "otro",
]
EstadoNcT = Literal["reportado", "en_revision", "en_proceso_solucion", "resuelto", "cerrado"]
EstadoGarantiaT = Literal[
    "reportada", "pendiente_revision", "enviada_proveedor", "aprobada", "rechazada", "solucionada", "cerrada"
]
DocumentoGarantiaT = Literal["factura_compra", "entrada_inventario", "venta", "otro"]


def _no_futura(valor: date | None) -> date | None:
    if valor is not None and valor > hoy_local():
        raise ValueError("La fecha no puede ser futura")
    return valor


class _Observacion(EsquemaBase):
    contenido: Texto(3, 1000)


ObservacionCrear = _Observacion


class EventoSalida(BaseModel):
    """Una línea del historial de una no conformidad o de una garantía."""

    id: int
    fecha: datetime
    usuario_id: int
    usuario_nombre: str | None = None
    evento: str  # creacion | estado | observacion | gestion
    estado_anterior: str | None
    estado_nuevo: str | None
    contenido: str | None


class EntradaVinculo(BaseModel):
    id: int
    numero: int
    fecha: datetime


# ------------------------------------------------------------------ no conformidades
class NoConformidadCrear(EsquemaBase):
    producto_id: int = Field(gt=0)
    sede_id: int | None = Field(default=None, gt=0, description="Obligatoria salvo que se indique la entrada o la persona tenga una sola sede")
    referencia: TextoOpcional(100)
    tipo: TipoNcT
    descripcion: Texto(10, 2000)
    fecha_deteccion: date
    cantidad_afectada: int = Field(gt=0, le=1_000_000)
    proveedor: TextoOpcional(150)
    observaciones: TextoOpcional(1000)
    entrada_id: int | None = Field(default=None, gt=0)
    entrada_observacion_id: int | None = Field(default=None, gt=0)

    _fecha = field_validator("fecha_deteccion")(_no_futura)

    @model_validator(mode="after")
    def _observacion_requiere_entrada(self):
        if self.entrada_observacion_id and not self.entrada_id:
            raise ValueError("Para vincular una observación indica también la entrada")
        return self


class NoConformidadGestionar(EsquemaBase):
    """Gestión por parte de quien administra la calidad. Debe traer al menos un cambio."""

    estado: EstadoNcT | None = None
    responsable_id: int | None = Field(default=None, gt=0)
    proveedor: TextoOpcional(150)
    solucion: TextoOpcional(2000)
    comentario: TextoOpcional(1000)

    @model_validator(mode="after")
    def _algo_que_hacer(self):
        if all(v is None for v in (self.estado, self.responsable_id, self.proveedor, self.solucion, self.comentario)):
            raise ValueError("Indica al menos un cambio")
        return self


class NoConformidadResumen(BaseModel):
    id: int
    numero: int
    producto: ProductoResumen
    sede: SedeResumen
    tipo: str
    estado: str
    fecha_deteccion: date
    cantidad_afectada: int
    referencia: str | None
    usuario_id: int
    usuario_nombre: str | None = None
    responsable_nombre: str | None = None
    entrada: EntradaVinculo | None = None
    created_at: datetime
    observaciones: int = 0
    adjuntos: int = 0


class NoConformidadDetalle(NoConformidadResumen):
    descripcion: str
    proveedor: str | None
    solucion: str | None
    responsable_id: int | None
    resuelta_en: datetime | None
    cerrada_en: datetime | None
    observacion_origen: str | None = None  # texto de la observación de la entrada de la que nació
    historial: list[EventoSalida]
    archivos: list[AdjuntoSalida]
    puede_gestionar: bool = False
    puede_observar: bool = False
    puede_adjuntar: bool = False


# ------------------------------------------------------------------ garantías
class GarantiaCrear(EsquemaBase):
    producto_id: int = Field(gt=0)
    sede_id: int | None = Field(default=None, gt=0)
    cantidad: int = Field(default=1, gt=0, le=1_000_000)
    documento_tipo: DocumentoGarantiaT
    documento_referencia: TextoOpcional(100)
    entrada_id: int | None = Field(default=None, gt=0)
    venta_id: int | None = Field(default=None, gt=0)
    fecha_compra: date
    garantia_hasta: date | None = None
    fecha_reporte: date | None = None  # por defecto, hoy
    defecto: Texto(10, 2000)
    proveedor: TextoOpcional(150)
    observaciones: TextoOpcional(1000)

    _fechas = field_validator("fecha_compra", "fecha_reporte")(_no_futura)

    @model_validator(mode="after")
    def _coherencia(self):
        reporte = self.fecha_reporte or hoy_local()
        if self.fecha_compra > reporte:
            raise ValueError("La fecha de compra o recepción no puede ser posterior a la fecha del reporte")
        if self.garantia_hasta and self.garantia_hasta < self.fecha_compra:
            raise ValueError("La vigencia de la garantía no puede ser anterior a la fecha de compra")
        if self.documento_tipo == "entrada_inventario" and not self.entrada_id:
            raise ValueError("Selecciona la entrada de inventario que respalda la garantía")
        if self.documento_tipo == "venta" and not self.venta_id:
            raise ValueError("Selecciona la venta que respalda la garantía")
        if self.documento_tipo in ("factura_compra", "otro") and not self.documento_referencia:
            raise ValueError("Indica el número o la referencia del documento")
        return self


class GarantiaGestionar(EsquemaBase):
    estado: EstadoGarantiaT | None = None
    responsable_id: int | None = Field(default=None, gt=0)
    proveedor: TextoOpcional(150)
    fecha_envio_proveedor: date | None = None
    respuesta_proveedor: TextoOpcional(2000)
    fecha_respuesta_proveedor: date | None = None
    solucion: TextoOpcional(2000)
    fecha_solucion: date | None = None
    comentario: TextoOpcional(1000)

    _fechas = field_validator("fecha_envio_proveedor", "fecha_respuesta_proveedor", "fecha_solucion")(_no_futura)

    @model_validator(mode="after")
    def _algo_que_hacer(self):
        if all(v is None for v in self.model_dump().values()):
            raise ValueError("Indica al menos un cambio")
        return self


class GarantiaResumen(BaseModel):
    id: int
    numero: int
    producto: ProductoResumen
    sede: SedeResumen
    cantidad: int
    estado: str
    documento_tipo: str
    documento_referencia: str | None
    fecha_compra: date
    fecha_reporte: date
    proveedor: str | None
    usuario_id: int
    usuario_nombre: str | None = None
    responsable_nombre: str | None = None
    en_garantia: bool | None = None  # None = no se registró la vigencia
    created_at: datetime
    observaciones: int = 0
    adjuntos: int = 0


class GarantiaDetalle(GarantiaResumen):
    defecto: str
    garantia_hasta: date | None
    entrada: EntradaVinculo | None = None
    venta_id: int | None
    venta_numero: int | None = None
    responsable_id: int | None
    fecha_envio_proveedor: date | None
    respuesta_proveedor: str | None
    fecha_respuesta_proveedor: date | None
    solucion: str | None
    fecha_solucion: date | None
    cerrada_en: datetime | None
    historial: list[EventoSalida]
    archivos: list[AdjuntoSalida]
    puede_gestionar: bool = False
    puede_observar: bool = False
    puede_adjuntar: bool = False


class ConteoEstado(BaseModel):
    estado: str
    total: int


class ResumenCalidad(BaseModel):
    no_conformidades: list[ConteoEstado]
    garantias: list[ConteoEstado]
    no_conformidades_abiertas: int
    garantias_abiertas: int
