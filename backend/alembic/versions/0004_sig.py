"""Sistema Integrado de Gestión (SIG): PQRS, SST, calidad, gestión ambiental y entradas de inventario.

Revision ID: 0004_sig
Revises: 0003_inventia

Solo AÑADE estructuras; no modifica ni borra datos existentes:

* ``entradas_inventario`` / ``entrada_observaciones``: cabecera de cada entrada de mercancía y sus observaciones
  (se acumulan, no se reemplazan). ``movimientos.entrada_id`` enlaza cada línea con su entrada; las entradas
  anteriores a esta versión quedan con ``entrada_id`` nulo y conservan su observación en el movimiento.
* ``pqrs`` / ``pqrs_historial``, ``sst_*``, ``no_conformidades`` / ``garantias`` (+ historiales), ``amb_*`` y
  ``sig_adjuntos`` (evidencias).
* Los historiales y las observaciones de entrada son de solo inserción (disparador de PostgreSQL).

Los permisos nuevos (pqrs.*, sst.*, calidad.*, ambiental.*) los sincroniza la API al iniciar
(``sincronizar_permisos``), igual que los permisos anteriores.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0004_sig'
down_revision: Union[str, Sequence[str], None] = '0003_inventia'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_SOLO_INSERCION = ("pqrs_historial", "no_conformidad_historial", "garantia_historial", "entrada_observaciones")


def upgrade() -> None:
    """Crea las tablas del SIG."""
    op.create_table('sst_actividades',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('titulo', sa.String(length=120), nullable=False),
    sa.Column('area', sa.String(length=20), nullable=False),
    sa.Column('mensaje', sa.String(length=300), nullable=False),
    sa.Column('instrucciones', sa.Text(), nullable=False),
    sa.Column('duracion_segundos', sa.Integer(), nullable=False),
    sa.Column('recomendaciones', sa.Text(), nullable=True),
    sa.Column('orden', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('activa', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('duracion_segundos BETWEEN 10 AND 900', name=op.f('ck_sst_actividades_duracion_valida')),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_sst_actividades_empresa_id_empresas')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sst_actividades'))
    )
    op.create_index('ix_sst_actividades_empresa_activa', 'sst_actividades', ['empresa_id', 'activa'], unique=False)
    op.create_table('amb_categorias',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('categoria_id', sa.Integer(), nullable=False),
    sa.Column('tipo_vehiculo', sa.String(length=30), nullable=False),
    sa.Column('propulsion', sa.String(length=30), nullable=False),
    sa.Column('distancia_anual_km', sa.Numeric(precision=10, scale=1), nullable=True),
    sa.Column('consumo_kwh_100km', sa.Numeric(precision=8, scale=3), nullable=True),
    sa.Column('vehiculo_referencia', sa.String(length=200), nullable=True),
    sa.Column('emision_referencia_gco2_km', sa.Numeric(precision=8, scale=2), nullable=True),
    sa.Column('horizonte_anios', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('fuente', sa.String(length=500), nullable=True),
    sa.Column('activa', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('actualizado_por', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('consumo_kwh_100km IS NULL OR consumo_kwh_100km >= 0', name=op.f('ck_amb_categorias_consumo_no_negativo')),
    sa.CheckConstraint('distancia_anual_km IS NULL OR distancia_anual_km > 0', name=op.f('ck_amb_categorias_distancia_positiva')),
    sa.CheckConstraint('emision_referencia_gco2_km IS NULL OR emision_referencia_gco2_km >= 0', name=op.f('ck_amb_categorias_emision_no_negativa')),
    sa.CheckConstraint('horizonte_anios BETWEEN 1 AND 30', name=op.f('ck_amb_categorias_horizonte_valido')),
    sa.ForeignKeyConstraint(['actualizado_por'], ['usuarios.id'], name=op.f('fk_amb_categorias_actualizado_por_usuarios')),
    sa.ForeignKeyConstraint(['categoria_id'], ['categorias.id'], name=op.f('fk_amb_categorias_categoria_id_categorias')),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_amb_categorias_empresa_id_empresas')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_amb_categorias')),
    sa.UniqueConstraint('categoria_id', name='uq_amb_categorias_categoria_id')
    )
    op.create_index(op.f('ix_amb_categorias_empresa_id'), 'amb_categorias', ['empresa_id'], unique=False)
    op.create_table('amb_configuracion',
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('factor_red_kgco2_kwh', sa.Numeric(precision=10, scale=5), nullable=True),
    sa.Column('factor_red_anio', sa.Integer(), nullable=True),
    sa.Column('factor_red_fuente', sa.String(length=500), nullable=True),
    sa.Column('actualizado_por', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['actualizado_por'], ['usuarios.id'], name=op.f('fk_amb_configuracion_actualizado_por_usuarios')),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_amb_configuracion_empresa_id_empresas')),
    sa.PrimaryKeyConstraint('empresa_id', name=op.f('pk_amb_configuracion'))
    )
    op.create_table('entradas_inventario',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('sede_id', sa.Integer(), nullable=False),
    sa.Column('numero', sa.Integer(), nullable=False),
    sa.Column('motivo', sa.String(length=40), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('fecha', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_entradas_inventario_empresa_id_empresas')),
    sa.ForeignKeyConstraint(['sede_id'], ['sedes.id'], name=op.f('fk_entradas_inventario_sede_id_sedes')),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_entradas_inventario_usuario_id_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_entradas_inventario')),
    sa.UniqueConstraint('empresa_id', 'numero', name='uq_entradas_inventario_empresa_numero')
    )
    op.create_index('ix_entradas_inventario_empresa_fecha', 'entradas_inventario', ['empresa_id', 'fecha'], unique=False)
    op.create_index('ix_entradas_inventario_sede_fecha', 'entradas_inventario', ['sede_id', 'fecha'], unique=False)
    op.create_table('pqrs',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('numero', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.String(length=15), nullable=False),
    sa.Column('asunto', sa.String(length=200), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=False),
    sa.Column('estado', sa.String(length=15), server_default='pendiente', nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('sede_id', sa.Integer(), nullable=True),
    sa.Column('respuesta', sa.Text(), nullable=True),
    sa.Column('respondida_por', sa.Integer(), nullable=True),
    sa.Column('respondida_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_pqrs_empresa_id_empresas')),
    sa.ForeignKeyConstraint(['respondida_por'], ['usuarios.id'], name=op.f('fk_pqrs_respondida_por_usuarios')),
    sa.ForeignKeyConstraint(['sede_id'], ['sedes.id'], name=op.f('fk_pqrs_sede_id_sedes')),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_pqrs_usuario_id_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_pqrs')),
    sa.UniqueConstraint('empresa_id', 'numero', name='uq_pqrs_empresa_numero')
    )
    op.create_index('ix_pqrs_empresa_created', 'pqrs', ['empresa_id', 'created_at'], unique=False)
    op.create_index('ix_pqrs_empresa_estado', 'pqrs', ['empresa_id', 'estado'], unique=False)
    op.create_index('ix_pqrs_usuario_created', 'pqrs', ['usuario_id', 'created_at'], unique=False)
    op.create_table('sst_configuracion',
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('pausas_activas', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('intervalo_minutos', sa.Integer(), server_default=sa.text('60'), nullable=False),
    sa.Column('actualizado_por', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('intervalo_minutos BETWEEN 1 AND 480', name=op.f('ck_sst_configuracion_intervalo_valido')),
    sa.ForeignKeyConstraint(['actualizado_por'], ['usuarios.id'], name=op.f('fk_sst_configuracion_actualizado_por_usuarios')),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_sst_configuracion_empresa_id_empresas')),
    sa.PrimaryKeyConstraint('empresa_id', name=op.f('pk_sst_configuracion'))
    )
    op.create_table('sst_pausas',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('actividad_id', sa.Integer(), nullable=True),
    sa.Column('actividad_titulo', sa.String(length=120), nullable=False),
    sa.Column('mostrada_en', sa.DateTime(timezone=True), nullable=False),
    sa.Column('estado', sa.String(length=10), nullable=False),
    sa.Column('cerrada_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('duracion_segundos', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['actividad_id'], ['sst_actividades.id'], name=op.f('fk_sst_pausas_actividad_id_sst_actividades'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_sst_pausas_empresa_id_empresas')),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_sst_pausas_usuario_id_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sst_pausas'))
    )
    op.create_index('ix_sst_pausas_empresa_mostrada', 'sst_pausas', ['empresa_id', 'mostrada_en'], unique=False)
    op.create_index('ix_sst_pausas_usuario_mostrada', 'sst_pausas', ['usuario_id', 'mostrada_en'], unique=False)
    op.create_index('uq_sst_pausa_abierta', 'sst_pausas', ['usuario_id'], unique=True, postgresql_where=sa.text("estado = 'mostrada'"), sqlite_where=sa.text("estado = 'mostrada'"))
    op.create_table('entrada_observaciones',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('entrada_id', sa.Integer(), nullable=False),
    sa.Column('producto_id', sa.Integer(), nullable=True),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('fecha', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('contenido', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['entrada_id'], ['entradas_inventario.id'], name=op.f('fk_entrada_observaciones_entrada_id_entradas_inventario')),
    sa.ForeignKeyConstraint(['producto_id'], ['productos.id'], name=op.f('fk_entrada_observaciones_producto_id_productos')),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_entrada_observaciones_usuario_id_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_entrada_observaciones'))
    )
    op.create_index('ix_entrada_observaciones_entrada_fecha', 'entrada_observaciones', ['entrada_id', 'fecha'], unique=False)
    op.create_table('garantias',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('numero', sa.Integer(), nullable=False),
    sa.Column('sede_id', sa.Integer(), nullable=False),
    sa.Column('producto_id', sa.Integer(), nullable=False),
    sa.Column('cantidad', sa.Integer(), nullable=False),
    sa.Column('documento_tipo', sa.String(length=20), nullable=False),
    sa.Column('documento_referencia', sa.String(length=100), nullable=True),
    sa.Column('entrada_id', sa.Integer(), nullable=True),
    sa.Column('venta_id', sa.Integer(), nullable=True),
    sa.Column('fecha_compra', sa.Date(), nullable=False),
    sa.Column('garantia_hasta', sa.Date(), nullable=True),
    sa.Column('fecha_reporte', sa.Date(), nullable=False),
    sa.Column('defecto', sa.Text(), nullable=False),
    sa.Column('estado', sa.String(length=25), server_default='reportada', nullable=False),
    sa.Column('proveedor', sa.String(length=150), nullable=True),
    sa.Column('fecha_envio_proveedor', sa.Date(), nullable=True),
    sa.Column('respuesta_proveedor', sa.Text(), nullable=True),
    sa.Column('fecha_respuesta_proveedor', sa.Date(), nullable=True),
    sa.Column('solucion', sa.Text(), nullable=True),
    sa.Column('fecha_solucion', sa.Date(), nullable=True),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('responsable_id', sa.Integer(), nullable=True),
    sa.Column('cerrada_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('cantidad > 0', name=op.f('ck_garantias_cantidad_positiva')),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_garantias_empresa_id_empresas')),
    sa.ForeignKeyConstraint(['entrada_id'], ['entradas_inventario.id'], name=op.f('fk_garantias_entrada_id_entradas_inventario')),
    sa.ForeignKeyConstraint(['producto_id'], ['productos.id'], name=op.f('fk_garantias_producto_id_productos')),
    sa.ForeignKeyConstraint(['responsable_id'], ['usuarios.id'], name=op.f('fk_garantias_responsable_id_usuarios')),
    sa.ForeignKeyConstraint(['sede_id'], ['sedes.id'], name=op.f('fk_garantias_sede_id_sedes')),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_garantias_usuario_id_usuarios')),
    sa.ForeignKeyConstraint(['venta_id'], ['ventas.id'], name=op.f('fk_garantias_venta_id_ventas')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_garantias')),
    sa.UniqueConstraint('empresa_id', 'numero', name='uq_garantias_empresa_numero')
    )
    op.create_index('ix_garantias_empresa_estado', 'garantias', ['empresa_id', 'estado'], unique=False)
    op.create_index(op.f('ix_garantias_entrada_id'), 'garantias', ['entrada_id'], unique=False)
    op.create_index(op.f('ix_garantias_producto_id'), 'garantias', ['producto_id'], unique=False)
    op.create_index('ix_garantias_sede_reporte', 'garantias', ['sede_id', 'fecha_reporte'], unique=False)
    op.create_index(op.f('ix_garantias_venta_id'), 'garantias', ['venta_id'], unique=False)
    op.create_table('pqrs_historial',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('pqrs_id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('fecha', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('evento', sa.String(length=15), nullable=False),
    sa.Column('estado_anterior', sa.String(length=15), nullable=True),
    sa.Column('estado_nuevo', sa.String(length=15), nullable=True),
    sa.Column('comentario', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['pqrs_id'], ['pqrs.id'], name=op.f('fk_pqrs_historial_pqrs_id_pqrs')),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_pqrs_historial_usuario_id_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_pqrs_historial'))
    )
    op.create_index('ix_pqrs_historial_pqrs_fecha', 'pqrs_historial', ['pqrs_id', 'fecha'], unique=False)
    op.create_table('amb_registros',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('venta_id', sa.Integer(), nullable=False),
    sa.Column('venta_item_id', sa.Integer(), nullable=False),
    sa.Column('sede_id', sa.Integer(), nullable=False),
    sa.Column('producto_id', sa.Integer(), nullable=False),
    sa.Column('categoria_id', sa.Integer(), nullable=False),
    sa.Column('fecha', sa.Date(), nullable=False),
    sa.Column('unidades', sa.Integer(), nullable=False),
    sa.Column('tipo_vehiculo', sa.String(length=30), nullable=False),
    sa.Column('propulsion', sa.String(length=30), nullable=False),
    sa.Column('estado', sa.String(length=10), server_default='activo', nullable=False),
    sa.Column('anulado_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('co2_evitado_kg', sa.Numeric(precision=14, scale=3), nullable=True),
    sa.Column('parametros', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=True),
    sa.Column('calculado_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('unidades > 0', name=op.f('ck_amb_registros_unidades_positivas')),
    sa.ForeignKeyConstraint(['categoria_id'], ['categorias.id'], name=op.f('fk_amb_registros_categoria_id_categorias')),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_amb_registros_empresa_id_empresas')),
    sa.ForeignKeyConstraint(['producto_id'], ['productos.id'], name=op.f('fk_amb_registros_producto_id_productos')),
    sa.ForeignKeyConstraint(['sede_id'], ['sedes.id'], name=op.f('fk_amb_registros_sede_id_sedes')),
    sa.ForeignKeyConstraint(['venta_id'], ['ventas.id'], name=op.f('fk_amb_registros_venta_id_ventas')),
    sa.ForeignKeyConstraint(['venta_item_id'], ['venta_items.id'], name=op.f('fk_amb_registros_venta_item_id_venta_items')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_amb_registros')),
    sa.UniqueConstraint('venta_item_id', name='uq_amb_registros_venta_item_id')
    )
    op.create_index('ix_amb_registros_empresa_estado_fecha', 'amb_registros', ['empresa_id', 'estado', 'fecha'], unique=False)
    op.create_index('ix_amb_registros_venta', 'amb_registros', ['venta_id'], unique=False)
    op.create_table('garantia_historial',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('garantia_id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('fecha', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('evento', sa.String(length=15), nullable=False),
    sa.Column('estado_anterior', sa.String(length=25), nullable=True),
    sa.Column('estado_nuevo', sa.String(length=25), nullable=True),
    sa.Column('contenido', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['garantia_id'], ['garantias.id'], name=op.f('fk_garantia_historial_garantia_id_garantias')),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_garantia_historial_usuario_id_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_garantia_historial'))
    )
    op.create_index('ix_garantia_historial_garantia_fecha', 'garantia_historial', ['garantia_id', 'fecha'], unique=False)
    op.create_table('no_conformidades',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('numero', sa.Integer(), nullable=False),
    sa.Column('sede_id', sa.Integer(), nullable=False),
    sa.Column('producto_id', sa.Integer(), nullable=False),
    sa.Column('referencia', sa.String(length=100), nullable=True),
    sa.Column('tipo', sa.String(length=30), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=False),
    sa.Column('fecha_deteccion', sa.Date(), nullable=False),
    sa.Column('cantidad_afectada', sa.Integer(), nullable=False),
    sa.Column('estado', sa.String(length=25), server_default='reportado', nullable=False),
    sa.Column('proveedor', sa.String(length=150), nullable=True),
    sa.Column('entrada_id', sa.Integer(), nullable=True),
    sa.Column('entrada_observacion_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('responsable_id', sa.Integer(), nullable=True),
    sa.Column('solucion', sa.Text(), nullable=True),
    sa.Column('resuelta_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('cerrada_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('cantidad_afectada > 0', name=op.f('ck_no_conformidades_cantidad_positiva')),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_no_conformidades_empresa_id_empresas')),
    sa.ForeignKeyConstraint(['entrada_id'], ['entradas_inventario.id'], name=op.f('fk_no_conformidades_entrada_id_entradas_inventario')),
    sa.ForeignKeyConstraint(['entrada_observacion_id'], ['entrada_observaciones.id'], name=op.f('fk_no_conformidades_entrada_observacion_id_entrada_observaciones')),
    sa.ForeignKeyConstraint(['producto_id'], ['productos.id'], name=op.f('fk_no_conformidades_producto_id_productos')),
    sa.ForeignKeyConstraint(['responsable_id'], ['usuarios.id'], name=op.f('fk_no_conformidades_responsable_id_usuarios')),
    sa.ForeignKeyConstraint(['sede_id'], ['sedes.id'], name=op.f('fk_no_conformidades_sede_id_sedes')),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_no_conformidades_usuario_id_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_no_conformidades')),
    sa.UniqueConstraint('empresa_id', 'numero', name='uq_no_conformidades_empresa_numero')
    )
    op.create_index('ix_no_conformidades_empresa_estado', 'no_conformidades', ['empresa_id', 'estado'], unique=False)
    op.create_index(op.f('ix_no_conformidades_entrada_id'), 'no_conformidades', ['entrada_id'], unique=False)
    op.create_index(op.f('ix_no_conformidades_producto_id'), 'no_conformidades', ['producto_id'], unique=False)
    op.create_index('ix_no_conformidades_sede_fecha', 'no_conformidades', ['sede_id', 'fecha_deteccion'], unique=False)
    op.create_table('no_conformidad_historial',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('no_conformidad_id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('fecha', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('evento', sa.String(length=15), nullable=False),
    sa.Column('estado_anterior', sa.String(length=25), nullable=True),
    sa.Column('estado_nuevo', sa.String(length=25), nullable=True),
    sa.Column('contenido', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['no_conformidad_id'], ['no_conformidades.id'], name=op.f('fk_no_conformidad_historial_no_conformidad_id_no_conformidades')),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_no_conformidad_historial_usuario_id_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_no_conformidad_historial'))
    )
    op.create_index('ix_no_conformidad_historial_nc_fecha', 'no_conformidad_historial', ['no_conformidad_id', 'fecha'], unique=False)
    op.create_table('sig_adjuntos',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('pqrs_id', sa.Integer(), nullable=True),
    sa.Column('no_conformidad_id', sa.Integer(), nullable=True),
    sa.Column('garantia_id', sa.Integer(), nullable=True),
    sa.Column('nombre', sa.String(length=200), nullable=False),
    sa.Column('tipo_mime', sa.String(length=60), nullable=False),
    sa.Column('tamano', sa.Integer(), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('contenido', sa.LargeBinary(), nullable=False),
    sa.Column('subido_por', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('(CASE WHEN pqrs_id IS NULL THEN 0 ELSE 1 END) + (CASE WHEN no_conformidad_id IS NULL THEN 0 ELSE 1 END) + (CASE WHEN garantia_id IS NULL THEN 0 ELSE 1 END) = 1', name=op.f('ck_sig_adjuntos_un_solo_destino')),
    sa.CheckConstraint('tamano > 0', name=op.f('ck_sig_adjuntos_tamano_positivo')),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_sig_adjuntos_empresa_id_empresas')),
    sa.ForeignKeyConstraint(['garantia_id'], ['garantias.id'], name=op.f('fk_sig_adjuntos_garantia_id_garantias')),
    sa.ForeignKeyConstraint(['no_conformidad_id'], ['no_conformidades.id'], name=op.f('fk_sig_adjuntos_no_conformidad_id_no_conformidades')),
    sa.ForeignKeyConstraint(['pqrs_id'], ['pqrs.id'], name=op.f('fk_sig_adjuntos_pqrs_id_pqrs')),
    sa.ForeignKeyConstraint(['subido_por'], ['usuarios.id'], name=op.f('fk_sig_adjuntos_subido_por_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sig_adjuntos'))
    )
    op.create_index('ix_sig_adjuntos_garantia', 'sig_adjuntos', ['garantia_id'], unique=False)
    op.create_index('ix_sig_adjuntos_no_conformidad', 'sig_adjuntos', ['no_conformidad_id'], unique=False)
    op.create_index('ix_sig_adjuntos_pqrs', 'sig_adjuntos', ['pqrs_id'], unique=False)
    op.add_column('movimientos', sa.Column('entrada_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_movimientos_entrada_id'), 'movimientos', ['entrada_id'], unique=False)
    op.create_foreign_key(op.f('fk_movimientos_entrada_id_entradas_inventario'), 'movimientos', 'entradas_inventario', ['entrada_id'], ['id'])

    # Historiales y observaciones: solo inserción (la función la creó la migración 0003).
    for tabla in _SOLO_INSERCION:
        op.execute(
            f"CREATE TRIGGER tr_{tabla}_inmutable BEFORE UPDATE OR DELETE ON {tabla} "
            "FOR EACH ROW EXECUTE FUNCTION inventia_bloquear_modificacion()"
        )


def downgrade() -> None:
    """Elimina las tablas del SIG. Los registros de PQRS, calidad, SST y ambiental se pierden."""
    for tabla in _SOLO_INSERCION:
        op.execute(f"DROP TRIGGER IF EXISTS tr_{tabla}_inmutable ON {tabla}")
    op.drop_constraint(op.f('fk_movimientos_entrada_id_entradas_inventario'), 'movimientos', type_='foreignkey')
    op.drop_index(op.f('ix_movimientos_entrada_id'), table_name='movimientos')
    op.drop_column('movimientos', 'entrada_id')
    op.drop_index('ix_sig_adjuntos_pqrs', table_name='sig_adjuntos')
    op.drop_index('ix_sig_adjuntos_no_conformidad', table_name='sig_adjuntos')
    op.drop_index('ix_sig_adjuntos_garantia', table_name='sig_adjuntos')
    op.drop_table('sig_adjuntos')
    op.drop_index('ix_no_conformidad_historial_nc_fecha', table_name='no_conformidad_historial')
    op.drop_table('no_conformidad_historial')
    op.drop_index('ix_no_conformidades_sede_fecha', table_name='no_conformidades')
    op.drop_index(op.f('ix_no_conformidades_producto_id'), table_name='no_conformidades')
    op.drop_index(op.f('ix_no_conformidades_entrada_id'), table_name='no_conformidades')
    op.drop_index('ix_no_conformidades_empresa_estado', table_name='no_conformidades')
    op.drop_table('no_conformidades')
    op.drop_index('ix_garantia_historial_garantia_fecha', table_name='garantia_historial')
    op.drop_table('garantia_historial')
    op.drop_index('ix_amb_registros_venta', table_name='amb_registros')
    op.drop_index('ix_amb_registros_empresa_estado_fecha', table_name='amb_registros')
    op.drop_table('amb_registros')
    op.drop_index('ix_pqrs_historial_pqrs_fecha', table_name='pqrs_historial')
    op.drop_table('pqrs_historial')
    op.drop_index(op.f('ix_garantias_venta_id'), table_name='garantias')
    op.drop_index('ix_garantias_sede_reporte', table_name='garantias')
    op.drop_index(op.f('ix_garantias_producto_id'), table_name='garantias')
    op.drop_index(op.f('ix_garantias_entrada_id'), table_name='garantias')
    op.drop_index('ix_garantias_empresa_estado', table_name='garantias')
    op.drop_table('garantias')
    op.drop_index('ix_entrada_observaciones_entrada_fecha', table_name='entrada_observaciones')
    op.drop_table('entrada_observaciones')
    op.drop_index('uq_sst_pausa_abierta', table_name='sst_pausas', postgresql_where=sa.text("estado = 'mostrada'"), sqlite_where=sa.text("estado = 'mostrada'"))
    op.drop_index('ix_sst_pausas_usuario_mostrada', table_name='sst_pausas')
    op.drop_index('ix_sst_pausas_empresa_mostrada', table_name='sst_pausas')
    op.drop_table('sst_pausas')
    op.drop_table('sst_configuracion')
    op.drop_index('ix_pqrs_usuario_created', table_name='pqrs')
    op.drop_index('ix_pqrs_empresa_estado', table_name='pqrs')
    op.drop_index('ix_pqrs_empresa_created', table_name='pqrs')
    op.drop_table('pqrs')
    op.drop_index('ix_entradas_inventario_sede_fecha', table_name='entradas_inventario')
    op.drop_index('ix_entradas_inventario_empresa_fecha', table_name='entradas_inventario')
    op.drop_table('entradas_inventario')
    op.drop_table('amb_configuracion')
    op.drop_index(op.f('ix_amb_categorias_empresa_id'), table_name='amb_categorias')
    op.drop_table('amb_categorias')
    op.drop_index('ix_sst_actividades_empresa_activa', table_name='sst_actividades')
    op.drop_table('sst_actividades')
