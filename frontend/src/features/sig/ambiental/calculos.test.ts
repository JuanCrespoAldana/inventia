import { describe, expect, it } from "vitest";
import { aNumeroDecimal, co2PorUnidadKg, emisionDesdeConsumoCombustible, FACTOR_GASOLINA_KG_POR_LITRO, formatoCo2, formatoEjeCo2 } from "./calculos";

const BASE = { distanciaAnualKm: 2000, horizonteAnios: 1, consumoKwh100km: 1.5, emisionReferenciaGco2Km: 150, factorRed: 0.22 };
const decimales = (n: number, d: number) => n.toFixed(d).replace(".", ",");

describe("CO₂ evitado por unidad", () => {
  it("aplica la fórmula documentada", () => {
    // 2 000 km × (0,150 − 0,015 × 0,22) = 2 000 × 0,1467 = 293,4 kg
    expect(co2PorUnidadKg(BASE)).toBeCloseTo(293.4, 3);
  });

  it("multiplica por el horizonte de años", () => {
    expect(co2PorUnidadKg({ ...BASE, horizonteAnios: 3 })).toBeCloseTo(880.2, 3);
  });

  it("nunca inventa valores: sin algún dato devuelve null", () => {
    expect(co2PorUnidadKg({ ...BASE, factorRed: null })).toBeNull();
    expect(co2PorUnidadKg({ ...BASE, distanciaAnualKm: null })).toBeNull();
    expect(co2PorUnidadKg({ ...BASE, consumoKwh100km: null })).toBeNull();
    expect(co2PorUnidadKg({ ...BASE, emisionReferenciaGco2Km: null })).toBeNull();
  });

  it("si el eléctrico emitiera más que la referencia, el resultado es negativo (no se oculta)", () => {
    expect(co2PorUnidadKg({ ...BASE, emisionReferenciaGco2Km: 0 })).toBeLessThan(0);
  });
});

describe("emisión desde el consumo de combustible", () => {
  it("convierte litros por 100 km en g CO₂/km con el factor de la gasolina", () => {
    expect(emisionDesdeConsumoCombustible(6)).toBeCloseTo((6 / 100) * FACTOR_GASOLINA_KG_POR_LITRO * 1000, 1);
    expect(emisionDesdeConsumoCombustible(0)).toBe(0);
  });
});

describe("lectura de decimales", () => {
  it("acepta coma o punto", () => {
    expect(aNumeroDecimal("0,22")).toBe(0.22);
    expect(aNumeroDecimal(" 0.22 ")).toBe(0.22);
    expect(aNumeroDecimal("12")).toBe(12);
  });

  it("rechaza vacío, texto y negativos", () => {
    expect(aNumeroDecimal("")).toBeNull();
    expect(aNumeroDecimal("abc")).toBeNull();
    expect(aNumeroDecimal("-1")).toBeNull();
    expect(aNumeroDecimal("1,2,3")).toBeNull();
  });
});

describe("formatoCo2", () => {
  it("usa kilogramos hasta 1 000 y toneladas a partir de ahí", () => {
    expect(formatoCo2(850, decimales)).toBe("850 kg");
    expect(formatoCo2(0, decimales)).toBe("0 kg");
    expect(formatoCo2(1480, decimales)).toBe("1,48 t");
    expect(formatoCo2(5.25, decimales)).toBe("5,3 kg");
  });
});

describe("formatoEjeCo2", () => {
  it("abrevia las marcas del eje sin decimales sobrantes", () => {
    expect(formatoEjeCo2(0, decimales)).toBe("0");
    expect(formatoEjeCo2(500, decimales)).toBe("500 kg");
    expect(formatoEjeCo2(1000, decimales)).toBe("1 t");
    expect(formatoEjeCo2(1500, decimales)).toBe("1,5 t");
    expect(formatoEjeCo2(100000, decimales)).toBe("100 t");
  });
});
