"""Seguridad y Salud en el Trabajo (SST): pausas activas automáticas."""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, BigIntPK, MarcaTiempo


class SstConfiguracion(MarcaTiempo, Base):
    """Parámetros de las pausas activas de la empresa (una fila por empresa, creada al primer uso)."""

    __tablename__ = "sst_configuracion"
    __table_args__ = (CheckConstraint("intervalo_minutos BETWEEN 1 AND 480", name="intervalo_valido"),)

    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), primary_key=True)
    pausas_activas: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    intervalo_minutos: Mapped[int] = mapped_column(Integer, nullable=False, default=60, server_default=text("60"))
    actualizado_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)


class SstActividad(MarcaTiempo, Base):
    """Ejercicio o recomendación que se muestra en una pausa activa. La administración lo edita."""

    __tablename__ = "sst_actividades"
    __table_args__ = (
        CheckConstraint("duracion_segundos BETWEEN 10 AND 900", name="duracion_valida"),
        Index("ix_sst_actividades_empresa_activa", "empresa_id", "activa"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    titulo: Mapped[str] = mapped_column(String(120), nullable=False)
    area: Mapped[str] = mapped_column(String(20), nullable=False)
    mensaje: Mapped[str] = mapped_column(String(300), nullable=False)  # texto breve y motivador
    instrucciones: Mapped[str] = mapped_column(Text, nullable=False)  # un paso por línea
    duracion_segundos: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    recomendaciones: Mapped[str | None] = mapped_column(Text, nullable=True)  # postura, ojos, manos, sentado
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))


class SstPausa(Base):
    """Registro de cada pausa mostrada a una persona. Una persona nunca tiene más de una pausa abierta
    («mostrada»): el índice único parcial lo garantiza aunque se abran dos pestañas a la vez."""

    __tablename__ = "sst_pausas"
    __table_args__ = (
        Index("ix_sst_pausas_usuario_mostrada", "usuario_id", "mostrada_en"),
        Index("ix_sst_pausas_empresa_mostrada", "empresa_id", "mostrada_en"),
        Index(
            "uq_sst_pausa_abierta",
            "usuario_id",
            unique=True,
            postgresql_where=text("estado = 'mostrada'"),
            sqlite_where=text("estado = 'mostrada'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    actividad_id: Mapped[int | None] = mapped_column(
        ForeignKey("sst_actividades.id", ondelete="SET NULL"), nullable=True
    )
    actividad_titulo: Mapped[str] = mapped_column(String(120), nullable=False)  # copia: sobrevive si se elimina
    mostrada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="mostrada")
    cerrada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duracion_segundos: Mapped[int | None] = mapped_column(Integer, nullable=True)  # lo que tardó en realizarla


__all__ = ["SstConfiguracion", "SstActividad", "SstPausa"]
