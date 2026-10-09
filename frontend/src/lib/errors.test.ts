import { AxiosError, type AxiosResponse } from "axios";
import { describe, expect, it } from "vitest";
import { ErrorApi, mensajeDeError, normalizarError } from "./errors";

function errorHttp(status: number, data: unknown) {
  const e = new AxiosError("fallo", "ERR_BAD_REQUEST", undefined, undefined, { status, data } as AxiosResponse);
  return e;
}

describe("normalizarError", () => {
  it("conserva el mensaje y el código que envía el backend", () => {
    const e = normalizarError(errorHttp(409, { detail: "Ya existe un rol llamado «Ventas»", codigo: "rol_duplicado", request_id: "abc" }));
    expect(e.message).toBe("Ya existe un rol llamado «Ventas»");
    expect(e.codigo).toBe("rol_duplicado");
    expect(e.status).toBe(409);
    expect(e.requestId).toBe("abc");
  });

  it("traduce los errores de validación a un mapa por campo", () => {
    const e = normalizarError(errorHttp(422, { detail: "Datos no válidos", codigo: "validacion", errores: [
      { campo: "admin_email", mensaje: "Correo no válido" },
      { campo: "items.0.cantidad", mensaje: "Debe ser mayor que 0" },
      { campo: "admin_email", mensaje: "segundo mensaje ignorado" },
    ] }));
    expect(e.campos).toEqual({ admin_email: "Correo no válido", "items.0.cantidad": "Debe ser mayor que 0" });
  });

  it("explica la falta de conexión en español", () => {
    const e = normalizarError(new AxiosError("Network Error", "ERR_NETWORK"));
    expect(e.codigo).toBe("sin_conexion");
    expect(e.message).toMatch(/conectar con el servidor/);
  });

  it("usa mensajes propios cuando el servidor no manda detalle", () => {
    expect(normalizarError(errorHttp(429, {})).message).toMatch(/Demasiados intentos/);
    expect(normalizarError(errorHttp(500, "<html>")).message).toMatch(/problema/);
    expect(normalizarError(errorHttp(400, null)).message).toMatch(/inesperado/);
  });

  it("no filtra detalles internos de errores desconocidos", () => {
    expect(mensajeDeError({ raro: true })).toMatch(/inesperado/);
    expect(mensajeDeError(new Error("falló algo"))).toBe("falló algo");
  });

  it("devuelve la misma instancia si ya está normalizado", () => {
    const original = new ErrorApi("hola");
    expect(normalizarError(original)).toBe(original);
  });
});
