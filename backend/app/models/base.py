"""Base declarativa, convención de nombres y tipos compartidos por todos los modelos."""

from datetime import datetime

from sqlalchemy import DDL, BigInteger, DateTime, Integer, JSON, MetaData, Table, event, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Nombres estables para índices y restricciones: hacen predecibles las migraciones
# de Alembic (revertir, comparar) y los mensajes de error de la base de datos.
CONVENCION_NOMBRES = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCION_NOMBRES)


# JSON binario en PostgreSQL (consultable e indexable); JSON estándar en SQLite (pruebas).
JSONType = JSON().with_variant(JSONB(), "postgresql")

# BIGINT en PostgreSQL; en SQLite debe ser INTEGER para que la llave primaria autoincremente.
BigIntPK = BigInteger().with_variant(Integer(), "sqlite")


class MarcaTiempo:
    """Fechas de creación y actualización (RF: «fechas de creación y actualización»)."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ---- Tablas de solo inserción (auditoría e historial de movimientos) ------------------------------
# En PostgreSQL un trigger impide UPDATE y DELETE aunque alguien escriba SQL a mano (RNF-007).
# La migración 0003 crea lo mismo en bases existentes; este evento lo crea en bases nuevas (pruebas).
_FUNCION_SOLO_INSERCION = DDL(
    """
    CREATE OR REPLACE FUNCTION inventia_bloquear_modificacion() RETURNS trigger AS $$
    BEGIN
        RAISE EXCEPTION 'La tabla %% es de solo inserción: no admite %% de filas', TG_TABLE_NAME, TG_OP
            USING ERRCODE = 'restrict_violation';
    END;
    $$ LANGUAGE plpgsql
    """
).execute_if(dialect="postgresql")


def proteger_solo_insercion(tabla: Table) -> None:
    event.listen(tabla, "after_create", _FUNCION_SOLO_INSERCION)
    event.listen(
        tabla,
        "after_create",
        DDL(
            f"CREATE TRIGGER tr_{tabla.name}_inmutable BEFORE UPDATE OR DELETE ON {tabla.name} "
            "FOR EACH ROW EXECUTE FUNCTION inventia_bloquear_modificacion()"
        ).execute_if(dialect="postgresql"),
    )
