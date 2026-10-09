/** Reglas de estado de calidad, iguales a las del servidor (que las valida de nuevo): solo para ofrecer opciones válidas. */

export const ORDEN_NC = ["reportado", "en_revision", "en_proceso_solucion", "resuelto", "cerrado"] as const;

/** Estados a los que puede pasar una no conformidad: avanza en orden y solo una «resuelta» puede reabrirse. */
export function siguientesNc(actual: string): string[] {
  const i = ORDEN_NC.indexOf(actual as (typeof ORDEN_NC)[number]);
  if (i < 0 || actual === "cerrado") return [];
  const adelante = ORDEN_NC.slice(i + 1) as readonly string[];
  return actual === "resuelto" ? ["en_proceso_solucion", ...adelante] : [...adelante];
}

export const TRANSICIONES_GARANTIA: Record<string, readonly string[]> = {
  reportada: ["pendiente_revision", "enviada_proveedor", "rechazada", "cerrada"],
  pendiente_revision: ["enviada_proveedor", "aprobada", "rechazada", "cerrada"],
  enviada_proveedor: ["aprobada", "rechazada", "cerrada"],
  aprobada: ["solucionada", "cerrada"],
  rechazada: ["enviada_proveedor", "cerrada"],
  solucionada: ["cerrada"],
  cerrada: [],
};

export function siguientesGarantia(actual: string): string[] {
  return [...(TRANSICIONES_GARANTIA[actual] ?? [])];
}

/** Qué datos exige el servidor para entrar a un estado de garantía (mensaje para mostrar antes de enviar). */
export function requisitoGarantia(nuevo: string, datos: { proveedor: string; respuesta: string; solucion: string }): string | null {
  if (nuevo === "enviada_proveedor" && datos.proveedor.trim().length < 2) return "Indica el proveedor al que se envía la garantía.";
  if ((nuevo === "aprobada" || nuevo === "rechazada") && datos.respuesta.trim().length < 3) return "Registra la respuesta del proveedor antes de aprobar o rechazar.";
  if (nuevo === "solucionada" && datos.solucion.trim().length < 3) return "Registra la solución antes de marcarla como solucionada.";
  return null;
}

export function requisitoNc(nuevo: string, solucion: string): string | null {
  if ((nuevo === "resuelto" || nuevo === "cerrado") && solucion.trim().length < 3) return "Registra la solución antes de marcarla como resuelta o cerrada.";
  return null;
}
