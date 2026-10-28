"""Permisos, roles y su relación (RF-038, RU-003)."""

from sqlalchemy import Boolean, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.model.base import Base, MarcaTiempo


class Permiso(Base):
    """Catálogo global de permisos. Se define en código (app/security/permisos.py) y se sincroniza."""

    __tablename__ = "permisos"

    codigo: Mapped[str] = mapped_column(String(80), primary_key=True)
    modulo: Mapped[str] = mapped_column(String(50), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(200), nullable=False)


class RolPermiso(Base):
    __tablename__ = "rol_permisos"

    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permiso_codigo: Mapped[str] = mapped_column(ForeignKey("permisos.codigo", ondelete="CASCADE"), primary_key=True)


class Rol(MarcaTiempo, Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    # Identificador estable de los roles del sistema (admin, gerente, ...). NULL en roles personalizados.
    clave: Mapped[str | None] = mapped_column(String(40), nullable=True)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # "empresa": ve todas las sedes. "sede": queda restringido a la sede asignada (RNF-024).
    alcance: Mapped[str] = mapped_column(String(10), nullable=False, default="empresa", server_default="empresa")
    es_sistema: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

    permisos: Mapped[list[RolPermiso]] = relationship(
        RolPermiso, cascade="all, delete-orphan", lazy="selectin", passive_deletes=True
    )

    @property
    def codigos_permisos(self) -> set[str]:
        return {p.permiso_codigo for p in self.permisos}


Index("uq_roles_empresa_nombre", Rol.empresa_id, func.lower(Rol.nombre), unique=True)
Index("uq_roles_empresa_clave", Rol.empresa_id, Rol.clave, unique=True)
