/**
 * Cálculos ambientales del lado del navegador. SOLO sirven para orientar al configurar (vista previa y ayuda);
 * la cifra oficial la calcula y guarda el servidor con la misma fórmula, que se documenta en la pestaña «Metodología».
 *
 *   CO₂ evitado por unidad (kg) = distancia_anual_km × horizonte_años × ( emisión_ref (g/km) / 1000 − consumo (kWh/100 km) / 100 × FE_red (kg CO₂e/kWh) )
 */

export interface ParametrosCo2 {
  distanciaAnualKm: number | null;
  horizonteAnios: number;
  consumoKwh100km: number | null;
  emisionReferenciaGco2Km: number | null;
  factorRed: number | null;
}

/** Devuelve `null` si falta algún dato: nunca se completa con valores inventados. */
export function co2PorUnidadKg(p: ParametrosCo2): number | null {
  if (p.distanciaAnualKm === null || p.consumoKwh100km === null || p.emisionReferenciaGco2Km === null || p.factorRed === null) return null;
  const referencia = p.emisionReferenciaGco2Km / 1000;
  const electrico = (p.consumoKwh100km / 100) * p.factorRed;
  return Math.round(p.distanciaAnualKm * p.horizonteAnios * (referencia - electrico) * 1000) / 1000;
}

/** Factor de emisión de la gasolina motor como referencia: 8 887 g CO₂ por galón (EPA) ≈ 2,35 kg CO₂ por litro. */
export const FACTOR_GASOLINA_KG_POR_LITRO = 2.35;

/** Emisión del vehículo de combustión de referencia (g CO₂/km) a partir de su consumo (L/100 km). */
export function emisionDesdeConsumoCombustible(litrosPor100km: number, kgCo2PorLitro = FACTOR_GASOLINA_KG_POR_LITRO): number {
  return Math.round(((litrosPor100km / 100) * kgCo2PorLitro * 1000) * 100) / 100;
}

/** Acepta «0,22» o «0.22». Devuelve `null` si está vacío o no es un número válido. */
export function aNumeroDecimal(texto: string): number | null {
  const limpio = texto.trim().replace(",", ".");
  if (limpio === "" || !/^\d+(\.\d+)?$/.test(limpio)) return null;
  return Number(limpio);
}

/** 850 kg → «850 kg»; 1 480 kg → «1,48 t». */
export function formatoCo2(kg: number, formatear: (n: number, d: number) => string): string {
  return kg >= 1000 ? `${formatear(kg / 1000, 2)} t` : `${formatear(kg, kg < 10 && kg !== 0 ? 1 : 0)} kg`;
}

/** Versión corta para los ejes de los gráficos: 0 · 850 kg · 1,5 t · 400 t. */
export function formatoEjeCo2(kg: number, formatear: (n: number, d: number) => string): string {
  if (kg === 0) return "0";
  if (kg >= 1000) {
    const t = kg / 1000;
    return `${formatear(t, Number.isInteger(t) ? 0 : 1)} t`;
  }
  return `${formatear(kg, 0)} kg`;
}
