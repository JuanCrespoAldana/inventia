import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiRoles } from "@/api/administracion";
import { apiAuth } from "@/api/auth";
import { crearSesion, renderizar } from "@/test/utilidades";
import RolesPage from "./RolesPage";

vi.mock("@/api/auth", () => ({ apiAuth: { yo: vi.fn(), logout: vi.fn() } }));
vi.mock("@/api/administracion", () => ({
  apiRoles: { listar: vi.fn(), permisos: vi.fn(), asignarPermisos: vi.fn(), crear: vi.fn(), actualizar: vi.fn(), eliminar: vi.fn() },
}));

const CATALOGO = [
  { codigo: "productos.ver", modulo: "Productos", descripcion: "Consultar productos" },
  { codigo: "ventas.ver", modulo: "Ventas", descripcion: "Consultar ventas" },
  { codigo: "agentes.gestionar", modulo: "Agentes de IA", descripcion: "Administrar llaves de agentes" },
];
const rol = (extra: object) => ({ id: 1, clave: null, nombre: "Rol", descripcion: null, alcance: "sede", es_sistema: false, activo: true, permisos: [], total_usuarios: 0, created_at: "2026-01-01T00:00:00Z", ...extra });
const ROLES = [
  rol({ id: 1, clave: "admin", nombre: "Administrador", alcance: "empresa", es_sistema: true, permisos: CATALOGO.map((p) => p.codigo), total_usuarios: 1 }),
  rol({ id: 2, nombre: "Auxiliar de ventas", permisos: ["ventas.ver", "agentes.gestionar"] }),
  rol({ id: 3, clave: "gerente", nombre: "Gerente", es_sistema: true, permisos: ["ventas.ver"], total_usuarios: 2 }),
];

function abrir(permisos: string[]) {
  vi.mocked(apiAuth.yo).mockResolvedValue(crearSesion({ permisos }));
  return renderizar(<RolesPage />, { conSesion: true });
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(apiRoles.listar).mockResolvedValue(ROLES as never);
  vi.mocked(apiRoles.permisos).mockResolvedValue(CATALOGO as never);
});

describe("<RolesPage>", () => {
  it("el rol Administrador se muestra bloqueado: no se puede editar ni eliminar", async () => {
    abrir(["roles.ver", "roles.editar", "roles.asignar_permisos", "productos.ver", "ventas.ver", "agentes.gestionar"]);
    expect(await screen.findByText(/siempre tiene todos los permisos/i)).toBeInTheDocument();
    for (const c of screen.getAllByRole("checkbox")) {
      expect(c).toBeDisabled();
      expect(c).toBeChecked();
    }
    expect(screen.queryByRole("button", { name: "Guardar permisos" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Eliminar/ })).not.toBeInTheDocument();
  });

  it("solo permite conceder permisos que quien edita ya tiene (sin escalada de privilegios)", async () => {
    const u = userEvent.setup();
    abrir(["roles.ver", "roles.editar", "roles.asignar_permisos", "productos.ver", "ventas.ver"]); // no tiene agentes.gestionar
    await u.click(await screen.findByRole("button", { name: /Auxiliar de ventas/ }));
    expect(await screen.findByText(/Solo puede conceder permisos que usted mismo tiene/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Administrar llaves de agentes/)).toBeDisabled();
    expect(screen.getByLabelText(/Administrar llaves de agentes/)).toBeChecked(); // el rol lo conserva
    expect(screen.getByLabelText(/Consultar productos/)).toBeEnabled();
  });

  it("guarda solo los permisos que la persona posee y detecta cambios sin guardar", async () => {
    const u = userEvent.setup();
    vi.mocked(apiRoles.asignarPermisos).mockResolvedValue(ROLES[1] as never);
    abrir(["roles.ver", "roles.editar", "roles.asignar_permisos", "productos.ver", "ventas.ver"]);
    await u.click(await screen.findByRole("button", { name: /Auxiliar de ventas/ }));
    const guardar = await screen.findByRole("button", { name: "Guardar permisos" });
    expect(guardar).toBeDisabled();
    await u.click(screen.getByLabelText(/Consultar productos/));
    expect(screen.getByText(/Hay cambios sin guardar/)).toBeInTheDocument();
    await u.click(guardar);
    await waitFor(() => expect(apiRoles.asignarPermisos).toHaveBeenCalledTimes(1));
    const [id, permisos] = vi.mocked(apiRoles.asignarPermisos).mock.calls[0];
    expect(id).toBe(2);
    expect([...permisos].sort()).toEqual(["productos.ver", "ventas.ver"]); // agentes.gestionar no se envía
  });

  it("descartar devuelve la selección original", async () => {
    const u = userEvent.setup();
    abrir(["roles.ver", "roles.asignar_permisos", "productos.ver", "ventas.ver", "agentes.gestionar"]);
    await u.click(await screen.findByRole("button", { name: /Auxiliar de ventas/ }));
    const productos = await screen.findByLabelText(/Consultar productos/);
    await u.click(productos);
    expect(productos).toBeChecked();
    await u.click(screen.getByRole("button", { name: "Descartar" }));
    expect(screen.getByLabelText(/Consultar productos/)).not.toBeChecked();
  });

  it("los roles del sistema no se pueden eliminar; los personalizados sí", async () => {
    const u = userEvent.setup();
    abrir(["roles.ver", "roles.editar", "roles.asignar_permisos"]);
    await u.click(await screen.findByRole("button", { name: /Gerente/ }));
    expect(await screen.findByText("Rol del sistema")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Eliminar/ })).not.toBeInTheDocument();
    await u.click(screen.getByRole("button", { name: /Auxiliar de ventas/ }));
    expect(await screen.findByRole("button", { name: /Eliminar/ })).toBeInTheDocument();
  });

  it("sin permiso para asignar, la matriz es de solo lectura", async () => {
    const u = userEvent.setup();
    abrir(["roles.ver", "productos.ver"]);
    await u.click(await screen.findByRole("button", { name: /Auxiliar de ventas/ }));
    expect(await screen.findByText(/puede consultar los permisos, pero no modificarlos/)).toBeInTheDocument();
    for (const c of screen.getAllByRole("checkbox")) expect(c).toBeDisabled();
  });

  it("agrupa los permisos por módulo con su conteo", async () => {
    abrir(["roles.ver"]);
    const modulo = await screen.findByRole("group", { name: /Ventas/ });
    expect(within(modulo).getByText(/1\/1/)).toBeInTheDocument();
  });
});
