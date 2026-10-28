import { descargar, get, post, type Parametros } from "@/lib/http";
import type {
  AlcanceLlave,
  CatalogoModelos,
  Dashboard,
  Ejecucion,
  Llave,
  LlaveCrear,
  LlaveCreada,
  OpcionesAuditoria,
  Pagina,
  Prediccion,
  Recomendacion,
  RegistroAuditoria,
  Reporte,
  ResultadoGeneracion,
  SerieDemanda,
  TipoReporte,
} from "@/types/api";

export interface FiltroPredicciones { ejecucion_id?: number | ""; sede_id?: number | ""; producto_id?: number | ""; confianza?: string; q?: string; orden?: string; pagina?: number; tamano?: number }
export interface FiltroRecomendaciones { estado?: string; tipo?: string; prioridad?: string; sede_id?: number | ""; q?: string; pagina?: number; tamano?: number }
export interface FiltroAuditoria { usuario_id?: number | ""; modulo?: string; accion?: string; resultado?: string; desde?: string; hasta?: string; q?: string; pagina?: number; tamano?: number }
export interface FiltroReporte { sede_id?: number | ""; desde?: string; hasta?: string; categoria_id?: number | ""; estado?: string; clase?: string }

export const apiDashboard = {
  obtener: (sede_id: number | "" | undefined, dias: number) => get<Dashboard>("/api/dashboard", { sede_id, dias }),
};

export const apiPredicciones = {
  ejecutar: (horizonte_dias?: number | null) => post<Ejecucion>("/api/predicciones/ejecutar", { horizonte_dias: horizonte_dias ?? null }),
  ejecuciones: (pagina = 1, tamano = 10) => get<Pagina<Ejecucion>>("/api/predicciones/ejecuciones", { pagina, tamano }),
  ejecucion: (id: number) => get<Ejecucion>(`/api/predicciones/ejecuciones/${id}`),
  listar: (f: FiltroPredicciones) => get<Pagina<Prediccion>>("/api/predicciones", { ...f }),
  serie: (sede_id: number, producto_id: number, dias = 90) => get<SerieDemanda>("/api/predicciones/serie", { sede_id, producto_id, dias }),
  modelos: () => get<CatalogoModelos>("/api/predicciones/modelos"),
};

export const apiRecomendaciones = {
  listar: (f: FiltroRecomendaciones) => get<Pagina<Recomendacion>>("/api/recomendaciones", { ...f }),
  generar: () => post<ResultadoGeneracion>("/api/recomendaciones/generar"),
  aprobar: (id: number, comentario?: string) => post<Recomendacion>(`/api/recomendaciones/${id}/aprobar`, { comentario: comentario || null }),
  rechazar: (id: number, comentario?: string) => post<Recomendacion>(`/api/recomendaciones/${id}/rechazar`, { comentario: comentario || null }),
  ejecutar: (id: number, comentario?: string) => post<Recomendacion>(`/api/recomendaciones/${id}/ejecutar`, { comentario: comentario || null }),
};

export const apiAuditoria = {
  listar: (f: FiltroAuditoria) => get<Pagina<RegistroAuditoria>>("/api/auditoria", { ...f }),
  opciones: () => get<OpcionesAuditoria>("/api/auditoria/opciones"),
};

export const apiReportes = {
  catalogo: () => get<TipoReporte[]>("/api/reportes"),
  vistaPrevia: (tipo: string, f: FiltroReporte) => get<Reporte>(`/api/reportes/${tipo}`, { ...f, formato: "json" }),
  descargar: (tipo: string, formato: "csv" | "xlsx" | "pdf", f: FiltroReporte) => descargar(`/api/reportes/${tipo}`, { ...(f as Parametros), formato }),
};

export const apiIntegraciones = {
  alcances: () => get<AlcanceLlave[]>("/api/integraciones/alcances"),
  llaves: () => get<Llave[]>("/api/integraciones/llaves"),
  crear: (d: LlaveCrear) => post<LlaveCreada>("/api/integraciones/llaves", d),
  revocar: (id: number) => post<Llave>(`/api/integraciones/llaves/${id}/revocar`),
};
