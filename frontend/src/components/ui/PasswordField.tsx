import { useState, type InputHTMLAttributes } from "react";
import { Check, Eye, EyeOff, Circle } from "lucide-react";
import { cn } from "@/lib/cn";
import { REQUISITOS_PASSWORD } from "@/lib/formularios";
import { Campo } from "./Field";

interface Props extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  etiqueta: string;
  error?: string;
  ayuda?: string;
  /** Muestra la lista de requisitos y cuáles se cumplen. */
  mostrarRequisitos?: boolean;
  valorActual?: string;
}

export function CampoPassword({ etiqueta, error, ayuda, mostrarRequisitos, valorActual = "", className, required, ...resto }: Props) {
  const [visible, setVisible] = useState(false);
  return (
    <div className={className}>
      <Campo etiqueta={etiqueta} error={error} ayuda={ayuda} requerido={required}>
        {(p) => (
          <div className="relative">
            <input
              {...p}
              required={required}
              type={visible ? "text" : "password"}
              className={cn(
                "h-10 w-full rounded-(--radius-control) border border-line-strong bg-surface-2 pl-3.5 pr-11 text-sm text-ink placeholder:text-ink-faint transition",
                "focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30 disabled:opacity-60",
                error && "border-danger/70",
              )}
              {...resto}
            />
            <button
              type="button"
              onClick={() => setVisible((v) => !v)}
              aria-label={visible ? "Ocultar contraseña" : "Mostrar contraseña"}
              aria-pressed={visible}
              className="absolute right-1.5 top-1/2 flex size-8 -translate-y-1/2 items-center justify-center rounded-lg text-ink-faint transition hover:text-ink"
            >
              {visible ? <EyeOff className="size-4" aria-hidden /> : <Eye className="size-4" aria-hidden />}
            </button>
          </div>
        )}
      </Campo>
      {mostrarRequisitos && (
        <ul className="mt-2.5 grid grid-cols-1 gap-1 sm:grid-cols-2" aria-label="Requisitos de la contraseña">
          {REQUISITOS_PASSWORD.map((r) => {
            const ok = r.cumple(valorActual);
            return (
              <li key={r.texto} className={cn("flex items-center gap-2 text-xs", ok ? "text-success" : "text-ink-faint")}>
                {ok ? <Check className="size-3.5" aria-hidden /> : <Circle className="size-3 opacity-60" aria-hidden />}
                <span>
                  {r.texto}
                  <span className="sr-only">{ok ? ": cumplido" : ": pendiente"}</span>
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
