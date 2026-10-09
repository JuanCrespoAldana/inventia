import { useEffect, useId, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { cn } from "@/lib/cn";
import { useBloquearPausas } from "@/lib/bloqueoPausas";
import { IconButton } from "./Button";

const ENFOCABLES = 'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

interface ModalProps {
  abierto: boolean;
  onCerrar: () => void;
  titulo: string;
  descripcion?: string;
  children: ReactNode;
  pie?: ReactNode;
  ancho?: "sm" | "md" | "lg" | "xl";
  /** Evita cerrar con Escape o clic fuera (p. ej. mientras se guarda). */
  bloqueado?: boolean;
  /** Mientras está abierto no se muestran pausas activas (hay una operación en curso). Solo la pausa misma lo desactiva. */
  bloqueaPausas?: boolean;
  /** Quita el botón «Cerrar» del encabezado (el diálogo se resuelve solo con sus botones de acción). */
  ocultarCierre?: boolean;
}

const ANCHOS = { sm: "max-w-md", md: "max-w-lg", lg: "max-w-2xl", xl: "max-w-4xl" };

export function Modal({ abierto, onCerrar, titulo, descripcion, children, pie, ancho = "md", bloqueado = false, bloqueaPausas = true, ocultarCierre = false }: ModalProps) {
  useBloquearPausas(abierto && bloqueaPausas);
  const idTitulo = useId();
  const idDescripcion = useId();
  const caja = useRef<HTMLDivElement>(null);
  const previo = useRef<Element | null>(null);

  useEffect(() => {
    if (!abierto) return;
    previo.current = document.activeElement;
    const desbordeAnterior = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const temporizador = window.setTimeout(() => {
      const primero = caja.current?.querySelector<HTMLElement>("[data-autofocus], input, select, textarea") ?? caja.current?.querySelector<HTMLElement>(ENFOCABLES);
      primero?.focus();
    }, 30);
    return () => {
      window.clearTimeout(temporizador);
      document.body.style.overflow = desbordeAnterior;
      if (previo.current instanceof HTMLElement) previo.current.focus();
    };
  }, [abierto]);

  function alTeclear(e: React.KeyboardEvent) {
    if (e.key === "Escape" && !bloqueado) {
      e.stopPropagation();
      onCerrar();
      return;
    }
    if (e.key !== "Tab" || !caja.current) return;
    const lista = Array.from(caja.current.querySelectorAll<HTMLElement>(ENFOCABLES));
    if (lista.length === 0) return;
    const primero = lista[0];
    const ultimo = lista[lista.length - 1];
    if (e.shiftKey && document.activeElement === primero) {
      e.preventDefault();
      ultimo.focus();
    } else if (!e.shiftKey && document.activeElement === ultimo) {
      e.preventDefault();
      primero.focus();
    }
  }

  return createPortal(
    <AnimatePresence>
      {abierto && (
        <motion.div
          className="fixed inset-0 z-50 flex items-end justify-center bg-black/65 p-0 backdrop-blur-sm sm:items-center sm:p-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          onMouseDown={(e) => {
            if (e.target === e.currentTarget && !bloqueado) onCerrar();
          }}
          onKeyDown={alTeclear}
        >
          <motion.div
            ref={caja}
            role="dialog"
            aria-modal="true"
            aria-labelledby={idTitulo}
            aria-describedby={descripcion ? idDescripcion : undefined}
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 420, damping: 34 }}
            className={cn(
              "flex max-h-[92dvh] w-full flex-col overflow-hidden border border-line-strong bg-surface shadow-(--shadow-pop)",
              "rounded-t-(--radius-panel) sm:rounded-(--radius-panel)",
              ANCHOS[ancho],
            )}
          >
            <header className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
              <div className="min-w-0">
                <h2 id={idTitulo} className="font-display text-lg font-semibold text-ink">
                  {titulo}
                </h2>
                {descripcion && (
                  <p id={idDescripcion} className="mt-0.5 text-[13px] text-ink-dim">
                    {descripcion}
                  </p>
                )}
              </div>
              {!ocultarCierre && (
                <IconButton etiqueta="Cerrar" onClick={onCerrar} disabled={bloqueado} className="-mr-2 -mt-1">
                  <X className="size-4" aria-hidden />
                </IconButton>
              )}
            </header>
            <div className="overflow-y-auto px-5 py-5">{children}</div>
            {pie && <footer className="flex flex-wrap items-center justify-end gap-2 border-t border-line bg-surface-2/40 px-5 py-3.5">{pie}</footer>}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
