import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export function Card({ children, className, ...resto }: { children: ReactNode; className?: string } & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("min-w-0 rounded-(--radius-panel) border border-line bg-surface shadow-(--shadow-panel)", className)} {...resto}>
      {children}
    </div>
  );
}

export function CardHeader({ titulo, descripcion, accion, className }: { titulo: string; descripcion?: string; accion?: ReactNode; className?: string }) {
  return (
    <div className={cn("flex flex-wrap items-start justify-between gap-3 border-b border-line px-5 py-4", className)}>
      <div className="min-w-0">
        <h2 className="font-display text-base font-semibold text-ink">{titulo}</h2>
        {descripcion && <p className="mt-0.5 text-[13px] text-ink-faint">{descripcion}</p>}
      </div>
      {accion}
    </div>
  );
}

export function Stat({
  etiqueta,
  valor,
  detalle,
  tono = "neutral",
  icono,
}: {
  etiqueta: string;
  valor: ReactNode;
  detalle?: ReactNode;
  tono?: "neutral" | "danger" | "warning" | "success" | "accent";
  icono?: ReactNode;
}) {
  const color = { neutral: "text-ink", danger: "text-danger", warning: "text-warning", success: "text-success", accent: "text-accent-light" }[tono];
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between gap-2 text-[13px] font-medium text-ink-dim">
        <span>{etiqueta}</span>
        {icono && <span className="text-ink-faint" aria-hidden>{icono}</span>}
      </div>
      <div className={cn("tabular mt-2 font-display text-[1.75rem] font-semibold leading-tight", color)}>{valor}</div>
      {detalle && <div className="mt-1.5 text-xs text-ink-faint">{detalle}</div>}
    </Card>
  );
}
