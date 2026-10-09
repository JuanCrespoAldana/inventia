// Prepara el entorno de desarrollo: entorno virtual de Python + dependencias del backend y del frontend.
import { existsSync, copyFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { BACKEND, RAIZ, ejecutar, pythonDelBackend } from "./lib/python.mjs";

const esWindows = process.platform === "win32";
const paso = (texto) => console.log(`\n== ${texto}`);

paso("Entorno virtual de Python (backend/.venv)");
if (!existsSync(path.join(BACKEND, ".venv"))) {
  const r = spawnSync(esWindows ? "python" : "python3", ["-m", "venv", ".venv"], { cwd: BACKEND, stdio: "inherit" });
  if (r.status !== 0) {
    console.error("No se pudo crear el entorno virtual. Se necesita Python 3.12 o superior (recomendado 3.13).");
    process.exit(1);
  }
}
console.log(`Python: ${pythonDelBackend()}`);

paso("Dependencias del backend");
ejecutar(["-m", "pip", "install", "--upgrade", "pip"]);
ejecutar(["-m", "pip", "install", "-r", "requirements-dev.txt"]);

paso("Dependencias del frontend");
const npm = esWindows ? "npm.cmd" : "npm";
const f = spawnSync(npm, ["ci", "--no-audit", "--no-fund"], { cwd: path.join(RAIZ, "frontend"), stdio: "inherit", shell: esWindows });
if (f.status !== 0) process.exit(f.status ?? 1);

paso("Archivo de configuración");
const env = path.join(BACKEND, ".env");
if (!existsSync(env)) {
  copyFileSync(path.join(BACKEND, ".env.example"), env);
  console.log("Se creó backend/.env desde el ejemplo. Complete DATABASE_URL y SECRET_KEY antes de iniciar.");
} else {
  console.log("backend/.env ya existe; no se modifica.");
}
console.log("\nListo. Siguientes pasos: npm run migrar  →  npm run dev");
