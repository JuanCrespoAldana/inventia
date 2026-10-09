import { useEffect, useSyncExternalStore } from "react";

/**
 * Registro de «momentos críticos» en los que NO se debe mostrar una pausa activa: un formulario abierto,
 * una venta o un traslado a medio armar, un guardado en curso. Quien lo necesita llama a `useBloquearPausas`;
 * el programador de pausas consulta `hayBloqueos()` antes de mostrar nada y espera a que se libere.
 */
let activos = 0;
const oyentes = new Set<() => void>();

function avisar() {
  for (const o of oyentes) o();
}

export function bloquearPausas(): () => void {
  activos += 1;
  avisar();
  let liberado = false;
  return () => {
    if (liberado) return;
    liberado = true;
    activos = Math.max(0, activos - 1);
    avisar();
  };
}

export function hayBloqueos(): boolean {
  return activos > 0;
}

/** Mientras `activo` sea verdadero (y el componente esté montado), las pausas esperan. */
export function useBloquearPausas(activo: boolean): void {
  useEffect(() => {
    if (!activo) return;
    return bloquearPausas();
  }, [activo]);
}

/** Se vuelve a renderizar cuando cambia el número de bloqueos. */
export function useHayBloqueos(): boolean {
  return useSyncExternalStore(
    (cb) => {
      oyentes.add(cb);
      return () => oyentes.delete(cb);
    },
    hayBloqueos,
    () => false,
  );
}

/** Solo para pruebas. */
export function reiniciarBloqueos(): void {
  activos = 0;
  avisar();
}
