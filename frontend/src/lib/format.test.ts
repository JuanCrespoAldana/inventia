import { describe, expect, it } from "vitest";
import { decimal, entero, fecha, fechaCorta, fechaHora, hace, moneda, monedaCompacta, parseDia, porcentaje } from "./format";

const sinEspacios = (t: string) => t.replace(/\s/g, " ");

describe("formato de números", () => {
  it("da formato de moneda colombiana sin decimales", () => {
    expect(sinEspacios(moneda(1234567))).toBe("$ 1.234.567");
    expect(sinEspacios(moneda("2500"))).toBe("$ 2.500");
  });

  it("devuelve raya para valores vacíos o no numéricos en lugar de «NaN»", () => {
    for (const v of [null, undefined, "", "abc", Number.NaN]) expect(moneda(v as never)).toBe("—");
    expect(entero(null)).toBe("—");
    expect(decimal(undefined)).toBe("—");
    expect(porcentaje(Number.POSITIVE_INFINITY)).toBe("—");
  });

  it("usa separador de miles y coma decimal", () => {
    expect(entero(12345)).toBe("12.345");
    expect(decimal(5.4321, 2)).toBe("5,43");
    expect(sinEspacios(porcentaje(12.5))).toBe("12,5 %");
  });

  it("abrevia importes grandes", () => {
    expect(monedaCompacta(4_200_000)).toContain("4,2");
    expect(monedaCompacta(null)).toBe("—");
  });
});

describe("formato de fechas", () => {
  it("interpreta un día calendario sin desplazarlo por zona horaria", () => {
    const d = parseDia("2026-10-08");
    expect([d.getFullYear(), d.getMonth(), d.getDate()]).toEqual([2026, 9, 8]);
    expect(fecha("2026-10-08")).toContain("08");
    expect(fechaCorta("2026-01-31")).toContain("31");
  });

  it("muestra raya ante fechas ausentes o inválidas", () => {
    expect(fecha(null)).toBe("—");
    expect(fecha("no-es-fecha")).toBe("—");
    expect(fechaHora("")).toBe("—");
  });

  it("incluye la hora en fechas con hora", () => {
    expect(fechaHora("2026-10-08T15:30:00Z")).toMatch(/\d{2}:\d{2}/);
  });

  it("describe el tiempo transcurrido en español", () => {
    const ahora = new Date("2026-10-08T12:00:00Z").getTime();
    expect(hace("2026-10-08T11:59:50Z", ahora)).toBe("hace un momento");
    expect(hace("2026-10-08T11:30:00Z", ahora)).toBe("hace 30 min");
    expect(hace("2026-10-08T09:00:00Z", ahora)).toBe("hace 3 h");
    expect(hace("2026-10-07T12:00:00Z", ahora)).toBe("hace 1 día");
    expect(hace("2026-10-01T12:00:00Z", ahora)).toBe("hace 7 días");
    expect(hace(null, ahora)).toBe("—");
  });
});
