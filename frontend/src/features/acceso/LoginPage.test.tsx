import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiAuth } from "@/api/auth";
import { ErrorApi } from "@/lib/errors";
import { crearSesion, renderizar } from "@/test/utilidades";
import LoginPage from "./LoginPage";

vi.mock("@/api/auth", () => ({ apiAuth: { estadoInstalacion: vi.fn(), login: vi.fn(), yo: vi.fn(), logout: vi.fn() } }));

const pantalla = () =>
  renderizar(
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<p>Panel de control</p>} />
      <Route path="/configuracion-inicial" element={<p>Configuración inicial</p>} />
    </Routes>,
    { ruta: "/login" },
  );

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(apiAuth.estadoInstalacion).mockResolvedValue({ configurado: true } as never);
});

describe("<LoginPage>", () => {
  it("valida los campos en español antes de llamar al servidor", async () => {
    const u = userEvent.setup();
    pantalla();
    await u.click(await screen.findByRole("button", { name: "Ingresar" }));
    expect(await screen.findByText("Escriba su correo electrónico")).toBeInTheDocument();
    expect(screen.getByText("Escriba su contraseña")).toBeInTheDocument();
    await u.type(screen.getByLabelText("Correo electrónico"), "no-es-correo");
    await u.click(screen.getByRole("button", { name: "Ingresar" }));
    expect(await screen.findByText("Escriba un correo válido")).toBeInTheDocument();
    expect(apiAuth.login).not.toHaveBeenCalled();
  });

  it("inicia sesión y entra al panel", async () => {
    const u = userEvent.setup();
    vi.mocked(apiAuth.login).mockResolvedValue({ access_token: "tok", token_type: "bearer", usuario: crearSesion() } as never);
    pantalla();
    await u.type(await screen.findByLabelText("Correo electrónico"), "  ana@empresa.com ");
    await u.type(screen.getByLabelText("Contraseña"), "Clave#Segura1");
    await u.click(screen.getByRole("button", { name: "Ingresar" }));
    expect(await screen.findByText("Panel de control")).toBeInTheDocument();
    expect(apiAuth.login).toHaveBeenCalledWith("ana@empresa.com", "Clave#Segura1");
    expect(sessionStorage.getItem("inventia.token")).toBe("tok");
  });

  it("muestra el mensaje del servidor cuando las credenciales son incorrectas", async () => {
    const u = userEvent.setup();
    vi.mocked(apiAuth.login).mockRejectedValue(new ErrorApi("Correo o contraseña incorrectos", { status: 401 }));
    pantalla();
    await u.type(await screen.findByLabelText("Correo electrónico"), "ana@empresa.com");
    await u.type(screen.getByLabelText("Contraseña"), "incorrecta");
    await u.click(screen.getByRole("button", { name: "Ingresar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Correo o contraseña incorrectos");
    expect(screen.queryByText("Panel de control")).not.toBeInTheDocument();
  });

  it("si la instalación no está configurada lleva al asistente inicial", async () => {
    vi.mocked(apiAuth.estadoInstalacion).mockResolvedValue({ configurado: false } as never);
    pantalla();
    await waitFor(() => expect(screen.getByText("Configuración inicial")).toBeInTheDocument());
  });

  it("permite mostrar y ocultar la contraseña", async () => {
    const u = userEvent.setup();
    pantalla();
    const campo = await screen.findByLabelText("Contraseña");
    expect(campo).toHaveAttribute("type", "password");
    await u.click(screen.getByRole("button", { name: "Mostrar contraseña" }));
    expect(campo).toHaveAttribute("type", "text");
  });
});
