import { describe, expect, it, vi } from "vitest";
import { aDinero, aplicarErroresServidor, generarPassword, REQUISITOS_PASSWORD, v } from "./formularios";
import { ErrorApi } from "./errors";

describe("política de contraseñas", () => {
  it.each([
    ["Corta1!", "al menos 8"],
    ["sinmayuscula1!", "mayúscula"],
    ["SINMINUSCULA1!", "minúscula"],
    ["SinNumeros!!", "número"],
    ["SinEspecial12", "especial"],
  ])("rechaza %s", (clave, parte) => {
    const r = v.password.safeParse(clave);
    expect(r.success).toBe(false);
    expect(r.error?.issues.map((i) => i.message).join(" ")).toContain(parte);
  });

  it("acepta una contraseña que cumple todo", () => {
    expect(v.password.safeParse("Clave#Segura1").success).toBe(true);
  });

  it("los requisitos visibles coinciden con la validación", () => {
    for (const clave of ["abc", "Clave#Segura1", "TODOMAYUS1!"]) {
      const cumpleTodo = REQUISITOS_PASSWORD.every((r) => r.cumple(clave));
      expect(cumpleTodo).toBe(v.password.safeParse(clave).success);
    }
  });

  it("la contraseña generada siempre cumple la política y es distinta cada vez", () => {
    const vistas = new Set<string>();
    for (let i = 0; i < 300; i++) {
      const p = generarPassword();
      expect(p).toHaveLength(14);
      expect(v.password.safeParse(p).success).toBe(true);
      expect(p).not.toMatch(/[0O1lI]/);
      vistas.add(p);
    }
    expect(vistas.size).toBe(300);
  });
});

describe("validadores de campos", () => {
  it("valida correos, teléfonos e identificaciones", () => {
    expect(v.correo.safeParse("sin-arroba").success).toBe(false);
    expect(v.correo.safeParse("  nombre@empresa.com ").success).toBe(true);
    expect(v.telefono.safeParse("").success).toBe(true);
    expect(v.telefono.safeParse("+57 (601) 555-0100").success).toBe(true);
    expect(v.telefono.safeParse("abc").success).toBe(false);
    expect(v.identificacion.safeParse("900.123.456-7").success).toBe(true);
    expect(v.identificacion.safeParse("12").success).toBe(false);
  });

  it("valida enteros y dinero", () => {
    const cantidad = v.entero("La cantidad", 1, 100);
    expect(cantidad.safeParse("5").success).toBe(true);
    expect(cantidad.safeParse("0").success).toBe(false);
    expect(cantidad.safeParse("1.5").success).toBe(false);
    expect(cantidad.safeParse("101").success).toBe(false);
    expect(v.dinero("El precio").safeParse("1200,50").success).toBe(true);
    expect(v.dinero("El precio").safeParse("12,505").success).toBe(false);
    expect(aDinero("1200,5")).toBe(1200.5);
    expect(aDinero("  ")).toBeNull();
  });
});

describe("aplicarErroresServidor", () => {
  it("asigna los errores a su campo y no devuelve mensaje general", () => {
    const setError = vi.fn();
    const general = aplicarErroresServidor(new ErrorApi("Datos no válidos", { campos: { email: "Correo no válido" } }), setError, ["email", "nombre"]);
    expect(setError).toHaveBeenCalledWith("email", { type: "server", message: "Correo no válido" });
    expect(general).toBeNull();
  });

  it("devuelve el mensaje general cuando el error no pertenece a un campo del formulario", () => {
    const setError = vi.fn();
    expect(aplicarErroresServidor(new ErrorApi("Ya existe una sede con ese nombre"), setError, ["nombre"])).toBe("Ya existe una sede con ese nombre");
    expect(aplicarErroresServidor(new ErrorApi("x", { campos: { otro: "y" } }), setError, ["nombre"])).toBe("x");
    expect(setError).not.toHaveBeenCalled();
  });
});
