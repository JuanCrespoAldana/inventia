import { describe, expect, it } from "vitest";
import { esAlcanceSede, tieneAlguno, tienePermiso } from "./permisos";

const sesion = { permisos: ["ventas.ver", "ventas.registrar"], rol: { alcance: "sede" } } as never;

describe("permisos", () => {
  it("tienePermiso exige todos los códigos", () => {
    expect(tienePermiso(sesion, "ventas.ver")).toBe(true);
    expect(tienePermiso(sesion, "ventas.ver", "ventas.anular")).toBe(false);
  });

  it("tieneAlguno basta con uno", () => {
    expect(tieneAlguno(sesion, "ventas.anular", "ventas.registrar")).toBe(true);
    expect(tieneAlguno(sesion, "ventas.anular")).toBe(false);
  });

  it("sin sesión o sin códigos nunca concede acceso", () => {
    expect(tienePermiso(null, "ventas.ver")).toBe(false);
    expect(tienePermiso(undefined, "ventas.ver")).toBe(false);
    expect(tienePermiso(sesion)).toBe(false);
    expect(tieneAlguno(null, "ventas.ver")).toBe(false);
  });

  it("identifica los roles que operan en una sola sede", () => {
    expect(esAlcanceSede(sesion)).toBe(true);
    expect(esAlcanceSede({ rol: { alcance: "empresa" } } as never)).toBe(false);
    expect(esAlcanceSede(null)).toBe(false);
  });
});
