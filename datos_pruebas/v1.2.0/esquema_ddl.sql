-- Inventia 1.2.0 (Línea Base 1) · 22 tablas
-- PostgreSQL 16 · esquema de la revisión 0006: la base migrada hasta 0005_integridad_mer (CRF-MER-01),
-- sin las estructuras del SIG ni de los agentes.
-- Las llaves foráneas hacia empresas.id (empresa_id) aíslan los datos de cada empresa.
--
CREATE OR REPLACE FUNCTION inventia_bloquear_modificacion()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    RAISE EXCEPTION 'La tabla % es de solo inserción: no admite % de filas', TG_TABLE_NAME, TG_OP
        USING ERRCODE = 'restrict_violation';
END;
$function$;

-- empresas: Empresa cliente; guarda los parámetros de inventario y predicción en un campo JSON.
CREATE TABLE empresas (
    id serial NOT NULL,
    nombre varchar(150) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    identificacion varchar(40),
    direccion varchar(200),
    ciudad varchar(100),
    telefono varchar(30),
    email varchar(255),
    activa boolean NOT NULL DEFAULT true,
    configuracion jsonb NOT NULL DEFAULT '{}'::jsonb,
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT pk_empresas PRIMARY KEY (id),
    CONSTRAINT uq_empresas_identificacion UNIQUE (identificacion)
);

-- permisos: Catálogo global de los 51 permisos; se sincroniza desde el código al iniciar la API.
CREATE TABLE permisos (
    codigo varchar(80) NOT NULL,
    modulo varchar(50) NOT NULL,
    descripcion varchar(200) NOT NULL,
    CONSTRAINT pk_permisos PRIMARY KEY (codigo)
);

-- categorias: Agrupación de productos; el nombre es único por empresa.
CREATE TABLE categorias (
    id serial NOT NULL,
    empresa_id integer NOT NULL,
    nombre varchar(100) NOT NULL,
    descripcion varchar(300),
    activa boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT pk_categorias PRIMARY KEY (id),
    CONSTRAINT fk_categorias_empresa_id_empresas FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);
CREATE INDEX ix_categorias_empresa_id ON categorias USING btree (empresa_id);
CREATE UNIQUE INDEX uq_categorias_empresa_nombre ON categorias USING btree (empresa_id,
        lower((nombre)::text));

-- roles: Roles de cada empresa; cinco son del sistema y no se eliminan ni cambian de permisos.
CREATE TABLE roles (
    id serial NOT NULL,
    empresa_id integer NOT NULL,
    clave varchar(40),
    nombre varchar(80) NOT NULL,
    descripcion varchar(300),
    alcance varchar(10) NOT NULL DEFAULT 'empresa'::character varying,
    es_sistema boolean NOT NULL DEFAULT false,
    activo boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT pk_roles PRIMARY KEY (id),
    CONSTRAINT fk_roles_empresa_id_empresas FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);
CREATE INDEX ix_roles_empresa_id ON roles USING btree (empresa_id);
CREATE UNIQUE INDEX uq_roles_empresa_clave ON roles USING btree (empresa_id, clave);
CREATE UNIQUE INDEX uq_roles_empresa_nombre ON roles USING btree (empresa_id, lower((nombre)::text));

-- secuencias: Consecutivos por empresa (ventas, traslados y entradas) que se incrementan de forma
-- atómica.
CREATE TABLE secuencias (
    empresa_id integer NOT NULL,
    nombre varchar(30) NOT NULL,
    valor integer NOT NULL,
    CONSTRAINT pk_secuencias PRIMARY KEY (empresa_id, nombre),
    CONSTRAINT fk_secuencias_empresa_id_empresas FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);

-- sedes: Ubicaciones físicas de la empresa; el nombre es único por empresa sin distinguir mayúsculas.
CREATE TABLE sedes (
    id serial NOT NULL,
    empresa_id integer NOT NULL,
    nombre varchar(150) NOT NULL,
    ciudad varchar(150),
    created_at timestamptz NOT NULL DEFAULT now(),
    direccion varchar(200),
    activa boolean NOT NULL DEFAULT true,
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT pk_sedes PRIMARY KEY (id),
    CONSTRAINT fk_sedes_empresa_id_empresas FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);
