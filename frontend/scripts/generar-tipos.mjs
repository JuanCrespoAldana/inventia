// Regenera src/types/api.gen.ts a partir del contrato OpenAPI del backend.
//
//   npm run tipos            (desde frontend/ o desde la raíz del repositorio)
//
// 1) Exporta el contrato con backend/scripts/exportar_openapi.py (no necesita base de datos).
// 2) Genera los tipos con openapi-typescript en una carpeta temporal: así no se mezcla con las dependencias del
//    proyecto (openapi-typescript 7 pide TypeScript 5 y el frontend usa 6).
// 3) Conserva solo el bloque de esquemas, que es lo único que usa la aplicación.
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { BACKEND, ejecutar } from "../../scripts/lib/python.mjs";

const salida = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "src", "types", "api.gen.ts");
const tmp = mkdtempSync(path.join(os.tmpdir(), "inventia-tipos-"));
const esWindows = process.platform === "win32";

try {
  const contrato = path.join(tmp, "openapi.json");
  ejecutar([path.join("scripts", "exportar_openapi.py"), contrato], { cwd: BACKEND });

  writeFileSync(path.join(tmp, "package.json"), JSON.stringify({ name: "tipos", private: true, dependencies: { "openapi-typescript": "^7.13.0", typescript: "^5.9.3" } }));
  const npm = esWindows ? "npm.cmd" : "npm";
  const i = spawnSync(npm, ["install", "--no-audit", "--no-fund", "--loglevel=error"], { cwd: tmp, stdio: "inherit", shell: esWindows });
  if (i.status !== 0) throw new Error("No se pudo instalar openapi-typescript");

  const generado = path.join(tmp, "api.ts");
  const g = spawnSync(process.execPath, [path.join(tmp, "node_modules", "openapi-typescript", "bin", "cli.js"), contrato, "-o", generado], { cwd: tmp, stdio: "inherit" });
  if (g.status !== 0) throw new Error("openapi-typescript falló");

  const lineas = readFileSync(generado, "utf8").split("\n");
  const ini = lineas.findIndex((l) => l.startsWith("export interface components"));
  const fin = lineas.findIndex((l) => l.startsWith("export type $defs"));
  if (ini < 0 || fin < 0) throw new Error("No se encontró el bloque de esquemas en la salida de openapi-typescript");
  const cabecera = [
    "/* Generado con openapi-typescript a partir de /openapi.json del backend. No editar a mano.",
    "   Regenerar: npm run tipos (ver docs/DESARROLLO.md). Solo se conserva el bloque de esquemas. */",
    "",
  ];
  writeFileSync(salida, [...cabecera, ...lineas.slice(ini, fin)].join("\n").trimEnd() + "\n");
  process.stdout.write(`Tipos escritos en ${path.relative(process.cwd(), salida)}\n`);
} finally {
  rmSync(tmp, { recursive: true, force: true });
}
