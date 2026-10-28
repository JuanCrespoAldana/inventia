"""Peticiones, quejas, reclamos y sugerencias (PQRS) del Sistema Integrado de Gestión."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.model.base import Base, BigIntPK, MarcaTiempo, proteger_solo_insercion


class Pqrs(MarcaTiempo, Base):
    """Solicitud de una persona usuaria. La conserva siempre: se gestiona cambiando su estado, no borrándola."""

    __tablename__ = "pqrs"
    __table_args__ = (
        UniqueConstraint("empresa_id", "numero", name="uq_pqrs_empresa_numero"),
        Index("ix_pqrs_empresa_estado", "empresa_id", "estado"),
        Index("ix_pqrs_empresa_created", "empresa_id", "created_at"),
        Index("ix_pqrs_usuario_created", "usuario_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)  # radicado consecutivo por empresa
    tipo: Mapped[str] = mapped_column(String(15), nullable=False)
    asunto: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    estado: Mapped[str] = mapped_column(String(15), nullable=False, default="pendiente", server_default="pendiente")
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    sede_id: Mapped[int | None] = mapped_column(ForeignKey("sedes.id"), nullable=True)  # sede de quien la envía
    # Última respuesta administrativa (el detalle completo vive en el historial).
    respuesta: Mapped[str | None] = mapped_column(Text, nullable=True)
    respondida_por: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    respondida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PqrsHistorial(Base):
    """Línea de tiempo de una PQRS: creación, cambios de estado y respuestas. Solo se inserta."""

    __tablename__ = "pqrs_historial"
    __table_args__ = (Index("ix_pqrs_historial_pqrs_fecha", "pqrs_id", "fecha"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    pqrs_id: Mapped[int] = mapped_column(ForeignKey("pqrs.id"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    evento: Mapped[str] = mapped_column(String(15), nullable=False)  # creacion | estado | respuesta
    estado_anterior: Mapped[str | None] = mapped_column(String(15), nullable=True)
    estado_nuevo: Mapped[str | None] = mapped_column(String(15), nullable=True)
    comentario: Mapped[str | None] = mapped_column(Text, nullable=True)


proteger_solo_insercion(PqrsHistorial.__table__)

__all__ = ["Pqrs", "PqrsHistorial"]
