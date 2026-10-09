import type { FieldPath, FieldValues, UseFormSetError } from "react-hook-form";
import { z } from "zod";
import { ErrorApi, normalizarError } from "./errors";

/**
 * Traslada los errores por campo del backend (422) al formulario. Devuelve un mensaje general
 * cuando el error no pertenece a un campo conocido, para mostrarlo en un aviso sobre el formulario.
 */
export function aplicarErroresServidor<T extends FieldValues>(error: unknown, setError: UseFormSetError<T>, campos: readonly string[]): string | null {
  const e: ErrorApi = normalizarError(error);
  let pendiente = Object.keys(e.campos).length === 0;
  for (const [campo, mensaje] of Object.entries(e.campos)) {
    if (campos.includes(campo)) setError(campo as FieldPath<T>, { type: "server", message: mensaje });
    else pendiente = true;
  }
  return pendiente ? e.message : null;
}

const textoRequerido = (nombre: string, min = 2, max = 150) =>
  z
    .string()
    .trim()
    .min(min, `${nombre} es obligatorio${min > 1 ? ` (mínimo ${min} caracteres)` : ""}`)
    .max(max, `${nombre} no puede superar los ${max} caracteres`);

export const v = {
  texto: textoRequerido,
  textoOpcional: (max = 200) => z.string().trim().max(max, `No puede superar los ${max} caracteres`),
  correo: z.string().trim().min(1, "El correo es obligatorio").email("Escriba un correo válido, por ejemplo nombre@empresa.com").max(150),
  telefono: z
    .string()
    .trim()
    .refine((t) => t === "" || /^[0-9+()\-\s]{7,20}$/.test(t), "Escriba un teléfono válido (solo números, +, - y paréntesis)"),
  identificacion: z
    .string()
    .trim()
    .refine((t) => /^[0-9A-Za-z\-\s.]{5,25}$/.test(t) && t.replace(/[\s.]/g, "").length >= 5, "La identificación debe tener entre 5 y 20 caracteres (números, letras o guion)"),
  /** Mismas reglas que el backend (`validar_password_segura`). */
  password: z
    .string()
    .min(8, "Debe tener al menos 8 caracteres")
    .max(128, "No puede superar los 128 caracteres")
    .refine((p) => /[A-Z]/.test(p), "Debe incluir una letra mayúscula")
    .refine((p) => /[a-z]/.test(p), "Debe incluir una letra minúscula")
    .refine((p) => /\d/.test(p), "Debe incluir un número")
    .refine((p) => /[^\w\s]|_/.test(p), "Debe incluir un carácter especial"),
  entero: (nombre: string, min = 0, max = 1_000_000) =>
    z
      .string()
      .trim()
      .min(1, `${nombre} es obligatorio`)
      .refine((t) => /^-?\d+$/.test(t), `${nombre} debe ser un número entero`)
      .refine((t) => Number(t) >= min, `${nombre} debe ser como mínimo ${min}`)
      .refine((t) => Number(t) <= max, `${nombre} no puede superar ${max}`),
  dinero: (nombre: string) =>
    z
      .string()
      .trim()
      .refine((t) => t === "" || /^\d+([.,]\d{1,2})?$/.test(t), `${nombre}: escriba un valor válido (hasta 2 decimales)`),
};

export function aDinero(texto: string): number | null {
  const limpio = texto.trim().replace(",", ".");
  return limpio === "" ? null : Number(limpio);
}

export const REQUISITOS_PASSWORD: { texto: string; cumple: (p: string) => boolean }[] = [
  { texto: "Al menos 8 caracteres", cumple: (p) => p.length >= 8 },
  { texto: "Una letra mayúscula", cumple: (p) => /[A-Z]/.test(p) },
  { texto: "Una letra minúscula", cumple: (p) => /[a-z]/.test(p) },
  { texto: "Un número", cumple: (p) => /\d/.test(p) },
  { texto: "Un carácter especial", cumple: (p) => /[^\w\s]|_/.test(p) },
];

/**
 * Genera una contraseña temporal que cumple la política (mayúscula, minúscula, número y carácter especial)
 * con aleatoriedad criptográfica. Evita caracteres ambiguos (0/O, 1/l/I) para que sea fácil de dictar.
 */
export function generarPassword(longitud = 14): string {
  const grupos = ["ABCDEFGHJKLMNPQRSTUVWXYZ", "abcdefghijkmnopqrstuvwxyz", "23456789", "!@#$%*?-_"];
  const todos = grupos.join("");
  const aleatorio = (tope: number) => {
    // Rechazo de valores que sesgarían la distribución (muestreo uniforme).
    const limite = Math.floor(0x1_0000_0000 / tope) * tope;
    const buffer = new Uint32Array(1);
    do crypto.getRandomValues(buffer);
    while (buffer[0] >= limite);
    return buffer[0] % tope;
  };
  const caracteres = grupos.map((g) => g[aleatorio(g.length)]);
  while (caracteres.length < longitud) caracteres.push(todos[aleatorio(todos.length)]);
  for (let i = caracteres.length - 1; i > 0; i--) {
    const j = aleatorio(i + 1);
    [caracteres[i], caracteres[j]] = [caracteres[j], caracteres[i]];
  }
  return caracteres.join("");
}
