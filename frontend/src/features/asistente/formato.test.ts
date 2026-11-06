import { describe, expect, it } from "vitest";
import { formatearCelda, partirNegritas } from "./formato";

describe("asistente: formato de celdas", () => {
  it("da formato según la columna", () => {
    expect(formatearCelda(1234567, "entero")).toMatch(/1\.234\.567|1,234,567/);
    expect(formatearCelda(1500000, "moneda")).toContain("1.500.000");
    expect(formatearCelda(0.5, "decimal")).toBe("0,5");
    expect(formatearCelda(2, "decimal")).toBe("2");
    expect(formatearCelda(39.9, "porcentaje")).toBe("39,9 %");
    expect(formatearCelda("2026-10-26", "fecha")).toMatch(/2026/);
  });

  it("muestra tal cual lo que no encaja con el formato y rellena los vacíos", () => {
    expect(formatearCelda("Nunca", "fecha")).toBe("Nunca");
    expect(formatearCelda("Sin dato", "moneda")).toBe("Sin dato");
    expect(formatearCelda(null, "entero")).toBe("—");
    expect(formatearCelda(undefined)).toBe("—");
    expect(formatearCelda("", "texto")).toBe("—");
    expect(formatearCelda(true)).toBe("Sí");
    expect(formatearCelda(false)).toBe("No");
  });
});

describe("asistente: negritas", () => {
  it("separa los trozos en negrita sin interpretar HTML", () => {
    expect(partirNegritas("Hay **12 unidades** en <b>toda</b> la empresa")).toEqual([
      { texto: "Hay ", negrita: false },
      { texto: "12 unidades", negrita: true },
      { texto: " en <b>toda</b> la empresa", negrita: false },
    ]);
  });

  it("deja igual el texto sin marcas o con marcas incompletas", () => {
    expect(partirNegritas("sin marcas")).toEqual([{ texto: "sin marcas", negrita: false }]);
    expect(partirNegritas("abierta **sin cerrar")).toEqual([{ texto: "abierta **sin cerrar", negrita: false }]);
    expect(partirNegritas("")).toEqual([]);
  });
});
