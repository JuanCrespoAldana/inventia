import { useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Send } from "lucide-react";
import { apiUsuarios } from "@/api/administracion";
import { useAuth } from "@/auth/AuthContext";
import { Aviso } from "@/components/ui/Aviso";
import { Button } from "@/components/ui/Button";
import { Select, Textarea } from "@/components/ui/Field";
import { mensajeDeError } from "@/lib/errors";

/** Personas a las que se puede asignar un caso. Sin permiso para ver usuarios, solo queda «asignarme a mí». */
export function useResponsables() {
  const { sesion, tiene } = useAuth();
  const lista = useQuery({
    queryKey: ["usuarios", "responsables-calidad"],
    queryFn: async () => (await apiUsuarios.listar({ activo: true, tamano: 100 })).items.map((u) => ({ id: u.id, nombre: u.nombre })),
    enabled: tiene("usuarios.ver"),
    staleTime: 5 * 60_000,
  });
  const yo = sesion ? { id: sesion.id, nombre: sesion.nombre } : null;
  const opciones = lista.data ?? (yo ? [yo] : []);
  return yo && !opciones.some((o) => o.id === yo.id) ? [yo, ...opciones] : opciones;
}

export function SelectorResponsable({ valor, onChange, actual }: { valor: string; onChange: (v: string) => void; actual?: string | null }) {
  const opciones = useResponsables();
  return (
    <Select etiqueta="Responsable" value={valor} onChange={(e) => onChange(e.target.value)} ayuda={actual ? `Actual: ${actual}` : "Sin responsable asignado"}>
      <option value="">{actual ? "Mantener el actual" : "Sin asignar"}</option>
      {opciones.map((o) => (
        <option key={o.id} value={o.id}>
          {o.nombre}
        </option>
      ))}
    </Select>
  );
}

/** Dato con etiqueta dentro de las fichas de detalle. */
export function Dato({ etiqueta, children }: { etiqueta: string; children: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs font-medium uppercase tracking-wide text-ink-faint">{etiqueta}</dt>
      <dd className="mt-0.5 text-sm text-ink">{children ?? "—"}</dd>
    </div>
  );
}

/** Caja para agregar una observación al historial (nunca se sobrescribe lo anterior). */
export function FormularioObservacion({ onEnviar, etiqueta = "Agregar una observación" }: { onEnviar: (texto: string) => Promise<unknown>; etiqueta?: string }) {
  const [texto, setTexto] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const valido = texto.trim().length >= 3;

  async function enviar() {
    setEnviando(true);
    setError(null);
    try {
      await onEnviar(texto.trim());
      setTexto("");
    } catch (e) {
      setError(mensajeDeError(e));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      {error && <Aviso tipo="error">{error}</Aviso>}
      <Textarea etiqueta={etiqueta} rows={2} maxLength={1000} value={texto} onChange={(e) => setTexto(e.target.value)} ayuda="Se guarda en el historial con tu nombre y la fecha; no reemplaza las observaciones anteriores." />
      <div className="flex justify-end">
        <Button tamano="sm" icono={<Send className="size-4" aria-hidden />} disabled={!valido} cargando={enviando} onClick={() => void enviar()}>
          Agregar al historial
        </Button>
      </div>
    </div>
  );
}

export const AVISO_SIN_INVENTARIO = "Registrar este caso no modifica el inventario. Si la solución exige ajustar existencias, se hace aparte con las operaciones normales de inventario.";
