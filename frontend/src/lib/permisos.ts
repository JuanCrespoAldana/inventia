import type { Sesion } from "@/types/api";

export function tienePermiso(sesion: Pick<Sesion, "permisos"> | null | undefined, ...codigos: string[]): boolean {
  if (!sesion || codigos.length === 0) return false;
  return codigos.every((c) => sesion.permisos.includes(c));
}

export function tieneAlguno(sesion: Pick<Sesion, "permisos"> | null | undefined, ...codigos: string[]): boolean {
  if (!sesion) return false;
  return codigos.some((c) => sesion.permisos.includes(c));
}

/** Roles de alcance «sede»: el backend los restringe a su sede; la interfaz solo oculta selectores. */
export function esAlcanceSede(sesion: Pick<Sesion, "rol"> | null | undefined): boolean {
  return sesion?.rol.alcance === "sede";
}
