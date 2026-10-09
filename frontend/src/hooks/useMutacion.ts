import { useMutation, useQueryClient, type QueryKey } from "@tanstack/react-query";
import { useToast } from "@/components/ui/Toast";
import { mensajeDeError } from "@/lib/errors";

interface Opciones<R> {
  /** Mensaje de éxito (o función que lo calcula con el resultado). */
  exito?: string | ((resultado: R) => string);
  /** Prefijos de consultas que deben recargarse tras el éxito. */
  invalidar?: QueryKey[];
  /** Si es false, el error no se muestra como aviso (el formulario lo maneja). */
  avisarError?: boolean;
  onExito?: (resultado: R) => void;
}

/** Mutación estándar: aviso de éxito/error en español e invalidación de las consultas afectadas. */
export function useMutacion<A, R>(fn: (args: A) => Promise<R>, { exito, invalidar = [], avisarError = true, onExito }: Opciones<R> = {}) {
  const cliente = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: fn,
    onSuccess: async (resultado) => {
      await Promise.all(invalidar.map((k) => cliente.invalidateQueries({ queryKey: k })));
      if (exito) toast.exito(typeof exito === "function" ? exito(resultado) : exito);
      onExito?.(resultado);
    },
    onError: (e) => {
      if (avisarError) toast.error(mensajeDeError(e));
    },
  });
}
