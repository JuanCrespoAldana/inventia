import { describe, expect, it } from "vitest";
import { crearSesion } from "@/test/utilidades";
import { gruposVisibles } from "./navegacion";

const etiquetas = (permisos: string[], rol: Partial<ReturnType<typeof crearSesion>["rol"]> = {}) =>
  gruposVisibles(crearSesion({ permisos, rol: { id: 9, clave: "x", nombre: "Rol", alcance: "empresa", ...rol } }))
    .flatMap((g) => g.items.map((i) => i.etiqueta));

describe("menú de navegación por permisos", () => {
  it("siempre muestra el panel de control y nada más sin permisos", () => {
    expect(etiquetas([])).toEqual(["Panel de control"]);
  });

  it("un encargado de sede no ve administración", () => {
    const e = etiquetas(["inventario.ver", "ventas.registrar", "traslados.solicitar", "alertas.ver", "productos.ver", "sedes.ver"], { alcance: "sede", clave: "encargado_sede" });
    expect(e).toEqual(expect.arrayContaining(["Existencias", "Ventas", "Traslados", "Alertas", "Productos"]));
    expect(e).not.toContain("Usuarios");
    expect(e).not.toContain("Roles y permisos");
    expect(e).not.toContain("Sedes"); // sin permisos de edición no tiene sentido la administración de sedes
    expect(e).not.toContain("Consolidado");
  });

  it("administración de sedes aparece para roles de empresa o con permiso de edición", () => {
    expect(etiquetas(["sedes.ver"])).toContain("Sedes");
    expect(etiquetas(["sedes.ver"], { alcance: "sede" })).not.toContain("Sedes");
    expect(etiquetas(["sedes.ver", "sedes.editar"], { alcance: "sede" })).toContain("Sedes");
  });

  it("roles y permisos exige poder ver roles y usuarios", () => {
    expect(etiquetas(["roles.ver"])).not.toContain("Roles y permisos");
    expect(etiquetas(["roles.ver", "usuarios.ver"])).toContain("Roles y permisos");
  });

  it("reportes aparece con cualquier permiso de reportes", () => {
    expect(etiquetas(["reportes.alertas"])).toContain("Reportes");
    expect(etiquetas(["alertas.ver"])).not.toContain("Reportes");
  });

  it("no deja grupos vacíos", () => {
    const grupos = gruposVisibles(crearSesion({ permisos: ["ventas.ver"] }));
    expect(grupos.every((g) => g.items.length > 0)).toBe(true);
    expect(grupos.map((g) => g.titulo)).toEqual([null, "Operación"]);
  });

  it("agentes de IA solo con su permiso", () => {
    expect(etiquetas(["agentes.gestionar"])).toContain("Agentes de IA");
    expect(etiquetas(["usuarios.ver"])).not.toContain("Agentes de IA");
  });
});
