// Prepara el entorno de desarrollo: entorno virtual de Python + dependencias del backend y del frontend.
import { existsSync, copyFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { BACKEND, RAIZ, ejecutar, pythonDelBackend, buscarPythonCompatible, esVersionCompatible, versionDe } from "./lib/python.mjs";

const esWindows = process.platform === "win32";
const paso = (texto) => console.log(`\n== ${texto}`);

paso("Entorno virtual de Python (backend/.venv)");
if (!existsSync(path.join(BACKEND, ".venv"))) {
  const py = buscarPythonCompatible();
  if (!py) {
    console.error(
      [
        "No se encontró un Python compatible (se necesita 3.12, 3.13 o 3.14; recomendado 3.13).",
        esWindows
          ? "Instálelo con:  py install 3.13   (o descárguelo de python.org/downloads marcando «Add python.exe to PATH»)."
          : "Instale python3.13 con el gestor de paquetes de su sistema (o desde python.org/downloads).",
        "Después cierre y abra la terminal y repita:  npm run setup",
      ].join("\n"),
    );
    process.exit(1);
  }
  console.log(`Se usará ${py.etiqueta}`);
  const r = spawnSync(py.comando, [...py.argumentos, "-m", "venv", ".venv"], { cwd: BACKEND, stdio: "inherit" });
  if (r.status !== 0) {
    console.error("No se pudo crear el entorno virtual.");
    process.exit(1);
  }
} else if (!process.env.INVENTIA_PYTHON) {
  const v = versionDe(pythonDelBackend());
  if (!esVersionCompatible(v)) {
    console.error(
      [
        `El entorno backend/.venv usa ${v ? `Python ${v.mayor}.${v.menor}` : "un Python que no se puede ejecutar"}, que no es compatible (se necesita 3.12, 3.13 o 3.14).`,
        "Bórrelo y vuelva a ejecutar el setup:",
        esWindows ? "  Remove-Item -Recurse -Force backend\\.venv   (PowerShell)" : "  rm -rf backend/.venv",
        "  npm run setup",
      ].join("\n"),
    );
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
