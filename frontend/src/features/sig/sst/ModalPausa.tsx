import { useEffect, useState } from "react";
import { CheckCircle2, Timer } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import type { ActividadSst } from "@/types/api";
import { ContenidoActividad } from "./ContenidoActividad";
import { formatoTemporizador } from "./programacion";

interface Props {
  actividad: ActividadSst;
  /** Vista previa (administración): no registra nada y se puede cerrar libremente. */
  vistaPrevia?: boolean;
  guardando?: boolean;
  error?: string | null;
  /** Segundos que la persona tardó (desde que se mostró). */
  onRealizada?: (segundos: number) => void;
  onOmitida?: (segundos: number) => void;
  onCerrarVistaPrevia?: () => void;
}

/** Diálogo de pausa activa: mensaje, ejercicio paso a paso, temporizador y registro de «realizada» u «omitida». */
export function ModalPausa({ actividad, vistaPrevia = false, guardando = false, error, onRealizada, onOmitida, onCerrarVistaPrevia }: Props) {
  // `key` en quien lo usa reinicia el diálogo si cambia la actividad: el inicio solo se fija al montarse.
  const [inicio] = useState(() => Date.now());
  const [ahora, setAhora] = useState(inicio);

  useEffect(() => {
    const id = window.setInterval(() => setAhora(Date.now()), 500);
    return () => window.clearInterval(id);
  }, []);

  const restante = Math.max(0, actividad.duracion_segundos - Math.floor((ahora - inicio) / 1000));
  const segundos = () => Math.min(3600, Math.max(0, Math.round((Date.now() - inicio) / 1000)));
  const terminado = restante === 0;
  const progreso = 1 - restante / Math.max(1, actividad.duracion_segundos);

  return (
    <Modal
      abierto
      ancho="lg"
      titulo={vistaPrevia ? "Vista previa de la pausa activa" : "Pausa activa"}
      descripcion={vistaPrevia ? "Así la verán las personas. Esta vista no registra nada." : "Tómate un momento para cuidar tu cuerpo. Tu trabajo está guardado y te espera."}
      bloqueaPausas={false}
      bloqueado={!vistaPrevia}
      ocultarCierre={!vistaPrevia}
      onCerrar={vistaPrevia ? (onCerrarVistaPrevia ?? (() => undefined)) : () => undefined}
      pie={
        vistaPrevia ? (
          <Button onClick={onCerrarVistaPrevia}>Cerrar vista previa</Button>
        ) : (
          <>
            <Button variante="ghost" disabled={guardando} onClick={() => onOmitida?.(segundos())}>
              Omitir por ahora
            </Button>
            <Button cargando={guardando} onClick={() => onRealizada?.(segundos())} icono={<CheckCircle2 className="size-4" aria-hidden />}>
              Realicé la pausa
            </Button>
          </>
        )
      }
    >
      <div className="flex flex-col gap-5">
        {error && (
          <p role="alert" className="rounded-(--radius-control) border border-danger/30 bg-danger-dim px-4 py-3 text-sm text-danger">
            {error}
          </p>
        )}
        <div className="flex items-center gap-4 rounded-(--radius-control) border border-line bg-surface-2 px-4 py-3">
          <div className="relative size-14 shrink-0" aria-hidden>
            <svg viewBox="0 0 36 36" className="size-14 -rotate-90">
              <circle cx="18" cy="18" r="15.5" fill="none" stroke="rgb(255 255 255 / 0.08)" strokeWidth="3" />
              <circle
                cx="18"
                cy="18"
                r="15.5"
                fill="none"
                stroke="currentColor"
                className="text-accent-light transition-[stroke-dashoffset] duration-500"
                strokeWidth="3"
                strokeLinecap="round"
                strokeDasharray={2 * Math.PI * 15.5}
                strokeDashoffset={2 * Math.PI * 15.5 * (1 - progreso)}
              />
            </svg>
            <Timer className="absolute inset-0 m-auto size-5 text-ink-dim" />
          </div>
          <div>
            <p className="tabular font-display text-2xl font-semibold text-ink">{formatoTemporizador(restante)}</p>
            <p className="text-xs text-ink-faint" role="status" aria-live="polite">
              {terminado ? "¡Tiempo cumplido! Cuando termines, marca la pausa como realizada." : `Duración sugerida: ${formatoTemporizador(actividad.duracion_segundos)}`}
            </p>
          </div>
        </div>
        <ContenidoActividad actividad={actividad} />
      </div>
    </Modal>
  );
}
