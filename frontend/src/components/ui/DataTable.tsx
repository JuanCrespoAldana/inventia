import { Fragment, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Skeleton } from "./Skeleton";
import { EstadoError, EstadoVacio } from "./EstadoVacio";

export interface Columna<T> {
  clave: string;
  encabezado: string;
  celda: (fila: T) => ReactNode;
  alinear?: "izquierda" | "derecha" | "centro";
  /** Oculta la columna por debajo de este punto de quiebre (diseño responsivo). */
  desde?: "sm" | "md" | "lg";
  className?: string;
}

interface TablaProps<T> {
  columnas: Columna<T>[];
  filas: T[] | undefined;
  idDe: (fila: T) => string | number;
  cargando?: boolean;
  error?: unknown;
  onReintentar?: () => void;
  vacio?: { titulo: string; descripcion?: string; accion?: ReactNode };
  onFila?: (fila: T) => void;
  descripcion: string;
  filasEsqueleto?: number;
  /** Filas desplegables: `abierta` indica cuáles están expandidas y `detalle` dibuja su contenido. */
  abierta?: (fila: T) => boolean;
  detalle?: (fila: T) => ReactNode;
}

const DESDE = { sm: "hidden sm:table-cell", md: "hidden md:table-cell", lg: "hidden lg:table-cell" };
const ALINEAR = { izquierda: "text-left", derecha: "text-right", centro: "text-center" };

export function Tabla<T>({ columnas, filas, idDe, cargando, error, onReintentar, vacio, onFila, descripcion, filasEsqueleto = 6, abierta, detalle }: TablaProps<T>) {
  if (error && !filas) return <EstadoError error={error} onReintentar={onReintentar} />;
  if (!cargando && filas && filas.length === 0) {
    return <EstadoVacio titulo={vacio?.titulo ?? "Sin resultados"} descripcion={vacio?.descripcion ?? "No hay registros que coincidan con los filtros aplicados."} accion={vacio?.accion} />;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-max border-collapse text-sm md:min-w-0" aria-busy={cargando || undefined}>
        <caption className="sr-only">{descripcion}</caption>
        <thead>
          <tr className="border-b border-line text-left text-xs font-semibold uppercase tracking-wide text-ink-faint">
            {columnas.map((c) => (
              <th key={c.clave} scope="col" className={cn("px-5 py-3 font-semibold", ALINEAR[c.alinear ?? "izquierda"], c.desde && DESDE[c.desde], c.className)}>
                {c.encabezado}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {cargando && !filas
            ? Array.from({ length: filasEsqueleto }, (_, i) => (
                <tr key={i} aria-hidden>
                  {columnas.map((c) => (
                    <td key={c.clave} className={cn("px-5 py-3.5", c.desde && DESDE[c.desde])}>
                      <Skeleton className="h-4 w-full max-w-40" />
                    </td>
                  ))}
                </tr>
              ))
            : filas?.map((fila) => (
                <Fragment key={idDe(fila)}>
                <tr
                  onClick={onFila ? () => onFila(fila) : undefined}
                  onKeyDown={
                    onFila
                      ? (e) => {
                          if (e.target === e.currentTarget && (e.key === "Enter" || e.key === " ")) {
                            e.preventDefault();
                            onFila(fila);
                          }
                        }
                      : undefined
                  }
                  tabIndex={onFila ? 0 : undefined}
                  className={cn("transition-colors", onFila && "cursor-pointer hover:bg-white/3 focus-visible:bg-white/3", cargando && "opacity-60")}
                >
                  {columnas.map((c) => (
                    <td key={c.clave} className={cn("px-5 py-3 align-middle text-ink", ALINEAR[c.alinear ?? "izquierda"], c.desde && DESDE[c.desde], c.className)}>
                      {c.celda(fila)}
                    </td>
                  ))}
                </tr>
                {abierta?.(fila) && detalle && (
                  <tr className="bg-surface-2/40">
                    <td colSpan={columnas.length} className="px-5 py-4">
                      {detalle(fila)}
                    </td>
                  </tr>
                )}
                </Fragment>
              ))}
        </tbody>
      </table>
    </div>
  );
}
