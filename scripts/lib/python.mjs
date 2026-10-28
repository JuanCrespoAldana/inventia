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

/** Versiones de Python con las que se probó el backend (las librerías de cálculo fijan versiones que exigen 3.12 o más). */
export const VERSIONES_PYTHON = [12, 13, 14];

/** Devuelve la versión «3.X» de un intérprete, o null si no se puede ejecutar. */
export function versionDe(comando, argumentos = []) {
  const r = spawnSync(comando, [...argumentos, "-c", "import sys; print(sys.version_info[0], sys.version_info[1])"], { encoding: "utf8" });
  if (r.error || r.status !== 0) return null;
  const [mayor, menor] = r.stdout.trim().split(/\s+/).map(Number);
  return Number.isInteger(mayor) && Number.isInteger(menor) ? { mayor, menor } : null;
}

export function esVersionCompatible(v) {
  return v !== null && v.mayor === 3 && VERSIONES_PYTHON.includes(v.menor);
}

/**
 * Busca en el sistema un Python compatible para crear el entorno virtual, sin que la persona tenga que saber cuál
 * es el que está primero en el PATH. Prefiere 3.13 (la versión recomendada), luego 3.12 y 3.14.
 */
export function buscarPythonCompatible() {
  const candidatos =
    process.platform === "win32"
      ? [["py", ["-3.13"]], ["py", ["-3.12"]], ["py", ["-3.14"]], ["python", []], ["python3", []]]
      : [["python3.13", []], ["python3.12", []], ["python3.14", []], ["python3", []], ["python", []]];
  for (const [comando, argumentos] of candidatos) {
    const v = versionDe(comando, argumentos);
    if (esVersionCompatible(v)) return { comando, argumentos, etiqueta: `Python ${v.mayor}.${v.menor} (${[comando, ...argumentos].join(" ")})` };
  }
  return null;
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
