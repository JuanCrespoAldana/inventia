import { cn } from "@/lib/cn";
import { abreviar, limitesNiceos } from "./escala";

export interface ColumnaDato {
  clave: string;
  etiqueta: string;
  valor: number;
  /** Texto accesible/tooltip, por ejemplo «Marzo: 12 vehículos». */
  descripcion?: string;
}

const COLOR = { accent: "bg-accent", success: "bg-success", warning: "bg-warning" };

/**
 * Gráfico de columnas (HTML/CSS, sin dependencias). Cada columna lleva su valor como texto para lectores de pantalla
 * y la serie completa se expone como lista; el eje se redondea a valores «bonitos».
 */
export function Columnas({
  datos,
  formato = (n) => abreviar(n),
  formatoEje,
  descripcion,
  alto = 200,
  tono = "accent",
}: {
  datos: ColumnaDato[];
  formato?: (n: number) => string;
  /** Formato (más corto) para las marcas del eje; por defecto el mismo que el de los valores. */
  formatoEje?: (n: number) => string;
  descripcion: string;
  alto?: number;
  tono?: keyof typeof COLOR;
}) {
  const { max, marcas } = limitesNiceos(0, Math.max(0, ...datos.map((d) => d.valor)), 4);
  const tope = max || 1;
  return (
    <figure className="m-0" aria-label={descripcion}>
      <div className="flex gap-2">
        <div className="relative flex shrink-0 flex-col-reverse justify-between text-right text-[10px] text-ink-faint" style={{ height: alto }} aria-hidden>
          {marcas.map((m) => (
            <span key={m} className="tabular leading-none">
              {(formatoEje ?? formato)(m)}
            </span>
          ))}
        </div>
        <div className="relative min-w-0 flex-1">
          <div className="pointer-events-none absolute inset-x-0 top-0 flex flex-col-reverse justify-between" style={{ height: alto }} aria-hidden>
            {marcas.map((m) => (
              <div key={m} className="border-t border-line" />
            ))}
          </div>
          <ul className="relative flex items-end gap-1 sm:gap-1.5" style={{ height: alto }}>
            {datos.map((d) => (
              <li key={d.clave} className="group relative flex h-full min-w-0 flex-1 flex-col justify-end" title={d.descripcion ?? `${d.etiqueta}: ${formato(d.valor)}`}>
                <span className="sr-only">{d.descripcion ?? `${d.etiqueta}: ${formato(d.valor)}`}</span>
                <div
                  className={cn("mx-auto w-full max-w-16 rounded-t-md transition-[height] duration-500", COLOR[tono], d.valor === 0 && "opacity-25")}
                  style={{ height: d.valor === 0 ? 2 : `${Math.max(2, (d.valor / tope) * 100)}%` }}
                  aria-hidden
                />
                <span className="tabular pointer-events-none absolute -top-5 left-1/2 hidden -translate-x-1/2 whitespace-nowrap rounded bg-surface-3 px-1.5 py-0.5 text-[10px] text-ink group-hover:block" aria-hidden>
                  {formato(d.valor)}
                </span>
              </li>
            ))}
          </ul>
          <div className="mt-1.5 flex gap-1 sm:gap-1.5" aria-hidden>
            {datos.map((d) => (
              <span key={d.clave} className="min-w-0 flex-1 truncate text-center text-[10px] text-ink-faint">
                {d.etiqueta}
              </span>
            ))}
          </div>
        </div>
      </div>
    </figure>
  );
}
