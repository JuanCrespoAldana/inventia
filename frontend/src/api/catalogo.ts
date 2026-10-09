import { get, patch, post, put } from "@/lib/http";
import type { Categoria, Pagina, Producto, ProductoActualizar, ProductoCrear } from "@/types/api";

export interface FiltroCategorias { q?: string; activa?: boolean | ""; pagina?: number; tamano?: number }
export interface FiltroProductos { q?: string; categoria_id?: number | ""; activo?: boolean | ""; pagina?: number; tamano?: number }

export const apiCategorias = {
  listar: (f: FiltroCategorias) => get<Pagina<Categoria>>("/api/categorias", { ...f }),
  crear: (d: { nombre: string; descripcion?: string | null }) => post<Categoria>("/api/categorias", d),
  actualizar: (id: number, d: { nombre?: string | null; descripcion?: string | null }) => put<Categoria>(`/api/categorias/${id}`, d),
  estado: (id: number, activa: boolean) => patch<Categoria>(`/api/categorias/${id}/estado`, { activa }),
};

export const apiProductos = {
  listar: (f: FiltroProductos) => get<Pagina<Producto>>("/api/productos", { ...f }),
  crear: (d: ProductoCrear) => post<Producto>("/api/productos", d),
  actualizar: (id: number, d: ProductoActualizar) => put<Producto>(`/api/productos/${id}`, d),
  estado: (id: number, activo: boolean) => patch<Producto>(`/api/productos/${id}/estado`, { activo }),
};