CREATE INDEX ix_sedes_empresa_id ON sedes USING btree (empresa_id);
CREATE UNIQUE INDEX uq_sedes_empresa_nombre ON sedes USING btree (empresa_id, lower((nombre)::text));

-- productos: Catálogo de productos; el código es único por empresa y no cambia.
CREATE TABLE productos (
    id serial NOT NULL,
    empresa_id integer NOT NULL,
    nombre varchar(200) NOT NULL,
    descripcion varchar(1000),
    created_at timestamptz NOT NULL DEFAULT now(),
    categoria_id integer NOT NULL,
    codigo varchar(60) NOT NULL,
    unidad_medida varchar(20) NOT NULL DEFAULT 'unidad'::character varying,
    costo numeric(14,2),
    precio_venta numeric(14,2),
    activo boolean NOT NULL DEFAULT true,
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT pk_productos PRIMARY KEY (id),
    CONSTRAINT uq_productos_empresa_codigo UNIQUE (empresa_id, codigo),
    CONSTRAINT fk_productos_categoria_id_categorias FOREIGN KEY (categoria_id) REFERENCES
            categorias(id),
    CONSTRAINT fk_productos_empresa_id_empresas FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);
CREATE INDEX ix_productos_categoria_id ON productos USING btree (categoria_id);
CREATE INDEX ix_productos_empresa_id ON productos USING btree (empresa_id);

-- rol_permisos: Relación entre cada rol y los permisos que otorga.
CREATE TABLE rol_permisos (
    rol_id integer NOT NULL,
    permiso_codigo varchar(80) NOT NULL,
    CONSTRAINT pk_rol_permisos PRIMARY KEY (rol_id, permiso_codigo),
    CONSTRAINT fk_rol_permisos_permiso_codigo_permisos FOREIGN KEY (permiso_codigo) REFERENCES
            permisos(codigo) ON DELETE CASCADE,
    CONSTRAINT fk_rol_permisos_rol_id_roles FOREIGN KEY (rol_id) REFERENCES roles(id) ON DELETE CASCADE
);

-- usuarios: Cuentas de acceso con rol, sede, contraseña (Argon2id) y control de bloqueo temporal.
CREATE TABLE usuarios (
    id serial NOT NULL,
    empresa_id integer NOT NULL,
    sede_id integer,
    nombre varchar(150) NOT NULL,
    email varchar(255) NOT NULL,
    password_hash varchar(255) NOT NULL,
    activo boolean NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    rol_id integer NOT NULL,
    debe_cambiar_password boolean NOT NULL DEFAULT false,
    password_version integer NOT NULL DEFAULT 0,
    intentos_fallidos integer NOT NULL DEFAULT 0,
    bloqueado_hasta timestamptz,
    ultimo_acceso timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT pk_usuarios PRIMARY KEY (id),
    CONSTRAINT fk_usuarios_empresa_id_empresas FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    CONSTRAINT fk_usuarios_rol_id_roles FOREIGN KEY (rol_id) REFERENCES roles(id),
    CONSTRAINT fk_usuarios_sede_id_sedes FOREIGN KEY (sede_id) REFERENCES sedes(id)
);
CREATE UNIQUE INDEX ix_usuarios_email ON usuarios USING btree (email);
CREATE INDEX ix_usuarios_empresa_id ON usuarios USING btree (empresa_id);
CREATE INDEX ix_usuarios_rol_id ON usuarios USING btree (rol_id);
CREATE INDEX ix_usuarios_sede_id ON usuarios USING btree (sede_id);

-- auditoria: Registro de solo inserción de accesos, operaciones y exportaciones, sin secretos.
CREATE TABLE auditoria (
    id bigserial NOT NULL,
    empresa_id integer,
    usuario_id integer,
    usuario_email varchar(255),
    sede_id integer,
    fecha timestamptz NOT NULL DEFAULT now(),
    modulo varchar(40) NOT NULL,
    accion varchar(60) NOT NULL,
    entidad varchar(60),
    entidad_id varchar(40),
    resultado varchar(10) NOT NULL,
    detalle jsonb NOT NULL,
    ip varchar(64),
    request_id varchar(40),
    CONSTRAINT pk_auditoria PRIMARY KEY (id),
    CONSTRAINT fk_auditoria_empresa_id_empresas FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    CONSTRAINT fk_auditoria_sede_id_sedes FOREIGN KEY (sede_id) REFERENCES sedes(id),
    CONSTRAINT fk_auditoria_usuario_id_usuarios FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);
