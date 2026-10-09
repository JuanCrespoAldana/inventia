/* Generado con openapi-typescript a partir de /openapi.json del backend. No editar a mano.
   Regenerar: npm run tipos (ver docs/DESARROLLO.md). Solo se conserva el bloque de esquemas. */

export interface components {
    schemas: {
        /** ActividadActualizar */
        ActividadActualizar: {
            /** Titulo */
            titulo?: string | null;
            /** Area */
            area?: ("cuello" | "hombros" | "espalda" | "manos_munecas" | "ojos" | "piernas" | "respiracion") | null;
            /** Mensaje */
            mensaje?: string | null;
            /** Instrucciones */
            instrucciones?: string | null;
            /** Duracion Segundos */
            duracion_segundos?: number | null;
            /** Recomendaciones */
            recomendaciones?: string | null;
            /** Orden */
            orden?: number | null;
            /** Activa */
            activa?: boolean | null;
        };
        /** ActividadCrear */
        ActividadCrear: {
            /** Titulo */
            titulo: string;
            /**
             * Area
             * @enum {string}
             */
            area: "cuello" | "hombros" | "espalda" | "manos_munecas" | "ojos" | "piernas" | "respiracion";
            /** Mensaje */
            mensaje: string;
            /** Instrucciones */
            instrucciones: string;
            /** Duracion Segundos */
            duracion_segundos: number;
            /** Recomendaciones */
            recomendaciones?: string | null;
            /**
             * Orden
             * @default 0
             */
            orden: number;
            /**
             * Activa
             * @default true
             */
            activa: boolean;
        };
        /** ActividadSalida */
        ActividadSalida: {
            /** Id */
            id: number;
            /** Titulo */
            titulo: string;
            /** Area */
            area: string;
            /** Mensaje */
            mensaje: string;
            /** Instrucciones */
            instrucciones: string;
            /** Duracion Segundos */
            duracion_segundos: number;
            /** Recomendaciones */
            recomendaciones: string | null;
            /** Orden */
            orden: number;
            /** Activa */
            activa: boolean;
            /** Pasos */
            readonly pasos: string[];
            /** Consejos */
            readonly consejos: string[];
        };
        /** AdjuntoSalida */
        AdjuntoSalida: {
            /** Id */
            id: number;
            /** Nombre */
            nombre: string;
            /** Tipo Mime */
            tipo_mime: string;
            /** Tamano */
            tamano: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Subido Por */
            subido_por: number;
            /** Subido Por Nombre */
            subido_por_nombre?: string | null;
            /**
             * Puede Eliminar
             * @default false
             */
            puede_eliminar: boolean;
        };
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
        /** CategoriaAmbientalActualizar */
        CategoriaAmbientalActualizar: {
            /**
             * Tipo Vehiculo
             * @enum {string}
             */
            tipo_vehiculo: "bicicleta_electrica" | "patineta_electrica" | "motocicleta_electrica" | "otro";
            /**
             * Propulsion
             * @enum {string}
             */
            propulsion: "electrica" | "asistida_pedaleo";
            /** Distancia Anual Km */
            distancia_anual_km?: number | string | null;
            /** Consumo Kwh 100Km */
            consumo_kwh_100km?: number | string | null;
            /** Vehiculo Referencia */
            vehiculo_referencia?: string | null;
            /** Emision Referencia Gco2 Km */
            emision_referencia_gco2_km?: number | string | null;
            /**
             * Horizonte Anios
             * @default 1
             */
            horizonte_anios: number;
            /** Fuente */
            fuente?: string | null;
            /**
             * Activa
             * @default true
             */
            activa: boolean;
        };
        /** CategoriaAmbientalSalida */
        CategoriaAmbientalSalida: {
            /** Categoria Id */
            categoria_id: number;
            /** Categoria Nombre */
            categoria_nombre: string;
            /** Es Vehiculo */
            es_vehiculo: boolean;
            /**
             * Activa
             * @default false
             */
            activa: boolean;
            /** Tipo Vehiculo */
            tipo_vehiculo?: string | null;
            /** Propulsion */
            propulsion?: string | null;
            /** Distancia Anual Km */
            distancia_anual_km?: number | null;
            /** Consumo Kwh 100Km */
            consumo_kwh_100km?: number | null;
            /** Vehiculo Referencia */
            vehiculo_referencia?: string | null;
            /** Emision Referencia Gco2 Km */
            emision_referencia_gco2_km?: number | null;
            /**
             * Horizonte Anios
             * @default 1
             */
            horizonte_anios: number;
            /** Fuente */
            fuente?: string | null;
            /**
             * Parametros Completos
             * @default false
             */
            parametros_completos: boolean;
            /** Co2 Por Unidad Kg */
            co2_por_unidad_kg?: number | null;
            /**
             * Unidades Vendidas
             * @default 0
             */
            unidades_vendidas: number;
            /**
             * Unidades Sin Parametrizar
             * @default 0
             */
            unidades_sin_parametrizar: number;
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
         * Cifras
         * @description ``unidades`` es un dato REAL (ventas confirmadas). ``co2_estimado_kg`` es una ESTIMACIÓN que solo
         *     suma los registros ya parametrizados; ``unidades_sin_parametrizar`` quedan fuera de la estimación.
         */
        Cifras: {
            /** Unidades */
            unidades: number;
            /** Co2 Estimado Kg */
            co2_estimado_kg: number;
            /** Unidades Sin Parametrizar */
            unidades_sin_parametrizar: number;
        };
        /** CifrasAnio */
        CifrasAnio: {
            /** Unidades */
            unidades: number;
            /** Co2 Estimado Kg */
            co2_estimado_kg: number;
            /** Unidades Sin Parametrizar */
            unidades_sin_parametrizar: number;
            /** Anio */
            anio: number;
        };
        /** CifrasMes */
        CifrasMes: {
            /** Unidades */
            unidades: number;
            /** Co2 Estimado Kg */
            co2_estimado_kg: number;
            /** Unidades Sin Parametrizar */
            unidades_sin_parametrizar: number;
            /** Mes */
            mes: number;
        };
        /** CifrasTipo */
        CifrasTipo: {
            /** Unidades */
            unidades: number;
            /** Co2 Estimado Kg */
            co2_estimado_kg: number;
            /** Unidades Sin Parametrizar */
            unidades_sin_parametrizar: number;
            /** Tipo Vehiculo */
            tipo_vehiculo: string;
        };
        /** ConfiguracionAmbiental */
        ConfiguracionAmbiental: {
            factor_red: components["schemas"]["FactorRedSalida"];
            /** Categorias */
            categorias: components["schemas"]["CategoriaAmbientalSalida"][];
            /**
             * Puede Configurar
             * @default false
             */
            puede_configurar: boolean;
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
        /** ConfiguracionSst */
        ConfiguracionSst: {
            /** Pausas Activas */
            pausas_activas: boolean;
            /** Intervalo Minutos */
            intervalo_minutos: number;
        };
        /** ConfiguracionSstActualizar */
        ConfiguracionSstActualizar: {
            /** Pausas Activas */
            pausas_activas?: boolean | null;
            /** Intervalo Minutos */
            intervalo_minutos?: number | null;
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
        /** ConteoEstado */
        ConteoEstado: {
            /** Estado */
            estado: string;
            /** Total */
            total: number;
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
        /** EntradaDetalle */
        EntradaDetalle: {
            /** Id */
            id: number;
            /** Numero */
            numero: number;
            /**
             * Fecha
             * Format: date-time
             */
            fecha: string;
            /** Motivo */
            motivo: string;
            sede: components["schemas"]["SedeResumen"];
            /** Usuario Id */
            usuario_id: number;
            /** Usuario Nombre */
            usuario_nombre?: string | null;
            /** Unidades */
            unidades: number;
            /** Lineas */
            lineas: number;
            /** Observaciones */
            observaciones: number;
            /** No Conformidades */
            no_conformidades: number;
            /** Detalle Lineas */
            detalle_lineas: components["schemas"]["EntradaLinea"][];
            /** Historial Observaciones */
            historial_observaciones: components["schemas"]["EntradaObservacionSalida"][];
            /** No Conformidades Vinculadas */
            no_conformidades_vinculadas: components["schemas"]["NoConformidadVinculo"][];
            /**
             * Puede Observar
             * @default false
             */
            puede_observar: boolean;
            /**
             * Puede Reportar Calidad
             * @default false
             */
            puede_reportar_calidad: boolean;
        };
        /** EntradaLinea */
        EntradaLinea: {
            producto: components["schemas"]["ProductoResumen"];
            /** Cantidad */
            cantidad: number;
            /** Saldo Posterior */
            saldo_posterior: number;
        };
        /** EntradaObservacionCrear */
        EntradaObservacionCrear: {
            /** Contenido */
            contenido: string;
            /**
             * Producto Id
             * @description Línea de la entrada a la que se refiere (opcional)
             */
            producto_id?: number | null;
        };
        /** EntradaObservacionSalida */
        EntradaObservacionSalida: {
            /** Id */
            id: number;
            /**
             * Fecha
             * Format: date-time
             */
            fecha: string;
            /** Usuario Id */
            usuario_id: number;
            /** Usuario Nombre */
            usuario_nombre?: string | null;
            /** Contenido */
            contenido: string;
            producto?: components["schemas"]["ProductoResumen"] | null;
            /**
             * No Conformidades
             * @default []
             */
            no_conformidades: components["schemas"]["NoConformidadVinculo"][];
        };
        /** EntradaResumen */
        EntradaResumen: {
            /** Id */
            id: number;
            /** Numero */
            numero: number;
            /**
             * Fecha
             * Format: date-time
             */
            fecha: string;
            /** Motivo */
            motivo: string;
            sede: components["schemas"]["SedeResumen"];
            /** Usuario Id */
            usuario_id: number;
            /** Usuario Nombre */
            usuario_nombre?: string | null;
            /** Unidades */
            unidades: number;
            /** Lineas */
            lineas: number;
            /** Observaciones */
            observaciones: number;
            /** No Conformidades */
            no_conformidades: number;
        };
        /** EntradaVinculo */
        EntradaVinculo: {
            /** Id */
            id: number;
            /** Numero */
            numero: number;
            /**
             * Fecha
             * Format: date-time
             */
            fecha: string;
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
        /**
         * EventoSalida
         * @description Una línea del historial de una no conformidad o de una garantía.
         */
        EventoSalida: {
            /** Id */
            id: number;
            /**
             * Fecha
             * Format: date-time
             */
            fecha: string;
            /** Usuario Id */
            usuario_id: number;
            /** Usuario Nombre */
            usuario_nombre?: string | null;
            /** Evento */
            evento: string;
            /** Estado Anterior */
            estado_anterior: string | null;
            /** Estado Nuevo */
            estado_nuevo: string | null;
            /** Contenido */
            contenido: string | null;
        };
        /** FactorRedActualizar */
        FactorRedActualizar: {
            /** Valor */
            valor: number | string;
            /** Anio */
            anio: number;
            /** Fuente */
            fuente: string;
        };
        /** FactorRedSalida */
        FactorRedSalida: {
            /** Valor */
            valor: number | null;
            /** Anio */
            anio: number | null;
            /** Fuente */
            fuente: string | null;
        };
        /** GarantiaCrear */
        GarantiaCrear: {
            /** Producto Id */
            producto_id: number;
            /** Sede Id */
            sede_id?: number | null;
            /**
             * Cantidad
             * @default 1
             */
            cantidad: number;
            /**
             * Documento Tipo
             * @enum {string}
             */
            documento_tipo: "factura_compra" | "entrada_inventario" | "venta" | "otro";
            /** Documento Referencia */
            documento_referencia?: string | null;
            /** Entrada Id */
            entrada_id?: number | null;
            /** Venta Id */
            venta_id?: number | null;
            /**
             * Fecha Compra
             * Format: date
             */
            fecha_compra: string;
            /** Garantia Hasta */
            garantia_hasta?: string | null;
            /** Fecha Reporte */
            fecha_reporte?: string | null;
            /** Defecto */
            defecto: string;
            /** Proveedor */
            proveedor?: string | null;
            /** Observaciones */
            observaciones?: string | null;
        };
        /** GarantiaDetalle */
        GarantiaDetalle: {
            /** Id */
            id: number;
            /** Numero */
            numero: number;
            producto: components["schemas"]["ProductoResumen"];
            sede: components["schemas"]["SedeResumen"];
            /** Cantidad */
            cantidad: number;
            /** Estado */
            estado: string;
            /** Documento Tipo */
            documento_tipo: string;
            /** Documento Referencia */
            documento_referencia: string | null;
            /**
             * Fecha Compra
             * Format: date
             */
            fecha_compra: string;
            /**
             * Fecha Reporte
             * Format: date
             */
            fecha_reporte: string;
            /** Proveedor */
            proveedor: string | null;
            /** Usuario Id */
            usuario_id: number;
            /** Usuario Nombre */
            usuario_nombre?: string | null;
            /** Responsable Nombre */
            responsable_nombre?: string | null;
            /** En Garantia */
            en_garantia?: boolean | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Observaciones
             * @default 0
             */
            observaciones: number;
            /**
             * Adjuntos
             * @default 0
             */
            adjuntos: number;
            /** Defecto */
            defecto: string;
            /** Garantia Hasta */
            garantia_hasta: string | null;
            entrada?: components["schemas"]["EntradaVinculo"] | null;
            /** Venta Id */
            venta_id: number | null;
            /** Venta Numero */
            venta_numero?: number | null;
            /** Responsable Id */
            responsable_id: number | null;
            /** Fecha Envio Proveedor */
            fecha_envio_proveedor: string | null;
            /** Respuesta Proveedor */
            respuesta_proveedor: string | null;
            /** Fecha Respuesta Proveedor */
            fecha_respuesta_proveedor: string | null;
            /** Solucion */
            solucion: string | null;
            /** Fecha Solucion */
            fecha_solucion: string | null;
            /** Cerrada En */
            cerrada_en: string | null;
            /** Historial */
            historial: components["schemas"]["EventoSalida"][];
            /** Archivos */
            archivos: components["schemas"]["AdjuntoSalida"][];
            /**
             * Puede Gestionar
             * @default false
             */
            puede_gestionar: boolean;
            /**
             * Puede Observar
             * @default false
             */
            puede_observar: boolean;
            /**
             * Puede Adjuntar
             * @default false
             */
            puede_adjuntar: boolean;
        };
        /** GarantiaGestionar */
        GarantiaGestionar: {
            /** Estado */
            estado?: ("reportada" | "pendiente_revision" | "enviada_proveedor" | "aprobada" | "rechazada" | "solucionada" | "cerrada") | null;
            /** Responsable Id */
            responsable_id?: number | null;
            /** Proveedor */
            proveedor?: string | null;
            /** Fecha Envio Proveedor */
            fecha_envio_proveedor?: string | null;
            /** Respuesta Proveedor */
            respuesta_proveedor?: string | null;
            /** Fecha Respuesta Proveedor */
            fecha_respuesta_proveedor?: string | null;
            /** Solucion */
            solucion?: string | null;
            /** Fecha Solucion */
            fecha_solucion?: string | null;
            /** Comentario */
            comentario?: string | null;
        };
        /** GarantiaResumen */
        GarantiaResumen: {
            /** Id */
            id: number;
            /** Numero */
            numero: number;
            producto: components["schemas"]["ProductoResumen"];
            sede: components["schemas"]["SedeResumen"];
            /** Cantidad */
            cantidad: number;
            /** Estado */
            estado: string;
            /** Documento Tipo */
            documento_tipo: string;
            /** Documento Referencia */
            documento_referencia: string | null;
            /**
             * Fecha Compra
             * Format: date
             */
            fecha_compra: string;
            /**
             * Fecha Reporte
             * Format: date
             */
            fecha_reporte: string;
            /** Proveedor */
            proveedor: string | null;
            /** Usuario Id */
            usuario_id: number;
            /** Usuario Nombre */
            usuario_nombre?: string | null;
            /** Responsable Nombre */
            responsable_nombre?: string | null;
            /** En Garantia */
            en_garantia?: boolean | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Observaciones
             * @default 0
             */
            observaciones: number;
            /**
             * Adjuntos
             * @default 0
             */
            adjuntos: number;
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
            /** Entrada Id */
            entrada_id?: number | null;
            /** Entrada Numero */
            entrada_numero?: number | null;
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
        /** NoConformidadCrear */
        NoConformidadCrear: {
            /** Producto Id */
            producto_id: number;
            /**
             * Sede Id
             * @description Obligatoria salvo que se indique la entrada o la persona tenga una sola sede
             */
            sede_id?: number | null;
            /** Referencia */
            referencia?: string | null;
            /**
             * Tipo
             * @enum {string}
             */
            tipo: "defecto_de_fabrica" | "dano_en_transporte" | "producto_equivocado" | "cantidad_incorrecta" | "empaque_deteriorado" | "no_cumple_especificacion" | "otro";
            /** Descripcion */
            descripcion: string;
            /**
             * Fecha Deteccion
             * Format: date
             */
            fecha_deteccion: string;
            /** Cantidad Afectada */
            cantidad_afectada: number;
            /** Proveedor */
            proveedor?: string | null;
            /** Observaciones */
            observaciones?: string | null;
            /** Entrada Id */
            entrada_id?: number | null;
            /** Entrada Observacion Id */
            entrada_observacion_id?: number | null;
        };
        /** NoConformidadDetalle */
        NoConformidadDetalle: {
            /** Id */
            id: number;
            /** Numero */
            numero: number;
            producto: components["schemas"]["ProductoResumen"];
            sede: components["schemas"]["SedeResumen"];
            /** Tipo */
            tipo: string;
            /** Estado */
            estado: string;
            /**
             * Fecha Deteccion
             * Format: date
             */
            fecha_deteccion: string;
            /** Cantidad Afectada */
            cantidad_afectada: number;
            /** Referencia */
            referencia: string | null;
            /** Usuario Id */
            usuario_id: number;
            /** Usuario Nombre */
            usuario_nombre?: string | null;
            /** Responsable Nombre */
            responsable_nombre?: string | null;
            entrada?: components["schemas"]["EntradaVinculo"] | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Observaciones
             * @default 0
             */
            observaciones: number;
            /**
             * Adjuntos
             * @default 0
             */
            adjuntos: number;
            /** Descripcion */
            descripcion: string;
            /** Proveedor */
            proveedor: string | null;
            /** Solucion */
            solucion: string | null;
            /** Responsable Id */
            responsable_id: number | null;
            /** Resuelta En */
            resuelta_en: string | null;
            /** Cerrada En */
            cerrada_en: string | null;
            /** Observacion Origen */
            observacion_origen?: string | null;
            /** Historial */
            historial: components["schemas"]["EventoSalida"][];
            /** Archivos */
            archivos: components["schemas"]["AdjuntoSalida"][];
            /**
             * Puede Gestionar
             * @default false
             */
            puede_gestionar: boolean;
            /**
             * Puede Observar
             * @default false
             */
            puede_observar: boolean;
            /**
             * Puede Adjuntar
             * @default false
             */
            puede_adjuntar: boolean;
        };
        /**
         * NoConformidadGestionar
         * @description Gestión por parte de quien administra la calidad. Debe traer al menos un cambio.
         */
        NoConformidadGestionar: {
            /** Estado */
            estado?: ("reportado" | "en_revision" | "en_proceso_solucion" | "resuelto" | "cerrado") | null;
            /** Responsable Id */
            responsable_id?: number | null;
            /** Proveedor */
            proveedor?: string | null;
            /** Solucion */
            solucion?: string | null;
            /** Comentario */
            comentario?: string | null;
        };
        /** NoConformidadResumen */
        NoConformidadResumen: {
            /** Id */
            id: number;
            /** Numero */
            numero: number;
            producto: components["schemas"]["ProductoResumen"];
            sede: components["schemas"]["SedeResumen"];
            /** Tipo */
            tipo: string;
            /** Estado */
            estado: string;
            /**
             * Fecha Deteccion
             * Format: date
             */
            fecha_deteccion: string;
            /** Cantidad Afectada */
            cantidad_afectada: number;
            /** Referencia */
            referencia: string | null;
            /** Usuario Id */
            usuario_id: number;
            /** Usuario Nombre */
            usuario_nombre?: string | null;
            /** Responsable Nombre */
            responsable_nombre?: string | null;
            entrada?: components["schemas"]["EntradaVinculo"] | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Observaciones
             * @default 0
             */
            observaciones: number;
            /**
             * Adjuntos
             * @default 0
             */
            adjuntos: number;
        };
        /** NoConformidadVinculo */
        NoConformidadVinculo: {
            /** Id */
            id: number;
            /** Numero */
            numero: number;
            /** Estado */
            estado: string;
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
        /** Pagina[EntradaResumen] */
        Pagina_EntradaResumen_: {
            /** Items */
            items: components["schemas"]["EntradaResumen"][];
            /** Total */
            total: number;
            /** Pagina */
            pagina: number;
            /** Tamano */
            tamano: number;
            /** Paginas */
            paginas: number;
        };
        /** Pagina[GarantiaResumen] */
        Pagina_GarantiaResumen_: {
            /** Items */
            items: components["schemas"]["GarantiaResumen"][];
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
        /** Pagina[NoConformidadResumen] */
        Pagina_NoConformidadResumen_: {
            /** Items */
            items: components["schemas"]["NoConformidadResumen"][];
            /** Total */
            total: number;
            /** Pagina */
            pagina: number;
            /** Tamano */
            tamano: number;
            /** Paginas */
            paginas: number;
        };
        /** Pagina[PausaRegistro] */
        Pagina_PausaRegistro_: {
            /** Items */
            items: components["schemas"]["PausaRegistro"][];
            /** Total */
            total: number;
            /** Pagina */
            pagina: number;
            /** Tamano */
            tamano: number;
            /** Paginas */
            paginas: number;
        };
        /** Pagina[PqrsResumen] */
        Pagina_PqrsResumen_: {
            /** Items */
            items: components["schemas"]["PqrsResumen"][];
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
        /** Pagina[RegistroAmbiental] */
        Pagina_RegistroAmbiental_: {
            /** Items */
            items: components["schemas"]["RegistroAmbiental"][];
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
        /** Parametrizacion */
        Parametrizacion: {
            /**
             * Estado
             * @enum {string}
             */
            estado: "completa" | "parcial" | "pendiente" | "sin_categorias";
            /** Mensaje */
            mensaje: string;
            /** Categorias Vehiculo */
            categorias_vehiculo: number;
            /** Categorias Parametrizadas */
            categorias_parametrizadas: number;
            /** Factor Red Definido */
            factor_red_definido: boolean;
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
        /** PausaCerrar */
        PausaCerrar: {
            /**
             * Resultado
             * @enum {string}
             */
            resultado: "realizada" | "omitida";
            /** Duracion Segundos */
            duracion_segundos?: number | null;
        };
        /** PausaEstado */
        PausaEstado: {
            /** Aplica */
            aplica: boolean;
            /** Activo */
            activo: boolean;
            /** Intervalo Minutos */
            intervalo_minutos: number;
            /**
             * Ahora
             * Format: date-time
             */
            ahora: string;
            /** Ultima Pausa En */
            ultima_pausa_en: string | null;
            pendiente: components["schemas"]["PausaMostrada"] | null;
        };
        /** PausaIniciada */
        PausaIniciada: {
            /** Mostrar */
            mostrar: boolean;
            pausa?: components["schemas"]["PausaMostrada"] | null;
            /** Proxima En */
            proxima_en?: string | null;
            /** Motivo */
            motivo?: string | null;
        };
        /** PausaMostrada */
        PausaMostrada: {
            /** Id */
            id: number;
            /**
             * Mostrada En
             * Format: date-time
             */
            mostrada_en: string;
            actividad: components["schemas"]["ActividadSalida"] | null;
        };
        /** PausaRegistro */
        PausaRegistro: {
            /** Id */
            id: number;
            /** Usuario Id */
            usuario_id: number;
            /** Usuario Nombre */
            usuario_nombre?: string | null;
            /** Actividad Titulo */
            actividad_titulo: string;
            /**
             * Mostrada En
             * Format: date-time
             */
            mostrada_en: string;
            /** Estado */
            estado: string;
            /** Cerrada En */
            cerrada_en: string | null;
            /** Duracion Segundos */
            duracion_segundos: number | null;
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
        /** PqrsConteo */
        PqrsConteo: {
            /** Total */
            total: number;
            /** Pendiente */
            pendiente: number;
            /** En Revision */
            en_revision: number;
            /** En Proceso */
            en_proceso: number;
            /** Resuelta */
            resuelta: number;
        };
        /** PqrsCrear */
        PqrsCrear: {
            /**
             * Tipo
             * @enum {string}
             */
            tipo: "peticion" | "queja" | "reclamo" | "sugerencia";
            /** Asunto */
            asunto: string;
            /** Descripcion */
            descripcion: string;
        };
        /** PqrsDetalle */
        PqrsDetalle: {
            /** Id */
            id: number;
            /** Numero */
            numero: number;
            /** Tipo */
            tipo: string;
            /** Asunto */
            asunto: string;
            /** Estado */
            estado: string;
            /** Usuario Id */
            usuario_id: number;
            /** Usuario Nombre */
            usuario_nombre?: string | null;
            sede?: components["schemas"]["SedeResumen"] | null;
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
            /** Respondida */
            respondida: boolean;
            /**
             * Adjuntos
             * @default 0
             */
            adjuntos: number;
            /** Descripcion */
            descripcion: string;
            /** Respuesta */
            respuesta: string | null;
            /** Respondida Por Nombre */
            respondida_por_nombre?: string | null;
            /** Respondida En */
            respondida_en?: string | null;
            /** Historial */
            historial: components["schemas"]["PqrsEvento"][];
            /** Archivos */
            archivos: components["schemas"]["AdjuntoSalida"][];
            /**
             * Puede Gestionar
             * @default false
             */
            puede_gestionar: boolean;
            /**
             * Puede Adjuntar
             * @default false
             */
            puede_adjuntar: boolean;
        };
        /** PqrsEvento */
        PqrsEvento: {
            /** Id */
            id: number;
            /**
             * Fecha
             * Format: date-time
             */
            fecha: string;
            /** Usuario Id */
            usuario_id: number;
            /** Usuario Nombre */
            usuario_nombre?: string | null;
            /** Evento */
            evento: string;
            /** Estado Anterior */
            estado_anterior: string | null;
            /** Estado Nuevo */
            estado_nuevo: string | null;
            /** Comentario */
            comentario: string | null;
        };
        /**
         * PqrsGestionar
         * @description Cambia el estado y/o registra la respuesta administrativa. Debe traer al menos uno de los dos.
         */
        PqrsGestionar: {
            /** Estado */
            estado?: ("pendiente" | "en_revision" | "en_proceso" | "resuelta") | null;
            /** Respuesta */
            respuesta?: string | null;
        };
        /** PqrsResumen */
        PqrsResumen: {
            /** Id */
            id: number;
            /** Numero */
            numero: number;
            /** Tipo */
            tipo: string;
            /** Asunto */
            asunto: string;
            /** Estado */
            estado: string;
            /** Usuario Id */
            usuario_id: number;
            /** Usuario Nombre */
            usuario_nombre?: string | null;
            sede?: components["schemas"]["SedeResumen"] | null;
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
            /** Respondida */
            respondida: boolean;
            /**
             * Adjuntos
             * @default 0
             */
            adjuntos: number;
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
        /** RegistroAmbiental */
        RegistroAmbiental: {
            /** Id */
            id: number;
            /**
             * Fecha
             * Format: date
             */
            fecha: string;
            /** Venta Id */
            venta_id: number;
            /** Venta Numero */
            venta_numero?: number | null;
            sede: components["schemas"]["SedeResumen"];
            producto: components["schemas"]["ProductoResumen"];
            /** Categoria */
            categoria?: string | null;
            /** Tipo Vehiculo */
            tipo_vehiculo: string;
            /** Propulsion */
            propulsion: string;
            /** Unidades */
            unidades: number;
            /** Estado */
            estado: string;
            /** Parametrizado */
            parametrizado: boolean;
            /** Co2 Estimado Kg */
            co2_estimado_kg: number | null;
            /** Anulado En */
            anulado_en: string | null;
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
            /** Entrada Id */
            entrada_id?: number | null;
            /** Entrada Numero */
            entrada_numero?: number | null;
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
        /** ResultadoSincronizacion */
        ResultadoSincronizacion: {
            /** Incorporados */
            incorporados: number;
            /** Calculados */
            calculados: number;
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
        /** ResumenAmbiental */
        ResumenAmbiental: {
            /** Anio */
            anio: number;
            parametrizacion: components["schemas"]["Parametrizacion"];
            mes_actual: components["schemas"]["Cifras"];
            anio_seleccionado: components["schemas"]["Cifras"];
            acumulado: components["schemas"]["Cifras"];
            /** Meses */
            meses: components["schemas"]["CifrasMes"][];
            /** Anios */
            anios: components["schemas"]["CifrasAnio"][];
            /** Por Tipo */
            por_tipo: components["schemas"]["CifrasTipo"][];
            /** Anios Disponibles */
            anios_disponibles: number[];
        };
        /** ResumenCalidad */
        ResumenCalidad: {
            /** No Conformidades */
            no_conformidades: components["schemas"]["ConteoEstado"][];
            /** Garantias */
            garantias: components["schemas"]["ConteoEstado"][];
            /** No Conformidades Abiertas */
            no_conformidades_abiertas: number;
            /** Garantias Abiertas */
            garantias_abiertas: number;
        };
        /** ResumenSst */
        ResumenSst: {
            /**
             * Desde
             * Format: date
             */
            desde: string;
            /** Mostradas */
            mostradas: number;
            /** Realizadas */
            realizadas: number;
            /** Omitidas */
            omitidas: number;
            /** Sin Responder */
            sin_responder: number;
            /** Cumplimiento */
            cumplimiento: number | null;
            /** Por Usuario */
            por_usuario: components["schemas"]["ResumenUsuarioSst"][];
        };
        /** ResumenUsuarioSst */
        ResumenUsuarioSst: {
            /** Usuario Id */
            usuario_id: number;
            /** Usuario Nombre */
            usuario_nombre: string | null;
            /** Mostradas */
            mostradas: number;
            /** Realizadas */
            realizadas: number;
            /** Omitidas */
            omitidas: number;
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
        /** _Observacion */
        _Observacion: {
            /** Contenido */
            contenido: string;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
