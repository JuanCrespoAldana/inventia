import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiRoles, apiSedes, apiUsuarios } from "@/api/administracion";
import { apiAuth } from "@/api/auth";
import { crearSesion, renderizar } from "@/test/utilidades";
import UsuariosPage from "./UsuariosPage";

vi.mock("@/api/auth", () => ({ apiAuth: { yo: vi.fn(), logout: vi.fn() } }));
vi.mock("@/api/administracion", () => ({
  apiRoles: { listar: vi.fn() },
  apiSedes: { listar: vi.fn() },
  apiUsuarios: { listar: vi.fn(), crear: vi.fn(), actualizar: vi.fn(), estado: vi.fn(), restablecerPassword: vi.fn(), desbloquear: vi.fn() },
}));

const ROLES = [
  { id: 1, clave: "admin", nombre: "Administrador", descripcion: null, alcance: "empresa", es_sistema: true, activo: true, permisos: [], total_usuarios: 1 },
  { id: 2, clave: "encargado_sede", nombre: "Encargado de sede", descripcion: "Opera su sede.", alcance: "sede", es_sistema: true, activo: true, permisos: [], total_usuarios: 0 },
];
const SEDES = [{ id: 10, nombre: "Sede Norte", ciudad: "Bogotá", activa: true }, { id: 11, nombre: "Sede Sur", ciudad: "Cali", activa: true }];
const usuario = (extra: object) => ({
  id: 1, nombre: "Ana Pérez", email: "ana@empresa.com", activo: true, bloqueado: false, debe_cambiar_password: false, ultimo_acceso: null, created_at: "2026-01-01T00:00:00Z",
  rol: { id: 1, clave: "admin", nombre: "Administrador", alcance: "empresa" }, sede: null, ...extra,
});
const PERMISOS = ["usuarios.ver", "usuarios.crear", "usuarios.editar", "usuarios.inhabilitar", "roles.ver", "sedes.ver"];

function abrir() {
  vi.mocked(apiAuth.yo).mockResolvedValue(crearSesion({ id: 1, permisos: PERMISOS }));
  return renderizar(<UsuariosPage />, { conSesion: true });
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(apiRoles.listar).mockResolvedValue(ROLES as never);
  vi.mocked(apiSedes.listar).mockResolvedValue({ items: SEDES, total: 2, pagina: 1, tamano: 100, paginas: 1 } as never);
  vi.mocked(apiUsuarios.listar).mockResolvedValue({
    items: [
      usuario({}),
      usuario({ id: 2, nombre: "Luis Gómez", email: "luis@empresa.com", bloqueado: true, rol: { id: 2, clave: "encargado_sede", nombre: "Encargado de sede", alcance: "sede" }, sede: { id: 10, nombre: "Sede Norte" } }),
      usuario({ id: 3, nombre: "Marta Ríos", email: "marta@empresa.com", debe_cambiar_password: true }),
      usuario({ id: 4, nombre: "Pedro Díaz", email: "pedro@empresa.com", activo: false }),
    ],
    total: 4, pagina: 1, tamano: 20, paginas: 1,
  } as never);
});