CREATE INDEX ix_auditoria_empresa_fecha ON auditoria USING btree (empresa_id, fecha);
CREATE INDEX ix_auditoria_modulo_accion ON auditoria USING btree (modulo, accion);
CREATE INDEX ix_auditoria_usuario_id ON auditoria USING btree (usuario_id);
CREATE TRIGGER tr_auditoria_inmutable BEFORE DELETE OR UPDATE ON auditoria FOR EACH ROW EXECUTE FUNCTION
        inventia_bloquear_modificacion();

-- ejecuciones_prediccion: Cada corrida del módulo predictivo con su estado, parámetros y resumen de
-- métricas.
CREATE TABLE ejecuciones_prediccion (
    id serial NOT NULL,
    empresa_id integer NOT NULL,
    usuario_id integer NOT NULL,
    estado varchar(15) NOT NULL,
    horizonte_dias integer NOT NULL,
    fecha_corte date,
    parametros jsonb NOT NULL,
    resumen jsonb NOT NULL,
    error text,
    creada_en timestamptz NOT NULL DEFAULT now(),
    iniciada_en timestamptz,
    finalizada_en timestamptz,
    CONSTRAINT pk_ejecuciones_prediccion PRIMARY KEY (id),
    CONSTRAINT fk_ejecuciones_prediccion_empresa_id_empresas FOREIGN KEY (empresa_id) REFERENCES
            empresas(id),
    CONSTRAINT fk_ejecuciones_prediccion_usuario_id_usuarios FOREIGN KEY (usuario_id) REFERENCES
            usuarios(id)
);
CREATE INDEX ix_ejecuciones_prediccion_empresa_id ON ejecuciones_prediccion USING btree (empresa_id);

-- entradas_inventario: Cabecera de cada entrada de mercancía; agrupa los movimientos que la componen.
CREATE TABLE entradas_inventario (
    id serial NOT NULL,
    empresa_id integer NOT NULL,
    sede_id integer NOT NULL,
    numero integer NOT NULL,
    motivo varchar(40) NOT NULL,
    usuario_id integer NOT NULL,
    fecha timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT pk_entradas_inventario PRIMARY KEY (id),
    CONSTRAINT uq_entradas_inventario_empresa_numero UNIQUE (empresa_id, numero),
    CONSTRAINT fk_entradas_inventario_empresa_id_empresas FOREIGN KEY (empresa_id) REFERENCES
            empresas(id),
    CONSTRAINT fk_entradas_inventario_sede_id_sedes FOREIGN KEY (sede_id) REFERENCES sedes(id),
    CONSTRAINT fk_entradas_inventario_usuario_id_usuarios FOREIGN KEY (usuario_id) REFERENCES
            usuarios(id)
);
CREATE INDEX ix_entradas_inventario_empresa_fecha ON entradas_inventario USING btree (empresa_id,
        fecha);
CREATE INDEX ix_entradas_inventario_sede_fecha ON entradas_inventario USING btree (sede_id, fecha);

