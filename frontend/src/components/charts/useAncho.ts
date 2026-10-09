import { useEffect, useRef, useState } from "react";

/** Mide el ancho disponible de un contenedor para dibujar el SVG a tamaño real (texto nítido). */
export function useAncho<T extends HTMLElement>(inicial = 640) {
  const ref = useRef<T>(null);
  const [ancho, setAncho] = useState(inicial);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const medir = () => setAncho(Math.max(240, Math.round(el.getBoundingClientRect().width)) || inicial);
    medir();
    if (typeof ResizeObserver === "undefined") return;
    const obs = new ResizeObserver(medir);
    obs.observe(el);
    return () => obs.disconnect();
  }, [inicial]);
  return { ref, ancho };
}
