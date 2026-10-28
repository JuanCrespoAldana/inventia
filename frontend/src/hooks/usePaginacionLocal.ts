import { useCallback, useState } from "react";

const SIN_ELEMENTOS: never[] = [];

/** Lo que necesita `<Paginacion />` para dibujarse (el mismo componente que usan los listados paginados por el servidor). */
export interface PropiedadesPaginacion {
  pagina: number;
  paginas: number;
  total: number;
  tamano: number;
  onCambiar: (pagina: number) => void;
}

/**
 * Paginado en el navegador para listas que el servidor entrega completas (vista previa de un reporte,
 * roles, llaves de integración, líneas de un documento…). Los listados grandes de verdad se paginan en
 * el servidor con `useFiltros`; este hook cubre el resto para que ninguna pantalla crezca sin límite.
 *
 * - `tamano` indefinido o 0 desactiva el paginado y devuelve la lista completa.
 * - `reiniciarCon` vuelve a la página 1 cuando cambia (por ejemplo, al cambiar de filtro o de reporte).
 * - Si la lista se acorta (se elimina un registro), la página se ajusta sola a la última que exista.
 */
export function usePaginacionLocal<T>(elementos: T[] | undefined, tamano: number | undefined, reiniciarCon = "") {
  const [elegida, setElegida] = useState({ pagina: 1, clave: reiniciarCon });
  const lista = elementos ?? SIN_ELEMENTOS;
  const total = lista.length;
  const activo = tamano !== undefined && tamano > 0;
  const porPagina = activo ? tamano : Math.max(total, 1);
  const paginas = Math.max(1, Math.ceil(total / porPagina));
  const solicitada = elegida.clave === reiniciarCon ? elegida.pagina : 1;
  const pagina = Math.min(Math.max(solicitada, 1), paginas);
  const visibles = activo ? lista.slice((pagina - 1) * porPagina, pagina * porPagina) : lista;

  const irAPagina = useCallback((p: number) => setElegida({ pagina: p, clave: reiniciarCon }), [reiniciarCon]);
  const paginacion: PropiedadesPaginacion = { pagina, paginas, total, tamano: porPagina, onCambiar: irAPagina };

  return { visibles, pagina, paginas, total, irAPagina, paginacion };
}
