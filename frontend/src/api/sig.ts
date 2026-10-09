import { del, get, http, post, patch, put, type Parametros } from "@/lib/http";
import type {
  ActividadSst,
  ActividadSstActualizar,
  ActividadSstCrear,
  AdjuntoSig,
  CategoriaAmbientalActualizar,
  ConfiguracionAmbiental,
  ConfiguracionSst,
  EntidadAdjunto,
  EntradaDetalle,
  EntradaResumen,
  FactorRedActualizar,
  GarantiaCrear,
  GarantiaDetalle,
  GarantiaGestionar,
  GarantiaResumen,
  NoConformidadCrear,
  NoConformidadDetalle,
  NoConformidadGestionar,
  NoConformidadResumen,
  Pagina,
  PausaEstado,
  PausaIniciada,
  PausaRegistro,
  PqrsConteo,
  PqrsCrear,
  PqrsDetalle,
  PqrsGestionar,
  PqrsResumen,
  RegistroAmbiental,
  ResultadoSincronizacion,
  ResumenAmbiental,
  ResumenCalidad,
  ResumenSst,
} from "@/types/api";

type Filtro = Parametros & { pagina?: number; tamano?: number };

/* ------------------------------------------------------------------ PQRS */

export interface FiltroPqrs extends Filtro { ambito?: "mias" | "todas"; tipo?: string; estado?: string; usuario_id?: number | ""; desde?: string; hasta?: string; q?: string }

export const apiPqrs = {
  listar: (f: FiltroPqrs) => get<Pagina<PqrsResumen>>("/api/sig/pqrs", { ...f }),
  conteo: () => get<PqrsConteo>("/api/sig/pqrs/conteo"),
  detalle: (id: number) => get<PqrsDetalle>(`/api/sig/pqrs/${id}`),
  crear: (d: PqrsCrear) => post<PqrsDetalle>("/api/sig/pqrs", d),
  gestionar: (id: number, d: PqrsGestionar) => patch<PqrsDetalle>(`/api/sig/pqrs/${id}`, d),
};

/* ------------------------------------------------------------------ Archivos adjuntos (evidencias) */

export const apiAdjuntos = {
  listar: (entidad: EntidadAdjunto, entidad_id: number) => get<AdjuntoSig[]>("/api/sig/adjuntos", { entidad, entidad_id }),
  /** El archivo viaja como cuerpo binario (sin multipart): el nombre va en la URL. */
  subir: async (entidad: EntidadAdjunto, entidad_id: number, archivo: File): Promise<AdjuntoSig> => {
    const r = await http.post<AdjuntoSig>("/api/sig/adjuntos", archivo, {
      params: { entidad, entidad_id, nombre: archivo.name },
      headers: { "Content-Type": "application/octet-stream" },
      timeout: 120_000,
    });
    return r.data;
  },
  eliminar: (id: number) => del<{ mensaje: string }>(`/api/sig/adjuntos/${id}`),
  /** Descarga con el token de la sesión (un enlace directo no lo enviaría). */
  descargar: async (adjunto: Pick<AdjuntoSig, "id" | "nombre">): Promise<void> => {
    const r = await http.get<Blob>(`/api/sig/adjuntos/${adjunto.id}/archivo`, { responseType: "blob" });
    const enlace = document.createElement("a");
    const url = URL.createObjectURL(r.data);
    enlace.href = url;
    enlace.download = adjunto.nombre;
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10_000);
  },
};

/* ------------------------------------------------------------------ SST */

export interface FiltroPausas extends Filtro { ambito?: "mias" | "todas"; usuario_id?: number | ""; estado?: string; desde?: string; hasta?: string }

export const apiSst = {
  estado: () => get<PausaEstado>("/api/sig/sst/pausa/estado"),
  iniciar: () => post<PausaIniciada>("/api/sig/sst/pausa/iniciar"),
  cerrar: (id: number, resultado: "realizada" | "omitida", duracion_segundos?: number) =>
    post<PausaRegistro>(`/api/sig/sst/pausa/${id}/cerrar`, { resultado, duracion_segundos: duracion_segundos ?? null }),
  pausas: (f: FiltroPausas) => get<Pagina<PausaRegistro>>("/api/sig/sst/pausas", { ...f }),
  resumen: (dias: number) => get<ResumenSst>("/api/sig/sst/resumen", { dias }),
  actividades: (todas = false) => get<ActividadSst[]>("/api/sig/sst/actividades", { todas }),
  crearActividad: (d: ActividadSstCrear) => post<ActividadSst>("/api/sig/sst/actividades", d),
  actualizarActividad: (id: number, d: ActividadSstActualizar) => patch<ActividadSst>(`/api/sig/sst/actividades/${id}`, d),
  eliminarActividad: (id: number) => del<void>(`/api/sig/sst/actividades/${id}`),
  configuracion: () => get<ConfiguracionSst>("/api/sig/sst/configuracion"),
  guardarConfiguracion: (d: { pausas_activas?: boolean; intervalo_minutos?: number }) => put<ConfiguracionSst>("/api/sig/sst/configuracion", d),
};

