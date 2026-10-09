import { cn } from "@/lib/cn";

export interface BarraDato {
  clave: string;
  etiqueta: string;
  valor: number;
  detalle?: string;
  tono?: "accent" | "success" | "warning" | "danger";
}

const COLOR = { accent: "bg-accent", success: "bg-success", warning: "bg-warning", danger: "bg-danger" };

/** Barras horizontales con valores visibles: más legibles que un gráfico de columnas para etiquetas largas. */
export function BarrasHorizontales({ datos, formato, descripcion }: { datos: BarraDato[]; formato: (n: number) => string; descripcion: string }) {
  const maximo = Math.max(1, ...datos.map((d) => d.valor));
  return (
    <ul className="flex flex-col gap-3" aria-label={descripcion}>
      {datos.map((d) => (
        <li key={d.clave}>
          <div className="mb-1 flex items-baseline justify-between gap-3 text-[13px]">
            <span className="truncate text-ink">{d.etiqueta}</span>
            <span className="tabular shrink-0 font-semibold text-ink">{formato(d.valor)}</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-surface-3" role="presentation">
            <div className={cn("h-full rounded-full transition-[width] duration-500", COLOR[d.tono ?? "accent"])} style={{ width: `${Math.max(2, (d.valor / maximo) * 100)}%` }} />
          </div>
          {d.detalle && <p className="mt-1 text-xs text-ink-faint">{d.detalle}</p>}
        </li>
      ))}
    </ul>
  );
}
