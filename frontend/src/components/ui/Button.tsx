import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/cn";

type Variante = "primary" | "secondary" | "ghost" | "danger";
type Tamano = "sm" | "md";

const VARIANTES: Record<Variante, string> = {
  primary: "bg-accent text-white hover:bg-accent-strong shadow-[0_8px_24px_-10px_rgb(76_111_255/0.7)]",
  secondary: "bg-surface-2 text-ink border border-line-strong hover:bg-surface-3",
  ghost: "text-ink-dim hover:text-ink hover:bg-white/5",
  danger: "bg-danger-dim text-danger border border-danger/30 hover:bg-danger/20",
};
const TAMANOS: Record<Tamano, string> = {
  sm: "h-8 px-3 text-[13px] gap-1.5",
  md: "h-10 px-4 text-sm gap-2",
};

export interface BotonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: Variante;
  tamano?: Tamano;
  cargando?: boolean;
  icono?: ReactNode;
}

export function Button({ variante = "primary", tamano = "md", cargando = false, icono, className, children, disabled, type = "button", ...resto }: BotonProps) {
  return (
    <button
      type={type}
      disabled={disabled || cargando}
      aria-busy={cargando || undefined}
      className={cn(
        "inline-flex shrink-0 select-none items-center justify-center whitespace-nowrap rounded-(--radius-control) font-semibold transition",
        "active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100",
        VARIANTES[variante],
        TAMANOS[tamano],
        className,
      )}
      {...resto}
    >
      {cargando ? <Loader2 className="size-4 animate-spin" aria-hidden /> : icono}
      {children}
    </button>
  );
}

export function IconButton({ etiqueta, className, children, ...resto }: Omit<BotonProps, "icono" | "tamano" | "variante"> & { etiqueta: string }) {
  return (
    <button
      type="button"
      aria-label={etiqueta}
      title={etiqueta}
      className={cn(
        "inline-flex size-9 shrink-0 items-center justify-center rounded-(--radius-control) text-ink-dim transition hover:bg-white/5 hover:text-ink",
        "active:scale-95 disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...resto}
    >
      {children}
    </button>
  );
}
