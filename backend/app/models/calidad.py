"""Calidad: no conformidades y garantías (Sistema Integrado de Gestión).

Registrar una no conformidad o una garantía NO modifica existencias: son registros de seguimiento. Cualquier
ajuste de inventario derivado de ellas se hace aparte, con las operaciones normales de inventario."""

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BigIntPK, MarcaTiempo, proteger_solo_insercion


class NoConformidad(MarcaTiempo, Base):
    __tablename__ = "no_conformidades"
    __table_args__ = (
        UniqueConstraint("empresa_id", "numero", name="uq_no_conformidades_empresa_numero"),
        CheckConstraint("cantidad_afectada > 0", name="cantidad_positiva"),
        Index("ix_no_conformidades_empresa_estado", "empresa_id", "estado"),
        Index("ix_no_conformidades_sede_fecha", "sede_id", "fecha_deteccion"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    sede_id: Mapped[int] = mapped_column(ForeignKey("sedes.id"), nullable=False)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"), nullable=False, index=True)
    referencia: Mapped[str | None] = mapped_column(String(100), nullable=True)  # lote, serie o referencia del proveedor
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_deteccion: Mapped[date] = mapped_column(Date, nullable=False)
    cantidad_afectada: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[str] = mapped_column(String(25), nullable=False, default="reportado", server_default="reportado")
    proveedor: Mapped[str | None] = mapped_column(String(150), nullable=True)
    # Origen: la entrada de inventario (y, si aplica, la observación) donde se detectó el problema.
    entrada_id: Mapped[int | None] = mapped_column(ForeignKey("entradas_inventario.id"), nullable=True, index=True)
    entrada_observacion_id: Mapped[int | None] = mapped_column(ForeignKey("entrada_observaciones.id"), nullable=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)  # quien la reporta
    responsable_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    solucion: Mapped[str | None] = mapped_column(Text, nullable=True)
    resuelta_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cerrada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NoConformidadHistorial(Base):
    """Observaciones y cambios de estado de una no conformidad, en orden. Solo se inserta."""

    __tablename__ = "no_conformidad_historial"
    __table_args__ = (Index("ix_no_conformidad_historial_nc_fecha", "no_conformidad_id", "fecha"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    no_conformidad_id: Mapped[int] = mapped_column(ForeignKey("no_conformidades.id"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    evento: Mapped[str] = mapped_column(String(15), nullable=False)  # creacion | estado | observacion | gestion
    estado_anterior: Mapped[str | None] = mapped_column(String(25), nullable=True)
    estado_nuevo: Mapped[str | None] = mapped_column(String(25), nullable=True)
    contenido: Mapped[str | None] = mapped_column(Text, nullable=True)


class Garantia(MarcaTiempo, Base):
    __tablename__ = "garantias"
    __table_args__ = (
        UniqueConstraint("empresa_id", "numero", name="uq_garantias_empresa_numero"),
        CheckConstraint("cantidad > 0", name="cantidad_positiva"),
        Index("ix_garantias_empresa_estado", "empresa_id", "estado"),
        Index("ix_garantias_sede_reporte", "sede_id", "fecha_reporte"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    sede_id: Mapped[int] = mapped_column(ForeignKey("sedes.id"), nullable=False)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"), nullable=False, index=True)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Documento que respalda la garantía: factura de compra, entrada de inventario, venta u otro.
    documento_tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    documento_referencia: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entrada_id: Mapped[int | None] = mapped_column(ForeignKey("entradas_inventario.id"), nullable=True, index=True)
    venta_id: Mapped[int | None] = mapped_column(ForeignKey("ventas.id"), nullable=True, index=True)
    fecha_compra: Mapped[date] = mapped_column(Date, nullable=False)  # fecha de compra o de recepción
    garantia_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)  # vigencia, si se conoce
    fecha_reporte: Mapped[date] = mapped_column(Date, nullable=False)
    defecto: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[str] = mapped_column(String(25), nullable=False, default="reportada", server_default="reportada")
    proveedor: Mapped[str | None] = mapped_column(String(150), nullable=True)
    fecha_envio_proveedor: Mapped[date | None] = mapped_column(Date, nullable=True)
    respuesta_proveedor: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_respuesta_proveedor: Mapped[date | None] = mapped_column(Date, nullable=True)
    solucion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_solucion: Mapped[date | None] = mapped_column(Date, nullable=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    responsable_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    cerrada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GarantiaHistorial(Base):
    """Observaciones y cambios de estado de una garantía, en orden. Solo se inserta."""

    __tablename__ = "garantia_historial"
    __table_args__ = (Index("ix_garantia_historial_garantia_fecha", "garantia_id", "fecha"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    garantia_id: Mapped[int] = mapped_column(ForeignKey("garantias.id"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    evento: Mapped[str] = mapped_column(String(15), nullable=False)  # creacion | estado | observacion | gestion
    estado_anterior: Mapped[str | None] = mapped_column(String(25), nullable=True)
    estado_nuevo: Mapped[str | None] = mapped_column(String(25), nullable=True)
    contenido: Mapped[str | None] = mapped_column(Text, nullable=True)


proteger_solo_insercion(NoConformidadHistorial.__table__)
proteger_solo_insercion(GarantiaHistorial.__table__)

__all__ = ["NoConformidad", "NoConformidadHistorial", "Garantia", "GarantiaHistorial"]
