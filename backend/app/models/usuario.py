from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.acceso import Rol
from app.models.base import Base, MarcaTiempo


class Usuario(MarcaTiempo, Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False, index=True)
    sede_id: Mapped[int | None] = mapped_column(ForeignKey("sedes.id"), nullable=True, index=True)

    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

    # Contraseña temporal asignada por un administrador: obliga a cambiarla en el primer ingreso.
    debe_cambiar_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    # Se incrementa en cada cambio de contraseña; invalida los tokens emitidos antes.
    password_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))

    # Control de intentos fallidos (RNF-026)
    intentos_fallidos: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ultimo_acceso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    rol: Mapped[Rol] = relationship(Rol, lazy="joined")
