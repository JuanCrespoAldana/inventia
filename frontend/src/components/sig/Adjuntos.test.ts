import { describe, expect, it } from "vitest";
import { ADJUNTO_MAX_BYTES, ADJUNTO_MAX_POR_REGISTRO, validarArchivo } from "./Adjuntos";

const archivo = (name: string, size: number, type: string) => ({ name, size, type });

describe("validación de evidencias adjuntas", () => {
  it("acepta imágenes y PDF dentro del límite", () => {
    expect(validarArchivo(archivo("foto.jpg", 1000, "image/jpeg"), 0)).toBeNull();
    expect(validarArchivo(archivo("factura.PDF", 1000, "application/pdf"), 2)).toBeNull();
    expect(validarArchivo(archivo("captura.webp", ADJUNTO_MAX_BYTES, "image/webp"), 0)).toBeNull();
  });

  it("rechaza archivos vacíos o demasiado grandes", () => {
    expect(validarArchivo(archivo("a.png", 0, "image/png"), 0)).toMatch(/vacío/);
    expect(validarArchivo(archivo("a.png", ADJUNTO_MAX_BYTES + 1, "image/png"), 0)).toMatch(/máximo/);
  });

  it("rechaza tipos no permitidos, aunque el nombre parezca válido", () => {
    expect(validarArchivo(archivo("macro.exe", 10, "application/octet-stream"), 0)).toMatch(/solo se aceptan/);
    expect(validarArchivo(archivo("falso.pdf", 10, "text/html"), 0)).toMatch(/solo se aceptan/);
    expect(validarArchivo(archivo("sin-extension", 10, "image/png"), 0)).toMatch(/solo se aceptan/);
  });

  it("limita la cantidad de archivos por registro", () => {
    expect(validarArchivo(archivo("a.png", 10, "image/png"), ADJUNTO_MAX_POR_REGISTRO)).toMatch(/hasta/);
  });
});