-- inventario_sede: Única fuente de existencias: cantidad por sede y producto con sus niveles mínimo y
-- máximo.
CREATE TABLE inventario_sede (
    id serial NOT NULL,
    sede_id integer NOT NULL,
    producto_id integer NOT NULL,
    cantidad integer NOT NULL,
    stock_minimo integer NOT NULL,
    empresa_id integer NOT NULL,
    stock_maximo integer,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT pk_inventario_sede PRIMARY KEY (id),
    CONSTRAINT uq_sede_producto UNIQUE (sede_id, producto_id),
    CONSTRAINT ck_inventario_sede_cantidad_no_negativa CHECK ((cantidad >= 0)),
    CONSTRAINT ck_inventario_sede_stock_maximo_mayor_o_igual_minimo CHECK (((stock_maximo IS NULL) OR
            (stock_maximo >= stock_minimo))),
    CONSTRAINT ck_inventario_sede_stock_minimo_no_negativo CHECK ((stock_minimo >= 0)),
    CONSTRAINT fk_inventario_sede_empresa_id_empresas FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    CONSTRAINT fk_inventario_sede_producto_id_productos FOREIGN KEY (producto_id) REFERENCES
            productos(id),
    CONSTRAINT fk_inventario_sede_sede_id_sedes FOREIGN KEY (sede_id) REFERENCES sedes(id)
);
CREATE INDEX ix_inventario_sede_empresa_id ON inventario_sede USING btree (empresa_id);
CREATE INDEX ix_inventario_sede_producto ON inventario_sede USING btree (sede_id, producto_id);
CREATE INDEX ix_inventario_sede_producto_id ON inventario_sede USING btree (producto_id);

-- password_reset_tokens: Códigos de recuperación de contraseña; se guardan solo como hash, de un solo
-- uso y con intentos limitados.
CREATE TABLE password_reset_tokens (
    id serial NOT NULL,
    usuario_id integer NOT NULL,
    expires_at timestamptz NOT NULL,
    used boolean NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    codigo_hash varchar(255) NOT NULL,
    intentos integer NOT NULL,
    verificado boolean NOT NULL,
    session_token_hash varchar(255),
    CONSTRAINT pk_password_reset_tokens PRIMARY KEY (id),
    CONSTRAINT fk_password_reset_tokens_usuario_id_usuarios FOREIGN KEY (usuario_id) REFERENCES
            usuarios(id)
);
CREATE INDEX ix_password_reset_tokens_session_token_hash ON password_reset_tokens USING btree
        (session_token_hash);
CREATE INDEX ix_password_reset_tokens_usuario_id ON password_reset_tokens USING btree (usuario_id);

-- ventas: Cabecera de cada venta con su consecutivo, total y estado; la anulada se conserva con motivo.
CREATE TABLE ventas (
    id serial NOT NULL,
    empresa_id integer NOT NULL,
    sede_id integer NOT NULL,
    numero integer NOT NULL,
    usuario_id integer NOT NULL,
    fecha timestamptz NOT NULL,
    fecha_dia date NOT NULL,
    total numeric(14,2) NOT NULL,
    estado varchar(15) NOT NULL DEFAULT 'registrada'::character varying,
    observacion varchar(500),
    anulada_por integer,
    anulada_en timestamptz,
    motivo_anulacion varchar(500),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT pk_ventas PRIMARY KEY (id),
    CONSTRAINT uq_ventas_empresa_numero UNIQUE (empresa_id, numero),
    CONSTRAINT fk_ventas_anulada_por_usuarios FOREIGN KEY (anulada_por) REFERENCES usuarios(id),
    CONSTRAINT fk_ventas_empresa_id_empresas FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    CONSTRAINT fk_ventas_sede_id_sedes FOREIGN KEY (sede_id) REFERENCES sedes(id),
    CONSTRAINT fk_ventas_usuario_id_usuarios FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);
CREATE INDEX ix_ventas_empresa_fecha_dia ON ventas USING btree (empresa_id, fecha_dia);
CREATE INDEX ix_ventas_sede_fecha_dia ON ventas USING btree (sede_id, fecha_dia);

-- alertas: Alertas de inventario abiertas y resueltas; nunca hay dos activas iguales para una sede y un
-- producto.
CREATE TABLE alertas (
    id bigserial NOT NULL,
    empresa_id integer NOT NULL,
    sede_id integer NOT NULL,
    producto_id integer NOT NULL,
    tipo varchar(30) NOT NULL,
    prioridad varchar(10) NOT NULL,
    estado varchar(10) NOT NULL,
    mensaje varchar(300) NOT NULL,
    detalle jsonb NOT NULL,
    abierta_en timestamptz NOT NULL DEFAULT now(),
    resuelta_en timestamptz,
    CONSTRAINT pk_alertas PRIMARY KEY (id),
    CONSTRAINT fk_alertas_empresa_id_empresas FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    CONSTRAINT fk_alertas_sede_id_inventario_sede FOREIGN KEY (sede_id, producto_id) REFERENCES
            inventario_sede(sede_id, producto_id)
);
CREATE INDEX ix_alertas_empresa_estado ON alertas USING btree (empresa_id, estado);
CREATE UNIQUE INDEX uq_alertas_activa ON alertas USING btree (sede_id, producto_id, tipo) WHERE
        ((estado)::text = 'activa'::text);