describe("<UsuariosPage>", () => {
  it("lista los usuarios con su estado y no deja que alguien se inhabilite a sí mismo", async () => {
    abrir();
    const fila = (nombre: string) => screen.getByText(nombre).closest("tr") as HTMLElement;
    expect(await screen.findByText("Luis Gómez")).toBeInTheDocument();
    expect(within(fila("Luis Gómez")).getByText("Bloqueado")).toBeInTheDocument();
    expect(within(fila("Marta Ríos")).getByText("Contraseña temporal")).toBeInTheDocument();
    expect(within(fila("Pedro Díaz")).getByText("Inhabilitado")).toBeInTheDocument();
    expect(within(fila("Ana Pérez")).queryByRole("button", { name: /Inhabilitar|Activar/ })).not.toBeInTheDocument();
    expect(within(fila("Ana Pérez")).queryByRole("button", { name: /Restablecer/ })).not.toBeInTheDocument();
    expect(within(fila("Luis Gómez")).getByRole("button", { name: /Desbloquear/ })).toBeInTheDocument();
  });

  it("un rol de una sola sede exige elegir la sede", async () => {
    const u = userEvent.setup();
    vi.mocked(apiUsuarios.crear).mockResolvedValue(usuario({}) as never);
    abrir();
    await u.click(await screen.findByRole("button", { name: "Nuevo usuario" }));
    const dialogo = await screen.findByRole("dialog");
    await u.type(within(dialogo).getByLabelText(/Nombre completo/), "Carla Mora");
    await u.type(within(dialogo).getByLabelText(/Correo electrónico/), "Carla@Empresa.com");
    expect(within(dialogo).queryByLabelText(/^Sede/)).not.toBeInTheDocument();
    await u.selectOptions(within(dialogo).getByRole("combobox", { name: /^Rol/ }), "2");
    const sede = await within(dialogo).findByRole("combobox", { name: /^Sede/ });
    await u.type(within(dialogo).getByLabelText(/Contraseña inicial/), "Clave#Segura1");
    await u.click(within(dialogo).getByRole("button", { name: "Crear usuario" }));
    expect(await within(dialogo).findByText(/Este rol opera dentro de una sede/)).toBeInTheDocument();
    expect(apiUsuarios.crear).not.toHaveBeenCalled();

    await u.selectOptions(sede, "11");
    await u.click(within(dialogo).getByRole("button", { name: "Crear usuario" }));
    await waitFor(() => expect(apiUsuarios.crear).toHaveBeenCalledTimes(1));
    expect(vi.mocked(apiUsuarios.crear).mock.calls[0][0]).toEqual({
      nombre: "Carla Mora", email: "carla@empresa.com", password: "Clave#Segura1", rol_id: 2, sede_id: 11, forzar_cambio_password: true,
    });
  });

  it("un rol de empresa se crea sin sede", async () => {
    const u = userEvent.setup();
    vi.mocked(apiUsuarios.crear).mockResolvedValue(usuario({}) as never);
    abrir();
    await u.click(await screen.findByRole("button", { name: "Nuevo usuario" }));
    const dialogo = await screen.findByRole("dialog");
    await u.type(within(dialogo).getByLabelText(/Nombre completo/), "Gerente Nuevo");
    await u.type(within(dialogo).getByLabelText(/Correo electrónico/), "gerente@empresa.com");
    await u.selectOptions(within(dialogo).getByRole("combobox", { name: /^Rol/ }), "1");
    expect(within(dialogo).getByText(/ve la información de todas las sedes/)).toBeInTheDocument();
    await u.type(within(dialogo).getByLabelText(/Contraseña inicial/), "Clave#Segura1");
    await u.click(within(dialogo).getByRole("button", { name: "Crear usuario" }));
    await waitFor(() => expect(apiUsuarios.crear).toHaveBeenCalled());
    expect(vi.mocked(apiUsuarios.crear).mock.calls[0][0]).toMatchObject({ rol_id: 1, sede_id: null });
  });

  it("rechaza contraseñas que no cumplen la política, con el motivo en español", async () => {
    const u = userEvent.setup();
    abrir();
    await u.click(await screen.findByRole("button", { name: "Nuevo usuario" }));
    const dialogo = await screen.findByRole("dialog");
    await u.type(within(dialogo).getByLabelText(/Nombre completo/), "Carla Mora");
    await u.type(within(dialogo).getByLabelText(/Correo electrónico/), "carla@empresa.com");
    await u.selectOptions(within(dialogo).getByRole("combobox", { name: /^Rol/ }), "1");
    await u.type(within(dialogo).getByLabelText(/Contraseña inicial/), "debil");
    await u.click(within(dialogo).getByRole("button", { name: "Crear usuario" }));
    expect(await within(dialogo).findByText("Debe tener al menos 8 caracteres")).toBeInTheDocument();
    expect(apiUsuarios.crear).not.toHaveBeenCalled();
  });

  it("muestra los errores que devuelve el servidor junto al campo", async () => {
    const u = userEvent.setup();
    const { ErrorApi } = await import("@/lib/errors");
    vi.mocked(apiUsuarios.crear).mockRejectedValue(new ErrorApi("Ya existe un usuario con ese correo", { status: 409, campos: { email: "Ese correo ya está registrado" } }));
    abrir();
    await u.click(await screen.findByRole("button", { name: "Nuevo usuario" }));
    const dialogo = await screen.findByRole("dialog");
    await u.type(within(dialogo).getByLabelText(/Nombre completo/), "Carla Mora");
    await u.type(within(dialogo).getByLabelText(/Correo electrónico/), "ana@empresa.com");
    await u.selectOptions(within(dialogo).getByRole("combobox", { name: /^Rol/ }), "1");
    await u.type(within(dialogo).getByLabelText(/Contraseña inicial/), "Clave#Segura1");
    await u.click(within(dialogo).getByRole("button", { name: "Crear usuario" }));
    expect(await within(dialogo).findByText("Ese correo ya está registrado")).toBeInTheDocument();
  });

  it("desbloquea a un usuario bloqueado", async () => {
    const u = userEvent.setup();
    vi.mocked(apiUsuarios.desbloquear).mockResolvedValue(usuario({ id: 2 }) as never);
    abrir();
    await u.click(await screen.findByRole("button", { name: /Desbloquear a Luis Gómez/ }));
    await waitFor(() => expect(apiUsuarios.desbloquear).toHaveBeenCalled());
    expect(vi.mocked(apiUsuarios.desbloquear).mock.calls[0][0]).toBe(2);
  });
});
