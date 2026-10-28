"""Reestructuración de Inventia: RBAC, auditoría, catálogo, inventario, ventas, traslados e IA.

Revision ID: 0003_inventia
Revises: 5cb4ddecc152

Esta migración CONSERVA los datos de la versión anterior:

* Cada empresa recibe sus cinco roles del sistema. ``ADMIN_GENERAL`` pasa a «Administrador» y
  ``USUARIO_SEDE`` a «Usuario de inventario» (mínimo privilegio). Un ``USUARIO_SEDE`` sin sede asignada
  queda inhabilitado hasta que un administrador le asigne una (un rol de sede exige sede).
* Los productos pasan a una categoría «General» por empresa; ``sku`` → ``codigo`` y ``precio`` → ``precio_venta``.
* Cada saldo existente genera un movimiento de «inventario inicial» para que el historial cuadre con las
  existencias (invariante: suma de movimientos = cantidad).
* Los nombres de sede repetidos (sin distinguir mayúsculas) se desambiguan añadiendo el identificador.
* Existencias negativas (inválidas) se dejan en 0.
* Tras migrar, ``auditoria`` y ``movimientos`` son de solo inserción (triggers de PostgreSQL).

Solo PostgreSQL. El catálogo de permisos y roles de abajo es una instantánea: el catálogo vigente se
sincroniza al iniciar la API (``sincronizar_permisos``).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_inventia"
down_revision: Union[str, Sequence[str], None] = "5cb4ddecc152"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (código, módulo, descripción)
_PERMISOS = [('empresa.ver', 'Empresa', 'Consultar los datos de la empresa'),
 ('empresa.editar', 'Empresa', 'Modificar los datos y parámetros de la empresa'),
 ('sedes.ver', 'Sedes', 'Consultar sedes'),
 ('sedes.crear', 'Sedes', 'Crear sedes'),
 ('sedes.editar', 'Sedes', 'Modificar sedes'),
 ('sedes.inhabilitar', 'Sedes', 'Inhabilitar o reactivar sedes'),
 ('usuarios.ver', 'Usuarios', 'Consultar usuarios'),
 ('usuarios.crear', 'Usuarios', 'Crear usuarios'),
 ('usuarios.editar', 'Usuarios', 'Modificar usuarios, su rol y su sede'),
 ('usuarios.inhabilitar', 'Usuarios', 'Inhabilitar o reactivar usuarios'),
 ('roles.ver', 'Roles y permisos', 'Consultar roles y permisos'),
 ('roles.crear', 'Roles y permisos', 'Crear roles'),
 ('roles.editar', 'Roles y permisos', 'Modificar roles'),
 ('roles.asignar_permisos', 'Roles y permisos', 'Asignar permisos a los roles'),
 ('categorias.ver', 'Categorías', 'Consultar categorías'),
 ('categorias.crear', 'Categorías', 'Crear categorías'),
 ('categorias.editar', 'Categorías', 'Modificar categorías'),
 ('productos.ver', 'Productos', 'Consultar productos'),
 ('productos.crear', 'Productos', 'Crear productos'),
 ('productos.editar', 'Productos', 'Modificar productos'),
 ('productos.inhabilitar', 'Productos', 'Inhabilitar o reactivar productos'),
 ('inventario.ver', 'Inventario', 'Consultar el inventario por sede'),
 ('inventario.consolidado', 'Inventario', 'Consultar el inventario consolidado de la empresa'),
 ('inventario.entrada', 'Inventario', 'Registrar entradas de productos'),
 ('inventario.salida', 'Inventario', 'Registrar salidas de productos'),
 ('inventario.ajustar', 'Inventario', 'Ajustar existencias'),
 ('inventario.niveles', 'Inventario', 'Configurar stock mínimo y máximo'),
 ('movimientos.ver', 'Inventario', 'Consultar el historial de movimientos'),
 ('ventas.registrar', 'Ventas', 'Registrar ventas'),
 ('ventas.ver', 'Ventas', 'Consultar ventas'),
 ('ventas.anular', 'Ventas', 'Anular ventas'),
 ('traslados.solicitar', 'Traslados', 'Solicitar traslados entre sedes'),
 ('traslados.ver', 'Traslados', 'Consultar traslados'),
 ('traslados.aprobar', 'Traslados', 'Aprobar o rechazar traslados'),
 ('traslados.confirmar', 'Traslados', 'Confirmar traslados'),
 ('alertas.ver', 'Alertas', 'Consultar alertas de inventario'),
 ('alertas.recalcular', 'Alertas', 'Recalcular las alertas de inventario'),
 ('prediccion.ver', 'Predicción', 'Consultar predicciones de demanda'),
 ('prediccion.ejecutar', 'Predicción', 'Generar predicciones de demanda'),
 ('recomendaciones.ver', 'Recomendaciones', 'Consultar recomendaciones'),
 ('recomendaciones.generar', 'Recomendaciones', 'Generar recomendaciones'),
 ('recomendaciones.aprobar', 'Recomendaciones', 'Aprobar o rechazar recomendaciones'),
 ('reportes.inventario', 'Reportes', 'Generar reportes de inventario'),
 ('reportes.ventas', 'Reportes', 'Generar reportes de ventas'),
 ('reportes.movimientos', 'Reportes', 'Generar reportes de movimientos'),
 ('reportes.traslados', 'Reportes', 'Generar reportes de traslados'),
 ('reportes.alertas', 'Reportes', 'Generar reportes de alertas'),
 ('reportes.predicciones', 'Reportes', 'Generar reportes de predicciones'),
 ('reportes.recomendaciones', 'Reportes', 'Generar reportes de recomendaciones'),
 ('auditoria.ver', 'Auditoría', 'Consultar la actividad completa de los usuarios'),
 ('auditoria.operaciones', 'Auditoría', 'Consultar el historial de operaciones'),
 ('agentes.gestionar', 'Agentes de IA', 'Administrar las llaves de acceso de agentes de IA')]

_ROLES = [{'clave': 'admin',
  'nombre': 'Administrador',
  'descripcion': 'Gestiona la empresa, las sedes, los usuarios, los roles, los productos y la configuración general.',
  'alcance': 'empresa',
  'permisos': ['agentes.gestionar',
               'alertas.recalcular',
               'alertas.ver',
               'auditoria.operaciones',
               'auditoria.ver',
               'categorias.crear',
               'categorias.editar',
               'categorias.ver',
               'empresa.editar',
               'empresa.ver',
               'inventario.ajustar',
               'inventario.consolidado',
               'inventario.entrada',
               'inventario.niveles',
               'inventario.salida',
               'inventario.ver',
               'movimientos.ver',
               'prediccion.ejecutar',
               'prediccion.ver',
               'productos.crear',
               'productos.editar',
               'productos.inhabilitar',
               'productos.ver',
               'recomendaciones.aprobar',
               'recomendaciones.generar',
               'recomendaciones.ver',
               'reportes.alertas',
               'reportes.inventario',
               'reportes.movimientos',
               'reportes.predicciones',
               'reportes.recomendaciones',
               'reportes.traslados',
               'reportes.ventas',
               'roles.asignar_permisos',
               'roles.crear',
               'roles.editar',
               'roles.ver',
               'sedes.crear',
               'sedes.editar',
               'sedes.inhabilitar',
               'sedes.ver',
               'traslados.aprobar',
               'traslados.confirmar',
               'traslados.solicitar',
               'traslados.ver',
               'usuarios.crear',
               'usuarios.editar',
               'usuarios.inhabilitar',
               'usuarios.ver',
               'ventas.anular',
               'ventas.registrar',
               'ventas.ver']},
 {'clave': 'gerente',
  'nombre': 'Gerente',
  'descripcion': 'Consulta reportes consolidados e indicadores para apoyar la toma de decisiones.',
  'alcance': 'empresa',
  'permisos': ['alertas.ver',
               'auditoria.operaciones',
               'categorias.ver',
               'empresa.ver',
               'inventario.consolidado',
               'inventario.ver',
               'movimientos.ver',
               'prediccion.ver',
               'productos.ver',
               'recomendaciones.aprobar',
               'recomendaciones.ver',
               'reportes.alertas',
               'reportes.inventario',
               'reportes.movimientos',
               'reportes.predicciones',
               'reportes.recomendaciones',
               'reportes.traslados',
               'reportes.ventas',
               'sedes.ver',
               'traslados.ver',
               'ventas.ver']},
 {'clave': 'encargado_sede',
  'nombre': 'Encargado de sede',
  'descripcion': 'Administra el inventario, las ventas y los movimientos de su sede.',
  'alcance': 'sede',
  'permisos': ['alertas.recalcular',
               'alertas.ver',
               'auditoria.operaciones',
               'categorias.ver',
               'inventario.ajustar',
               'inventario.entrada',
               'inventario.niveles',
               'inventario.salida',
               'inventario.ver',
               'movimientos.ver',
               'prediccion.ver',
               'productos.ver',
               'recomendaciones.aprobar',
               'recomendaciones.ver',
               'reportes.alertas',
               'reportes.inventario',
               'reportes.movimientos',
               'reportes.recomendaciones',
               'reportes.traslados',
               'reportes.ventas',
               'roles.ver',
               'sedes.ver',
               'traslados.aprobar',
               'traslados.confirmar',
               'traslados.solicitar',
               'traslados.ver',
               'ventas.anular',
               'ventas.registrar',
               'ventas.ver']},
 {'clave': 'usuario_inventario',
  'nombre': 'Usuario de inventario',
  'descripcion': 'Registra y consulta entradas, salidas, ventas, existencias y traslados de su sede.',
  'alcance': 'sede',
  'permisos': ['alertas.ver',
               'categorias.ver',
               'inventario.ajustar',
               'inventario.entrada',
               'inventario.salida',
               'inventario.ver',
               'movimientos.ver',
               'productos.ver',
               'reportes.alertas',
               'reportes.movimientos',
               'sedes.ver',
               'traslados.confirmar',
               'traslados.solicitar',
               'traslados.ver',
               'ventas.registrar',
               'ventas.ver']},
 {'clave': 'analista_compras',
  'nombre': 'Analista de compras',
  'descripcion': 'Consulta históricos y predicciones, y revisa las recomendaciones de reabastecimiento.',
  'alcance': 'empresa',
  'permisos': ['alertas.ver',
               'categorias.ver',
               'inventario.consolidado',
               'inventario.ver',
               'movimientos.ver',
               'prediccion.ejecutar',
               'prediccion.ver',
               'productos.ver',
               'recomendaciones.aprobar',
               'recomendaciones.generar',
               'recomendaciones.ver',
               'reportes.alertas',
               'reportes.inventario',
               'reportes.movimientos',
               'reportes.predicciones',
               'reportes.recomendaciones',
               'reportes.ventas',
               'sedes.ver',
               'traslados.ver',
               'ventas.ver']}]

_FUNCION_INMUTABLE = """
CREATE OR REPLACE FUNCTION inventia_bloquear_modificacion() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'La tabla % es de solo inserción: no admite % de filas', TG_TABLE_NAME, TG_OP
        USING ERRCODE = 'restrict_violation';
