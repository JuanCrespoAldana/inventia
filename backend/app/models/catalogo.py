"""Categorías y productos (RF-011 a RF-014)."""

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Index, Numeric, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, MarcaTiempo


class Categoria(MarcaTiempo, Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(300), nullable=True)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))


Index("uq_categorias_empresa_nombre", Categoria.empresa_id, func.lower(Categoria.nombre), unique=True)


class Producto(MarcaTiempo, Base):
    __tablename__ = "productos"
    # El código es único DENTRO de cada empresa (dos empresas independientes pueden usar el mismo).
    __table_args__ = (UniqueConstraint("empresa_id", "codigo", name="uq_productos_empresa_codigo"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categorias.id"), nullable=False, index=True)
    codigo: Mapped[str] = mapped_column(String(60), nullable=False)  # inmutable: identificación histórica
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    unidad_medida: Mapped[str] = mapped_column(String(20), nullable=False, default="unidad", server_default="unidad")
    # Costo de compra (para valorar el inventario) y precio de venta de referencia son datos distintos.
    costo: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    precio_venta: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
