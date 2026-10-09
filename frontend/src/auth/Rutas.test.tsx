import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiAuth } from "@/api/auth";
import { crearSesion, renderizar } from "@/test/utilidades";
import { RequierePermiso, RutaProtegida, RutaPublica } from "./Rutas";

vi.mock("@/api/auth", () => ({ apiAuth: { yo: vi.fn(), logout: vi.fn(), login: vi.fn() } }));

function Arbol() {
  return (
    <Routes>
      <Route element={<RutaPublica />}>
        <Route path="/login" element={<p>Pantalla de ingreso</p>} />
      </Route>
      <Route element={<RutaProtegida />}>
        <Route path="/cambiar-password" element={<p>Cambio obligatorio</p>} />
        <Route index element={<p>Panel privado</p>} />
        <Route path="/usuarios" element={<RequierePermiso alguno={["usuarios.ver"]}><p>Listado de usuarios</p></RequierePermiso>} />
      </Route>
    </Routes>
  );
}

beforeEach(() => vi.resetAllMocks());

describe("rutas protegidas", () => {
  it("lleva a quien no ha iniciado sesión a la pantalla de ingreso", async () => {
    renderizar(<Arbol />, { ruta: "/usuarios" });
    expect(await screen.findByText("Pantalla de ingreso")).toBeInTheDocument();
    expect(screen.queryByText("Listado de usuarios")).not.toBeInTheDocument();
  });

  it("muestra el contenido cuando hay una sesión válida", async () => {
    vi.mocked(apiAuth.yo).mockResolvedValue(crearSesion());
    renderizar(<Arbol />, { conSesion: true });
    expect(await screen.findByText("Panel privado")).toBeInTheDocument();
  });

  it("obliga a cambiar la contraseña temporal antes de usar el sistema", async () => {
    vi.mocked(apiAuth.yo).mockResolvedValue(crearSesion({ debe_cambiar_password: true }));
    renderizar(<Arbol />, { conSesion: true });
    expect(await screen.findByText("Cambio obligatorio")).toBeInTheDocument();
    expect(screen.queryByText("Panel privado")).not.toBeInTheDocument();
  });

  it("cierra la sesión local si el servidor rechaza el token", async () => {
    vi.mocked(apiAuth.yo).mockRejectedValue(new Error("401"));
    renderizar(<Arbol />, { conSesion: true });
    expect(await screen.findByText("Pantalla de ingreso")).toBeInTheDocument();
    expect(sessionStorage.getItem("inventia.token")).toBeNull();
  });

  it("quien ya inició sesión no vuelve a ver el ingreso", async () => {
    vi.mocked(apiAuth.yo).mockResolvedValue(crearSesion());
    renderizar(<Arbol />, { ruta: "/login", conSesion: true });
    expect(await screen.findByText("Panel privado")).toBeInTheDocument();
  });
});

describe("<RequierePermiso>", () => {
  it("bloquea la pantalla cuando falta el permiso", async () => {
    vi.mocked(apiAuth.yo).mockResolvedValue(crearSesion({ permisos: ["ventas.ver"] }));
    renderizar(<Arbol />, { ruta: "/usuarios", conSesion: true });
    expect(await screen.findByText("No tiene acceso a esta sección")).toBeInTheDocument();
    expect(screen.queryByText("Listado de usuarios")).not.toBeInTheDocument();
  });

  it("deja pasar con el permiso", async () => {
    vi.mocked(apiAuth.yo).mockResolvedValue(crearSesion({ permisos: ["usuarios.ver"] }));
    renderizar(<Arbol />, { ruta: "/usuarios", conSesion: true });
    expect(await screen.findByText("Listado de usuarios")).toBeInTheDocument();
  });
});
