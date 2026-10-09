import { describe, expect, it } from "vitest";
import { calcularProximaPausa, formatoTemporizador, GRACIA_MS, puedeMostrarPausa } from "./programacion";

const MIN = 60_000;
const BASE = { ahora: 10_000_000, proxima: 10_000_000, hayBloqueos: false, mutacionesEnCurso: 0, pestanaVisible: true, pausaAbierta: false };

describe("calcularProximaPausa", () => {
  it("sin pausas previas espera un intervalo completo desde que se abrió la aplicación", () => {
    expect(calcularProximaPausa({ ahora: 1_000_000, ultimaPausa: null, intervaloMin: 45 })).toBe(1_000_000 + 45 * MIN);
  });

  it("tras una pausa espera un intervalo completo desde esa pausa", () => {
    const ahora = 5_000_000;
    expect(calcularProximaPausa({ ahora, ultimaPausa: ahora - 10 * MIN, intervaloMin: 45 })).toBe(ahora + 35 * MIN);
  });

  it("si ya tocaba (persona ausente) da una breve cortesía en lugar de interrumpir de inmediato", () => {
    const ahora = 9_000_000;
    expect(calcularProximaPausa({ ahora, ultimaPausa: ahora - 3 * 60 * MIN, intervaloMin: 45 })).toBe(ahora + GRACIA_MS);
  });

  it("la cortesía nunca supera el intervalo configurado", () => {
    const ahora = 9_000_000;
    expect(calcularProximaPausa({ ahora, ultimaPausa: ahora - 60 * MIN, intervaloMin: 1 })).toBe(ahora + MIN);
  });
});

describe("puedeMostrarPausa", () => {
  it("se muestra cuando ya toca y no hay nada que lo impida", () => {
    expect(puedeMostrarPausa(BASE)).toBe(true);
  });

  it("no se muestra antes de tiempo", () => {
    expect(puedeMostrarPausa({ ...BASE, proxima: BASE.ahora + 1 })).toBe(false);
  });

  it("no interrumpe un formulario abierto o una venta a medio armar", () => {
    expect(puedeMostrarPausa({ ...BASE, hayBloqueos: true })).toBe(false);
  });

  it("no interrumpe un guardado o una transacción en curso", () => {
    expect(puedeMostrarPausa({ ...BASE, mutacionesEnCurso: 1 })).toBe(false);
  });

  it("no se muestra con la pestaña oculta ni si ya hay una pausa abierta (nunca simultáneas)", () => {
    expect(puedeMostrarPausa({ ...BASE, pestanaVisible: false })).toBe(false);
    expect(puedeMostrarPausa({ ...BASE, pausaAbierta: true })).toBe(false);
  });

  it("no interrumpe a quien está escribiendo", () => {
    expect(puedeMostrarPausa({ ...BASE, escribiendo: true })).toBe(false);
  });
});

describe("formatoTemporizador", () => {
  it("muestra minutos y segundos", () => {
    expect(formatoTemporizador(0)).toBe("0:00");
    expect(formatoTemporizador(75)).toBe("1:15");
    expect(formatoTemporizador(-3)).toBe("0:00");
  });
});
