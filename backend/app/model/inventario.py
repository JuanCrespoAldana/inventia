"""Existencias por sede y su historial de movimientos (RF-015 a RF-019, RF-024)."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.model.base import Base, BigIntPK, JSONType, MarcaTiempo, proteger_solo_insercion


class InventarioSede(MarcaTiempo, Base):
    """Cantidad disponible de un producto en una sede. Es la ÚNICA fuente de existencias:
    el inventario consolidado se calcula siempre sumando estas filas (RNF-019)."""

    __tablename__ = "inventario_sede"
    __table_args__ = (
        UniqueConstraint("sede_id", "producto_id", name="uq_sede_producto"),
        CheckConstraint("cantidad >= 0", name="cantidad_no_negativa"),
        CheckConstraint("stock_minimo >= 0", name="stock_minimo_no_negativo"),
        CheckConstraint(
            "stock_maximo IS NULL OR stock_maximo >= stock_minimo", name="stock_maximo_mayor_o_igual_minimo"
        ),
        Index("ix_inventario_sede_producto", "sede_id", "producto_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False, index=True)
    sede_id: Mapped[int] = mapped_column(ForeignKey("sedes.id"), nullable=False)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"), nullable=False, index=True)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    stock_minimo: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    stock_maximo: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Movimiento(Base):
    """Registro inmutable de cada cambio de existencias. Nunca se actualiza ni se elimina:
    los errores se corrigen con un ajuste o una operación compensatoria (RNF-007, RF-024)."""

    __tablename__ = "movimientos"
    __table_args__ = (
        CheckConstraint("delta <> 0", name="delta_distinto_de_cero"),
        CheckConstraint("saldo_posterior >= 0", name="saldo_posterior_no_negativo"),
        Index("ix_movimientos_empresa_fecha", "empresa_id", "fecha"),
        Index("ix_movimientos_sede_producto_fecha", "sede_id", "producto_id", "fecha"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    sede_id: Mapped[int] = mapped_column(ForeignKey("sedes.id"), nullable=False)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    motivo: Mapped[str | None] = mapped_column(String(40), nullable=True)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)  # + entra, − sale
    saldo_anterior: Mapped[int] = mapped_column(Integer, nullable=False)
    saldo_posterior: Mapped[int] = mapped_column(Integer, nullable=False)
    # En traslados: la otra sede involucrada (origen o destino).
    sede_contraparte_id: Mapped[int | None] = mapped_column(ForeignKey("sedes.id"), nullable=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observacion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    venta_id: Mapped[int | None] = mapped_column(ForeignKey("ventas.id"), nullable=True, index=True)
    traslado_id: Mapped[int | None] = mapped_column(ForeignKey("traslados.id"), nullable=True, index=True)
    # Entradas registradas desde la versión 1.1: agrupa las líneas de una misma recepción de mercancía.
    entrada_id: Mapped[int | None] = mapped_column(ForeignKey("entradas_inventario.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EntradaInventario(Base):
    """Cabecera de una entrada de mercancía (recepción). Agrupa los movimientos de sus líneas y es el punto
    al que se asocian las observaciones de la recepción y, si hay un problema, las no conformidades.
    No modifica existencias por sí misma: eso sigue haciéndolo únicamente ``Movimiento``."""

    __tablename__ = "entradas_inventario"
    __table_args__ = (
        UniqueConstraint("empresa_id", "numero", name="uq_entradas_inventario_empresa_numero"),
        Index("ix_entradas_inventario_empresa_fecha", "empresa_id", "fecha"),
        Index("ix_entradas_inventario_sede_fecha", "sede_id", "fecha"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    sede_id: Mapped[int] = mapped_column(ForeignKey("sedes.id"), nullable=False)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    motivo: Mapped[str] = mapped_column(String(40), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EntradaObservacion(Base):
    """Observación de una entrada (estado de la mercancía, empaque, novedades con el proveedor...).

    Es independiente de los datos del producto y se acumula: agregar una observación nueva NUNCA reemplaza las
    anteriores. Solo se inserta (en PostgreSQL un disparador impide UPDATE y DELETE)."""

    __tablename__ = "entrada_observaciones"
    __table_args__ = (Index("ix_entrada_observaciones_entrada_fecha", "entrada_id", "fecha"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    entrada_id: Mapped[int] = mapped_column(ForeignKey("entradas_inventario.id"), nullable=False)
    producto_id: Mapped[int | None] = mapped_column(ForeignKey("productos.id"), nullable=True)  # línea concreta
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    contenido: Mapped[str] = mapped_column(Text, nullable=False)


class Secuencia(Base):
    """Consecutivos por empresa (número de venta, de traslado) sin huecos ni duplicados concurrentes."""

    __tablename__ = "secuencias"

    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(30), primary_key=True)
    valor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Alerta(Base):
    """Alerta de inventario. Se abre y se resuelve automáticamente al cambiar las existencias."""

    __tablename__ = "alertas"
    __table_args__ = (
        Index("ix_alertas_empresa_estado", "empresa_id", "estado"),
        # Solo puede haber UNA alerta activa por sede-producto-tipo (evita duplicados concurrentes).
        Index(
            "uq_alertas_activa",
            "sede_id",
            "producto_id",
            "tipo",
            unique=True,
            postgresql_where=text("estado = 'activa'"),
            sqlite_where=text("estado = 'activa'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id"), nullable=False)
    sede_id: Mapped[int] = mapped_column(ForeignKey("sedes.id"), nullable=False)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    prioridad: Mapped[str] = mapped_column(String(10), nullable=False)
    estado: Mapped[str] = mapped_column(String(10), nullable=False, default="activa")
    mensaje: Mapped[str] = mapped_column(String(300), nullable=False)
    detalle: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    abierta_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resuelta_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


proteger_solo_insercion(Movimiento.__table__)
proteger_solo_insercion(EntradaObservacion.__table__)

__all__ = ["InventarioSede", "Movimiento", "EntradaInventario", "EntradaObservacion", "Secuencia", "Alerta"]
