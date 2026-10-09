import { cn } from "@/lib/cn";

export interface PestanaDef<T extends string> {
  clave: T;
  etiqueta: string;
  conteo?: number;
}

export function Pestanas<T extends string>({ pestanas, activa, onCambiar, etiqueta }: { pestanas: PestanaDef<T>[]; activa: T; onCambiar: (clave: T) => void; etiqueta: string }) {
  return (
    <div role="tablist" aria-label={etiqueta} className="inline-flex max-w-full gap-1 overflow-x-auto rounded-(--radius-control) border border-line bg-surface p-1">
      {pestanas.map((p) => (
        <button
          key={p.clave}
          type="button"
          role="tab"
          aria-selected={activa === p.clave}
          onClick={() => onCambiar(p.clave)}
          className={cn(
            "inline-flex items-center gap-2 whitespace-nowrap rounded-lg px-3.5 py-1.5 text-[13px] font-semibold transition",
            activa === p.clave ? "bg-accent-dim text-accent-light" : "text-ink-dim hover:text-ink",
          )}
        >
          {p.etiqueta}
          {p.conteo !== undefined && <span className="tabular rounded-full bg-white/8 px-1.5 text-[11px] text-ink-dim">{p.conteo}</span>}
        </button>
      ))}
    </div>
  );
}
