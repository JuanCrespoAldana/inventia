import { useSearchParams } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";
import { useSedes } from "./useCatalogos";

/**
 * Sede sobre la que se trabaja en pantallas que operan una sola sede a la vez (existencias, nueva venta).
 * Los roles de alcance «sede» quedan fijos en la suya; los de empresa eligen (por defecto la primera activa).
 */
export function useSedeActiva(parametro = "sede") {
  const { sesion } = useAuth();
  const [params, setParams] = useSearchParams();
  const sedes = useSedes();
  const fija = sesion?.rol.alcance === "sede" && sesion.sede !== null;
  const deUrl = Number(params.get(parametro)) || null;
  const lista = sedes.data ?? [];
  const sedeId = fija ? (sesion?.sede?.id ?? null) : (deUrl && lista.some((s) => s.id === deUrl) ? deUrl : (lista[0]?.id ?? null));

  function elegir(id: number) {
    setParams(
      (previo) => {
        const siguiente = new URLSearchParams(previo);
        siguiente.set(parametro, String(id));
        siguiente.delete("pagina");
        return siguiente;
      },
      { replace: true },
    );
  }

  return { sedeId, elegir, fija, sedes: lista, cargando: !fija && sedes.isPending, nombre: fija ? sesion?.sede?.nombre : lista.find((s) => s.id === sedeId)?.nombre };
}