-- predicciones: Pronóstico de demanda por producto y sede, con intervalo, modelo elegido, confianza y
-- métricas.
CREATE TABLE predicciones (
    id bigserial NOT NULL,
    empresa_id integer NOT NULL,
    ejecucion_id integer NOT NULL,
    sede_id integer NOT NULL,
    producto_id integer NOT NULL,
    fecha_inicio date NOT NULL,
    fecha_fin date NOT NULL,
    demanda_estimada numeric(14,2) NOT NULL,
    limite_inferior numeric(14,2),
    limite_superior numeric(14,2),
    modelo varchar(40) NOT NULL,
    es_linea_base boolean NOT NULL,
    confianza varchar(10) NOT NULL,
    metricas jsonb NOT NULL,
    serie_diaria jsonb NOT NULL,
    advertencias jsonb NOT NULL,
    generada_en timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT pk_predicciones PRIMARY KEY (id),
    CONSTRAINT uq_predicciones_ejecucion_serie UNIQUE (ejecucion_id, sede_id, producto_id),
    CONSTRAINT fk_predicciones_ejecucion_id_ejecuciones_prediccion FOREIGN KEY (ejecucion_id) REFERENCES
            ejecuciones_prediccion(id) ON DELETE CASCADE,
    CONSTRAINT fk_predicciones_empresa_id_empresas FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    CONSTRAINT fk_predicciones_producto_id_productos FOREIGN KEY (producto_id) REFERENCES productos(id),
    CONSTRAINT fk_predicciones_sede_id_sedes FOREIGN KEY (sede_id) REFERENCES sedes(id)
);
CREATE INDEX ix_predicciones_ejecucion_id ON predicciones USING btree (ejecucion_id);
CREATE INDEX ix_predicciones_empresa_serie ON predicciones USING btree (empresa_id, sede_id,
        producto_id);

-- recomendaciones: Sugerencias de reabastecimiento o traslado con su justificación y su estado de
-- revisión.
CREATE TABLE recomendaciones (
    id serial NOT NULL,
    empresa_id integer NOT NULL,
    ejecucion_id integer NOT NULL,
    tipo varchar(20) NOT NULL,
    producto_id integer NOT NULL,
    sede_id integer NOT NULL,
    sede_origen_id integer,
    cantidad_sugerida integer NOT NULL,
    prioridad varchar(10) NOT NULL,
    estado varchar(15) NOT NULL,
    resumen varchar(600) NOT NULL,
    justificacion jsonb NOT NULL,
    generada_en timestamptz NOT NULL DEFAULT now(),
    revisada_por integer,
    revisada_en timestamptz,
    comentario_revision varchar(500),
    CONSTRAINT pk_recomendaciones PRIMARY KEY (id),
    CONSTRAINT fk_recomendaciones_ejecucion_id_ejecuciones_prediccion FOREIGN KEY (ejecucion_id)
            REFERENCES ejecuciones_prediccion(id),
    CONSTRAINT fk_recomendaciones_empresa_id_empresas FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    CONSTRAINT fk_recomendaciones_producto_id_productos FOREIGN KEY (producto_id) REFERENCES
            productos(id),
    CONSTRAINT fk_recomendaciones_revisada_por_usuarios FOREIGN KEY (revisada_por) REFERENCES
            usuarios(id),
    CONSTRAINT fk_recomendaciones_sede_id_sedes FOREIGN KEY (sede_id) REFERENCES sedes(id),
    CONSTRAINT fk_recomendaciones_sede_origen_id_sedes FOREIGN KEY (sede_origen_id) REFERENCES sedes(id)
);
CREATE INDEX ix_recomendaciones_empresa_estado ON recomendaciones USING btree (empresa_id, estado);
CREATE INDEX ix_recomendaciones_producto_id ON recomendaciones USING btree (producto_id);
CREATE INDEX ix_recomendaciones_sede_id ON recomendaciones USING btree (sede_id);

