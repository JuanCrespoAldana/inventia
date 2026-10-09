from sqlalchemy import Boolean, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, MarcaTiempo


class Sede(MarcaTiempo, Base):
    __tablename__ = "sedes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    direccion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ciudad: Mapped[str | None] = mapped_column(String(150), nullable=True)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))


# Una sede no puede repetirse dentro de la misma empresa (RF-008), sin distinguir mayúsculas.
Index("uq_sedes_empresa_nombre", Sede.empresa_id, func.lower(Sede.nombre), unique=True)
