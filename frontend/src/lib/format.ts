const LOCALE = import.meta.env.VITE_LOCALE ?? "es-CO";
const MONEDA = import.meta.env.VITE_MONEDA ?? "COP";

const fmtMoneda = new Intl.NumberFormat(LOCALE, { style: "currency", currency: MONEDA, maximumFractionDigits: MONEDA === "COP" ? 0 : 2 });
const fmtMonedaCompacta = new Intl.NumberFormat(LOCALE, { style: "currency", currency: MONEDA, notation: "compact", maximumFractionDigits: 1 });
const fmtEntero = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 0 });
const fmtFecha = new Intl.DateTimeFormat(LOCALE, { day: "2-digit", month: "short", year: "numeric" });
const fmtFechaCorta = new Intl.DateTimeFormat(LOCALE, { day: "2-digit", month: "short" });
const fmtFechaHora = new Intl.DateTimeFormat(LOCALE, { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

const VACIO = "—";

export function moneda(valor: number | string | null | undefined): string {
  if (valor === null || valor === undefined || valor === "") return VACIO;
  const n = Number(valor);
  return Number.isFinite(n) ? fmtMoneda.format(n) : VACIO;
}

export function monedaCompacta(valor: number | null | undefined): string {
  return valor === null || valor === undefined || !Number.isFinite(valor) ? VACIO : fmtMonedaCompacta.format(valor);
}

export function entero(valor: number | null | undefined): string {
  return valor === null || valor === undefined || !Number.isFinite(valor) ? VACIO : fmtEntero.format(valor);
}

export function decimal(valor: number | null | undefined, decimales = 1): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) return VACIO;
  return new Intl.NumberFormat(LOCALE, { minimumFractionDigits: decimales, maximumFractionDigits: decimales }).format(valor);
}

/** `valor` ya viene en porcentaje (12.5 = 12,5 %). */
export function porcentaje(valor: number | null | undefined, decimales = 1): string {
  return valor === null || valor === undefined || !Number.isFinite(valor) ? VACIO : `${decimal(valor, decimales)} %`;
}

/** Fecha sin hora ("2026-10-08"): se interpreta como día calendario, sin desplazamiento por zona horaria. */
export function parseDia(valor: string): Date {
  const [a, m, d] = valor.slice(0, 10).split("-").map(Number);
  return new Date(a, m - 1, d);
}

export function fecha(valor: string | null | undefined): string {
  if (!valor) return VACIO;
  const d = valor.length === 10 ? parseDia(valor) : new Date(valor);
  return Number.isNaN(d.getTime()) ? VACIO : fmtFecha.format(d);
}

export function fechaCorta(valor: string | null | undefined): string {
  if (!valor) return VACIO;
  const d = valor.length === 10 ? parseDia(valor) : new Date(valor);
  return Number.isNaN(d.getTime()) ? VACIO : fmtFechaCorta.format(d);
}

export function fechaHora(valor: string | null | undefined): string {
  if (!valor) return VACIO;
  const d = new Date(valor);
  return Number.isNaN(d.getTime()) ? VACIO : fmtFechaHora.format(d);
}

export function hace(valor: string | null | undefined, ahora: number = Date.now()): string {
  if (!valor) return VACIO;
  const t = new Date(valor).getTime();
  if (Number.isNaN(t)) return VACIO;
  const seg = Math.max(0, Math.round((ahora - t) / 1000));
  if (seg < 60) return "hace un momento";
  const min = Math.round(seg / 60);
  if (min < 60) return `hace ${min} min`;
  const h = Math.round(min / 60);
  if (h < 24) return `hace ${h} h`;
  const dias = Math.round(h / 24);
  if (dias < 30) return `hace ${dias} ${dias === 1 ? "día" : "días"}`;
  return fecha(valor);
}

/** Fecha de hoy en formato ISO local (yyyy-mm-dd) para valores por defecto de filtros. */
export function hoyISO(desplazamientoDias = 0): string {
  const d = new Date();
  d.setDate(d.getDate() + desplazamientoDias);
  const dos = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())}`;
}

export function pluralizar(n: number, singular: string, plural: string): string {
  return `${entero(n)} ${n === 1 ? singular : plural}`;
}
