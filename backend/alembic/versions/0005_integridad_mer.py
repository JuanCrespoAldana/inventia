"""Integridad del modelo entidad-relación (CRF-MER-01).

Revision ID: 0005_integridad_mer
Revises: 0004_sig

Tres reglas que el modelo exigía y la base de datos no garantizaba por sí sola (observaciones 1, 4 y 5 del MER):

* RGN-13: ``alertas`` pasa de dos llaves foráneas simples (sedes y productos) a UNA llave compuesta
  ``(sede_id, producto_id)`` hacia ``inventario_sede``. Una alerta pertenece a una existencia por sede.
* RGN-23: ``traslados.recomendacion_id`` es único. Una recomendación da lugar a lo sumo a un traslado.
* RGN-21: ``recomendaciones.ejecucion_id`` es obligatorio. Toda recomendación nace de una ejecución de predicción.

No borra datos de negocio. Las alertas sin fila de existencia son datos derivados (el servicio las recalcula) y se
descartan; si hay recomendaciones con más de un traslado o sin ejecución, la migración se DETIENE con un mensaje
claro y no modifica nada, porque corregirlas exige una decisión de una persona.

Reversible: ``downgrade`` restablece las llaves y restricciones anteriores.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0005_integridad_mer'
down_revision: Union[str, Sequence[str], None] = '0004_sig'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _verificar_datos_existentes() -> None:
    """Detiene la migración, antes de tocar nada, si los datos impiden aplicar las restricciones."""
    conexion = op.get_bind()
    repetidas = conexion.execute(sa.text(
        "SELECT recomendacion_id, count(*) FROM traslados WHERE recomendacion_id IS NOT NULL "
        "GROUP BY recomendacion_id HAVING count(*) > 1 ORDER BY recomendacion_id"
    )).all()
    if repetidas:
        detalle = ", ".join(f"#{r[0]} ({r[1]} traslados)" for r in repetidas[:10])
        raise RuntimeError(
            "No se puede aplicar la restricción de unicidad de traslados.recomendacion_id: hay recomendaciones con "
            f"más de un traslado: {detalle}. Corrígelas (deja un solo traslado por recomendación) y vuelve a "
            "ejecutar la migración."
        )
    sin_ejecucion = conexion.execute(sa.text("SELECT count(*) FROM recomendaciones WHERE ejecucion_id IS NULL")).scalar()
    if sin_ejecucion:
        raise RuntimeError(
            f"No se puede exigir recomendaciones.ejecucion_id: hay {sin_ejecucion} recomendaciones sin ejecución de "
            "predicción. Asígnales su ejecución o elimínalas y vuelve a ejecutar la migración."
        )


def upgrade() -> None:
    _verificar_datos_existentes()
    # Datos derivados: una alerta sin fila de existencia no tiene a qué pertenecer; el servicio la recalcula.
    op.execute(
        "DELETE FROM alertas a WHERE NOT EXISTS ("
        "SELECT 1 FROM inventario_sede i WHERE i.sede_id = a.sede_id AND i.producto_id = a.producto_id)"
    )
    op.drop_constraint(op.f('fk_alertas_sede_id_sedes'), 'alertas', type_='foreignkey')
    op.drop_constraint(op.f('fk_alertas_producto_id_productos'), 'alertas', type_='foreignkey')
    op.create_foreign_key(
        op.f('fk_alertas_sede_id_inventario_sede'), 'alertas', 'inventario_sede',
        ['sede_id', 'producto_id'], ['sede_id', 'producto_id'],
    )
    op.create_unique_constraint('uq_traslados_recomendacion_id', 'traslados', ['recomendacion_id'])
    op.alter_column('recomendaciones', 'ejecucion_id', existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    op.alter_column('recomendaciones', 'ejecucion_id', existing_type=sa.Integer(), nullable=True)
    op.drop_constraint('uq_traslados_recomendacion_id', 'traslados', type_='unique')
    op.drop_constraint(op.f('fk_alertas_sede_id_inventario_sede'), 'alertas', type_='foreignkey')
    op.create_foreign_key(op.f('fk_alertas_sede_id_sedes'), 'alertas', 'sedes', ['sede_id'], ['id'])
    op.create_foreign_key(op.f('fk_alertas_producto_id_productos'), 'alertas', 'productos', ['producto_id'], ['id'])
