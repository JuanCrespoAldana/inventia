import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/cn";
import type { BloqueAsistente } from "@/types/api";
import { formatearCelda, partirNegritas } from "./formato";

const TONO_TEXTO = { neutral: "text-ink", accent: "text-accent-light", success: "text-success", warning: "text-warning", danger: "text-danger" } as const;
const TONO_BARRA = { neutral: "bg-accent", accent: "bg-accent", success: "bg-success", warning: "bg-warning", danger: "bg-danger" } as const;

/** Texto del asistente: respeta las `**negritas**` y los saltos de línea, y nunca se interpreta como HTML. */
export function TextoAsistente({ texto, className }: { texto: string; className?: string }) {
  return (
    <p className={cn("whitespace-pre-line text-sm leading-relaxed text-ink", className)}>
      {partirNegritas(texto).map((t, i) =>
        t.negrita ? (
          <strong key={i} className="font-semibold">
            {t.texto}
          </strong>
        ) : (
          <span key={i}>{t.texto}</span>
        ),
      )}
    </p>
  );
}

function Titulo({ texto }: { texto?: string | null }) {
  return texto ? <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-faint">{texto}</h3> : null;
}

/** Una ruta solo es un enlace interno si empieza por «/» (nunca se navega a direcciones externas). */
export const esRutaInterna = (ruta: string | null | undefined): ruta is string => typeof ruta === "string" && ruta.startsWith("/") && !ruta.startsWith("//");

export function BloqueVista({ bloque }: { bloque: BloqueAsistente }) {
  switch (bloque.tipo) {
    case "metricas":
      return (
        <section aria-label={bloque.titulo ?? "Cifras"}>
          <Titulo texto={bloque.titulo} />
          <dl className="grid grid-cols-2 gap-2 lg:grid-cols-3">
            {bloque.metricas.map((m, i) => (
              <div key={`${m.etiqueta}-${i}`} className="min-w-0 rounded-(--radius-control) border border-line bg-surface px-3 py-2.5">
                <dt className="truncate text-xs text-ink-faint">{m.etiqueta}</dt>
                <dd className={cn("tabular mt-0.5 break-words font-display text-base font-semibold leading-tight", TONO_TEXTO[m.tono ?? "neutral"])}>{m.valor}</dd>
                {m.detalle && <dd className="mt-0.5 text-xs text-ink-faint">{m.detalle}</dd>}
              </div>
            ))}
          </dl>
        </section>
      );

    case "tabla":
      return (
        <section aria-label={bloque.titulo ?? "Resultados"}>
          <Titulo texto={bloque.titulo} />
          <div className="overflow-x-auto rounded-(--radius-control) border border-line bg-surface">
            <table className="w-full min-w-max border-collapse text-[13px]">
              <caption className="sr-only">{bloque.titulo ?? "Resultados de la consulta"}</caption>
              <thead>
                <tr className="border-b border-line text-left text-[11px] font-semibold uppercase tracking-wide text-ink-faint">
                  {bloque.columnas.map((c) => (
                    <th key={c.clave} scope="col" className={cn("px-3 py-2 font-semibold", c.alinear === "der" && "text-right")}>
                      {c.etiqueta}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {bloque.filas.map((fila, i) => (
                  <tr key={i}>
                    {bloque.columnas.map((c, j) => {
                      const texto = formatearCelda(fila.celdas[c.clave], c.formato);
                      const tono = fila.tonos?.[c.clave];
                      return (
                        <td key={c.clave} className={cn("px-3 py-2 text-ink", c.alinear === "der" && "tabular text-right")}>
                          {tono ? (
                            <Badge tono={tono}>{texto}</Badge>
                          ) : j === 0 && esRutaInterna(fila.ruta) ? (
                            <Link to={fila.ruta} className="font-medium text-accent-light underline-offset-2 hover:underline">
                              {texto}
                            </Link>
                          ) : (
                            texto
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {bloque.nota && <p className="mt-1.5 text-xs text-ink-faint">{bloque.nota}</p>}
        </section>
      );

    case "barras": {
      const maximo = Math.max(1, ...bloque.barras.map((b) => Math.abs(b.valor)));
      return (
        <section aria-label={bloque.titulo ?? "Comparación"}>
          <Titulo texto={bloque.titulo} />
          <ul className="flex flex-col gap-2.5">
            {bloque.barras.map((b, i) => (
              <li key={`${b.etiqueta}-${i}`}>
                <div className="mb-1 flex items-baseline justify-between gap-3 text-[13px]">
                  <span className="truncate text-ink">{b.etiqueta}</span>
                  <span className="tabular shrink-0 font-semibold text-ink">{b.texto}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-surface-3" role="presentation">
                  <div className={cn("h-full rounded-full", TONO_BARRA.neutral)} style={{ width: `${Math.max(2, (Math.abs(b.valor) / maximo) * 100)}%` }} />
                </div>
              </li>
            ))}
          </ul>
        </section>
      );
    }

    case "lista":
      return (
        <section aria-label={bloque.titulo ?? "Lista"}>
          <Titulo texto={bloque.titulo} />
          <ul className="list-disc space-y-1 pl-5 text-sm text-ink marker:text-ink-faint">
            {bloque.elementos.map((e, i) => (
              <li key={i}>
                <TextoAsistente texto={e} className="inline" />
              </li>
            ))}
          </ul>
        </section>
      );
  }
}

export function Enlaces({ enlaces }: { enlaces: { etiqueta: string; ruta: string }[] }) {
  const internos = enlaces.filter((e) => esRutaInterna(e.ruta));
  if (internos.length === 0) return null;
  return (
    <nav aria-label="Pantallas relacionadas" className="flex flex-wrap gap-2">
      {internos.map((e) => (
        <Link
          key={e.ruta}
          to={e.ruta}
          className="inline-flex items-center gap-1 rounded-full border border-line-strong bg-surface-2 px-3 py-1 text-xs font-medium text-ink-dim transition hover:bg-surface-3 hover:text-ink"
        >
          {e.etiqueta}
          <ArrowUpRight className="size-3.5" aria-hidden />
        </Link>
      ))}
    </nav>
  );
}
