"""Auditoría de accesos y operaciones (RF-036, RF-037, RNF-028) y llaves de API para agentes."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.model.base import Base, BigIntPK, JSONType, proteger_solo_insercion


class Auditoria(Base):
    """Registro de actividad. Solo se inserta: el esquema de PostgreSQL incluye un disparador
    que rechaza UPDATE y DELETE, de modo que ningún módulo operativo puede alterarlo."""

    __tablename__ = "auditoria"
    __table_args__ = (
        Index("ix_auditoria_empresa_fecha", "empresa_id", "fecha"),
        Index("ix_auditoria_modulo_accion", "modulo", "accion"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int | None] = mapped_column(ForeignKey("empresas.id"), nullable=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True, index=True)
    usuario_email: Mapped[str | None] = mapped_column(String(255), nullable=True)  # copia: sobrevive a cambios
    sede_id: Mapped[int | None] = mapped_column(ForeignKey("sedes.id"), nullable=True)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    modulo: Mapped[str] = mapped_column(String(40), nullable=False)
    accion: Mapped[str] = mapped_column(String(60), nullable=False)
    entidad: Mapped[str | None] = mapped_column(String(60), nullable=True)
    entidad_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    resultado: Mapped[str] = mapped_column(String(10), nullable=False, default="exitoso")
    detalle: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)  # nunca secretos
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(40), nullable=True)


class ApiKey(Base):
    """Llave para que un agente de IA consulte información autorizada de solo lectura (RNF-049)."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    sede_id: Mapped[int | None] = mapped_column(ForeignKey("sedes.id"), nullable=True)  # restringe a una sede
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    prefijo: Mapped[str] = mapped_column(String(12), nullable=False, unique=True)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    alcances: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    creada_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expira_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ultimo_uso_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


proteger_solo_insercion(Auditoria.__table__)
