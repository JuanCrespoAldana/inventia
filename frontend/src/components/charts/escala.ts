/** Utilidades de escala para los gráficos SVG. */

export function limitesNiceos(min: number, max: number, marcas = 4): { min: number; max: number; marcas: number[] } {
  if (!Number.isFinite(min) || !Number.isFinite(max)) return { min: 0, max: 1, marcas: [0, 1] };
  if (max === min) max = min + 1;
  const bruto = (max - min) / marcas;
  const magnitud = 10 ** Math.floor(Math.log10(bruto));
  const residuo = bruto / magnitud;
  const paso = (residuo >= 5 ? 10 : residuo >= 2 ? 5 : residuo >= 1 ? 2 : 1) * magnitud;
  const minNice = Math.floor(min / paso) * paso;
  const maxNice = Math.ceil(max / paso) * paso;
  const lista: number[] = [];
  for (let v = minNice; v <= maxNice + paso / 2; v += paso) lista.push(Number(v.toFixed(10)));
  return { min: minNice, max: maxNice, marcas: lista };
}

export function abreviar(n: number): string {
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return `${(n / 1_000_000).toLocaleString("es-CO", { maximumFractionDigits: 1 })} M`;
  if (abs >= 1_000) return `${(n / 1_000).toLocaleString("es-CO", { maximumFractionDigits: 1 })} mil`;
  return n.toLocaleString("es-CO", { maximumFractionDigits: 1 });
}
