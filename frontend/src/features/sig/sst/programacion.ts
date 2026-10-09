/** Lógica pura del programador de pausas activas (sin React ni red), para poder probarla con facilidad. */

/** Tiempo de cortesía tras abrir la aplicación si ya tocaba una pausa: no se interrumpe de inmediato. */
export const GRACIA_MS = 2 * 60_000;
/** Cada cuánto se revisa si ya toca (el temporizador no depende de un único `setTimeout` largo). */
export const REVISION_MS = 15_000;
/** Si el servidor dice «todavía no» sin una hora, o no hay actividades, se vuelve a consultar más tarde. */
export const REINTENTO_MS = 10 * 60_000;
/** Tras la última tecla en un campo de texto se espera este tiempo antes de mostrar la pausa. */
export const ESPERA_ESCRITURA_MS = 8_000;

export interface EntradaProximaPausa {
  /** Hora del servidor (ms) al consultar el estado. */
  ahora: number;
  /** Hora (ms) en que se mostró la última pausa, si hubo alguna. */
  ultimaPausa: number | null;
  intervaloMin: number;
  graciaMs?: number;
}

/**
 * Momento (ms, hora del servidor) en que corresponde la próxima pausa:
 * - tras la última pausa, un intervalo completo;
 * - si nunca hubo una, un intervalo desde que se abrió la aplicación;
 * - si ese momento ya pasó (la persona estuvo ausente), una breve cortesía desde ahora.
 */
export function calcularProximaPausa({ ahora, ultimaPausa, intervaloMin, graciaMs = GRACIA_MS }: EntradaProximaPausa): number {
  const intervalo = intervaloMin * 60_000;
  const base = ultimaPausa ?? ahora;
  const debida = base + intervalo;
  return debida <= ahora ? ahora + Math.min(graciaMs, intervalo) : debida;
}

export interface EntradaPuedeMostrar {
  ahora: number;
  proxima: number;
  hayBloqueos: boolean;
  mutacionesEnCurso: number;
  pestanaVisible: boolean;
  pausaAbierta: boolean;
  /** La persona está escribiendo en un campo en este momento (no se le interrumpe a mitad de una frase). */
  escribiendo?: boolean;
}

/** Una pausa se muestra solo si ya toca y no hay nada crítico en marcha. */
export function puedeMostrarPausa(e: EntradaPuedeMostrar): boolean {
  return e.ahora >= e.proxima && !e.hayBloqueos && e.mutacionesEnCurso === 0 && e.pestanaVisible && !e.pausaAbierta && !e.escribiendo;
}

/** Segundos que se muestran en el temporizador del ejercicio. */
export function formatoTemporizador(segundos: number): string {
  const s = Math.max(0, Math.round(segundos));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}
