import { useEffect, useId, useRef, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Loader2, Search } from "lucide-react";
import { cn } from "@/lib/cn";
import { entero } from "@/lib/format";
import type { ProductoResumen } from "@/types/api";

export interface OpcionProducto {
  producto: ProductoResumen;
  /** Existencias disponibles en la sede de origen (cuando aplica). */
  disponible?: number;
  precio?: number | null;
}

interface Props {
  etiqueta: string;
  /** Identifica el origen de datos para la caché (p. ej. `["sede", 3]`). */
  origen: readonly unknown[];
  buscar: (q: string) => Promise<OpcionProducto[]>;
  onElegir: (opcion: OpcionProducto) => void;
  deshabilitado?: boolean;
  placeholder?: string;
  ayuda?: string;
}

/** Combobox accesible con búsqueda en servidor (por código o nombre). */
export function SelectorProducto({ etiqueta, origen, buscar, onElegir, deshabilitado, placeholder = "Buscar por código o nombre…", ayuda }: Props) {
  const id = useId();
  const [texto, setTexto] = useState("");
  const [consulta, setConsulta] = useState("");
  const [abierto, setAbierto] = useState(false);
  const [activo, setActivo] = useState(0);
  const contenedor = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const t = window.setTimeout(() => setConsulta(texto.trim()), 250);
    return () => window.clearTimeout(t);
  }, [texto]);

  useEffect(() => {
    const alClic = (e: MouseEvent) => {
      if (!contenedor.current?.contains(e.target as Node)) setAbierto(false);
    };
    document.addEventListener("mousedown", alClic);
    return () => document.removeEventListener("mousedown", alClic);
  }, []);

  const resultados = useQuery({
    queryKey: ["selector-producto", ...origen, consulta],
    queryFn: () => buscar(consulta),
    enabled: abierto && !deshabilitado,
    placeholderData: keepPreviousData,
    staleTime: 15_000,
  });
  const opciones = resultados.data ?? [];

  function elegir(o: OpcionProducto) {
    onElegir(o);
    setTexto("");
    setConsulta("");
    setAbierto(false);
  }

  function alTeclear(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setAbierto(true);
      setActivo((a) => Math.min(a + 1, Math.max(opciones.length - 1, 0)));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActivo((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter" && abierto && opciones[activo]) {
      e.preventDefault();
      elegir(opciones[activo]);
    } else if (e.key === "Escape" && abierto) {
      e.stopPropagation();
      setAbierto(false);
    }
  }

  return (
    <div ref={contenedor} className="relative flex flex-col gap-1.5">
      <label htmlFor={id} className="text-[13px] font-medium text-ink-dim">
        {etiqueta}
      </label>
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-faint" aria-hidden />
        <input
          id={id}
          role="combobox"
          aria-expanded={abierto}
          aria-controls={`${id}-lista`}
          aria-autocomplete="list"
          aria-activedescendant={abierto && opciones[activo] ? `${id}-op-${opciones[activo].producto.id}` : undefined}
          autoComplete="off"
          disabled={deshabilitado}
          value={texto}
          placeholder={placeholder}
          onChange={(e) => {
            setTexto(e.target.value);
            setAbierto(true);
            setActivo(0);
          }}
          onFocus={() => setAbierto(true)}
          onKeyDown={alTeclear}
          className="h-10 w-full rounded-(--radius-control) border border-line-strong bg-surface-2 pl-9 pr-9 text-sm text-ink placeholder:text-ink-faint transition focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30 disabled:cursor-not-allowed disabled:opacity-60"
        />
        {resultados.isFetching && <Loader2 className="absolute right-3 top-1/2 size-4 -translate-y-1/2 animate-spin text-ink-faint" aria-hidden />}
      </div>
      {ayuda && <p className="text-xs text-ink-faint">{ayuda}</p>}
      {abierto && !deshabilitado && (
        <div
          id={`${id}-lista`}
          role="listbox"
          aria-label={`Resultados de ${etiqueta}`}
          className="absolute left-0 right-0 top-full z-30 mt-1 max-h-64 overflow-y-auto rounded-(--radius-control) border border-line-strong bg-surface-2 p-1 shadow-(--shadow-pop)"
        >
          {opciones.length === 0 && !resultados.isFetching && <p className="px-3 py-3 text-sm text-ink-dim">No se encontraron productos.</p>}
          {opciones.map((o, i) => (
            <div
              key={o.producto.id}
              id={`${id}-op-${o.producto.id}`}
              role="option"
              tabIndex={-1}
              aria-selected={i === activo}
              onMouseEnter={() => setActivo(i)}
              onMouseDown={(e) => {
                e.preventDefault();
                elegir(o);
              }}
              className={cn("flex cursor-pointer items-center justify-between gap-3 rounded-lg px-3 py-2 text-sm", i === activo ? "bg-accent-dim" : "hover:bg-white/5")}
            >
              <span className="min-w-0">
                <span className="block truncate font-medium text-ink">{o.producto.nombre}</span>
                <span className="block text-xs text-ink-faint">{o.producto.codigo}</span>
              </span>
              {o.disponible !== undefined && (
                <span className={cn("tabular shrink-0 text-xs font-semibold", o.disponible > 0 ? "text-ink-dim" : "text-danger")}>
                  {o.disponible > 0 ? `${entero(o.disponible)} disp.` : "Sin existencias"}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
