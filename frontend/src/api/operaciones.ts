import { get, post } from "@/lib/http";
import type { Pagina, TrasladoCrear, TrasladoDetalle, TrasladoResumen, VentaCrear, VentaDetalle, VentaResumen } from "@/types/api";

export interface FiltroVentas { sede_id?: number | ""; estado?: string; desde?: string; hasta?: string; numero?: number | ""; pagina?: number; tamano?: number }
export interface FiltroTraslados { sede_id?: number | ""; estado?: string; desde?: string; hasta?: string; numero?: number | ""; pagina?: number; tamano?: number }

export const apiVentas = {
  listar: (f: FiltroVentas) => get<Pagina<VentaResumen>>("/api/ventas", { ...f }),
  detalle: (id: number) => get<VentaDetalle>(`/api/ventas/${id}`),
  crear: (d: VentaCrear) => post<VentaDetalle>("/api/ventas", d),
  anular: (id: number, motivo: string) => post<VentaDetalle>(`/api/ventas/${id}/anular`, { motivo }),
};

export const apiTraslados = {
  listar: (f: FiltroTraslados) => get<Pagina<TrasladoResumen>>("/api/traslados", { ...f }),
  detalle: (id: number) => get<TrasladoDetalle>(`/api/traslados/${id}`),
  crear: (d: TrasladoCrear) => post<TrasladoDetalle>("/api/traslados", d),
  aprobar: (id: number) => post<TrasladoDetalle>(`/api/traslados/${id}/aprobar`),
  rechazar: (id: number, motivo: string) => post<TrasladoDetalle>(`/api/traslados/${id}/rechazar`, { motivo }),
  confirmar: (id: number) => post<TrasladoDetalle>(`/api/traslados/${id}/confirmar`),
  cancelar: (id: number, motivo: string) => post<TrasladoDetalle>(`/api/traslados/${id}/cancelar`, { motivo }),
};