-- venta_items: Líneas de cada venta con el precio congelado al momento de vender.
CREATE TABLE venta_items (
    id serial NOT NULL,
    venta_id integer NOT NULL,
    producto_id integer NOT NULL,
    cantidad integer NOT NULL,
    precio_unitario numeric(14,2) NOT NULL,
    subtotal numeric(14,2) NOT NULL,
    CONSTRAINT pk_venta_items PRIMARY KEY (id),
    CONSTRAINT uq_venta_items_venta_producto UNIQUE (venta_id, producto_id),
    CONSTRAINT ck_venta_items_cantidad_positiva CHECK ((cantidad > 0)),
    CONSTRAINT ck_venta_items_precio_no_negativo CHECK ((precio_unitario >= (0)::numeric)),
    CONSTRAINT fk_venta_items_producto_id_productos FOREIGN KEY (producto_id) REFERENCES productos(id),
    CONSTRAINT fk_venta_items_venta_id_ventas FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE
            CASCADE
);
CREATE INDEX ix_venta_items_producto_id ON venta_items USING btree (producto_id);
CREATE INDEX ix_venta_items_venta_id ON venta_items USING btree (venta_id);

-- traslados: Solicitudes de traslado entre sedes con quién y cuándo las solicitó, aprobó, confirmó o
-- cerró.
CREATE TABLE traslados (
    id serial NOT NULL,
    empresa_id integer NOT NULL,
    numero integer NOT NULL,
    sede_origen_id integer NOT NULL,
    sede_destino_id integer NOT NULL,
    estado varchar(15) NOT NULL,
    observacion varchar(500),
    recomendacion_id integer,
    solicitado_por integer NOT NULL,
    solicitado_en timestamptz NOT NULL,
    aprobado_por integer,
    aprobado_en timestamptz,
    confirmado_por integer,
    confirmado_en timestamptz,
    cerrado_por integer,
    cerrado_en timestamptz,
    motivo_cierre varchar(500),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT pk_traslados PRIMARY KEY (id),
    CONSTRAINT uq_traslados_empresa_numero UNIQUE (empresa_id, numero),
    CONSTRAINT uq_traslados_recomendacion_id UNIQUE (recomendacion_id),
    CONSTRAINT ck_traslados_sedes_distintas CHECK ((sede_origen_id <> sede_destino_id)),
    CONSTRAINT fk_traslados_aprobado_por_usuarios FOREIGN KEY (aprobado_por) REFERENCES usuarios(id),
    CONSTRAINT fk_traslados_cerrado_por_usuarios FOREIGN KEY (cerrado_por) REFERENCES usuarios(id),
    CONSTRAINT fk_traslados_confirmado_por_usuarios FOREIGN KEY (confirmado_por) REFERENCES
            usuarios(id),
    CONSTRAINT fk_traslados_empresa_id_empresas FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    CONSTRAINT fk_traslados_recomendacion_id_recomendaciones FOREIGN KEY (recomendacion_id) REFERENCES
            recomendaciones(id),
    CONSTRAINT fk_traslados_sede_destino_id_sedes FOREIGN KEY (sede_destino_id) REFERENCES sedes(id),
    CONSTRAINT fk_traslados_sede_origen_id_sedes FOREIGN KEY (sede_origen_id) REFERENCES sedes(id),
    CONSTRAINT fk_traslados_solicitado_por_usuarios FOREIGN KEY (solicitado_por) REFERENCES usuarios(id)
);
CREATE INDEX ix_traslados_empresa_estado ON traslados USING btree (empresa_id, estado);
CREATE INDEX ix_traslados_sede_destino_id ON traslados USING btree (sede_destino_id);
CREATE INDEX ix_traslados_sede_origen_id ON traslados USING btree (sede_origen_id);

