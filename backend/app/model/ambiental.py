"""Gestión ambiental: contribución estimada de la venta de vehículos eléctricos.

Dos cifras que nunca se mezclan:
  * REAL: unidades de vehículo vendidas (ventas confirmadas, no anuladas) de categorías marcadas como vehículo.
  * ESTIMADA: CO₂ evitado, calculado con parámetros documentados y editables por la administración. Si faltan
    parámetros, el registro queda «sin parametrizar» y solo cuenta como unidades vendidas.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.model.base import Base, BigIntPK, JSONType, MarcaTiempo


class AmbConfiguracion(MarcaTiempo, Base):
    """Parámetros comunes de la empresa: factor de emisión de la red eléctrica."""

    __tablename__ = "amb_configuracion"

    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), primary_key=True)
    factor_red_kgco2_kwh: Mapped[Decimal | None] = mapped_column(Numeric(10, 5), nullable=True)
    factor_red_anio: Mapped[int | None] = mapped_column(Integer, nullable=True)
    factor_red_fuente: Mapped[str | None] = mapped_column(String(500), nullable=True)
    actualizado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)


class AmbCategoria(MarcaTiempo, Base):
    """Marca una categoría del catálogo como «vehículo» y guarda los parámetros de su estimación."""

    __tablename__ = "amb_categorias"
    __table_args__ = (
        UniqueConstraint("categoria_id", name="uq_amb_categorias_categoria_id"),
        CheckConstraint("horizonte_anios BETWEEN 1 AND 30", name="horizonte_valido"),
        CheckConstraint("distancia_anual_km IS NULL OR distancia_anual_km > 0", name="distancia_positiva"),
        CheckConstraint("consumo_kwh_100km IS NULL OR consumo_kwh_100km >= 0", name="consumo_no_negativo"),
        CheckConstraint("emision_referencia_gco2_km IS NULL OR emision_referencia_gco2_km >= 0", name="emision_no_negativa"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categorias.id"), nullable=False)
    tipo_vehiculo: Mapped[str] = mapped_column(String(30), nullable=False)
    propulsion: Mapped[str] = mapped_column(String(30), nullable=False)
    distancia_anual_km: Mapped[Decimal | None] = mapped_column(Numeric(10, 1), nullable=True)
    consumo_kwh_100km: Mapped[Decimal | None] = mapped_column(Numeric(8, 3), nullable=True)
    vehiculo_referencia: Mapped[str | None] = mapped_column(String(200), nullable=True)
    emision_referencia_gco2_km: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    horizonte_anios: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    fuente: Mapped[str | None] = mapped_column(String(500), nullable=True)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    actualizado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)


class AmbRegistro(Base):
    """Una línea de venta de vehículos contabilizada. Un mismo ``venta_item_id`` solo puede contarse una vez.

    Al anular la venta el registro pasa a «anulado» (no se borra) y deja de sumar. Los parámetros usados se
    guardan en ``parametros``: cambiar la configuración después NO altera lo ya calculado."""

    __tablename__ = "amb_registros"
    __table_args__ = (
        UniqueConstraint("venta_item_id", name="uq_amb_registros_venta_item_id"),
        CheckConstraint("unidades > 0", name="unidades_positivas"),
        Index("ix_amb_registros_empresa_estado_fecha", "empresa_id", "estado", "fecha"),
        Index("ix_amb_registros_venta", "venta_id"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    venta_id: Mapped[int] = mapped_column(ForeignKey("ventas.id"), nullable=False)
    venta_item_id: Mapped[int] = mapped_column(ForeignKey("venta_items.id"), nullable=False)
    sede_id: Mapped[int] = mapped_column(ForeignKey("sedes.id"), nullable=False)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"), nullable=False)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categorias.id"), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)  # día local de la venta
    unidades: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo_vehiculo: Mapped[str] = mapped_column(String(30), nullable=False)
    propulsion: Mapped[str] = mapped_column(String(30), nullable=False)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="activo", server_default="activo")
    anulado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    co2_evitado_kg: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)  # NULL = sin parametrizar
    parametros: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    calculado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


__all__ = ["AmbConfiguracion", "AmbCategoria", "AmbRegistro"]
