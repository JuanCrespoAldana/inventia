import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";
import { cn } from "@/lib/cn";

const ESTILOS = {
  info: { caja: "border-accent/30 bg-accent-dim text-accent-light", Icono: Info },
  exito: { caja: "border-success/30 bg-success-dim text-success", Icono: CheckCircle2 },
  aviso: { caja: "border-warning/30 bg-warning-dim text-warning", Icono: AlertTriangle },
  error: { caja: "border-danger/30 bg-danger-dim text-danger", Icono: XCircle },
};

export function Aviso({ tipo = "info", titulo, children, className }: { tipo?: keyof typeof ESTILOS; titulo?: string; children?: ReactNode; className?: string }) {
  const { caja, Icono } = ESTILOS[tipo];
  return (
    <div role={tipo === "error" ? "alert" : "status"} className={cn("flex gap-3 rounded-(--radius-control) border px-4 py-3 text-sm", caja, className)}>
      <Icono className="mt-0.5 size-4 shrink-0" aria-hidden />
      <div className="min-w-0">
        {titulo && <p className="font-semibold">{titulo}</p>}
        {children && <div className={cn("text-ink", titulo && "mt-0.5 text-ink-dim")}>{children}</div>}
      </div>
    </div>
  );
}
