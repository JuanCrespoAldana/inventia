import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/cn";

const BASE =
  "w-full rounded-(--radius-control) border border-line-strong bg-surface-2 px-3.5 text-sm text-ink placeholder:text-ink-faint " +
  "transition focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30 disabled:cursor-not-allowed disabled:opacity-60";

interface CampoProps {
  etiqueta: string;
  error?: string;
  ayuda?: string;
  requerido?: boolean;
  children: (props: { id: string; "aria-invalid": boolean | undefined; "aria-describedby": string | undefined }) => ReactNode;
  className?: string;
}

/** Envuelve un control con etiqueta, ayuda y mensaje de error asociados por accesibilidad. */
export function Campo({ etiqueta, error, ayuda, requerido, children, className }: CampoProps) {
  const id = useId();
  const idMensaje = `${id}-msg`;
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label htmlFor={id} className="text-[13px] font-medium text-ink-dim">
        {etiqueta}
        {requerido && <span className="ml-0.5 text-accent-light" aria-hidden> *</span>}
      </label>
      {children({ id, "aria-invalid": error ? true : undefined, "aria-describedby": error || ayuda ? idMensaje : undefined })}
      {error ? (
        <p id={idMensaje} role="alert" className="text-xs text-danger">
          {error}
        </p>
      ) : ayuda ? (
        <p id={idMensaje} className="text-xs text-ink-faint">
          {ayuda}
        </p>
      ) : null}
    </div>
  );
}

interface EntradaProps extends InputHTMLAttributes<HTMLInputElement> {
  etiqueta: string;
  error?: string;
  ayuda?: string;
}

export function Input({ etiqueta, error, ayuda, className, required, ...resto }: EntradaProps) {
  return (
    <Campo etiqueta={etiqueta} error={error} ayuda={ayuda} requerido={required} className={className}>
      {(p) => <input {...p} required={required} className={cn(BASE, "h-10", error && "border-danger/70")} {...resto} />}
    </Campo>
  );
}

interface AreaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  etiqueta: string;
  error?: string;
  ayuda?: string;
}

export function Textarea({ etiqueta, error, ayuda, className, required, rows = 3, ...resto }: AreaProps) {
  return (
    <Campo etiqueta={etiqueta} error={error} ayuda={ayuda} requerido={required} className={className}>
      {(p) => <textarea {...p} rows={rows} required={required} className={cn(BASE, "resize-y py-2.5", error && "border-danger/70")} {...resto} />}
    </Campo>
  );
}

interface SeleccionProps extends SelectHTMLAttributes<HTMLSelectElement> {
  etiqueta: string;
  error?: string;
  ayuda?: string;
}

export function Select({ etiqueta, error, ayuda, className, children, required, ...resto }: SeleccionProps) {
  return (
    <Campo etiqueta={etiqueta} error={error} ayuda={ayuda} requerido={required} className={className}>
      {(p) => (
        <div className="relative">
          <select {...p} required={required} className={cn(BASE, "h-10 appearance-none pr-9", error && "border-danger/70")} {...resto}>
            {children}
          </select>
          <ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-ink-faint" aria-hidden />
        </div>
      )}
    </Campo>
  );
}

/** Select compacto para barras de filtros: la etiqueta es solo para lectores de pantalla. */
export function FiltroSelect({ etiqueta, className, children, ...resto }: Omit<SeleccionProps, "error" | "ayuda">) {
  return (
    <div className={cn("relative min-w-36", className)}>
      <select
        aria-label={etiqueta}
        className={cn(BASE, "h-9 appearance-none pr-8 text-[13px]")}
        {...resto}
      >
        {children}
      </select>
      <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 size-4 -translate-y-1/2 text-ink-faint" aria-hidden />
    </div>
  );
}

export function FiltroFecha({ etiqueta, className, ...resto }: Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & { etiqueta: string }) {
  return (
    <label className={cn("flex items-center gap-2 text-xs text-ink-faint", className)}>
      <span className="shrink-0">{etiqueta}</span>
      <input type="date" className={cn(BASE, "h-9 w-auto px-2.5 text-[13px]")} {...resto} />
    </label>
  );
}

interface CasillaProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  etiqueta: ReactNode;
  descripcion?: string;
}

export function Casilla({ etiqueta, descripcion, className, ...resto }: CasillaProps) {
  const id = useId();
  return (
    <div className={cn("flex items-start gap-3", className)}>
      <input
        id={id}
        type="checkbox"
        className="mt-0.5 size-4 shrink-0 cursor-pointer rounded border-line-strong bg-surface-2 accent-[#4C6FFF] disabled:cursor-not-allowed"
        {...resto}
      />
      <label htmlFor={id} className="cursor-pointer text-sm text-ink">
        {etiqueta}
        {descripcion && <span className="mt-0.5 block text-xs text-ink-faint">{descripcion}</span>}
      </label>
    </div>
  );
}

interface InterruptorProps {
  activo: boolean;
  onChange: (activo: boolean) => void;
  etiqueta: string;
  disabled?: boolean;
}

export function Interruptor({ activo, onChange, etiqueta, disabled }: InterruptorProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={activo}
      aria-label={etiqueta}
      disabled={disabled}
      onClick={() => onChange(!activo)}
      className={cn(
        "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border transition disabled:cursor-not-allowed disabled:opacity-50",
        activo ? "border-accent bg-accent" : "border-line-strong bg-surface-3",
      )}
    >
      <span className={cn("inline-block size-4 rounded-full bg-white shadow transition-transform", activo ? "translate-x-6" : "translate-x-1")} />
    </button>
  );
}
