import type { ReactNode } from "react";
import { Logo } from "@/components/ui/Logo";

const BARRAS = [62, 84, 48, 92, 70, 38, 78];

export function AuthShell({ titulo, descripcion, children, pie }: { titulo: string; descripcion?: string; children: ReactNode; pie?: ReactNode }) {
  return (
    <div className="min-h-dvh bg-bg lg:grid lg:grid-cols-[1.05fr_1fr]">
      <aside className="relative hidden overflow-hidden border-r border-line bg-surface lg:flex lg:flex-col lg:justify-between lg:p-12" aria-hidden>
        <Logo />
        <div className="relative z-10 max-w-md">
          <p className="font-display text-[2.6rem] font-semibold leading-[1.08] tracking-tight text-ink">
            Cada sede, <span className="text-accent-light">un solo inventario</span>.
          </p>
          <p className="mt-5 text-[15px] leading-relaxed text-ink-dim">
            Existencias, ventas y traslados de todas sus sedes en un solo lugar, con alertas reales y predicción de demanda que explica de dónde sale cada número.
          </p>
        </div>
        <div className="relative z-10 flex h-28 items-end gap-2.5">
          {BARRAS.map((h, i) => (
            <div key={i} className="flex-1 rounded-t-lg bg-accent/20" style={{ height: `${h}%` }}>
              <div className="h-1.5 rounded-t-lg bg-accent-light/70" />
            </div>
          ))}
        </div>
        <div className="pointer-events-none absolute -right-24 -top-24 size-96 rounded-full bg-accent/10 blur-3xl" />
      </aside>

      <main className="flex min-h-dvh flex-col justify-center px-5 py-10 sm:px-10">
        <div className="mx-auto w-full max-w-md">
          <Logo className="mb-10 lg:hidden" />
          <h1 className="font-display text-[1.75rem] font-semibold tracking-tight text-ink">{titulo}</h1>
          {descripcion && <p className="mt-2 text-sm text-ink-dim">{descripcion}</p>}
          <div className="mt-8">{children}</div>
          {pie && <div className="mt-8 text-center text-sm text-ink-dim">{pie}</div>}
        </div>
      </main>
    </div>
  );
}
