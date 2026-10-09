"""Ventas y traslados entre sedes (RF-020 a RF-023)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, MarcaTiempo


class VentaItem(Base):
    __tablename__ = "venta_items"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="cantidad_positiva"),
        CheckConstraint("precio_unitario >= 0", name="precio_no_negativo"),
        UniqueConstraint("venta_id", "producto_id", name="uq_venta_items_venta_producto"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas.id", ondelete="CASCADE"), nullable=False, index=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"), nullable=False, index=True)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)


class Venta(MarcaTiempo, Base):
    """Cabecera de venta. Una venta anulada se conserva (estado «anulada») y devuelve las
    existencias con movimientos compensatorios: el historial nunca se altera."""

    __tablename__ = "ventas"
    __table_args__ = (
        UniqueConstraint("empresa_id", "numero", name="uq_ventas_empresa_numero"),
        Index("ix_ventas_empresa_fecha_dia", "empresa_id", "fecha_dia"),
        Index("ix_ventas_sede_fecha_dia", "sede_id", "fecha_dia"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    sede_id: Mapped[int] = mapped_column(ForeignKey("sedes.id"), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_dia: Mapped[date] = mapped_column(Date, nullable=False)  # día local, para agrupar y predecir
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    estado: Mapped[str] = mapped_column(String(15), nullable=False, default="registrada", server_default="registrada")
    observacion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    anulada_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    anulada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_anulacion: Mapped[str | None] = mapped_column(String(500), nullable=True)

    items: Mapped[list[VentaItem]] = relationship(VentaItem, lazy="selectin", order_by=VentaItem.id)


class TrasladoItem(Base):
    __tablename__ = "traslado_items"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="cantidad_positiva"),
        UniqueConstraint("traslado_id", "producto_id", name="uq_traslado_items_traslado_producto"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    traslado_id: Mapped[int] = mapped_column(
        ForeignKey("traslados.id", ondelete="CASCADE"), nullable=False, index=True
    )
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"), nullable=False, index=True)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)


class Traslado(MarcaTiempo, Base):
    """Traslado de productos entre dos sedes de la misma empresa.

    Flujo: solicitado → aprobado → confirmado (o rechazado / cancelado). Las existencias solo
    cambian al CONFIRMAR, en una única transacción que descuenta del origen y suma al destino.
    """

    __tablename__ = "traslados"
    __table_args__ = (
        UniqueConstraint("empresa_id", "numero", name="uq_traslados_empresa_numero"),
        CheckConstraint("sede_origen_id <> sede_destino_id", name="sedes_distintas"),
        Index("ix_traslados_empresa_estado", "empresa_id", "estado"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    sede_origen_id: Mapped[int] = mapped_column(ForeignKey("sedes.id"), nullable=False, index=True)
    sede_destino_id: Mapped[int] = mapped_column(ForeignKey("sedes.id"), nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String(15), nullable=False, default="solicitado")
    observacion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    recomendacion_id: Mapped[int | None] = mapped_column(ForeignKey("recomendaciones.id"), nullable=True)

    solicitado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    solicitado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    aprobado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    aprobado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    confirmado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cerrado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)  # rechazo/cancelación
    cerrado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_cierre: Mapped[str | None] = mapped_column(String(500), nullable=True)

    items: Mapped[list[TrasladoItem]] = relationship(TrasladoItem, lazy="selectin", order_by=TrasladoItem.id)


__all__ = ["Venta", "VentaItem", "Traslado", "TrasladoItem"]
