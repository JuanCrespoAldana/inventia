import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

/**
 * Estado de filtros y paginación guardado en la URL: se puede compartir un enlace filtrado y el botón
 * «atrás» del navegador funciona como se espera. Cambiar un filtro reinicia la página a 1.
 */
export function useFiltros<T extends Record<string, string>>(valoresIniciales: T, tamanoPagina = 20) {
  const [params, setParams] = useSearchParams();

  const filtros = useMemo(() => {
    const salida: Record<string, string> = {};
    for (const clave of Object.keys(valoresIniciales)) salida[clave] = params.get(clave) ?? valoresIniciales[clave];
    return salida as T;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  const pagina = Math.max(1, Number(params.get("pagina")) || 1);

  const cambiar = useCallback(
    (cambios: Partial<T>) => {
      setParams(
        (previo) => {
          const siguiente = new URLSearchParams(previo);
          for (const [k, v] of Object.entries(cambios)) {
            if (v === undefined || v === "" || v === valoresIniciales[k]) siguiente.delete(k);
            else siguiente.set(k, String(v));
          }
          siguiente.delete("pagina");
          return siguiente;
        },
        { replace: true },
      );
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [setParams],
  );

  const irAPagina = useCallback(
    (p: number) =>
      setParams(
        (previo) => {
          const siguiente = new URLSearchParams(previo);
          if (p <= 1) siguiente.delete("pagina");
          else siguiente.set("pagina", String(p));
          return siguiente;
        },
        { replace: true },
      ),
    [setParams],
  );

  const limpiar = useCallback(() => setParams({}, { replace: true }), [setParams]);
  const hayFiltros = Object.keys(valoresIniciales).some((k) => filtros[k] !== valoresIniciales[k]);

  return { filtros, pagina, tamano: tamanoPagina, cambiar, irAPagina, limpiar, hayFiltros };
}

/** Convierte un filtro de texto en número o cadena vacía para la API. */
export function aNumero(valor: string): number | "" {
  const n = Number(valor);
  return valor !== "" && Number.isFinite(n) ? n : "";
}

export function aBooleano(valor: string): boolean | "" {
  return valor === "true" ? true : valor === "false" ? false : "";
}
