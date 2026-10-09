import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { apiRoles, apiSedes } from "@/api/administracion";
import { apiCategorias, apiProductos } from "@/api/catalogo";
import { useAuth } from "@/auth/AuthContext";

const CINCO_MIN = 5 * 60_000;

/** Sedes activas para selectores. Solo se consulta si el usuario puede ver sedes. */
export function useSedes(soloActivas = true) {
  const { tiene } = useAuth();
  return useQuery({
    queryKey: ["catalogo", "sedes", soloActivas],
    queryFn: async () => (await apiSedes.listar({ activa: soloActivas ? true : "", tamano: 100 })).items,
    enabled: tiene("sedes.ver"),
    staleTime: CINCO_MIN,
  });
}

/** Todas las sedes activas (datos mínimos): incluye las que un usuario de una sola sede no puede listar. */
export function useDirectorioSedes() {
  const { tieneAlguno } = useAuth();
  return useQuery({
    queryKey: ["catalogo", "directorio-sedes"],
    queryFn: apiSedes.directorio,
    enabled: tieneAlguno("traslados.solicitar", "traslados.ver", "sedes.ver"),
    staleTime: CINCO_MIN,
  });
}

export function useCategorias(soloActivas = true) {
  const { tiene } = useAuth();
  return useQuery({
    queryKey: ["catalogo", "categorias", soloActivas],
    queryFn: async () => (await apiCategorias.listar({ activa: soloActivas ? true : "", tamano: 100 })).items,
    enabled: tiene("categorias.ver"),
    staleTime: CINCO_MIN,
  });
}

export function useRoles() {
  const { tieneAlguno } = useAuth();
  return useQuery({ queryKey: ["catalogo", "roles"], queryFn: apiRoles.listar, enabled: tieneAlguno("roles.ver", "usuarios.ver"), staleTime: CINCO_MIN });
}

/** Búsqueda de productos activos para el selector con autocompletado. */
export function useBuscarProductos(q: string) {
  const { tiene } = useAuth();
  return useQuery({
    queryKey: ["catalogo", "productos", q],
    queryFn: async () => (await apiProductos.listar({ q, activo: true, tamano: 12 })).items,
    enabled: tiene("productos.ver"),
    placeholderData: keepPreviousData,
    staleTime: 30_000,
  });
}
