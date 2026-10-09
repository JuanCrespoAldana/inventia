"""Archivos adjuntos (evidencias) de PQRS, no conformidades y garantías.

Se guardan en la base de datos (no en el disco del servidor) para que viajen con las copias de seguridad y
funcionen igual en cualquier despliegue. La API solo acepta imágenes y PDF de tamaño limitado y verifica el
contenido real del archivo, no solo su extensión."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, LargeBinary, String, func
from sqlalchemy.orm import Mapped, deferred, mapped_column

from app.models.base import Base


class Adjunto(Base):
    __tablename__ = "sig_adjuntos"
    __table_args__ = (
        # Cada archivo pertenece a exactamente un registro (integridad referencial real, sin referencias sueltas).
        CheckConstraint(
            "(CASE WHEN pqrs_id IS NULL THEN 0 ELSE 1 END) + (CASE WHEN no_conformidad_id IS NULL THEN 0 ELSE 1 END)"
            " + (CASE WHEN garantia_id IS NULL THEN 0 ELSE 1 END) = 1",
            name="un_solo_destino",
        ),
        CheckConstraint("tamano > 0", name="tamano_positivo"),
        Index("ix_sig_adjuntos_pqrs", "pqrs_id"),
        Index("ix_sig_adjuntos_no_conformidad", "no_conformidad_id"),
        Index("ix_sig_adjuntos_garantia", "garantia_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    pqrs_id: Mapped[int | None] = mapped_column(ForeignKey("pqrs.id"), nullable=True)
    no_conformidad_id: Mapped[int | None] = mapped_column(ForeignKey("no_conformidades.id"), nullable=True)
    garantia_id: Mapped[int | None] = mapped_column(ForeignKey("garantias.id"), nullable=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo_mime: Mapped[str] = mapped_column(String(60), nullable=False)
    tamano: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    contenido: Mapped[bytes] = deferred(mapped_column(LargeBinary, nullable=False))
    subido_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


__all__ = ["Adjunto"]
