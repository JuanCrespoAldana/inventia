import { useEffect, useState } from "react";
import { Search, X } from "lucide-react";
import { cn } from "@/lib/cn";

/** Campo de búsqueda con retardo (debounce) para no consultar en cada pulsación. */
export function Busqueda({
  valor,
  onCambiar,
  placeholder = "Buscar…",
  etiqueta = "Buscar",
  className,
  retardo = 350,
}: {
  valor: string;
  onCambiar: (valor: string) => void;
  placeholder?: string;
  etiqueta?: string;
  className?: string;
  retardo?: number;
}) {
  const [texto, setTexto] = useState(valor);
  const [valorPrevio, setValorPrevio] = useState(valor);
  if (valor !== valorPrevio) {
    setValorPrevio(valor);
    setTexto(valor);
  }

  useEffect(() => {
    if (texto === valor) return;
    const t = window.setTimeout(() => onCambiar(texto), retardo);
    return () => window.clearTimeout(t);
  }, [texto, valor, onCambiar, retardo]);

  return (
    <div className={cn("relative min-w-52 flex-1 sm:max-w-xs", className)}>
      <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-faint" aria-hidden />
      <input
        type="search"
        aria-label={etiqueta}
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        placeholder={placeholder}
        className="h-9 w-full rounded-(--radius-control) border border-line-strong bg-surface-2 pl-9 pr-8 text-[13px] text-ink placeholder:text-ink-faint transition focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30 [&::-webkit-search-cancel-button]:hidden"
      />
      {texto && (
        <button
          type="button"
          aria-label="Limpiar búsqueda"
          onClick={() => {
            setTexto("");
            onCambiar("");
          }}
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-ink-faint hover:text-ink"
        >
          <X className="size-3.5" aria-hidden />
        </button>
      )}
    </div>
  );
}
