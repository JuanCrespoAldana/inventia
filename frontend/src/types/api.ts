import type { components } from "./api.gen";

type S = components["schemas"];

/** Respuesta paginada genérica del backend. */
export interface Pagina<T> {
  items: T[];
  total: number;
  pagina: number;
  tamano: number;
  paginas: number;
}

export type Sesion = S["UsuarioSesion"];
export type TokenSalida = S["TokenSalida"];
export type EstadoInstalacion = S["EstadoInstalacion"];
export type ConfiguracionInicial = S["ConfiguracionInicial"];

export type Empresa = S["EmpresaSalida"];
export type EmpresaActualizar = S["EmpresaActualizar"];
export type ParametrosEmpresa = S["ParametrosEmpresa"];

export type Sede = S["SedeDetalle"];
export type SedeResumen = S["SedeResumen"];
export type SedeCrear = S["SedeCrear"];
export type SedeActualizar = S["SedeActualizar"];

export type Usuario = S["UsuarioSalida"];
export type UsuarioCrear = S["UsuarioCrear"];
export type UsuarioActualizar = S["UsuarioActualizar"];

export type Rol = S["RolSalida"];
export type RolCrear = S["RolCrear"];
export type RolActualizar = S["RolActualizar"];
export type Permiso = S["PermisoSalida"];

export type Categoria = S["CategoriaSalida"];
export type Producto = S["ProductoSalida"];
export type ProductoCrear = S["ProductoCrear"];
export type ProductoActualizar = S["ProductoActualizar"];
export type ProductoResumen = S["ProductoResumen"];
export type UnidadMedida = NonNullable<S["ProductoCrear"]["unidad_medida"]>;

export type InventarioFila = S["InventarioFila"];
export type InventarioSedePagina = S["InventarioSedePagina"];
export type ConsolidadoFila = S["ConsolidadoFila"];
export type EstadoStock = InventarioFila["estado"];
export type Movimiento = S["MovimientoSalida"];
export type ResultadoOperacion = S["ResultadoOperacion"];
export type EntradaCrear = S["EntradaCrear"];
export type SalidaCrear = S["SalidaCrear"];
export type AjusteCrear = S["AjusteCrear"];
export type NivelesActualizar = S["NivelesActualizar"];

export type Alerta = S["AlertaSalida"];
export type ResumenAlertas = S["ResumenAlertas"];
export type ResultadoRecalculo = S["ResultadoRecalculo"];

export type VentaResumen = S["VentaResumen"];
export type VentaDetalle = S["VentaDetalle"];
export type VentaCrear = S["VentaCrear"];

export type TrasladoResumen = S["TrasladoResumen"];
export type TrasladoDetalle = S["TrasladoDetalle"];
export type TrasladoCrear = S["TrasladoCrear"];

export type Ejecucion = S["EjecucionSalida"];
export type Prediccion = S["PrediccionSalida"];
export type SerieDemanda = S["SerieDemanda"];
export type CatalogoModelos = S["CatalogoModelos"];
export type Recomendacion = S["RecomendacionSalida"];
export type ResultadoGeneracion = S["ResultadoGeneracion"];

export type RegistroAuditoria = S["RegistroAuditoria"];
export type OpcionesAuditoria = S["OpcionesAuditoria"];

export type Llave = S["LlaveSalida"];
export type LlaveCreada = S["LlaveCreada"];
export type LlaveCrear = S["LlaveCrear"];
export interface AlcanceLlave {
  alcance: string;
  descripcion: string;
}

export type TipoReporte = S["TipoReporte"];
export interface ColumnaReporte {
  clave: string;
  titulo: string;
  tipo: "texto" | "entero" | "dinero" | "decimal" | "fecha" | "fechahora" | "porcentaje";
}
export interface Reporte {
  tipo: string;
  titulo: string;
  columnas: ColumnaReporte[];
  filas: Record<string, unknown>[];
  resumen: Record<string, unknown>;
  total: number;
  truncado: boolean;
}

/** Carga del panel de control: cada sección es null cuando el usuario no tiene el permiso. */
export interface Dashboard {
  generado_en: string;
  periodo: { desde: string; hasta: string; dias: number };
  sede_id: number | null;
  inventario: {
    productos_activos: number;
    referencias_con_existencias: number;
    unidades_totales: number;
    valor_inventario: number;
    productos_sin_costo: number;
    valor_completo: boolean;
    agotados: number;
    bajos: number;
    excesivos: number;
  } | null;
  ventas: {
    total: number;
    numero_ventas: number;
    unidades: number;
    ticket_promedio: number;
    anuladas: number;
    total_periodo_anterior: number;
    variacion_pct: number | null;
    serie_diaria: { fecha: string; total: number; unidades: number; ventas: number }[];
    top_productos: { producto_id: number; codigo: string; nombre: string; unidades: number; total: number }[];
  } | null;
  por_sede: { sede_id: number; sede: string; unidades: number; valor: number; alertas: number }[] | null;
  alertas: {
    total: number;
    por_tipo: Record<string, number>;
    por_prioridad: Record<string, number>;
    principales: { id: number; tipo: string; prioridad: string; mensaje: string; sede: string; producto: string }[];
  } | null;
  traslados_pendientes: number | null;
  recomendaciones_pendientes: number | null;
  prediccion: {
    ejecucion_id: number;
    finalizada_en: string | null;
    fecha_corte: string | null;
    horizonte_dias: number;
    series_con_prediccion: number | null;
    series_omitidas: number | null;
    wape_global: number | null;
    mejora_vs_linea_base_pct: number | null;
  } | null;
  movimientos_recientes: Movimiento[] | null;
}
