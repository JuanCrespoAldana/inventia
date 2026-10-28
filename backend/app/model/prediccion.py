"""Predicción de demanda y recomendaciones (RF-025 a RF-030, RNF-029 a RNF-034)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.model.base import Base, BigIntPK, JSONType


class EjecucionPrediccion(Base):
    """Una corrida del módulo predictivo: qué datos usó, qué modelos comparó y cómo le fue."""

    __tablename__ = "ejecuciones_prediccion"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    estado: Mapped[str] = mapped_column(String(15), nullable=False, default="en_cola")
    horizonte_dias: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_corte: Mapped[date | None] = mapped_column(Date, nullable=True)  # último día de ventas usado
    parametros: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    # Resumen: series evaluadas/omitidas, calidad de datos, comparación de modelos, métricas globales.
    resumen: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    iniciada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalizada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Prediccion(Base):
    """Demanda estimada de un producto en una sede para un periodo. Es una ESTIMACIÓN: nunca
    se mezcla con ventas reales (RF-027). Cada fila conserva producto, sede y periodo (RNF-031)."""

    __tablename__ = "predicciones"
    __table_args__ = (
        UniqueConstraint("ejecucion_id", "sede_id", "producto_id", name="uq_predicciones_ejecucion_serie"),
        Index("ix_predicciones_empresa_serie", "empresa_id", "sede_id", "producto_id"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    ejecucion_id: Mapped[int] = mapped_column(
        ForeignKey("ejecuciones_prediccion.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sede_id: Mapped[int] = mapped_column(ForeignKey("sedes.id"), nullable=False)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"), nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date] = mapped_column(Date, nullable=False)
    demanda_estimada: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)  # total del periodo
    limite_inferior: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    limite_superior: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    modelo: Mapped[str] = mapped_column(String(40), nullable=False)
    es_linea_base: Mapped[bool] = mapped_column(nullable=False, default=False)
    confianza: Mapped[str] = mapped_column(String(10), nullable=False, default="media")  # alta | media | baja
    metricas: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)  # MAE, WAPE, base, n_*
    serie_diaria: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)  # [[fecha, valor], ...]
    advertencias: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    generada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Recomendacion(Base):
    """Sugerencia de reabastecimiento o de traslado. NO es una operación: requiere revisión
    humana (RNF-034) antes de convertirse en un traslado o en una compra."""

    __tablename__ = "recomendaciones"
    __table_args__ = (Index("ix_recomendaciones_empresa_estado", "empresa_id", "estado"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    ejecucion_id: Mapped[int | None] = mapped_column(ForeignKey("ejecuciones_prediccion.id"), nullable=True)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"), nullable=False, index=True)
    sede_id: Mapped[int] = mapped_column(ForeignKey("sedes.id"), nullable=False, index=True)  # sede con la necesidad
    sede_origen_id: Mapped[int | None] = mapped_column(ForeignKey("sedes.id"), nullable=True)  # solo traslados
    cantidad_sugerida: Mapped[int] = mapped_column(Integer, nullable=False)
    prioridad: Mapped[str] = mapped_column(String(10), nullable=False)
    estado: Mapped[str] = mapped_column(String(15), nullable=False, default="pendiente")
    resumen: Mapped[str] = mapped_column(String(600), nullable=False)  # explicación legible
    justificacion: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)  # datos que la originan
    generada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revisada_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    revisada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    comentario_revision: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # El traslado resultante se localiza con ``traslados.recomendacion_id`` (un solo sentido evita FK circulares).
