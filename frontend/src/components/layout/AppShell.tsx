import { Suspense, useCallback, useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { KeyRound, LogOut, Menu, X } from "lucide-react";
import { useSesion, useAuth } from "@/auth/AuthContext";
import { cn } from "@/lib/cn";
import { Logo } from "@/components/ui/Logo";
import { IconButton } from "@/components/ui/Button";
import { PanelCargando } from "@/components/ui/Skeleton";
import { gruposVisibles } from "./navegacion";

function Menulateral({ alNavegar }: { alNavegar?: () => void }) {
  const sesion = useSesion();
  const grupos = gruposVisibles(sesion);
  return (
    <nav aria-label="Navegación principal" className="flex flex-1 flex-col gap-5 overflow-y-auto px-3 pb-4">
      {grupos.map((g) => (
        <div key={g.titulo ?? "inicio"}>
          {g.titulo && <p className="mb-1.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-ink-faint">{g.titulo}</p>}
          <ul className="flex flex-col gap-0.5">
            {g.items.map((item) => (
              <li key={item.ruta}>
                <NavLink
                  to={item.ruta}
                  end={item.fin}
                  onClick={alNavegar}
                  className={({ isActive }) =>
                    cn(
                      "group flex items-center gap-3 rounded-(--radius-control) px-3 py-2 text-sm font-medium transition",
                      isActive ? "bg-accent-dim text-accent-light" : "text-ink-dim hover:bg-white/5 hover:text-ink",
                    )
                  }
                >
                  <item.icono className="size-[18px] shrink-0" aria-hidden />
                  <span className="truncate">{item.etiqueta}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}

function MenuUsuario() {
  const sesion = useSesion();
  const { cerrarSesion } = useAuth();
  const navegar = useNavigate();
  const [saliendo, setSaliendo] = useState(false);
  const iniciales = sesion.nombre
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");

  return (
    <div className="border-t border-line p-3">
      <div className="flex items-center gap-3 rounded-(--radius-control) px-2 py-2">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-accent-dim font-display text-sm font-semibold text-accent-light" aria-hidden>
          {iniciales}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-ink">{sesion.nombre}</p>
          <p className="truncate text-xs text-ink-faint">
            {sesion.rol.nombre}
            {sesion.sede ? ` · ${sesion.sede.nombre}` : ""}
          </p>
        </div>
      </div>
      <div className="mt-1 flex gap-1">
        <button
          type="button"
          onClick={() => navegar("/perfil")}
          className="flex flex-1 items-center justify-center gap-2 rounded-(--radius-control) px-3 py-2 text-[13px] font-medium text-ink-dim transition hover:bg-white/5 hover:text-ink"
        >
          <KeyRound className="size-4" aria-hidden />
          Mi cuenta
        </button>
        <button
          type="button"
          disabled={saliendo}
          onClick={async () => {
            setSaliendo(true);
            await cerrarSesion();
            navegar("/login", { replace: true });
          }}
          className="flex flex-1 items-center justify-center gap-2 rounded-(--radius-control) px-3 py-2 text-[13px] font-medium text-ink-dim transition hover:bg-danger-dim hover:text-danger disabled:opacity-50"
        >
          <LogOut className="size-4" aria-hidden />
          Salir
        </button>
      </div>
    </div>
  );
}

export function AppShell() {
  const sesion = useSesion();
  const ubicacion = useLocation();
  /* El menú móvil se asocia a la ruta en la que se abrió: al navegar deja de coincidir y se cierra solo. */
  const [abiertoEn, setAbiertoEn] = useState<string | null>(null);
  const abierto = abiertoEn === ubicacion.pathname;
  const setAbierto = useCallback((valor: boolean) => setAbiertoEn(valor ? ubicacion.pathname : null), [ubicacion.pathname]);
  useEffect(() => {
    if (!abierto) return;
    const alTeclear = (e: KeyboardEvent) => e.key === "Escape" && setAbierto(false);
    window.addEventListener("keydown", alTeclear);
    return () => window.removeEventListener("keydown", alTeclear);
  }, [abierto, setAbierto]);

  return (
    <div className="min-h-dvh bg-bg lg:grid lg:grid-cols-[264px_1fr]">
      <a href="#contenido" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[70] focus:rounded-lg focus:bg-accent focus:px-4 focus:py-2 focus:text-white">
        Saltar al contenido
      </a>

      <aside className="sticky top-0 hidden h-dvh flex-col border-r border-line bg-surface lg:flex">
        <div className="flex h-16 items-center px-6">
          <Logo />
        </div>
        <p className="truncate px-6 pb-4 text-xs text-ink-faint">{sesion.empresa_nombre}</p>
        <Menulateral />
        <MenuUsuario />
      </aside>

      <div className="flex min-w-0 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-line bg-bg/85 px-4 backdrop-blur lg:hidden">
          <IconButton etiqueta="Abrir menú" onClick={() => setAbierto(true)} aria-expanded={abierto}>
            <Menu className="size-5" aria-hidden />
          </IconButton>
          <Logo />
        </header>

        <AnimatePresence>
          {abierto && (
            <motion.div className="fixed inset-0 z-40 lg:hidden" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }}>
              <div className="absolute inset-0 bg-black/65 backdrop-blur-sm" onClick={() => setAbierto(false)} aria-hidden />
              <motion.aside
                initial={{ x: -280 }}
                animate={{ x: 0 }}
                exit={{ x: -280 }}
                transition={{ type: "spring", stiffness: 420, damping: 38 }}
                className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col border-r border-line bg-surface"
                aria-label="Menú"
              >
                <div className="flex h-14 items-center justify-between px-4">
                  <Logo />
                  <IconButton etiqueta="Cerrar menú" onClick={() => setAbierto(false)}>
                    <X className="size-5" aria-hidden />
                  </IconButton>
                </div>
                <p className="truncate px-4 pb-3 text-xs text-ink-faint">{sesion.empresa_nombre}</p>
                <Menulateral alNavegar={() => setAbierto(false)} />
                <MenuUsuario />
              </motion.aside>
            </motion.div>
          )}
        </AnimatePresence>

        <main id="contenido" tabIndex={-1} className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 sm:px-6 lg:px-10 lg:py-9">
          <Suspense fallback={<PanelCargando etiqueta="Cargando la sección…" />}>
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  );
}
