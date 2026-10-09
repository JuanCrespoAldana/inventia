import { get, post, put } from "@/lib/http";
import type {
  AjusteCrear,
  Alerta,
  ConsolidadoFila,
  EntradaCrear,
  InventarioSedePagina,
  Movimiento,
  NivelesActualizar,
  Pagina,
  ResultadoOperacion,
  ResultadoRecalculo,
  ResumenAlertas,
  SalidaCrear,
} from "@/types/api";

export interface FiltroInventario { sede_id?: number | ""; q?: string; categoria_id?: number | ""; estado?: string; pagina?: number; tamano?: number }
export interface FiltroConsolidado { q?: string; categoria_id?: number | ""; solo_con_existencias?: boolean; pagina?: number; tamano?: number }
export interface FiltroMovimientos { sede_id?: number | ""; producto_id?: number | ""; tipo?: string; desde?: string; hasta?: string; pagina?: number; tamano?: number }
export interface FiltroAlertas { estado?: string; tipo?: string; prioridad?: string; sede_id?: number | ""; q?: string; pagina?: number; tamano?: number }

export const apiInventario = {
  porSede: (f: FiltroInventario) => get<InventarioSedePagina>("/api/inventario", { ...f }),
  consolidado: (f: FiltroConsolidado) => get<Pagina<ConsolidadoFila>>("/api/inventario/consolidado", { ...f }),
  entrada: (d: EntradaCrear) => post<ResultadoOperacion>("/api/inventario/entradas", d),
  salida: (d: SalidaCrear) => post<ResultadoOperacion>("/api/inventario/salidas", d),
  ajuste: (d: AjusteCrear) => post<ResultadoOperacion>("/api/inventario/ajustes", d),
  niveles: (d: NivelesActualizar) => put("/api/inventario/niveles", d),
  movimientos: (f: FiltroMovimientos) => get<Pagina<Movimiento>>("/api/movimientos", { ...f }),
};

export const apiAlertas = {
  listar: (f: FiltroAlertas) => get<Pagina<Alerta>>("/api/alertas", { ...f }),
  resumen: (sede_id?: number | "") => get<ResumenAlertas>("/api/alertas/resumen", { sede_id }),
  recalcular: () => post<ResultadoRecalculo>("/api/alertas/recalcular"),
};
