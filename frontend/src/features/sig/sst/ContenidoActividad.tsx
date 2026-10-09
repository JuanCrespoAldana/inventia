import { Eye, HandMetal, Info } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { AREA_PAUSA, etiqueta } from "@/lib/etiquetas";
import type { ActividadSst } from "@/types/api";

/** Mensaje, pasos y recomendaciones de una actividad. Lo comparten la pausa real, la vista previa y la guía. */
export function ContenidoActividad({ actividad }: { actividad: ActividadSst }) {
  return (
    <div className="flex flex-col gap-5">
      <div>
        <Badge tono="accent">{etiqueta(AREA_PAUSA, actividad.area)}</Badge>
        <h3 className="mt-2 font-display text-xl font-semibold text-ink">{actividad.titulo}</h3>
        <p className="mt-1 text-sm text-ink-dim">{actividad.mensaje}</p>
      </div>
      {actividad.pasos.length > 0 && (
        <section aria-labelledby={`pasos-${actividad.id}`}>
          <h4 id={`pasos-${actividad.id}`} className="mb-2 text-[13px] font-semibold uppercase tracking-wide text-ink-faint">
            Cómo hacerlo
          </h4>
          <ol className="flex flex-col gap-2">
            {actividad.pasos.map((p, i) => (
              <li key={i} className="flex gap-3 text-sm text-ink">
                <span className="tabular flex size-6 shrink-0 items-center justify-center rounded-full bg-accent-dim text-xs font-semibold text-accent-light" aria-hidden>
                  {i + 1}
                </span>
                <span className="pt-0.5">{p}</span>
              </li>
            ))}
          </ol>
        </section>
      )}
      {actividad.consejos.length > 0 && (
        <section aria-labelledby={`consejos-${actividad.id}`} className="rounded-(--radius-control) border border-line bg-surface-2 px-4 py-3">
          <h4 id={`consejos-${actividad.id}`} className="mb-2 flex items-center gap-2 text-[13px] font-semibold uppercase tracking-wide text-ink-faint">
            <Eye className="size-4" aria-hidden />
            Postura, ojos, manos y descanso
          </h4>
          <ul className="flex flex-col gap-1.5 text-sm text-ink-dim">
            {actividad.consejos.map((c, i) => (
              <li key={i} className="flex gap-2">
                <HandMetal className="mt-0.5 size-3.5 shrink-0 text-ink-faint" aria-hidden />
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
      <p className="flex items-center gap-2 text-xs text-ink-faint">
        <Info className="size-3.5" aria-hidden />
        Si sientes dolor o mareo, detén el ejercicio y consulta a tu área de seguridad y salud en el trabajo.
      </p>
    </div>
  );
}
