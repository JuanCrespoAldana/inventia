import { Suspense, useCallback, useEffect, useId, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, KeyRound, LogOut, Menu, X } from "lucide-react";
import { useSesion, useAuth } from "@/auth/AuthContext";
import { cn } from "@/lib/cn";
import { Logo } from "@/components/ui/Logo";
import { IconButton } from "@/components/ui/Button";
import { PanelCargando } from "@/components/ui/Skeleton";
import { PausasActivas } from "@/features/sig/sst/PausasActivas";
import { gruposVisibles, type GrupoNavegacion, type ItemNavegacion } from "./navegacion";

const CLAVE_SIG_ABIERTO = "inventia.menu.sig";

function leerAbierto(): boolean {
  try {
    return localStorage.getItem(CLAVE_SIG_ABIERTO) === "1";
  } catch {
    return false;
  }
}

function guardarAbierto(valor: boolean) {
  try {
    localStorage.setItem(CLAVE_SIG_ABIERTO, valor ? "1" : "0");
  } catch {
    /* sin almacenamiento: el menú simplemente no recuerda su estado */
  }
}

function EnlaceMenu({ item, alNavegar, sangrado = false }: { item: ItemNavegacion; alNavegar?: () => void; sangrado?: boolean }) {
  return (
    <NavLink
      to={item.ruta}
      end={item.fin}
      title={item.etiqueta}
      onClick={alNavegar}
      className={({ isActive }) =>
        cn(
          "group flex items-center gap-3 rounded-(--radius-control) px-3 py-2 text-sm font-medium transition",
          sangrado && "py-1.5",
          isActive ? "bg-accent-dim text-accent-light" : "text-ink-dim hover:bg-white/5 hover:text-ink",
        )
      }
    >
      <item.icono className="size-[18px] shrink-0" aria-hidden />
      <span className={sangrado ? "leading-snug" : "truncate"}>{item.etiqueta}</span>
    </NavLink>
  );
}

/** Menú desplegable (SIG): se abre solo al entrar en una de sus secciones y recuerda si la persona lo dejó abierto. */
function GrupoDesplegable({ grupo, alNavegar }: { grupo: GrupoNavegacion; alNavegar?: () => void }) {
  const { pathname } = useLocation();
  const dentro = grupo.items.some((i) => pathname === i.ruta || pathname.startsWith(`${i.ruta}/`));
  const [abierto, setAbierto] = useState(() => dentro || leerAbierto());
  const [estabaDentro, setEstabaDentro] = useState(dentro);
  const idLista = useId();
  if (dentro !== estabaDentro) {
    // Al entrar en una de sus secciones (enlace directo, atrás/adelante) el menú se abre solo.
    setEstabaDentro(dentro);
    if (dentro) setAbierto(true);
  }
  const Icono = grupo.desplegable!.icono;
  const contenedor = useRef<HTMLDivElement>(null);
  useEffect(() => {
    // En pantallas bajas el menú se desplaza: la sección activa debe quedar a la vista al entrar.
    if (dentro) contenedor.current?.querySelector(`a[href="${pathname}"]`)?.scrollIntoView?.({ block: "nearest" });
  }, [dentro, pathname]);

  return (
    <div ref={contenedor}>
      <button
        type="button"
        aria-expanded={abierto}
        aria-controls={idLista}
        title={grupo.desplegable!.descripcion}
        onClick={() => {
          setAbierto(!abierto);
          guardarAbierto(!abierto);
        }}
        className={cn(
          "flex w-full items-center gap-3 rounded-(--radius-control) px-3 py-2 text-sm font-semibold transition",
          dentro ? "text-accent-light" : "text-ink-dim hover:bg-white/5 hover:text-ink",
        )}
      >
        <Icono className="size-[18px] shrink-0" aria-hidden />
        <span className="flex-1 truncate text-left">{grupo.titulo}</span>
        <ChevronDown className={cn("size-4 shrink-0 transition-transform", abierto && "rotate-180")} aria-hidden />
      </button>
      {abierto && (
        <ul id={idLista} className="ml-[17px] mt-0.5 flex flex-col gap-0.5 border-l border-line pl-2">
          {grupo.items.map((item) => (
            <li key={item.ruta}>
              <EnlaceMenu item={item} alNavegar={alNavegar} sangrado />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Menulateral({ alNavegar }: { alNavegar?: () => void }) {
  const sesion = useSesion();
  const grupos = gruposVisibles(sesion);
  return (
    <nav aria-label="Navegación principal" className="flex flex-1 flex-col gap-5 overflow-y-auto px-3 pb-4">
      {grupos.map((g) =>
        g.desplegable ? (
          <GrupoDesplegable key={g.titulo} grupo={g} alNavegar={alNavegar} />
        ) : (
          <div key={g.titulo ?? "inicio"}>
            {g.titulo && <p className="mb-1.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-ink-faint">{g.titulo}</p>}
            <ul className="flex flex-col gap-0.5">
              {g.items.map((item) => (
                <li key={item.ruta}>
                  <EnlaceMenu item={item} alNavegar={alNavegar} />
                </li>
              ))}
            </ul>
          </div>
        ),
      )}
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
      <PausasActivas />
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
