import { del, get, patch, post, put } from "@/lib/http";
import type {
  Empresa,
  EmpresaActualizar,
  Pagina,
  ParametrosEmpresa,
  Permiso,
  Rol,
  RolActualizar,
  RolCrear,
  Sede,
  SedeActualizar,
  SedeResumen,
  SedeCrear,
  Usuario,
  UsuarioActualizar,
  UsuarioCrear,
} from "@/types/api";

export interface FiltroSedes { q?: string; ciudad?: string; activa?: boolean | ""; pagina?: number; tamano?: number }
export interface FiltroUsuarios { q?: string; rol_id?: number | ""; sede_id?: number | ""; activo?: boolean | ""; pagina?: number; tamano?: number }

export const apiEmpresa = {
  obtener: () => get<Empresa>("/api/empresa"),
  actualizar: (datos: EmpresaActualizar) => put<Empresa>("/api/empresa", datos),
  parametros: (datos: ParametrosEmpresa) => put<Empresa>("/api/empresa/parametros", datos),
};

export const apiSedes = {
  listar: (f: FiltroSedes) => get<Pagina<Sede>>("/api/sedes", { ...f }),
  directorio: () => get<SedeResumen[]>("/api/sedes/directorio"),
  crear: (d: SedeCrear) => post<Sede>("/api/sedes", d),
  actualizar: (id: number, d: SedeActualizar) => put<Sede>(`/api/sedes/${id}`, d),
  estado: (id: number, activa: boolean) => patch<Sede>(`/api/sedes/${id}/estado`, { activa }),
};

export const apiUsuarios = {
  listar: (f: FiltroUsuarios) => get<Pagina<Usuario>>("/api/usuarios", { ...f }),
  crear: (d: UsuarioCrear) => post<Usuario>("/api/usuarios", d),
  actualizar: (id: number, d: UsuarioActualizar) => put<Usuario>(`/api/usuarios/${id}`, d),
  estado: (id: number, activo: boolean) => patch<Usuario>(`/api/usuarios/${id}/estado`, { activo }),
  restablecerPassword: (id: number, nueva_password: string) => post<Usuario>(`/api/usuarios/${id}/restablecer-password`, { nueva_password }),
  desbloquear: (id: number) => post<Usuario>(`/api/usuarios/${id}/desbloquear`),
};

export const apiRoles = {
  listar: () => get<Rol[]>("/api/roles"),
  permisos: () => get<Permiso[]>("/api/permisos"),
  crear: (d: RolCrear) => post<Rol>("/api/roles", d),
  actualizar: (id: number, d: RolActualizar) => put<Rol>(`/api/roles/${id}`, d),
  asignarPermisos: (id: number, permisos: string[]) => put<Rol>(`/api/roles/${id}/permisos`, { permisos }),
  eliminar: (id: number) => del<{ mensaje: string }>(`/api/roles/${id}`),
};