END;
$$ LANGUAGE plpgsql;
"""


def _ejecutar(sql: str, **parametros) -> None:
    op.get_bind().execute(sa.text(sql), parametros)


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        raise RuntimeError("Las migraciones de Inventia requieren PostgreSQL.")

    # ------------------------------------------------------------------ tablas nuevas
    op.create_table('permisos',
    sa.Column('codigo', sa.String(length=80), nullable=False),
    sa.Column('modulo', sa.String(length=50), nullable=False),
    sa.Column('descripcion', sa.String(length=200), nullable=False),
    sa.PrimaryKeyConstraint('codigo', name=op.f('pk_permisos'))
    )
    op.create_table('categorias',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=100), nullable=False),
    sa.Column('descripcion', sa.String(length=300), nullable=True),
    sa.Column('activa', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_categorias_empresa_id_empresas')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_categorias'))
    )
    op.create_index(op.f('ix_categorias_empresa_id'), 'categorias', ['empresa_id'], unique=False)
    op.create_index('uq_categorias_empresa_nombre', 'categorias', ['empresa_id', sa.literal_column('lower(nombre)')], unique=True)
    op.create_table('roles',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('clave', sa.String(length=40), nullable=True),
    sa.Column('nombre', sa.String(length=80), nullable=False),
    sa.Column('descripcion', sa.String(length=300), nullable=True),
    sa.Column('alcance', sa.String(length=10), server_default='empresa', nullable=False),
    sa.Column('es_sistema', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('activo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_roles_empresa_id_empresas')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_roles'))
    )
    op.create_index(op.f('ix_roles_empresa_id'), 'roles', ['empresa_id'], unique=False)
    op.create_index('uq_roles_empresa_clave', 'roles', ['empresa_id', 'clave'], unique=True)
    op.create_index('uq_roles_empresa_nombre', 'roles', ['empresa_id', sa.literal_column('lower(nombre)')], unique=True)
    op.create_table('secuencias',
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=30), nullable=False),
    sa.Column('valor', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_secuencias_empresa_id_empresas')),
    sa.PrimaryKeyConstraint('empresa_id', 'nombre', name=op.f('pk_secuencias'))
    )
    op.create_table('rol_permisos',
    sa.Column('rol_id', sa.Integer(), nullable=False),
    sa.Column('permiso_codigo', sa.String(length=80), nullable=False),
    sa.ForeignKeyConstraint(['permiso_codigo'], ['permisos.codigo'], name=op.f('fk_rol_permisos_permiso_codigo_permisos'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['rol_id'], ['roles.id'], name=op.f('fk_rol_permisos_rol_id_roles'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('rol_id', 'permiso_codigo', name=op.f('pk_rol_permisos'))
    )
    op.create_table('alertas',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('sede_id', sa.Integer(), nullable=False),
    sa.Column('producto_id', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.String(length=30), nullable=False),
    sa.Column('prioridad', sa.String(length=10), nullable=False),
    sa.Column('estado', sa.String(length=10), nullable=False),
    sa.Column('mensaje', sa.String(length=300), nullable=False),
    sa.Column('detalle', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('abierta_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('resuelta_en', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_alertas_empresa_id_empresas')),
    sa.ForeignKeyConstraint(['producto_id'], ['productos.id'], name=op.f('fk_alertas_producto_id_productos')),
    sa.ForeignKeyConstraint(['sede_id'], ['sedes.id'], name=op.f('fk_alertas_sede_id_sedes')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_alertas'))
    )
    op.create_index('ix_alertas_empresa_estado', 'alertas', ['empresa_id', 'estado'], unique=False)
    op.create_index('uq_alertas_activa', 'alertas', ['sede_id', 'producto_id', 'tipo'], unique=True, postgresql_where=sa.text("estado = 'activa'"))
    op.create_table('api_keys',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('sede_id', sa.Integer(), nullable=True),
    sa.Column('nombre', sa.String(length=100), nullable=False),
    sa.Column('prefijo', sa.String(length=12), nullable=False),
    sa.Column('key_hash', sa.String(length=64), nullable=False),
    sa.Column('alcances', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('activa', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('creada_por', sa.Integer(), nullable=False),
    sa.Column('creada_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('expira_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ultimo_uso_en', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['creada_por'], ['usuarios.id'], name=op.f('fk_api_keys_creada_por_usuarios')),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_api_keys_empresa_id_empresas')),
    sa.ForeignKeyConstraint(['sede_id'], ['sedes.id'], name=op.f('fk_api_keys_sede_id_sedes')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_api_keys')),
    sa.UniqueConstraint('key_hash', name=op.f('uq_api_keys_key_hash')),
    sa.UniqueConstraint('prefijo', name=op.f('uq_api_keys_prefijo'))
    )
    op.create_index(op.f('ix_api_keys_empresa_id'), 'api_keys', ['empresa_id'], unique=False)
    op.create_table('auditoria',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=True),
    sa.Column('usuario_id', sa.Integer(), nullable=True),
    sa.Column('usuario_email', sa.String(length=255), nullable=True),
    sa.Column('sede_id', sa.Integer(), nullable=True),
    sa.Column('fecha', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('modulo', sa.String(length=40), nullable=False),
    sa.Column('accion', sa.String(length=60), nullable=False),
    sa.Column('entidad', sa.String(length=60), nullable=True),
    sa.Column('entidad_id', sa.String(length=40), nullable=True),
    sa.Column('resultado', sa.String(length=10), nullable=False),
    sa.Column('detalle', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('ip', sa.String(length=64), nullable=True),
    sa.Column('request_id', sa.String(length=40), nullable=True),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_auditoria_empresa_id_empresas')),
    sa.ForeignKeyConstraint(['sede_id'], ['sedes.id'], name=op.f('fk_auditoria_sede_id_sedes')),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_auditoria_usuario_id_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_auditoria'))
    )
    op.create_index('ix_auditoria_empresa_fecha', 'auditoria', ['empresa_id', 'fecha'], unique=False)
    op.create_index('ix_auditoria_modulo_accion', 'auditoria', ['modulo', 'accion'], unique=False)
    op.create_index(op.f('ix_auditoria_usuario_id'), 'auditoria', ['usuario_id'], unique=False)
    op.create_table('ejecuciones_prediccion',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('estado', sa.String(length=15), nullable=False),
    sa.Column('horizonte_dias', sa.Integer(), nullable=False),
    sa.Column('fecha_corte', sa.Date(), nullable=True),
    sa.Column('parametros', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('resumen', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('creada_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('iniciada_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finalizada_en', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_ejecuciones_prediccion_empresa_id_empresas')),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_ejecuciones_prediccion_usuario_id_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ejecuciones_prediccion'))
    )
    op.create_index(op.f('ix_ejecuciones_prediccion_empresa_id'), 'ejecuciones_prediccion', ['empresa_id'], unique=False)
    op.create_table('ventas',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('sede_id', sa.Integer(), nullable=False),
    sa.Column('numero', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('fecha', sa.DateTime(timezone=True), nullable=False),
    sa.Column('fecha_dia', sa.Date(), nullable=False),
    sa.Column('total', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('estado', sa.String(length=15), server_default='registrada', nullable=False),
    sa.Column('observacion', sa.String(length=500), nullable=True),
    sa.Column('anulada_por', sa.Integer(), nullable=True),
    sa.Column('anulada_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('motivo_anulacion', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['anulada_por'], ['usuarios.id'], name=op.f('fk_ventas_anulada_por_usuarios')),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_ventas_empresa_id_empresas')),
    sa.ForeignKeyConstraint(['sede_id'], ['sedes.id'], name=op.f('fk_ventas_sede_id_sedes')),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_ventas_usuario_id_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ventas')),
    sa.UniqueConstraint('empresa_id', 'numero', name='uq_ventas_empresa_numero')
    )
    op.create_index('ix_ventas_empresa_fecha_dia', 'ventas', ['empresa_id', 'fecha_dia'], unique=False)
    op.create_index('ix_ventas_sede_fecha_dia', 'ventas', ['sede_id', 'fecha_dia'], unique=False)
    op.create_table('predicciones',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('ejecucion_id', sa.Integer(), nullable=False),
    sa.Column('sede_id', sa.Integer(), nullable=False),
    sa.Column('producto_id', sa.Integer(), nullable=False),
    sa.Column('fecha_inicio', sa.Date(), nullable=False),
    sa.Column('fecha_fin', sa.Date(), nullable=False),
    sa.Column('demanda_estimada', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('limite_inferior', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('limite_superior', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('modelo', sa.String(length=40), nullable=False),
    sa.Column('es_linea_base', sa.Boolean(), nullable=False),
    sa.Column('confianza', sa.String(length=10), nullable=False),
    sa.Column('metricas', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('serie_diaria', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('advertencias', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('generada_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['ejecucion_id'], ['ejecuciones_prediccion.id'], name=op.f('fk_predicciones_ejecucion_id_ejecuciones_prediccion'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_predicciones_empresa_id_empresas')),
    sa.ForeignKeyConstraint(['producto_id'], ['productos.id'], name=op.f('fk_predicciones_producto_id_productos')),
    sa.ForeignKeyConstraint(['sede_id'], ['sedes.id'], name=op.f('fk_predicciones_sede_id_sedes')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_predicciones')),
    sa.UniqueConstraint('ejecucion_id', 'sede_id', 'producto_id', name='uq_predicciones_ejecucion_serie')
    )
    op.create_index(op.f('ix_predicciones_ejecucion_id'), 'predicciones', ['ejecucion_id'], unique=False)
    op.create_index('ix_predicciones_empresa_serie', 'predicciones', ['empresa_id', 'sede_id', 'producto_id'], unique=False)
    op.create_table('recomendaciones',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('ejecucion_id', sa.Integer(), nullable=True),
    sa.Column('tipo', sa.String(length=20), nullable=False),
    sa.Column('producto_id', sa.Integer(), nullable=False),
    sa.Column('sede_id', sa.Integer(), nullable=False),
    sa.Column('sede_origen_id', sa.Integer(), nullable=True),
    sa.Column('cantidad_sugerida', sa.Integer(), nullable=False),
    sa.Column('prioridad', sa.String(length=10), nullable=False),
    sa.Column('estado', sa.String(length=15), nullable=False),
    sa.Column('resumen', sa.String(length=600), nullable=False),
    sa.Column('justificacion', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('generada_en', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('revisada_por', sa.Integer(), nullable=True),
    sa.Column('revisada_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('comentario_revision', sa.String(length=500), nullable=True),
    sa.ForeignKeyConstraint(['ejecucion_id'], ['ejecuciones_prediccion.id'], name=op.f('fk_recomendaciones_ejecucion_id_ejecuciones_prediccion')),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_recomendaciones_empresa_id_empresas')),
    sa.ForeignKeyConstraint(['producto_id'], ['productos.id'], name=op.f('fk_recomendaciones_producto_id_productos')),
    sa.ForeignKeyConstraint(['revisada_por'], ['usuarios.id'], name=op.f('fk_recomendaciones_revisada_por_usuarios')),
    sa.ForeignKeyConstraint(['sede_id'], ['sedes.id'], name=op.f('fk_recomendaciones_sede_id_sedes')),
    sa.ForeignKeyConstraint(['sede_origen_id'], ['sedes.id'], name=op.f('fk_recomendaciones_sede_origen_id_sedes')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_recomendaciones'))
    )
    op.create_index('ix_recomendaciones_empresa_estado', 'recomendaciones', ['empresa_id', 'estado'], unique=False)
    op.create_index(op.f('ix_recomendaciones_producto_id'), 'recomendaciones', ['producto_id'], unique=False)
    op.create_index(op.f('ix_recomendaciones_sede_id'), 'recomendaciones', ['sede_id'], unique=False)
    op.create_table('venta_items',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('venta_id', sa.Integer(), nullable=False),
    sa.Column('producto_id', sa.Integer(), nullable=False),
    sa.Column('cantidad', sa.Integer(), nullable=False),
    sa.Column('precio_unitario', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('subtotal', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.CheckConstraint('cantidad > 0', name=op.f('ck_venta_items_cantidad_positiva')),
    sa.CheckConstraint('precio_unitario >= 0', name=op.f('ck_venta_items_precio_no_negativo')),
    sa.ForeignKeyConstraint(['producto_id'], ['productos.id'], name=op.f('fk_venta_items_producto_id_productos')),
    sa.ForeignKeyConstraint(['venta_id'], ['ventas.id'], name=op.f('fk_venta_items_venta_id_ventas'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_venta_items')),
    sa.UniqueConstraint('venta_id', 'producto_id', name='uq_venta_items_venta_producto')
    )
    op.create_index(op.f('ix_venta_items_producto_id'), 'venta_items', ['producto_id'], unique=False)
    op.create_index(op.f('ix_venta_items_venta_id'), 'venta_items', ['venta_id'], unique=False)
    op.create_table('traslados',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('numero', sa.Integer(), nullable=False),
    sa.Column('sede_origen_id', sa.Integer(), nullable=False),
    sa.Column('sede_destino_id', sa.Integer(), nullable=False),
    sa.Column('estado', sa.String(length=15), nullable=False),
    sa.Column('observacion', sa.String(length=500), nullable=True),
    sa.Column('recomendacion_id', sa.Integer(), nullable=True),
    sa.Column('solicitado_por', sa.Integer(), nullable=False),
    sa.Column('solicitado_en', sa.DateTime(timezone=True), nullable=False),
    sa.Column('aprobado_por', sa.Integer(), nullable=True),
    sa.Column('aprobado_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('confirmado_por', sa.Integer(), nullable=True),
    sa.Column('confirmado_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('cerrado_por', sa.Integer(), nullable=True),
    sa.Column('cerrado_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('motivo_cierre', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('sede_origen_id <> sede_destino_id', name=op.f('ck_traslados_sedes_distintas')),
    sa.ForeignKeyConstraint(['aprobado_por'], ['usuarios.id'], name=op.f('fk_traslados_aprobado_por_usuarios')),
    sa.ForeignKeyConstraint(['cerrado_por'], ['usuarios.id'], name=op.f('fk_traslados_cerrado_por_usuarios')),
    sa.ForeignKeyConstraint(['confirmado_por'], ['usuarios.id'], name=op.f('fk_traslados_confirmado_por_usuarios')),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_traslados_empresa_id_empresas')),
    sa.ForeignKeyConstraint(['recomendacion_id'], ['recomendaciones.id'], name=op.f('fk_traslados_recomendacion_id_recomendaciones')),
    sa.ForeignKeyConstraint(['sede_destino_id'], ['sedes.id'], name=op.f('fk_traslados_sede_destino_id_sedes')),
    sa.ForeignKeyConstraint(['sede_origen_id'], ['sedes.id'], name=op.f('fk_traslados_sede_origen_id_sedes')),
    sa.ForeignKeyConstraint(['solicitado_por'], ['usuarios.id'], name=op.f('fk_traslados_solicitado_por_usuarios')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_traslados')),
    sa.UniqueConstraint('empresa_id', 'numero', name='uq_traslados_empresa_numero')
    )
    op.create_index('ix_traslados_empresa_estado', 'traslados', ['empresa_id', 'estado'], unique=False)
    op.create_index(op.f('ix_traslados_sede_destino_id'), 'traslados', ['sede_destino_id'], unique=False)
    op.create_index(op.f('ix_traslados_sede_origen_id'), 'traslados', ['sede_origen_id'], unique=False)
    op.create_table('movimientos',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('empresa_id', sa.Integer(), nullable=False),
    sa.Column('sede_id', sa.Integer(), nullable=False),
    sa.Column('producto_id', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.String(length=30), nullable=False),
    sa.Column('motivo', sa.String(length=40), nullable=True),
    sa.Column('delta', sa.Integer(), nullable=False),
    sa.Column('saldo_anterior', sa.Integer(), nullable=False),
    sa.Column('saldo_posterior', sa.Integer(), nullable=False),
    sa.Column('sede_contraparte_id', sa.Integer(), nullable=True),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('fecha', sa.DateTime(timezone=True), nullable=False),
    sa.Column('observacion', sa.String(length=500), nullable=True),
    sa.Column('venta_id', sa.Integer(), nullable=True),
    sa.Column('traslado_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('delta <> 0', name=op.f('ck_movimientos_delta_distinto_de_cero')),
    sa.CheckConstraint('saldo_posterior >= 0', name=op.f('ck_movimientos_saldo_posterior_no_negativo')),
    sa.ForeignKeyConstraint(['empresa_id'], ['empresas.id'], name=op.f('fk_movimientos_empresa_id_empresas')),
    sa.ForeignKeyConstraint(['producto_id'], ['productos.id'], name=op.f('fk_movimientos_producto_id_productos')),
    sa.ForeignKeyConstraint(['sede_contraparte_id'], ['sedes.id'], name=op.f('fk_movimientos_sede_contraparte_id_sedes')),
    sa.ForeignKeyConstraint(['sede_id'], ['sedes.id'], name=op.f('fk_movimientos_sede_id_sedes')),
    sa.ForeignKeyConstraint(['traslado_id'], ['traslados.id'], name=op.f('fk_movimientos_traslado_id_traslados')),
    sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id'], name=op.f('fk_movimientos_usuario_id_usuarios')),
    sa.ForeignKeyConstraint(['venta_id'], ['ventas.id'], name=op.f('fk_movimientos_venta_id_ventas')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_movimientos'))
    )
    op.create_index('ix_movimientos_empresa_fecha', 'movimientos', ['empresa_id', 'fecha'], unique=False)
    op.create_index(op.f('ix_movimientos_producto_id'), 'movimientos', ['producto_id'], unique=False)
    op.create_index('ix_movimientos_sede_producto_fecha', 'movimientos', ['sede_id', 'producto_id', 'fecha'], unique=False)
    op.create_index(op.f('ix_movimientos_tipo'), 'movimientos', ['tipo'], unique=False)
    op.create_index(op.f('ix_movimientos_traslado_id'), 'movimientos', ['traslado_id'], unique=False)
    op.create_index(op.f('ix_movimientos_venta_id'), 'movimientos', ['venta_id'], unique=False)
    op.create_table('traslado_items',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('traslado_id', sa.Integer(), nullable=False),
    sa.Column('producto_id', sa.Integer(), nullable=False),
    sa.Column('cantidad', sa.Integer(), nullable=False),
    sa.CheckConstraint('cantidad > 0', name=op.f('ck_traslado_items_cantidad_positiva')),
    sa.ForeignKeyConstraint(['producto_id'], ['productos.id'], name=op.f('fk_traslado_items_producto_id_productos')),
    sa.ForeignKeyConstraint(['traslado_id'], ['traslados.id'], name=op.f('fk_traslado_items_traslado_id_traslados'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_traslado_items')),
    sa.UniqueConstraint('traslado_id', 'producto_id', name='uq_traslado_items_traslado_producto')
    )
    op.create_index(op.f('ix_traslado_items_producto_id'), 'traslado_items', ['producto_id'], unique=False)
    op.create_index(op.f('ix_traslado_items_traslado_id'), 'traslado_items', ['traslado_id'], unique=False)

    # ------------------------------------------------------------------ empresas
    op.add_column("empresas", sa.Column("identificacion", sa.String(length=40), nullable=True))
    op.add_column("empresas", sa.Column("direccion", sa.String(length=200), nullable=True))
    op.add_column("empresas", sa.Column("ciudad", sa.String(length=100), nullable=True))
    op.add_column("empresas", sa.Column("telefono", sa.String(length=30), nullable=True))
    op.add_column("empresas", sa.Column("email", sa.String(length=255), nullable=True))
    op.add_column("empresas", sa.Column("activa", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column(
        "empresas",
        sa.Column(
            "configuracion",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )
    op.add_column(
        "empresas", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)
    )
    op.create_unique_constraint(op.f("uq_empresas_identificacion"), "empresas", ["identificacion"])

    # ------------------------------------------------------------------ sedes
    _ejecutar(
        """
        UPDATE sedes SET nombre = left(nombre, 140) || ' (' || id || ')'
        WHERE id NOT IN (SELECT MIN(id) FROM sedes GROUP BY empresa_id, lower(nombre))
        """
    )
    op.add_column("sedes", sa.Column("direccion", sa.String(length=200), nullable=True))
    op.add_column("sedes", sa.Column("activa", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column(
        "sedes", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)
    )
    op.create_index(op.f("ix_sedes_empresa_id"), "sedes", ["empresa_id"], unique=False)
    op.create_index(
        "uq_sedes_empresa_nombre", "sedes", ["empresa_id", sa.literal_column("lower(nombre)")], unique=True
    )

    # ------------------------------------------------------------------ permisos y roles
    permisos = sa.table(
        "permisos", sa.column("codigo", sa.String), sa.column("modulo", sa.String), sa.column("descripcion", sa.String)
    )
    op.bulk_insert(permisos, [{"codigo": c, "modulo": m, "descripcion": d} for c, m, d in _PERMISOS])
    for rol in _ROLES:
        _ejecutar(
            """
            INSERT INTO roles (empresa_id, clave, nombre, descripcion, alcance, es_sistema, activo)
            SELECT id, :clave, :nombre, :descripcion, :alcance, true, true FROM empresas
            """,
            clave=rol["clave"], nombre=rol["nombre"], descripcion=rol["descripcion"], alcance=rol["alcance"],
        )
        op.get_bind().execute(
            sa.text(
                """
                INSERT INTO rol_permisos (rol_id, permiso_codigo)
                SELECT r.id, p.codigo FROM roles r CROSS JOIN unnest(:permisos) AS p(codigo) WHERE r.clave = :clave
                """
            ).bindparams(sa.bindparam("permisos", type_=postgresql.ARRAY(sa.String()))),
            {"clave": rol["clave"], "permisos": list(rol["permisos"])},
        )

    # ------------------------------------------------------------------ usuarios
    op.add_column("usuarios", sa.Column("rol_id", sa.Integer(), nullable=True))
    op.add_column(
        "usuarios",
        sa.Column("debe_cambiar_password", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "usuarios", sa.Column("password_version", sa.Integer(), server_default=sa.text("0"), nullable=False)
    )
    op.add_column(
        "usuarios", sa.Column("intentos_fallidos", sa.Integer(), server_default=sa.text("0"), nullable=False)
    )
    op.add_column("usuarios", sa.Column("bloqueado_hasta", sa.DateTime(timezone=True), nullable=True))
    op.add_column("usuarios", sa.Column("ultimo_acceso", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "usuarios", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)
    )
    _ejecutar(
        """
        UPDATE usuarios u SET rol_id = r.id
        FROM roles r
        WHERE r.empresa_id = u.empresa_id
          AND r.clave = CASE u.rol::text WHEN 'ADMIN_GENERAL' THEN 'admin' ELSE 'usuario_inventario' END
        """
    )
    # Un rol de sede exige sede: sin sede, la cuenta queda inhabilitada hasta que se corrija.
    _ejecutar("UPDATE usuarios SET activo = false WHERE rol::text <> 'ADMIN_GENERAL' AND sede_id IS NULL")
    # Un administrador no se asocia a una sede.
    _ejecutar("UPDATE usuarios SET sede_id = NULL WHERE rol::text = 'ADMIN_GENERAL'")
    # El correo se normaliza a minúsculas salvo que choque con otro que solo difiera en mayúsculas.
    _ejecutar(
        """
        UPDATE usuarios SET email = lower(email)
        WHERE email <> lower(email)
          AND NOT EXISTS (SELECT 1 FROM usuarios o WHERE lower(o.email) = lower(usuarios.email) AND o.id <> usuarios.id)
        """
    )
    op.alter_column("usuarios", "rol_id", nullable=False)
    op.create_index(op.f("ix_usuarios_empresa_id"), "usuarios", ["empresa_id"], unique=False)
    op.create_index(op.f("ix_usuarios_rol_id"), "usuarios", ["rol_id"], unique=False)
    op.create_index(op.f("ix_usuarios_sede_id"), "usuarios", ["sede_id"], unique=False)
    op.create_foreign_key(op.f("fk_usuarios_rol_id_roles"), "usuarios", "roles", ["rol_id"], ["id"])
    op.drop_column("usuarios", "rol")
    op.execute("DROP TYPE IF EXISTS rolusuario")
    op.create_index(
        op.f("ix_password_reset_tokens_usuario_id"), "password_reset_tokens", ["usuario_id"], unique=False
    )

    # ------------------------------------------------------------------ categorías y productos
    _ejecutar(
        """
        INSERT INTO categorias (empresa_id, nombre, descripcion)
        SELECT DISTINCT empresa_id, 'General', 'Categoría creada al migrar desde la versión anterior' FROM productos
        """
    )
    op.add_column("productos", sa.Column("categoria_id", sa.Integer(), nullable=True))
    op.add_column("productos", sa.Column("codigo", sa.String(length=60), nullable=True))
    op.add_column(
        "productos", sa.Column("unidad_medida", sa.String(length=20), server_default="unidad", nullable=False)
    )
    op.add_column("productos", sa.Column("costo", sa.Numeric(precision=14, scale=2), nullable=True))
    op.add_column("productos", sa.Column("precio_venta", sa.Numeric(precision=14, scale=2), nullable=True))
    op.add_column("productos", sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column(
        "productos", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)
    )
    _ejecutar(
        """
        UPDATE productos p SET
            categoria_id = c.id,
            codigo = CASE WHEN length(p.sku) <= 60 THEN p.sku ELSE left(p.sku, 50) || '-' || p.id END,
            precio_venta = p.precio
        FROM categorias c
        WHERE c.empresa_id = p.empresa_id AND lower(c.nombre) = 'general'
        """
    )
    op.alter_column("productos", "categoria_id", nullable=False)
    op.alter_column("productos", "codigo", nullable=False)
    op.drop_index(op.f("ix_productos_sku"), table_name="productos")
    op.create_index(op.f("ix_productos_categoria_id"), "productos", ["categoria_id"], unique=False)
    op.create_index(op.f("ix_productos_empresa_id"), "productos", ["empresa_id"], unique=False)
    op.create_unique_constraint("uq_productos_empresa_codigo", "productos", ["empresa_id", "codigo"])
    op.create_foreign_key(
        op.f("fk_productos_categoria_id_categorias"), "productos", "categorias", ["categoria_id"], ["id"]
    )
    op.drop_column("productos", "sku")
    op.drop_column("productos", "precio")

    # ------------------------------------------------------------------ inventario por sede
    op.add_column("inventario_sede", sa.Column("empresa_id", sa.Integer(), nullable=True))
    op.add_column("inventario_sede", sa.Column("stock_maximo", sa.Integer(), nullable=True))
    op.add_column(
        "inventario_sede",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.add_column(
        "inventario_sede",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    _ejecutar("UPDATE inventario_sede i SET empresa_id = s.empresa_id FROM sedes s WHERE s.id = i.sede_id")
    _ejecutar("UPDATE inventario_sede SET cantidad = 0 WHERE cantidad < 0")
    _ejecutar("UPDATE inventario_sede SET stock_minimo = 0 WHERE stock_minimo < 0")
    op.alter_column("inventario_sede", "empresa_id", nullable=False)
    op.create_index(op.f("ix_inventario_sede_empresa_id"), "inventario_sede", ["empresa_id"], unique=False)
    op.create_index(op.f("ix_inventario_sede_producto_id"), "inventario_sede", ["producto_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_inventario_sede_empresa_id_empresas"), "inventario_sede", "empresas", ["empresa_id"], ["id"]
    )
    op.create_check_constraint(op.f("ck_inventario_sede_cantidad_no_negativa"), "inventario_sede", "cantidad >= 0")
    op.create_check_constraint(
        op.f("ck_inventario_sede_stock_minimo_no_negativo"), "inventario_sede", "stock_minimo >= 0"
    )
    op.create_check_constraint(
        op.f("ck_inventario_sede_stock_maximo_mayor_o_igual_minimo"),
        "inventario_sede",
        "stock_maximo IS NULL OR stock_maximo >= stock_minimo",
    )

    # Cada saldo heredado queda respaldado por un movimiento de inventario inicial (el historial cuadra).
    _ejecutar(
        """
        INSERT INTO movimientos
            (empresa_id, sede_id, producto_id, tipo, motivo, delta, saldo_anterior, saldo_posterior,
             usuario_id, fecha, observacion)
        SELECT i.empresa_id, i.sede_id, i.producto_id, 'entrada', 'inventario_inicial', i.cantidad, 0, i.cantidad,
               (SELECT MIN(u.id) FROM usuarios u WHERE u.empresa_id = i.empresa_id),
               now(), 'Saldo inicial migrado desde la versión anterior'
        FROM inventario_sede i
        WHERE i.cantidad > 0 AND EXISTS (SELECT 1 FROM usuarios u WHERE u.empresa_id = i.empresa_id)
        """
    )

    # ------------------------------------------------------------------ solo inserción
    op.execute(_FUNCION_INMUTABLE)
    for tabla in ("auditoria", "movimientos"):
        op.execute(
            f"CREATE TRIGGER tr_{tabla}_inmutable BEFORE UPDATE OR DELETE ON {tabla} "
            "FOR EACH ROW EXECUTE FUNCTION inventia_bloquear_modificacion()"
        )


def downgrade() -> None:
    """Vuelve al esquema anterior. Los datos nuevos (ventas, traslados, movimientos, etc.) se pierden."""
    for tabla in ("auditoria", "movimientos"):
        op.execute(f"DROP TRIGGER IF EXISTS tr_{tabla}_inmutable ON {tabla}")
    op.execute("DROP FUNCTION IF EXISTS inventia_bloquear_modificacion()")

    # inventario_sede
    for nombre in (
        "ck_inventario_sede_stock_maximo_mayor_o_igual_minimo",
        "ck_inventario_sede_stock_minimo_no_negativo",
        "ck_inventario_sede_cantidad_no_negativa",
    ):
        op.drop_constraint(op.f(nombre), "inventario_sede", type_="check")
    op.drop_constraint(op.f("fk_inventario_sede_empresa_id_empresas"), "inventario_sede", type_="foreignkey")
    op.drop_index(op.f("ix_inventario_sede_producto_id"), table_name="inventario_sede")
    op.drop_index(op.f("ix_inventario_sede_empresa_id"), table_name="inventario_sede")
    for columna in ("updated_at", "created_at", "stock_maximo", "empresa_id"):
        op.drop_column("inventario_sede", columna)

    # productos
    op.add_column("productos", sa.Column("precio", sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column("productos", sa.Column("sku", sa.String(length=100), nullable=True))
    _ejecutar(
        """
        UPDATE productos p SET precio = p.precio_venta,
            sku = CASE WHEN (SELECT count(*) FROM productos o WHERE o.codigo = p.codigo) > 1
                       THEN p.codigo || '-E' || p.empresa_id ELSE p.codigo END
        """
    )
    op.alter_column("productos", "sku", nullable=False)
    op.drop_constraint(op.f("fk_productos_categoria_id_categorias"), "productos", type_="foreignkey")
    op.drop_constraint("uq_productos_empresa_codigo", "productos", type_="unique")
    op.drop_index(op.f("ix_productos_empresa_id"), table_name="productos")
    op.drop_index(op.f("ix_productos_categoria_id"), table_name="productos")
    op.create_index(op.f("ix_productos_sku"), "productos", ["sku"], unique=True)
    for columna in ("updated_at", "activo", "precio_venta", "costo", "unidad_medida", "codigo", "categoria_id"):
        op.drop_column("productos", columna)

    # usuarios
    op.drop_index(op.f("ix_password_reset_tokens_usuario_id"), table_name="password_reset_tokens")
    postgresql.ENUM("ADMIN_GENERAL", "USUARIO_SEDE", name="rolusuario").create(op.get_bind(), checkfirst=True)
    op.add_column(
        "usuarios",
        sa.Column("rol", postgresql.ENUM("ADMIN_GENERAL", "USUARIO_SEDE", name="rolusuario", create_type=False), nullable=True),
    )
    _ejecutar(
        """
        UPDATE usuarios u SET rol = CASE WHEN r.clave = 'admin' THEN 'ADMIN_GENERAL' ELSE 'USUARIO_SEDE' END::rolusuario
        FROM roles r WHERE r.id = u.rol_id
        """
    )
    op.alter_column("usuarios", "rol", nullable=False)
    op.drop_constraint(op.f("fk_usuarios_rol_id_roles"), "usuarios", type_="foreignkey")
    op.drop_index(op.f("ix_usuarios_sede_id"), table_name="usuarios")
    op.drop_index(op.f("ix_usuarios_rol_id"), table_name="usuarios")
    op.drop_index(op.f("ix_usuarios_empresa_id"), table_name="usuarios")
    for columna in (
        "updated_at", "ultimo_acceso", "bloqueado_hasta", "intentos_fallidos", "password_version",
        "debe_cambiar_password", "rol_id",
    ):
        op.drop_column("usuarios", columna)

    # sedes y empresas
    op.drop_index("uq_sedes_empresa_nombre", table_name="sedes")
    op.drop_index(op.f("ix_sedes_empresa_id"), table_name="sedes")
    for columna in ("updated_at", "activa", "direccion"):
        op.drop_column("sedes", columna)
    op.drop_constraint(op.f("uq_empresas_identificacion"), "empresas", type_="unique")
    for columna in (
        "updated_at", "configuracion", "activa", "email", "telefono", "ciudad", "direccion", "identificacion",
    ):
        op.drop_column("empresas", columna)

    # tablas nuevas (de las dependientes a las base)
    for tabla, indices in (
        ("traslado_items", ["ix_traslado_items_traslado_id", "ix_traslado_items_producto_id"]),
        (
            "movimientos",
            [
                "ix_movimientos_venta_id", "ix_movimientos_traslado_id", "ix_movimientos_tipo",
                "ix_movimientos_sede_producto_fecha", "ix_movimientos_producto_id", "ix_movimientos_empresa_fecha",
            ],
        ),
        ("traslados", ["ix_traslados_sede_origen_id", "ix_traslados_sede_destino_id", "ix_traslados_empresa_estado"]),
        ("venta_items", ["ix_venta_items_venta_id", "ix_venta_items_producto_id"]),
        (
            "recomendaciones",
            ["ix_recomendaciones_sede_id", "ix_recomendaciones_producto_id", "ix_recomendaciones_empresa_estado"],
        ),
        ("predicciones", ["ix_predicciones_empresa_serie", "ix_predicciones_ejecucion_id"]),
        ("ventas", ["ix_ventas_sede_fecha_dia", "ix_ventas_empresa_fecha_dia"]),
        ("ejecuciones_prediccion", ["ix_ejecuciones_prediccion_empresa_id"]),
        ("auditoria", ["ix_auditoria_usuario_id", "ix_auditoria_modulo_accion", "ix_auditoria_empresa_fecha"]),
        ("api_keys", ["ix_api_keys_empresa_id"]),
        ("alertas", ["uq_alertas_activa", "ix_alertas_empresa_estado"]),
        ("rol_permisos", []),
        ("secuencias", []),
        ("roles", ["uq_roles_empresa_nombre", "uq_roles_empresa_clave", "ix_roles_empresa_id"]),
        ("categorias", ["uq_categorias_empresa_nombre", "ix_categorias_empresa_id"]),
        ("permisos", []),
    ):
        for indice in indices:
            op.drop_index(indice, table_name=tabla)
        op.drop_table(tabla)
