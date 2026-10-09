import { cn } from "@/lib/cn";

export function Marca({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={cn("size-8", className)} role="img" aria-label="Inventia">
      <rect width="64" height="64" rx="16" fill="#4C6FFF" />
      <rect x="16" y="14" width="32" height="8" rx="4" fill="#fff" />
      <rect x="16" y="28" width="22" height="8" rx="4" fill="#fff" fillOpacity=".85" />
      <rect x="16" y="42" width="12" height="8" rx="4" fill="#fff" fillOpacity=".65" />
    </svg>
  );
}

export function Logo({ className, mostrarNombre = true }: { className?: string; mostrarNombre?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <Marca />
      {mostrarNombre && <span className="font-display text-lg font-semibold tracking-tight text-ink">Inventia</span>}
    </span>
  );
}
