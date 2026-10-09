/** Estructuras del campo `resumen` / `metricas` que el backend entrega como JSON libre. */

export interface OmitidaDetalle {
  sede_id: number;
  producto_id: number;
  motivo: string;
  dias_historia: number;
  dias_con_ventas: number;
  producto?: string | null;
  codigo?: string | null;
  sede?: string | null;
}

export interface ResumenEjecucion {
  series_total?: number;
  series_con_prediccion?: number;
  series_omitidas?: number;
  motivos_omision?: Record<string, number>;
  wape_global?: number | null;
  wape_linea_base_global?: number | null;
  mejora_vs_linea_base_pct?: number | null;
  modelos_elegidos?: Record<string, number>;
  series_por_confianza?: Record<string, number>;
  series_mejor_que_linea_base?: number;
  truncado?: boolean;
  omitidas?: OmitidaDetalle[];
  advertencia_global?: string | null;
  alertas?: Record<string, number>;
}

export interface CandidatoMetricas {
  modelo: string;
  avanzado: boolean;
  wape: number | null;
  mae: number | null;
}

export interface MetricasPrediccion {
  wape?: number | null;
  mae?: number | null;
  sesgo?: number | null;
  wape_linea_base?: number | null;
  mae_linea_base?: number | null;
  mejora_vs_linea_base_pct?: number | null;
  n_pliegues?: number;
  dias_validados?: number;
  dias_historia?: number;
  dias_con_ventas?: number;
  candidatos?: CandidatoMetricas[];
}

export const NOMBRE_MODELO: Record<string, string> = {
  media_28: "Promedio de 28 días (línea base)",
  media_7: "Promedio de 7 días",
  estacional_7: "Perfil semanal",
  croston_sba: "Demanda intermitente (Croston-SBA)",
  ets_semanal: "Suavizado exponencial estacional",
  gbr_rezagos: "Gradient boosting con rezagos",
};

export function nombreModelo(clave: string | null | undefined): string {
  return clave ? (NOMBRE_MODELO[clave] ?? clave) : "—";
}
