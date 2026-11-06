import { entero, fecha, fechaHora, moneda, porcentaje } from "@/lib/format";
import type { BloqueTablaAsistente } from "@/types/api";

type Columna = BloqueTablaAsistente["columnas"][number];
export type Celda = BloqueTablaAsistente["filas"][number]["celdas"][string];

const ES_FECHA = /^\d{4}-\d{2}-\d{2}/;
/** Hasta dos decimales y sin ceros sobrantes: 0,5 · 1,26 · 2. */
const fmtDecimal = new Intl.NumberFormat(import.meta.env.VITE_LOCALE ?? "es-CO", { maximumFractionDigits: 2 });

/** Da formato a una celda de la tabla según la columna. Lo que no encaja con el formato («Nunca» en una fecha) se muestra tal cual. */
export function formatearCelda(valor: Celda | undefined, formato: Columna["formato"] = "texto"): string {
  if (valor === null || valor === undefined || valor === "") return "—";
  if (typeof valor === "boolean") return valor ? "Sí" : "No";
  switch (formato) {
    case "entero":
      return typeof valor === "number" ? entero(valor) : String(valor);
    case "decimal":
      return typeof valor === "number" ? fmtDecimal.format(valor) : String(valor);
    case "moneda":
      return typeof valor === "number" ? moneda(valor) : String(valor);
    case "porcentaje":
      return typeof valor === "number" ? porcentaje(valor) : String(valor);
    case "fecha":
      return typeof valor === "string" && ES_FECHA.test(valor) ? fecha(valor) : String(valor);
    case "fecha_hora":
      return typeof valor === "string" && ES_FECHA.test(valor) ? fechaHora(valor) : String(valor);
    default:
      return String(valor);
  }
}

export interface Trozo {
  texto: string;
  negrita: boolean;
}

/** Parte un texto con `**negritas**` en trozos, para dibujarlo sin HTML (el texto del asistente nunca se inserta como HTML). */
export function partirNegritas(texto: string): Trozo[] {
  const trozos: Trozo[] = [];
  const patron = /\*\*(.+?)\*\*/g;
  let desde = 0;
  for (const m of texto.matchAll(patron)) {
    const inicio = m.index ?? 0;
    if (inicio > desde) trozos.push({ texto: texto.slice(desde, inicio), negrita: false });
    trozos.push({ texto: m[1], negrita: true });
    desde = inicio + m[0].length;
  }
  if (desde < texto.length) trozos.push({ texto: texto.slice(desde), negrita: false });
  return trozos;
}
