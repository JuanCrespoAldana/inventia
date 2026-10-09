// Localiza el Python del backend (entorno virtual del proyecto o el del sistema) en Windows, macOS y Linux.
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
export const BACKEND = path.join(RAIZ, "backend");

export function pythonDelBackend() {
  // Permite apuntar a otro intérprete (p. ej. en CI o con un entorno fuera del repositorio).
  if (process.env.INVENTIA_PYTHON) return process.env.INVENTIA_PYTHON;
  const candidatos = [
    path.join(BACKEND, ".venv", "Scripts", "python.exe"),
    path.join(BACKEND, ".venv", "bin", "python"),
    path.join(BACKEND, "venv", "Scripts", "python.exe"),
    path.join(BACKEND, "venv", "bin", "python"),
  ];
  const venv = candidatos.find((c) => existsSync(c));
  if (venv) return venv;
  return process.platform === "win32" ? "python" : "python3";
}

/** Ejecuta Python en la carpeta del backend mostrando su salida; termina el proceso con el mismo código. */
export function ejecutar(args, { cwd = BACKEND, salirSiFalla = true } = {}) {
  const r = spawnSync(pythonDelBackend(), args, { cwd, stdio: "inherit", env: process.env });
  if (r.error) {
    console.error(`No se pudo ejecutar Python: ${r.error.message}\nEjecute primero: npm run setup`);
    process.exit(1);
  }
  if (salirSiFalla && r.status !== 0) process.exit(r.status ?? 1);
  return r.status ?? 0;
}
