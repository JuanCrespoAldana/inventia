import type { ReactNode } from "react";
import { FilterX } from "lucide-react";
import { Button } from "./Button";

export function BarraFiltros({ children, hayFiltros, onLimpiar }: { children: ReactNode; hayFiltros?: boolean; onLimpiar?: () => void }) {
  return (
    <div role="search" className="flex flex-wrap items-center gap-2.5 border-b border-line px-5 py-3.5">
      {children}
      {hayFiltros && onLimpiar && (
        <Button variante="ghost" tamano="sm" onClick={onLimpiar} icono={<FilterX className="size-4" aria-hidden />}>
          Limpiar filtros
        </Button>
      )}
    </div>
  );
}
