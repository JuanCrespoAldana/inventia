/* Generado con openapi-typescript a partir de /openapi.json del backend. No editar a mano.
   Regenerar: npm run tipos (ver docs/DESARROLLO.md). Solo se conserva el bloque de esquemas. */

export interface components {
    schemas: {
        /** AjusteCrear */
        AjusteCrear: {
            /** Sede Id */
            sede_id: number;
            /** Producto Id */
            producto_id: number;
            /**
             * Cantidad Real
             * @description Existencias contadas físicamente
             */
            cantidad_real: number;
            /**
             * Motivo
             * @default conteo_fisico
             * @enum {string}
             */
            motivo: "conteo_fisico" | "correccion" | "otro";
            /** Observacion */
            observacion: string;
        };
        /** AlertaSalida */
        AlertaSalida: {
            /** Id */
            id: number;
            /** Tipo */
            tipo: string;
            /** Prioridad */
            prioridad: string;
            /** Estado */
            estado: string;
            /** Mensaje */
            mensaje: string;
            /** Detalle */
            detalle: {
                [key: string]: unknown;
            };
            /**
             * Abierta En
             * Format: date-time
             */
            abierta_en: string;
            /** Resuelta En */
            resuelta_en: string | null;
            producto: components["schemas"]["ProductoResumen"];
            sede: components["schemas"]["SedeResumen"];
        };
        /** CambiarPasswordEntrada */
        CambiarPasswordEntrada: {
            /** Password Actual */
            password_actual: string;
            /** Nueva Password */
            nueva_password: string;
        };
        /** CatalogoModelos */
        CatalogoModelos: {
            /** Modelos */
            modelos: components["schemas"]["ModeloInfo"][];
            /** Minimo Dias Historia */
            minimo_dias_historia: number;
            /** Minimo Dias Con Ventas */
            minimo_dias_con_ventas: number;
            /** Mejora Minima Modelo Avanzado Pct */
            mejora_minima_modelo_avanzado_pct: number;
        };
        /** CategoriaActualizar */
        CategoriaActualizar: {
            /** Nombre */
            nombre?: string | null;
            /** Descripcion */
            descripcion?: string | null;
        };
        /** CategoriaCrear */
        CategoriaCrear: {
            /** Nombre */
            nombre: string;
            /** Descripcion */
            descripcion?: string | null;
        };
        /** CategoriaEstado */
        CategoriaEstado: {
            /** Activa */
            activa: boolean;
        };
        /** CategoriaResumen */
        CategoriaResumen: {
            /** Id */
            id: number;
            /** Nombre */
            nombre: string;
        };
        /** CategoriaSalida */
        CategoriaSalida: {
            /** Id */
            id: number;
            /** Nombre */
            nombre: string;
            /** Descripcion */
            descripcion: string | null;
            /** Activa */
            activa: boolean;
            /**
             * Total Productos
             * @default 0
             */
            total_productos: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * ConfiguracionInicial
         * @description Alta controlada de la empresa y de su primer administrador (RF-007, RF-001).
         */
        ConfiguracionInicial: {
            /** Empresa Nombre */
            empresa_nombre: string;
            /** Empresa Identificacion */
            empresa_identificacion: string;
            /** Empresa Direccion */
            empresa_direccion?: string | null;
            /** Empresa Ciudad */
            empresa_ciudad?: string | null;
            /** Empresa Telefono */
            empresa_telefono?: string | null;
            /** Empresa Email */
            empresa_email?: string | null;
            /** Admin Nombre */
            admin_nombre: string;
            /**
             * Admin Email
             * Format: email
             */
            admin_email: string;
            /** Admin Password */
            admin_password: string;
            /**
             * Token Configuracion
             * @default
             */
            token_configuracion: string;
        };
        /** ConsolidadoFila */
        ConsolidadoFila: {
            producto: components["schemas"]["ProductoResumen"];
            /** Categoria */
            categoria: string;
            /** Producto Activo */
            producto_activo: boolean;
            /** Total */
            total: number;
            /** Costo */
            costo: number | null;
            /** Valor */
            valor: number | null;
            /** Sedes En Alerta */
            sedes_en_alerta: number;
            /** Sedes */
            sedes: components["schemas"]["DesgloseSede"][];
        };
        /** DesgloseSede */
        DesgloseSede: {
            /** Sede Id */
            sede_id: number;
            /** Sede */
            sede: string;
            /** Cantidad */
            cantidad: number;
            /** Stock Minimo */
            stock_minimo: number;
            /** Stock Maximo */
            stock_maximo: number | null;
            /**
             * Estado
             * @enum {string}
             */
            estado: "agotado" | "bajo" | "normal" | "excesivo";
        };
        /** EjecucionSalida */
        EjecucionSalida: {
            /** Id */
            id: number;
            /** Estado */
            estado: string;
            /** Horizonte Dias */
            horizonte_dias: number;
            /** Fecha Corte */
            fecha_corte: string | null;
            /** Parametros */
            parametros: {
                [key: string]: unknown;
            };
            /** Resumen */
            resumen: {
                [key: string]: unknown;
            };
            /** Error */
            error: string | null;
            /**
             * Creada En
             * Format: date-time
             */
            creada_en: string;
            /** Iniciada En */
            iniciada_en: string | null;
            /** Finalizada En */
            finalizada_en: string | null;
            /** Solicitada Por */
            solicitada_por?: string | null;
        };
        /** EjecutarPrediccion */
        EjecutarPrediccion: {
            /**
             * Horizonte Dias
             * @description Vacío = parámetro de la empresa
             */
            horizonte_dias?: number | null;
        };
        /** EmpresaActualizar */
        EmpresaActualizar: {
            /** Nombre */
            nombre?: string | null;
            /** Identificacion */
            identificacion?: string | null;
            /** Direccion */
            direccion?: string | null;
            /** Ciudad */
            ciudad?: string | null;
            /** Telefono */
            telefono?: string | null;
            /** Email */
            email?: string | null;
        };
        /** EmpresaSalida */
        EmpresaSalida: {
            /** Id */
            id: number;
            /** Nombre */
            nombre: string;
            /** Identificacion */
            identificacion: string | null;
            /** Direccion */
            direccion: string | null;
            /** Ciudad */
            ciudad: string | null;
            /** Telefono */
            telefono: string | null;
            /** Email */
            email: string | null;
            /** Activa */
            activa: boolean;
            /** Parametros */
            parametros: {
                [key: string]: number;
            };
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** EntradaCrear */
        EntradaCrear: {
            /** Sede Id */
            sede_id: number;
            /**
             * Motivo
             * @default compra
             * @enum {string}
             */
            motivo: "compra" | "devolucion_cliente" | "inventario_inicial" | "produccion" | "otro";
            /** Observacion */
            observacion?: string | null;
            /** Items */
            items: components["schemas"]["ItemCantidad"][];
        };
        /** EstadoInstalacion */
        EstadoInstalacion: {
            /** Configurado */
            configurado: boolean;
            /** Requiere Token */
            requiere_token: boolean;
            /** Nombre Aplicacion */
            nombre_aplicacion: string;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** InventarioFila */
        InventarioFila: {
            producto: components["schemas"]["ProductoResumen"];
            /** Categoria */
            categoria: string;
            /** Producto Activo */
            producto_activo: boolean;
            /** Cantidad */
            cantidad: number;
            /** Stock Minimo */
            stock_minimo: number;
            /** Stock Maximo */
            stock_maximo: number | null;
            /**
             * Estado
             * @enum {string}
             */
            estado: "agotado" | "bajo" | "normal" | "excesivo";
            /** Costo */
            costo: number | null;
            /** Valor */
            valor: number | null;
            /** Actualizado En */
            actualizado_en: string | null;
        };
        /** InventarioSedePagina */
        InventarioSedePagina: {
            /** Items */
            items: components["schemas"]["InventarioFila"][];
            /** Total */
            total: number;
            /** Pagina */
            pagina: number;
            /** Tamano */
            tamano: number;
            /** Paginas */
            paginas: number;
            sede: components["schemas"]["SedeResumen"];
        };
        /** ItemCantidad */
        ItemCantidad: {
            /** Producto Id */
            producto_id: number;
            /**
             * Cantidad
             * @description Unidades enteras, mayor que cero
             */
            cantidad: number;
        };
        /** LlaveCreada */
        LlaveCreada: {
            /** Id */
            id: number;
            /** Nombre */
            nombre: string;
            /** Prefijo */
            prefijo: string;
            /** Alcances */
            alcances: string[];
            /** Sede Id */
            sede_id: number | null;
            /** Activa */
            activa: boolean;
            /**
             * Creada En
             * Format: date-time
             */
            creada_en: string;
            /** Expira En */
            expira_en: string | null;
            /** Ultimo Uso En */
            ultimo_uso_en: string | null;
            /** Llave */
            llave: string;
        };
        /** LlaveCrear */
        LlaveCrear: {
            /** Nombre */
            nombre: string;
            /** Alcances */
            alcances: string[];
            /** Sede Id */
            sede_id?: number | null;
            /**
             * Dias Vigencia
             * @default 90
             */
            dias_vigencia: number | null;
        };
        /** LlaveSalida */
        LlaveSalida: {
            /** Id */
            id: number;
            /** Nombre */
            nombre: string;
            /** Prefijo */
            prefijo: string;
            /** Alcances */
            alcances: string[];
            /** Sede Id */
            sede_id: number | null;
            /** Activa */
            activa: boolean;
            /**
             * Creada En
             * Format: date-time
             */
            creada_en: string;
            /** Expira En */
            expira_en: string | null;
            /** Ultimo Uso En */
            ultimo_uso_en: string | null;
        };
        /** LoginEntrada */
        LoginEntrada: {
            /**
             * Email
             * Format: email
             */
            email: string;
            /** Password */
            password: string;
        };
        /** Mensaje */
        Mensaje: {
            /** Mensaje */
            mensaje: string;
        };
        /** ModeloInfo */
        ModeloInfo: {
            /** Nombre */
            nombre: string;
            /** Descripcion */
            descripcion: string;
            /** Avanzado */
            avanzado: boolean;
            /** Es Linea Base */
            es_linea_base: boolean;
        };
        /** MovimientoSalida */
        MovimientoSalida: {
            /** Id */
            id: number;
            /**
             * Fecha
             * Format: date-time
             */
            fecha: string;
            /** Tipo */
            tipo: string;
            /** Motivo */
            motivo: string | null;
            /** Delta */
            delta: number;
            /** Saldo Anterior */
            saldo_anterior: number;
            /** Saldo Posterior */
            saldo_posterior: number;
            /** Observacion */
            observacion: string | null;
            producto: components["schemas"]["ProductoResumen"];
            sede: components["schemas"]["SedeResumen"];
            sede_contraparte?: components["schemas"]["SedeResumen"] | null;
            /** Usuario Id */
            usuario_id: number;
            /** Usuario Nombre */
            usuario_nombre?: string | null;
            /** Venta Id */
            venta_id?: number | null;
            /** Venta Numero */
            venta_numero?: number | null;
            /** Traslado Id */
            traslado_id?: number | null;
            /** Traslado Numero */
            traslado_numero?: number | null;
        };
        /** NivelesActualizar */
        NivelesActualizar: {
            /** Sede Id */
            sede_id: number;
            /** Producto Id */
            producto_id: number;
            /** Stock Minimo */
            stock_minimo: number;
            /** Stock Maximo */
            stock_maximo?: number | null;
        };
        /** NivelesSalida */
        NivelesSalida: {
            /** Sede Id */
            sede_id: number;
            /** Producto Id */
            producto_id: number;
            /** Cantidad */
            cantidad: number;
            /** Stock Minimo */
            stock_minimo: number;
            /** Stock Maximo */
            stock_maximo: number | null;
        };
        /** OpcionesAuditoria */
        OpcionesAuditoria: {
            /** Modulos */
            modulos: string[];
            /** Acciones */
            acciones: string[];
        };
        /** Pagina[AlertaSalida] */
        Pagina_AlertaSalida_: {
            /** Items */
            items: components["schemas"]["AlertaSalida"][];
            /** Total */
            total: number;
            /** Pagina */
            pagina: number;
            /** Tamano */
            tamano: number;
            /** Paginas */
            paginas: number;
        };
        /** Pagina[CategoriaSalida] */
        Pagina_CategoriaSalida_: {
            /** Items */
            items: components["schemas"]["CategoriaSalida"][];
            /** Total */
            total: number;
            /** Pagina */
            pagina: number;
            /** Tamano */
            tamano: number;
            /** Paginas */
            paginas: number;
        };
        /** Pagina[ConsolidadoFila] */
        Pagina_ConsolidadoFila_: {
            /** Items */
            items: components["schemas"]["ConsolidadoFila"][];
            /** Total */
            total: number;
            /** Pagina */
            pagina: number;
            /** Tamano */
            tamano: number;
            /** Paginas */
            paginas: number;
        };
        /** Pagina[EjecucionSalida] */
        Pagina_EjecucionSalida_: {
            /** Items */
            items: components["schemas"]["EjecucionSalida"][];
            /** Total */
            total: number;
            /** Pagina */
            pagina: number;
            /** Tamano */
            tamano: number;
            /** Paginas */
            paginas: number;
        };
        /** Pagina[MovimientoSalida] */
        Pagina_MovimientoSalida_: {
            /** Items */
            items: components["schemas"]["MovimientoSalida"][];
            /** Total */
            total: number;
            /** Pagina */
            pagina: number;
            /** Tamano */
            tamano: number;
            /** Paginas */
            paginas: number;
        };
        /** Pagina[PrediccionSalida] */
        Pagina_PrediccionSalida_: {
            /** Items */
            items: components["schemas"]["PrediccionSalida"][];
            /** Total */
            total: number;
            /** Pagina */
            pagina: number;
            /** Tamano */
            tamano: number;
            /** Paginas */
            paginas: number;
        };
        /** Pagina[ProductoSalida] */
        Pagina_ProductoSalida_: {
            /** Items */
            items: components["schemas"]["ProductoSalida"][];
            /** Total */
            total: number;
            /** Pagina */
            pagina: number;
            /** Tamano */
            tamano: number;
            /** Paginas */
            paginas: number;
        };
        /** Pagina[RecomendacionSalida] */
        Pagina_RecomendacionSalida_: {
            /** Items */
            items: components["schemas"]["RecomendacionSalida"][];
            /** Total */
            total: number;
            /** Pagina */
            pagina: number;
            /** Tamano */
            tamano: number;
            /** Paginas */
            paginas: number;
        };
        /** Pagina[RegistroAuditoria] */
        Pagina_RegistroAuditoria_: {
            /** Items */
            items: components["schemas"]["RegistroAuditoria"][];
            /** Total */
            total: number;
            /** Pagina */
            pagina: number;
            /** Tamano */
            tamano: number;
            /** Paginas */
            paginas: number;
        };
        /** Pagina[SedeDetalle] */
        Pagina_SedeDetalle_: {
            /** Items */
            items: components["schemas"]["SedeDetalle"][];
            /** Total */
            total: number;
            /** Pagina */
            pagina: number;
            /** Tamano */
            tamano: number;
            /** Paginas */
            paginas: number;
        };
        /** Pagina[TrasladoResumen] */
        Pagina_TrasladoResumen_: {
            /** Items */
            items: components["schemas"]["TrasladoResumen"][];
            /** Total */
            total: number;
            /** Pagina */
            pagina: number;
            /** Tamano */
            tamano: number;
            /** Paginas */
            paginas: number;
        };
        /** Pagina[UsuarioSalida] */
        Pagina_UsuarioSalida_: {
            /** Items */
            items: components["schemas"]["UsuarioSalida"][];
            /** Total */
            total: number;
            /** Pagina */
            pagina: number;
            /** Tamano */
            tamano: number;
            /** Paginas */
            paginas: number;
        };
        /** Pagina[VentaResumen] */
        Pagina_VentaResumen_: {
            /** Items */
            items: components["schemas"]["VentaResumen"][];
            /** Total */
            total: number;
            /** Pagina */
            pagina: number;
            /** Tamano */
            tamano: number;
            /** Paginas */
            paginas: number;
        };
        /**
         * ParametrosEmpresa
         * @description Reglas configurables del inventario y la predicción (se documentan en docs/PREDICCION.md).
         *
         *     Todos los campos son opcionales: solo se modifican los que se envían.
         */
        ParametrosEmpresa: {
            /** Plazo Entrega Dias */
            plazo_entrega_dias?: number | null;
            /** Dias Seguridad */
            dias_seguridad?: number | null;
            /** Dias Cobertura Objetivo */
            dias_cobertura_objetivo?: number | null;
            /** Horizonte Dias */
            horizonte_dias?: number | null;
            /** Umbral Cobertura Alerta Dias */
            umbral_cobertura_alerta_dias?: number | null;
            /** Dias Sin Rotacion */
            dias_sin_rotacion?: number | null;
            /** Dias Max Anulacion */
            dias_max_anulacion?: number | null;
        };
        /** PermisoSalida */
        PermisoSalida: {
            /** Codigo */
            codigo: string;
            /** Modulo */
            modulo: string;
            /** Descripcion */
            descripcion: string;
        };
        /** PrediccionSalida */
        PrediccionSalida: {
            /** Id */
            id: number;
            /** Ejecucion Id */
            ejecucion_id: number;
            producto: components["schemas"]["ProductoResumen"];
            sede: components["schemas"]["SedeResumen"];
            /**
             * Fecha Inicio
             * Format: date
             */
            fecha_inicio: string;
            /**
             * Fecha Fin
             * Format: date
             */
            fecha_fin: string;
            /** Demanda Estimada */
            demanda_estimada: number;
            /** Demanda Diaria */
            demanda_diaria: number;
            /** Limite Inferior */
            limite_inferior: number | null;
            /** Limite Superior */
            limite_superior: number | null;
            /** Modelo */
            modelo: string;
            /** Modelo Descripcion */
            modelo_descripcion: string;
            /** Es Linea Base */
            es_linea_base: boolean;
            /** Confianza */
            confianza: string;
            /** Metricas */
            metricas: {
                [key: string]: unknown;
            };
            /** Advertencias */
            advertencias: string[];
            /** Existencias Actuales */
            existencias_actuales: number | null;
            /** Cobertura Dias */
            cobertura_dias: number | null;
            /**
             * Generada En
             * Format: date-time
             */
            generada_en: string;
        };
        /**
         * ProductoActualizar
         * @description El código no se puede modificar: identifica al producto en todo su historial.
         */
        ProductoActualizar: {
            /** Nombre */
            nombre?: string | null;
            /** Descripcion */
            descripcion?: string | null;
            /** Categoria Id */
            categoria_id?: number | null;
            /** Unidad Medida */
            unidad_medida?: ("unidad" | "caja" | "paquete" | "docena" | "par" | "bolsa" | "rollo" | "frasco" | "kg" | "g" | "lb" | "litro" | "ml" | "metro") | null;
            /** Costo */
            costo?: number | string | null;
            /** Precio Venta */
            precio_venta?: number | string | null;
        };
        /** ProductoCrear */
        ProductoCrear: {
            /** Codigo */
            codigo: string;
            /** Nombre */
            nombre: string;
            /** Descripcion */
            descripcion?: string | null;
            /** Categoria Id */
            categoria_id: number;
            /**
             * Unidad Medida
             * @default unidad
             * @enum {string}
             */
            unidad_medida: "unidad" | "caja" | "paquete" | "docena" | "par" | "bolsa" | "rollo" | "frasco" | "kg" | "g" | "lb" | "litro" | "ml" | "metro";
            /** Costo */
            costo?: number | string | null;
            /** Precio Venta */
            precio_venta?: number | string | null;
        };
        /** ProductoEstado */
        ProductoEstado: {
            /** Activo */
            activo: boolean;
        };
        /** ProductoResumen */
        ProductoResumen: {
            /** Id */
            id: number;
            /** Codigo */
            codigo: string;
            /** Nombre */
            nombre: string;
            /** Unidad Medida */
            unidad_medida: string;
        };
        /** ProductoSalida */
        ProductoSalida: {
            /** Id */
            id: number;
            /** Codigo */
            codigo: string;
            /** Nombre */
            nombre: string;
            /** Descripcion */
            descripcion: string | null;
            categoria: components["schemas"]["CategoriaResumen"];
            /** Unidad Medida */
            unidad_medida: string;
            /** Costo */
            costo: number | null;
            /** Precio Venta */
            precio_venta: number | null;
            /** Activo */
            activo: boolean;
            /**
             * Existencias Total
             * @default 0
             */
            existencias_total: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** RecomendacionSalida */
        RecomendacionSalida: {
            /** Id */
            id: number;
            /** Tipo */
            tipo: string;
            /** Prioridad */
            prioridad: string;
            /** Estado */
            estado: string;
            producto: components["schemas"]["ProductoResumen"];
            sede: components["schemas"]["SedeResumen"];
            sede_origen: components["schemas"]["SedeResumen"] | null;
            /** Cantidad Sugerida */
            cantidad_sugerida: number;
            /** Resumen */
            resumen: string;
            /** Justificacion */
            justificacion: {
                [key: string]: unknown;
            };
            /** Ejecucion Id */
            ejecucion_id: number | null;
            /**
             * Generada En
             * Format: date-time
             */
            generada_en: string;
            /** Revisada Por Nombre */
            revisada_por_nombre: string | null;
            /** Revisada En */
            revisada_en: string | null;
            /** Comentario Revision */
            comentario_revision: string | null;
            /** Traslado Id */
            traslado_id?: number | null;
            /** Traslado Numero */
            traslado_numero?: number | null;
            /**
             * Acciones
             * @default []
             */
            acciones: string[];
        };
        /** RegistroAuditoria */
        RegistroAuditoria: {
            /** Id */
            id: number;
            /**
             * Fecha
             * Format: date-time
             */
            fecha: string;
            /** Usuario Email */
            usuario_email: string | null;
            /** Modulo */
            modulo: string;
            /** Accion */
            accion: string;
            /** Entidad */
            entidad: string | null;
            /** Entidad Id */
            entidad_id: string | null;
            /** Resultado */
            resultado: string;
            /** Detalle */
            detalle: {
                [key: string]: unknown;
            };
            /** Ip */
            ip: string | null;
            /** Sede Id */
            sede_id: number | null;
        };
        /** RestablecerPasswordEntrada */
        RestablecerPasswordEntrada: {
            /** Session Token */
            session_token: string;
            /** Nueva Password */
            nueva_password: string;
        };
        /** ResultadoGeneracion */
        ResultadoGeneracion: {
            /** Ejecucion Id */
            ejecucion_id: number;
            /** Generadas */
            generadas: number;
            /** Reabastecimientos */
            reabastecimientos: number;
            /** Traslados */
            traslados: number;
            /** Reemplazadas */
            reemplazadas: number;
            /** Series Evaluadas */
            series_evaluadas: number;
        };
        /** ResultadoOperacion */
        ResultadoOperacion: {
            /** Mensaje */
            mensaje: string;
            /** Movimientos */
            movimientos: components["schemas"]["MovimientoSalida"][];
            /**
             * Alertas Abiertas
             * @default 0
             */
            alertas_abiertas: number;
            /**
             * Alertas Resueltas
             * @default 0
             */
            alertas_resueltas: number;
        };
        /** ResultadoRecalculo */
        ResultadoRecalculo: {
            /** Abiertas */
            abiertas: number;
            /** Resueltas */
            resueltas: number;
            /** Actualizadas */
            actualizadas: number;
            /** Activas */
            activas: number;
            /** Series Evaluadas */
            series_evaluadas: number;
        };
        /** ResumenAlertas */
        ResumenAlertas: {
            /** Total */
            total: number;
            /** Por Tipo */
            por_tipo: {
                [key: string]: number;
            };
            /** Por Prioridad */
            por_prioridad: {
                [key: string]: number;
            };
        };
        /** RevisionRecomendacion */
        RevisionRecomendacion: {
            /** Comentario */
            comentario?: string | null;
        };
        /** RolActualizar */
        RolActualizar: {
            /** Nombre */
            nombre?: string | null;
            /** Descripcion */
            descripcion?: string | null;
            /** Alcance */
            alcance?: ("empresa" | "sede") | null;
            /** Activo */
            activo?: boolean | null;
        };
        /** RolCrear */
        RolCrear: {
            /** Nombre */
            nombre: string;
            /** Descripcion */
            descripcion?: string | null;
            /**
             * Alcance
             * @default sede
             * @enum {string}
             */
            alcance: "empresa" | "sede";
            /** Permisos */
            permisos?: string[];
        };
        /** RolPermisosEntrada */
        RolPermisosEntrada: {
            /** Permisos */
            permisos: string[];
        };
        /** RolResumen */
        RolResumen: {
            /** Id */
            id: number;
            /** Clave */
            clave: string | null;
            /** Nombre */
            nombre: string;
            /** Alcance */
            alcance: string;
        };
        /** RolSalida */
        RolSalida: {
            /** Id */
            id: number;
            /** Clave */
            clave: string | null;
            /** Nombre */
            nombre: string;
            /** Descripcion */
            descripcion: string | null;
            /** Alcance */
            alcance: string;
            /** Es Sistema */
            es_sistema: boolean;
            /** Activo */
            activo: boolean;
            /** Permisos */
            permisos: string[];
            /** Total Usuarios */
            total_usuarios: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** SalidaCrear */
        SalidaCrear: {
            /** Sede Id */
            sede_id: number;
            /**
             * Motivo
             * @enum {string}
             */
            motivo: "perdida" | "deterioro" | "consumo_interno" | "devolucion_proveedor" | "otro";
            /** Observacion */
            observacion?: string | null;
            /** Items */
            items: components["schemas"]["ItemCantidad"][];
        };
        /** SedeActualizar */
        SedeActualizar: {
            /** Nombre */
            nombre?: string | null;
            /** Direccion */
            direccion?: string | null;
            /** Ciudad */
            ciudad?: string | null;
        };
        /** SedeCrear */
        SedeCrear: {
            /** Nombre */
            nombre: string;
            /** Direccion */
            direccion?: string | null;
            /** Ciudad */
            ciudad: string;
        };
        /** SedeDetalle */
        SedeDetalle: {
            /** Id */
            id: number;
            /** Nombre */
            nombre: string;
            /** Direccion */
            direccion: string | null;
            /** Ciudad */
            ciudad: string | null;
            /** Activa */
            activa: boolean;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /**
             * Total Usuarios
             * @default 0
             */
            total_usuarios: number;
            /**
             * Unidades En Existencia
             * @default 0
             */
            unidades_en_existencia: number;
        };
        /** SedeEstado */
        SedeEstado: {
            /** Activa */
            activa: boolean;
        };
        /** SedeResumen */
        SedeResumen: {
            /** Id */
            id: number;
            /** Nombre */
            nombre: string;
            /** Ciudad */
            ciudad?: string | null;
        };
        /** SedeUsuario */
        SedeUsuario: {
            /** Id */
            id: number;
            /** Nombre */
            nombre: string;
        };
        /** SerieDemanda */
        SerieDemanda: {
            producto: components["schemas"]["ProductoResumen"];
            sede: components["schemas"]["SedeResumen"];
            /** Ejecucion Id */
            ejecucion_id: number | null;
            /** Historial */
            historial: [
                string,
                number
            ][];
            /** Pronostico */
            pronostico: [
                string,
                number
            ][];
            /** Modelo */
            modelo: string | null;
            /** Confianza */
            confianza: string | null;
            /** Demanda Estimada */
            demanda_estimada: number | null;
            /** Limite Inferior */
            limite_inferior: number | null;
            /** Limite Superior */
            limite_superior: number | null;
            /** Metricas */
            metricas: {
                [key: string]: unknown;
            };
            /** Advertencias */
            advertencias: string[];
            /** Motivo Sin Prediccion */
            motivo_sin_prediccion: string | null;
        };
        /** SolicitudRecuperacion */
        SolicitudRecuperacion: {
            /**
             * Email
             * Format: email
             */
            email: string;
        };
        /** TipoReporte */
        TipoReporte: {
            /** Tipo */
            tipo: string;
            /** Titulo */
            titulo: string;
            /** Permiso */
            permiso: string;
        };
        /** TokenSalida */
        TokenSalida: {
            /** Access Token */
            access_token: string;
            /**
             * Token Type
             * @default bearer
             */
            token_type: string;
            /** Expira En Minutos */
            expira_en_minutos: number;
            usuario: components["schemas"]["UsuarioSesion"];
        };
        /** TrasladoCrear */
        TrasladoCrear: {
            /** Sede Origen Id */
            sede_origen_id: number;
            /** Sede Destino Id */
            sede_destino_id: number;
            /** Observacion */
            observacion?: string | null;
            /** Items */
            items: components["schemas"]["ItemCantidad"][];
        };
        /** TrasladoDetalle */
        TrasladoDetalle: {
            /** Id */
            id: number;
            /** Numero */
            numero: number;
            /** Estado */
            estado: string;
            origen: components["schemas"]["SedeResumen"];
            destino: components["schemas"]["SedeResumen"];
            /** Unidades */
            unidades: number;
            /** Lineas */
            lineas: number;
            /** Observacion */
            observacion: string | null;
            /**
             * Solicitado En
             * Format: date-time
             */
            solicitado_en: string;
            /** Solicitado Por Nombre */
            solicitado_por_nombre: string | null;
            /** Recomendacion Id */
            recomendacion_id: number | null;
            /** Items */
            items: components["schemas"]["TrasladoItemSalida"][];
            /** Aprobado Por Nombre */
            aprobado_por_nombre?: string | null;
            /** Aprobado En */
            aprobado_en?: string | null;
            /** Confirmado Por Nombre */
            confirmado_por_nombre?: string | null;
            /** Confirmado En */
            confirmado_en?: string | null;
            /** Cerrado Por Nombre */
            cerrado_por_nombre?: string | null;
            /** Cerrado En */
            cerrado_en?: string | null;
            /** Motivo Cierre */
            motivo_cierre?: string | null;
            /**
             * Acciones
             * @default []
             */
            acciones: string[];
        };
        /** TrasladoItemSalida */
        TrasladoItemSalida: {
            producto: components["schemas"]["ProductoResumen"];
            /** Cantidad */
            cantidad: number;
            /** Existencias Origen */
            existencias_origen: number;
            /** Existencias Destino */
            existencias_destino: number;
        };
        /** TrasladoMotivo */
        TrasladoMotivo: {
            /** Motivo */
            motivo: string;
        };
        /** TrasladoResumen */
        TrasladoResumen: {
            /** Id */
            id: number;
            /** Numero */
            numero: number;
            /** Estado */
            estado: string;
            origen: components["schemas"]["SedeResumen"];
            destino: components["schemas"]["SedeResumen"];
            /** Unidades */
            unidades: number;
            /** Lineas */
            lineas: number;
            /** Observacion */
            observacion: string | null;
            /**
             * Solicitado En
             * Format: date-time
             */
            solicitado_en: string;
            /** Solicitado Por Nombre */
            solicitado_por_nombre: string | null;
            /** Recomendacion Id */
            recomendacion_id: number | null;
        };
        /** UsuarioActualizar */
        UsuarioActualizar: {
            /** Nombre */
            nombre?: string | null;
            /** Email */
            email?: string | null;
            /** Rol Id */
            rol_id?: number | null;
            /** Sede Id */
            sede_id?: number | null;
            /**
             * Quitar Sede
             * @default false
             */
            quitar_sede: boolean;
        };
        /** UsuarioCrear */
        UsuarioCrear: {
            /** Nombre */
            nombre: string;
            /**
             * Email
             * Format: email
             */
            email: string;
            /** Password */
            password: string;
            /** Rol Id */
            rol_id: number;
            /** Sede Id */
            sede_id?: number | null;
            /**
             * Forzar Cambio Password
             * @default true
             */
            forzar_cambio_password: boolean;
        };
        /** UsuarioEstado */
        UsuarioEstado: {
            /** Activo */
            activo: boolean;
        };
        /** UsuarioRestablecerPassword */
        UsuarioRestablecerPassword: {
            /** Nueva Password */
            nueva_password: string;
        };
        /** UsuarioSalida */
        UsuarioSalida: {
            /** Id */
            id: number;
            /** Nombre */
            nombre: string;
            /** Email */
            email: string;
            /** Activo */
            activo: boolean;
            rol: components["schemas"]["RolResumen"];
            sede: components["schemas"]["SedeUsuario"] | null;
            /** Bloqueado */
            bloqueado: boolean;
            /** Debe Cambiar Password */
            debe_cambiar_password: boolean;
            /** Ultimo Acceso */
            ultimo_acceso: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /**
         * UsuarioSesion
         * @description Lo que necesita la interfaz tras iniciar sesión: identidad, rol, sede y permisos efectivos.
         */
        UsuarioSesion: {
            /** Id */
            id: number;
            /** Nombre */
            nombre: string;
            /** Email */
            email: string;
            /** Empresa Id */
            empresa_id: number;
            /** Empresa Nombre */
            empresa_nombre: string;
            rol: components["schemas"]["RolResumen"];
            sede: components["schemas"]["SedeUsuario"] | null;
            /** Permisos */
            permisos: string[];
            /** Debe Cambiar Password */
            debe_cambiar_password: boolean;
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
        /** VentaAnular */
        VentaAnular: {
            /** Motivo */
            motivo: string;
        };
        /** VentaCrear */
        VentaCrear: {
            /** Sede Id */
            sede_id: number;
            /** Observacion */
            observacion?: string | null;
            /** Items */
            items: components["schemas"]["VentaItemCrear"][];
        };
        /** VentaDetalle */
        VentaDetalle: {
            /** Id */
            id: number;
            /** Numero */
            numero: number;
            /**
             * Fecha
             * Format: date-time
             */
            fecha: string;
            /**
             * Fecha Dia
             * Format: date
             */
            fecha_dia: string;
            sede: components["schemas"]["SedeResumen"];
            /** Usuario Nombre */
            usuario_nombre: string | null;
            /** Total */
            total: number;
            /** Unidades */
            unidades: number;
            /** Lineas */
            lineas: number;
            /** Estado */
            estado: string;
            /** Observacion */
            observacion: string | null;
            /** Items */
            items: components["schemas"]["VentaItemSalida"][];
            /** Anulada Por Nombre */
            anulada_por_nombre?: string | null;
            /** Anulada En */
            anulada_en?: string | null;
            /** Motivo Anulacion */
            motivo_anulacion?: string | null;
            /**
             * Puede Anularse
             * @default false
             */
            puede_anularse: boolean;
        };
        /** VentaItemCrear */
        VentaItemCrear: {
            /** Producto Id */
            producto_id: number;
            /** Cantidad */
            cantidad: number;
            /**
             * Precio Unitario
             * @description Si se omite, se usa el precio de venta del producto
             */
            precio_unitario?: number | string | null;
        };
        /** VentaItemSalida */
        VentaItemSalida: {
            producto: components["schemas"]["ProductoResumen"];
            /** Cantidad */
            cantidad: number;
            /** Precio Unitario */
            precio_unitario: number;
            /** Subtotal */
            subtotal: number;
        };
        /** VentaResumen */
        VentaResumen: {
            /** Id */
            id: number;
            /** Numero */
            numero: number;
            /**
             * Fecha
             * Format: date-time
             */
            fecha: string;
            /**
             * Fecha Dia
             * Format: date
             */
            fecha_dia: string;
            sede: components["schemas"]["SedeResumen"];
            /** Usuario Nombre */
            usuario_nombre: string | null;
            /** Total */
            total: number;
            /** Unidades */
            unidades: number;
            /** Lineas */
            lineas: number;
            /** Estado */
            estado: string;
            /** Observacion */
            observacion: string | null;
        };
        /** VerificarCodigoEntrada */
        VerificarCodigoEntrada: {
            /**
             * Email
             * Format: email
             */
            email: string;
            /** Codigo */
            codigo: string;
        };
        /** VerificarCodigoSalida */
        VerificarCodigoSalida: {
            /** Session Token */
            session_token: string;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
