import { ChevronLeft, ChevronRight } from "lucide-react";
import { entero } from "@/lib/format";
import { IconButton } from "./Button";

interface PaginacionProps {
  pagina: number;
  paginas: number;
  total: number;
  tamano: number;
  onCambiar: (p: number) => void;
  /** Lo que se cuenta, si no son filas: «módulos», «roles»… Se agrega después del total. */
  unidad?: string;
  /** Nombre accesible de la navegación; cámbielo cuando haya más de un paginador en la misma pantalla. */
  etiqueta?: string;
}

export function Paginacion({ pagina, paginas, total, tamano, onCambiar, unidad, etiqueta = "Paginación" }: PaginacionProps) {
  if (total === 0) return null;
  const desde = (pagina - 1) * tamano + 1;
  const hasta = Math.min(pagina * tamano, total);
  return (
    <nav aria-label={etiqueta} className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-5 py-3 text-[13px] text-ink-dim">
      <span className="tabular">
        {entero(desde)}–{entero(hasta)} de {entero(total)}
        {unidad ? ` ${unidad}` : ""}
      </span>
      <div className="flex items-center gap-1">
        <IconButton etiqueta="Página anterior" disabled={pagina <= 1} onClick={() => onCambiar(pagina - 1)}>
          <ChevronLeft className="size-4" aria-hidden />
        </IconButton>
        <span className="tabular min-w-24 text-center">
          Página {pagina} de {Math.max(paginas, 1)}
        </span>
        <IconButton etiqueta="Página siguiente" disabled={pagina >= paginas} onClick={() => onCambiar(pagina + 1)}>
          <ChevronRight className="size-4" aria-hidden />
        </IconButton>
      </div>
    </nav>
  );
}
