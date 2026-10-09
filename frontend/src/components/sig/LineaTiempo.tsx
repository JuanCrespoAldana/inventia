import { ArrowRight, CircleDot, MessageSquareText } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { estado, EVENTO_HISTORIAL, etiqueta, type Tono } from "@/lib/etiquetas";
import { fechaHora } from "@/lib/format";

export interface EventoLinea {
  id: number;
  fecha: string;
  usuario_nombre?: string | null;
  evento: string;
  estado_anterior: string | null;
  estado_nuevo: string | null;
  texto: string | null;
}

/** Historial cronológico (el más antiguo arriba): cambios de estado, respuestas y observaciones con fecha y autor. */
export function LineaTiempo({ eventos, estados, vacio = "Aún no hay movimientos en el historial." }: { eventos: EventoLinea[]; estados: Record<string, { etiqueta: string; tono: Tono }>; vacio?: string }) {
  if (eventos.length === 0) return <p className="text-sm text-ink-faint">{vacio}</p>;
  return (
    <ol className="flex flex-col" aria-label="Historial">
      {eventos.map((e, i) => {
        const esComentario = e.evento === "observacion" || e.evento === "respuesta";
        const Icono = esComentario ? MessageSquareText : CircleDot;
        return (
          <li key={e.id} className="relative flex gap-3 pb-5 last:pb-0">
            {i < eventos.length - 1 && <span className="absolute left-[11px] top-6 h-[calc(100%-1.25rem)] w-px bg-line" aria-hidden />}
            <span className="relative mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-surface-2 text-ink-faint ring-1 ring-line" aria-hidden>
              <Icono className="size-3.5" />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
                <span className="font-semibold text-ink">{etiqueta(EVENTO_HISTORIAL, e.evento)}</span>
                {e.estado_nuevo && (
                  <span className="inline-flex flex-wrap items-center gap-1.5">
                    {e.estado_anterior && (
                      <>
                        <Badge tono={estado(estados, e.estado_anterior).tono}>{estado(estados, e.estado_anterior).etiqueta}</Badge>
                        <ArrowRight className="size-3.5 text-ink-faint" aria-hidden />
                      </>
                    )}
                    <Badge tono={estado(estados, e.estado_nuevo).tono}>{estado(estados, e.estado_nuevo).etiqueta}</Badge>
                  </span>
                )}
              </div>
              <p className="text-xs text-ink-faint">
                {e.usuario_nombre ?? "—"} · {fechaHora(e.fecha)}
              </p>
              {e.texto && <p className="mt-1.5 whitespace-pre-line rounded-(--radius-control) bg-surface-2 px-3 py-2 text-sm text-ink">{e.texto}</p>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
