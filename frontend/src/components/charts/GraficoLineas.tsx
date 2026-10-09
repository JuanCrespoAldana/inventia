import { useId, useMemo, useState } from "react";
import { limitesNiceos, abreviar } from "./escala";
import { useAncho } from "./useAncho";

export interface PuntoSerie {
  /** Marca de tiempo (ms) del día. */
  t: number;
  y: number;
  /** Límites del intervalo (solo en pronósticos). */
  lo?: number;
  hi?: number;
  /** Día en curso: el dato aún no está completo, así que se dibuja punteado y no se confunde con una caída real. */
  parcial?: boolean;
}

export interface CapaLinea {
  nombre: string;
  puntos: PuntoSerie[];
  color: string;
  punteada?: boolean;
  area?: boolean;
  /** Dibuja la banda lo–hi alrededor de la línea. */
  banda?: boolean;
}

interface Props {
  capas: CapaLinea[];
  alto?: number;
  formatoY?: (v: number) => string;
  formatoX?: (t: number) => string;
  descripcion: string;
  /** Marca vertical (p. ej. fecha de corte de la predicción). */
  marcaVertical?: { t: number; etiqueta: string };
}

const MARGEN = { arriba: 12, derecha: 12, abajo: 26, izquierda: 44 };

export function GraficoLineas({ capas, alto = 240, formatoY = (v) => abreviar(v), formatoX, descripcion, marcaVertical }: Props) {
  const { ref, ancho } = useAncho<HTMLDivElement>();
  const idGradiente = useId().replace(/:/g, "");
  const [activo, setActivo] = useState<number | null>(null);

  const datos = useMemo(() => {
    const todos = capas.flatMap((c) => c.puntos);
    if (todos.length === 0) return null;
    const ts = todos.map((p) => p.t);
    const ys = todos.flatMap((p) => [p.y, p.lo ?? p.y, p.hi ?? p.y]);
    const tMin = Math.min(...ts);
    const tMax = Math.max(...ts);
    const escalaY = limitesNiceos(Math.min(0, ...ys), Math.max(...ys));
    return { tMin, tMax: tMax === tMin ? tMin + 86_400_000 : tMax, escalaY, ts: Array.from(new Set(ts)).sort((a, b) => a - b) };
  }, [capas]);

  if (!datos) return null;
  const anchoUtil = ancho - MARGEN.izquierda - MARGEN.derecha;
  const altoUtil = alto - MARGEN.arriba - MARGEN.abajo;
  const x = (t: number) => MARGEN.izquierda + ((t - datos.tMin) / (datos.tMax - datos.tMin)) * anchoUtil;
  const y = (v: number) => MARGEN.arriba + (1 - (v - datos.escalaY.min) / (datos.escalaY.max - datos.escalaY.min)) * altoUtil;
  const fx = formatoX ?? ((t: number) => new Date(t).toLocaleDateString("es-CO", { day: "2-digit", month: "short" }));

  const marcasX = (() => {
    const cantidad = Math.max(2, Math.floor(anchoUtil / 90));
    const salida: number[] = [];
    for (let i = 0; i < cantidad; i++) salida.push(datos.tMin + ((datos.tMax - datos.tMin) * i) / (cantidad - 1));
    return salida;
  })();

  function camino(p: PuntoSerie[]) {
    return p.map((q, i) => `${i === 0 ? "M" : "L"}${x(q.t).toFixed(1)},${y(q.y).toFixed(1)}`).join(" ");
  }

  /** Separa los puntos completos del tramo final parcial (que arranca en el último punto completo). */
  function tramos(p: PuntoSerie[]) {
    const completos = p.filter((q) => !q.parcial);
    const parciales = p.filter((q) => q.parcial);
    const enlace = completos.length > 0 && parciales.length > 0 ? [completos[completos.length - 1], ...parciales] : [];
    return { completos, enlace };
  }

  function alMover(e: React.PointerEvent<SVGSVGElement>) {
    const caja = e.currentTarget.getBoundingClientRect();
    const px = e.clientX - caja.left;
    const t = datos!.tMin + ((px - MARGEN.izquierda) / anchoUtil) * (datos!.tMax - datos!.tMin);
    let mejor = datos!.ts[0];
    for (const c of datos!.ts) if (Math.abs(c - t) < Math.abs(mejor - t)) mejor = c;
    setActivo(mejor);
  }

  const valoresActivos = activo === null ? [] : capas.map((c) => ({ capa: c, punto: c.puntos.find((p) => p.t === activo) })).filter((v) => v.punto);
  const lado = activo !== null && x(activo) > ancho * 0.6 ? "izq" : "der";

  return (
    <div ref={ref} className="relative w-full">
      <svg
        width={ancho}
        height={alto}
        role="img"
        aria-label={descripcion}
        onPointerMove={alMover}
        onPointerLeave={() => setActivo(null)}
        className="touch-pan-y overflow-visible"
      >
        <defs>
          {capas.map((c, i) => (
            <linearGradient key={i} id={`${idGradiente}-${i}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={c.color} stopOpacity="0.28" />
              <stop offset="100%" stopColor={c.color} stopOpacity="0" />
            </linearGradient>
          ))}
        </defs>
        {datos.escalaY.marcas.map((m) => (
          <g key={m}>
            <line x1={MARGEN.izquierda} x2={ancho - MARGEN.derecha} y1={y(m)} y2={y(m)} stroke="rgb(255 255 255 / 0.06)" />
            <text x={MARGEN.izquierda - 8} y={y(m)} textAnchor="end" dominantBaseline="middle" className="fill-ink-faint text-[10px]">
              {formatoY(m)}
            </text>
          </g>
        ))}
        {marcasX.map((t, i) => (
          <text key={i} x={x(t)} y={alto - 6} textAnchor={i === 0 ? "start" : i === marcasX.length - 1 ? "end" : "middle"} className="fill-ink-faint text-[10px]">
            {fx(t)}
          </text>
        ))}
        {marcaVertical && marcaVertical.t >= datos.tMin && marcaVertical.t <= datos.tMax && (
          <g>
            <line x1={x(marcaVertical.t)} x2={x(marcaVertical.t)} y1={MARGEN.arriba} y2={MARGEN.arriba + altoUtil} stroke="rgb(255 255 255 / 0.25)" strokeDasharray="3 4" />
            <text x={x(marcaVertical.t) + 6} y={MARGEN.arriba + 10} className="fill-ink-faint text-[10px]">
              {marcaVertical.etiqueta}
            </text>
          </g>
        )}
        {capas.map((c, i) => {
          if (c.puntos.length === 0) return null;
          const conBanda = c.banda && c.puntos.every((p) => p.lo !== undefined && p.hi !== undefined);
          const { completos, enlace } = tramos(c.puntos);
          return (
            <g key={c.nombre}>
              {conBanda && (
                <path
                  d={`${c.puntos.map((p, k) => `${k === 0 ? "M" : "L"}${x(p.t).toFixed(1)},${y(p.hi!).toFixed(1)}`).join(" ")} ${[...c.puntos]
                    .reverse()
                    .map((p) => `L${x(p.t).toFixed(1)},${y(p.lo!).toFixed(1)}`)
                    .join(" ")} Z`}
                  fill={c.color}
                  fillOpacity="0.14"
                />
              )}
              {c.area && completos.length > 1 && (
                <path d={`${camino(completos)} L${x(completos[completos.length - 1].t).toFixed(1)},${y(datos.escalaY.min)} L${x(completos[0].t).toFixed(1)},${y(datos.escalaY.min)} Z`} fill={`url(#${idGradiente}-${i})`} />
              )}
              <path d={camino(completos)} fill="none" stroke={c.color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" strokeDasharray={c.punteada ? "5 4" : undefined} />
              {enlace.length > 1 && <path d={camino(enlace)} fill="none" stroke={c.color} strokeOpacity="0.55" strokeWidth="2" strokeDasharray="2 4" strokeLinecap="round" />}
              {c.puntos.length === 1 && <circle cx={x(c.puntos[0].t)} cy={y(c.puntos[0].y)} r="3" fill={c.color} />}
            </g>
          );
        })}
        {activo !== null && (
          <g pointerEvents="none">
            <line x1={x(activo)} x2={x(activo)} y1={MARGEN.arriba} y2={MARGEN.arriba + altoUtil} stroke="rgb(255 255 255 / 0.3)" />
            {valoresActivos.map(({ capa, punto }) => (
              <circle key={capa.nombre} cx={x(activo)} cy={y(punto!.y)} r="4" fill={capa.color} stroke="#131319" strokeWidth="2" />
            ))}
          </g>
        )}
      </svg>
      {activo !== null && valoresActivos.length > 0 && (
        <div
          role="presentation"
          className="pointer-events-none absolute top-2 z-10 min-w-36 rounded-(--radius-control) border border-line-strong bg-surface-2 px-3 py-2 text-xs shadow-(--shadow-pop)"
          style={lado === "der" ? { left: Math.min(x(activo) + 12, ancho - 160) } : { left: Math.max(x(activo) - 172, 0) }}
        >
          <p className="mb-1 font-semibold text-ink">{fx(activo)}</p>
          {valoresActivos.map(({ capa, punto }) => (
            <p key={capa.nombre} className="tabular flex items-center justify-between gap-3 text-ink-dim">
              <span className="flex items-center gap-1.5">
                <span className="inline-block size-2 rounded-full" style={{ background: capa.color }} />
                {capa.nombre}
              </span>
              <span className="text-ink">
                {punto!.parcial && <span className="mr-1 text-ink-faint">día en curso ·</span>}
                {formatoY(punto!.y)}
                {punto!.lo !== undefined && punto!.hi !== undefined && (
                  <span className="ml-1 text-ink-faint">
                    ({formatoY(punto!.lo)}–{formatoY(punto!.hi)})
                  </span>
                )}
              </span>
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
