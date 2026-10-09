import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import type { Tono } from "@/lib/etiquetas";

const TONOS: Record<Tono, string> = {
  neutral: "bg-white/6 text-ink-dim ring-line-strong",
  accent: "bg-accent-dim text-accent-light ring-accent/30",
  success: "bg-success-dim text-success ring-success/30",
  warning: "bg-warning-dim text-warning ring-warning/30",
  danger: "bg-danger-dim text-danger ring-danger/30",
};

export function Badge({ tono = "neutral", children, className }: { tono?: Tono; children: ReactNode; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset", TONOS[tono], className)}>
      {children}
    </span>
  );
}