-- movimientos: Historial inalterable de cada cambio de existencias con saldo anterior y posterior (solo
-- inserción).
CREATE TABLE movimientos (
    id bigserial NOT NULL,
    empresa_id integer NOT NULL,
    sede_id integer NOT NULL,
    producto_id integer NOT NULL,
    tipo varchar(30) NOT NULL,
    motivo varchar(40),
    delta integer NOT NULL,
    saldo_anterior integer NOT NULL,
    saldo_posterior integer NOT NULL,
    sede_contraparte_id integer,
    usuario_id integer NOT NULL,
    fecha timestamptz NOT NULL,
    observacion varchar(500),
    venta_id integer,
    traslado_id integer,
    created_at timestamptz NOT NULL DEFAULT now(),
    entrada_id integer,
    CONSTRAINT pk_movimientos PRIMARY KEY (id),
    CONSTRAINT ck_movimientos_delta_distinto_de_cero CHECK ((delta <> 0)),
    CONSTRAINT ck_movimientos_saldo_posterior_no_negativo CHECK ((saldo_posterior >= 0)),
    CONSTRAINT fk_movimientos_empresa_id_empresas FOREIGN KEY (empresa_id) REFERENCES empresas(id),
    CONSTRAINT fk_movimientos_entrada_id_entradas_inventario FOREIGN KEY (entrada_id) REFERENCES
            entradas_inventario(id),
    CONSTRAINT fk_movimientos_producto_id_productos FOREIGN KEY (producto_id) REFERENCES productos(id),
    CONSTRAINT fk_movimientos_sede_contraparte_id_sedes FOREIGN KEY (sede_contraparte_id) REFERENCES
            sedes(id),
    CONSTRAINT fk_movimientos_sede_id_sedes FOREIGN KEY (sede_id) REFERENCES sedes(id),
    CONSTRAINT fk_movimientos_traslado_id_traslados FOREIGN KEY (traslado_id) REFERENCES traslados(id),
    CONSTRAINT fk_movimientos_usuario_id_usuarios FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    CONSTRAINT fk_movimientos_venta_id_ventas FOREIGN KEY (venta_id) REFERENCES ventas(id)
);
CREATE INDEX ix_movimientos_empresa_fecha ON movimientos USING btree (empresa_id, fecha);
CREATE INDEX ix_movimientos_entrada_id ON movimientos USING btree (entrada_id);
CREATE INDEX ix_movimientos_producto_id ON movimientos USING btree (producto_id);
CREATE INDEX ix_movimientos_sede_producto_fecha ON movimientos USING btree (sede_id, producto_id,
        fecha);
CREATE INDEX ix_movimientos_tipo ON movimientos USING btree (tipo);
CREATE INDEX ix_movimientos_traslado_id ON movimientos USING btree (traslado_id);
CREATE INDEX ix_movimientos_venta_id ON movimientos USING btree (venta_id);
CREATE TRIGGER tr_movimientos_inmutable BEFORE DELETE OR UPDATE ON movimientos FOR EACH ROW EXECUTE
        FUNCTION inventia_bloquear_modificacion();

-- traslado_items: Líneas de cada traslado (producto y cantidad).
CREATE TABLE traslado_items (
    id serial NOT NULL,
    traslado_id integer NOT NULL,
    producto_id integer NOT NULL,
    cantidad integer NOT NULL,
    CONSTRAINT pk_traslado_items PRIMARY KEY (id),
    CONSTRAINT uq_traslado_items_traslado_producto UNIQUE (traslado_id, producto_id),
    CONSTRAINT ck_traslado_items_cantidad_positiva CHECK ((cantidad > 0)),
    CONSTRAINT fk_traslado_items_producto_id_productos FOREIGN KEY (producto_id) REFERENCES
            productos(id),
    CONSTRAINT fk_traslado_items_traslado_id_traslados FOREIGN KEY (traslado_id) REFERENCES
            traslados(id) ON DELETE CASCADE
);
CREATE INDEX ix_traslado_items_producto_id ON traslado_items USING btree (producto_id);
CREATE INDEX ix_traslado_items_traslado_id ON traslado_items USING btree (traslado_id);
