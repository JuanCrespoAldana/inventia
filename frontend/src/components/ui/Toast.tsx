import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, Info, X } from "lucide-react";
import { cn } from "@/lib/cn";

type TipoToast = "exito" | "error" | "info";
interface ItemToast {
  id: number;
  tipo: TipoToast;
  mensaje: string;
}
interface ApiToast {
  exito: (mensaje: string) => void;
  error: (mensaje: string) => void;
  info: (mensaje: string) => void;
}

const Contexto = createContext<ApiToast | null>(null);

const ICONOS = { exito: CheckCircle2, error: AlertTriangle, info: Info };
const COLORES = { exito: "text-success", error: "text-danger", info: "text-accent-light" };

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ItemToast[]>([]);
  const contador = useRef(0);

  const quitar = useCallback((id: number) => setItems((prev) => prev.filter((t) => t.id !== id)), []);
  const agregar = useCallback(
    (tipo: TipoToast, mensaje: string) => {
      const id = ++contador.current;
      setItems((prev) => [...prev.slice(-3), { id, tipo, mensaje }]);
      window.setTimeout(() => quitar(id), tipo === "error" ? 8000 : 4500);
    },
    [quitar],
  );

  const api = useMemo<ApiToast>(
    () => ({ exito: (m) => agregar("exito", m), error: (m) => agregar("error", m), info: (m) => agregar("info", m) }),
    [agregar],
  );

  return (
    <Contexto.Provider value={api}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-0 z-[60] flex flex-col items-center gap-2 p-4 sm:items-end" aria-live="polite" aria-atomic="false">
        <AnimatePresence initial={false}>
          {items.map((t) => {
            const Icono = ICONOS[t.tipo];
            return (
              <motion.div
                key={t.id}
                layout
                initial={{ opacity: 0, y: 16, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, scale: 0.97 }}
                transition={{ duration: 0.18 }}
                role={t.tipo === "error" ? "alert" : "status"}
                className="pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-(--radius-control) border border-line-strong bg-surface-2 px-4 py-3 shadow-(--shadow-pop)"
              >
                <Icono className={cn("mt-0.5 size-4 shrink-0", COLORES[t.tipo])} aria-hidden />
                <p className="flex-1 text-sm text-ink">{t.mensaje}</p>
                <button type="button" aria-label="Cerrar aviso" onClick={() => quitar(t.id)} className="text-ink-faint transition hover:text-ink">
                  <X className="size-4" aria-hidden />
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </Contexto.Provider>
  );
}

export function useToast(): ApiToast {
  const ctx = useContext(Contexto);
  if (!ctx) throw new Error("useToast debe usarse dentro de <ToastProvider>");
  return ctx;
}
