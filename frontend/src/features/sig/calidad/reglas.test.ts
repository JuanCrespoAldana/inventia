import { describe, expect, it } from "vitest";
import { requisitoGarantia, requisitoNc, siguientesGarantia, siguientesNc } from "./reglas";

describe("transiciones de no conformidad", () => {
  it("avanza en orden y no retrocede", () => {
    expect(siguientesNc("reportado")).toEqual(["en_revision", "en_proceso_solucion", "resuelto", "cerrado"]);
    expect(siguientesNc("en_proceso_solucion")).toEqual(["resuelto", "cerrado"]);
  });

  it("una resuelta puede reabrirse al proceso de solución; una cerrada no cambia", () => {
    expect(siguientesNc("resuelto")).toEqual(["en_proceso_solucion", "cerrado"]);
    expect(siguientesNc("cerrado")).toEqual([]);
    expect(siguientesNc("desconocido")).toEqual([]);
  });

  it("exige solución para resolver o cerrar", () => {
    expect(requisitoNc("resuelto", "  ")).not.toBeNull();
    expect(requisitoNc("cerrado", "")).not.toBeNull();
    expect(requisitoNc("resuelto", "Se cambió la pieza")).toBeNull();
    expect(requisitoNc("en_revision", "")).toBeNull();
  });
});

describe("transiciones de garantía", () => {
  it("ofrece solo los estados permitidos", () => {
    expect(siguientesGarantia("reportada")).toContain("enviada_proveedor");
    expect(siguientesGarantia("reportada")).not.toContain("solucionada");
    expect(siguientesGarantia("aprobada")).toEqual(["solucionada", "cerrada"]);
    expect(siguientesGarantia("cerrada")).toEqual([]);
  });

  it("una rechazada puede volver a enviarse al proveedor", () => {
    expect(siguientesGarantia("rechazada")).toContain("enviada_proveedor");
  });

  it("devuelve una copia: modificarla no altera las reglas", () => {
    siguientesGarantia("reportada").push("x");
    expect(siguientesGarantia("reportada")).not.toContain("x");
  });

  it("exige los datos del proveedor, la respuesta y la solución en los estados que corresponden", () => {
    const vacio = { proveedor: "", respuesta: "", solucion: "" };
    expect(requisitoGarantia("enviada_proveedor", vacio)).not.toBeNull();
    expect(requisitoGarantia("enviada_proveedor", { ...vacio, proveedor: "Proveedor S. A." })).toBeNull();
    expect(requisitoGarantia("aprobada", vacio)).not.toBeNull();
    expect(requisitoGarantia("rechazada", { ...vacio, respuesta: "Fuera de plazo" })).toBeNull();
    expect(requisitoGarantia("solucionada", vacio)).not.toBeNull();
    expect(requisitoGarantia("solucionada", { ...vacio, solucion: "Reposición del equipo" })).toBeNull();
    expect(requisitoGarantia("cerrada", vacio)).toBeNull();
  });
});
