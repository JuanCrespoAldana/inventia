import { cn } from "@/lib/cn";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={cn("animate-shimmer rounded-md bg-[linear-gradient(90deg,var(--color-surface-2)_25%,var(--color-surface-3)_50%,var(--color-surface-2)_75%)] bg-[length:200%_100%]", className)}
    />
  );
}

export function PanelCargando({ etiqueta = "Cargando…", className }: { etiqueta?: string; className?: string }) {
  return (
    <div role="status" aria-live="polite" className={cn("flex flex-col gap-3 p-5", className)}>
      <span className="sr-only">{etiqueta}</span>
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  );
}