/* ------------------------------------------------------------------ Calidad */

export interface FiltroNc extends Filtro { sede_id?: number | ""; estado?: string; tipo?: string; producto_id?: number | ""; entrada_id?: number | ""; desde?: string; hasta?: string; q?: string }
export interface FiltroGarantias extends Filtro { sede_id?: number | ""; estado?: string; producto_id?: number | ""; proveedor?: string; desde?: string; hasta?: string; q?: string }

export const apiCalidad = {
  resumen: (sede_id?: number | "") => get<ResumenCalidad>("/api/sig/calidad/resumen", { sede_id }),
  listarNc: (f: FiltroNc) => get<Pagina<NoConformidadResumen>>("/api/sig/calidad/no-conformidades", { ...f }),
  detalleNc: (id: number) => get<NoConformidadDetalle>(`/api/sig/calidad/no-conformidades/${id}`),
  crearNc: (d: NoConformidadCrear) => post<NoConformidadDetalle>("/api/sig/calidad/no-conformidades", d),
  gestionarNc: (id: number, d: NoConformidadGestionar) => patch<NoConformidadDetalle>(`/api/sig/calidad/no-conformidades/${id}`, d),
  observarNc: (id: number, contenido: string) => post<NoConformidadDetalle>(`/api/sig/calidad/no-conformidades/${id}/observaciones`, { contenido }),
  listarGarantias: (f: FiltroGarantias) => get<Pagina<GarantiaResumen>>("/api/sig/calidad/garantias", { ...f }),
  detalleGarantia: (id: number) => get<GarantiaDetalle>(`/api/sig/calidad/garantias/${id}`),
  crearGarantia: (d: GarantiaCrear) => post<GarantiaDetalle>("/api/sig/calidad/garantias", d),
  gestionarGarantia: (id: number, d: GarantiaGestionar) => patch<GarantiaDetalle>(`/api/sig/calidad/garantias/${id}`, d),
  observarGarantia: (id: number, contenido: string) => post<GarantiaDetalle>(`/api/sig/calidad/garantias/${id}/observaciones`, { contenido }),
};

/* ------------------------------------------------------------------ Entradas de inventario (observaciones) */

export interface FiltroEntradas extends Filtro { sede_id?: number | ""; desde?: string; hasta?: string; numero?: number | "" }

export const apiEntradas = {
  listar: (f: FiltroEntradas) => get<Pagina<EntradaResumen>>("/api/inventario/entradas", { ...f }),
  detalle: (id: number) => get<EntradaDetalle>(`/api/inventario/entradas/${id}`),
  observar: (id: number, contenido: string, producto_id?: number | null) =>
    post<EntradaDetalle>(`/api/inventario/entradas/${id}/observaciones`, { contenido, producto_id: producto_id ?? null }),
};

/* ------------------------------------------------------------------ Gestión ambiental */

export interface FiltroRegistrosAmbientales extends Filtro { sede_id?: number | ""; desde?: string; hasta?: string; tipo_vehiculo?: string; estado?: string; pendientes?: boolean | "" }

export const apiAmbiental = {
  resumen: (anio?: number, sede_id?: number | "") => get<ResumenAmbiental>("/api/sig/ambiental/resumen", { anio, sede_id }),
  registros: (f: FiltroRegistrosAmbientales) => get<Pagina<RegistroAmbiental>>("/api/sig/ambiental/registros", { ...f }),
  configuracion: () => get<ConfiguracionAmbiental>("/api/sig/ambiental/configuracion"),
  guardarFactor: (d: FactorRedActualizar) => put<ResultadoSincronizacion>("/api/sig/ambiental/factor-red", d),
  guardarCategoria: (categoriaId: number, d: CategoriaAmbientalActualizar) => put<ResultadoSincronizacion>(`/api/sig/ambiental/categorias/${categoriaId}`, d),
  sincronizar: () => post<ResultadoSincronizacion>("/api/sig/ambiental/sincronizar", {}),
};
