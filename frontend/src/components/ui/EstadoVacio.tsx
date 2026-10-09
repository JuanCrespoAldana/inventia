import type { ReactNode } from "react";
import { AlertTriangle, Inbox } from "lucide-react";
import { Button } from "./Button";
import { mensajeDeError } from "@/lib/errors";

/** `comoPagina`: el estado ocupa toda la pantalla (sin otro encabezado), así que su título es el h1. */
export function EstadoVacio({ titulo, descripcion, accion, icono, comoPagina = false }: { titulo: string; descripcion?: string; accion?: ReactNode; icono?: ReactNode; comoPagina?: boolean }) {
  const Titulo = comoPagina ? "h1" : "p";
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-14 text-center">
      <div className="flex size-12 items-center justify-center rounded-2xl bg-surface-2 text-ink-faint ring-1 ring-line">{icono ?? <Inbox className="size-5" aria-hidden />}</div>
      <div>
        <Titulo className="font-display text-base font-semibold text-ink">{titulo}</Titulo>
        {descripcion && <p className="mx-auto mt-1 max-w-md text-sm text-ink-dim">{descripcion}</p>}
      </div>
      {accion}
    </div>
  );
}

export function EstadoError({ error, onReintentar }: { error: unknown; onReintentar?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center justify-center gap-3 px-6 py-12 text-center">
      <div className="flex size-12 items-center justify-center rounded-2xl bg-danger-dim text-danger ring-1 ring-danger/30">
        <AlertTriangle className="size-5" aria-hidden />
      </div>
      <div>
        <p className="font-display text-base font-semibold text-ink">No se pudo cargar la información</p>
        <p className="mx-auto mt-1 max-w-md text-sm text-ink-dim">{mensajeDeError(error)}</p>
      </div>
      {onReintentar && (
        <Button variante="secondary" tamano="sm" onClick={onReintentar}>
          Reintentar
        </Button>
      )}
    </div>
  );
}
