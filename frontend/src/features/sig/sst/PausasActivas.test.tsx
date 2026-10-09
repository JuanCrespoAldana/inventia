import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiAuth } from "@/api/auth";
import { apiSst } from "@/api/sig";
import { bloquearPausas, reiniciarBloqueos } from "@/lib/bloqueoPausas";
import { crearSesion, renderizar } from "@/test/utilidades";
import type { PausaEstado, PausaMostrada } from "@/types/api";
import { PausasActivas } from "./PausasActivas";

vi.mock("@/api/auth", () => ({ apiAuth: { yo: vi.fn(), logout: vi.fn() } }));
vi.mock("@/api/sig", () => ({ apiSst: { estado: vi.fn(), iniciar: vi.fn(), cerrar: vi.fn() } }));

const PAUSA: PausaMostrada = {
  id: 77,
  mostrada_en: "2026-10-09T15:00:00Z",
  actividad: {
    id: 5,
    titulo: "Estiramiento de cuello",
    area: "cuello",
    mensaje: "Relaja los hombros y gira suavemente la cabeza.",
    instrucciones: "Gira la cabeza a cada lado.",
    duracion_segundos: 60,
    recomendaciones: null,
    orden: 1,
    activa: true,
    pasos: ["Siéntate recto", "Gira la cabeza a la derecha"],
    consejos: ["Apoya bien la espalda"],
  },
};

const estado = (cambios: Partial<PausaEstado> = {}): PausaEstado => ({
  aplica: true,
  activo: true,
  intervalo_minutos: 45,
  ahora: new Date().toISOString(),
  ultima_pausa_en: null,
  pendiente: PAUSA, // quedó una pausa abierta: el programador la retoma en cuanto no haya nada crítico
  ...cambios,
});

function abrir(rol: "usuario" | "admin" = "usuario") {
  vi.mocked(apiAuth.yo).mockResolvedValue(crearSesion({ id: 3, rol: { id: 2, clave: rol, nombre: "Rol", alcance: "empresa" }, permisos: ["sst.ver"] }));
  return renderizar(<PausasActivas />, { conSesion: true });
}

const esperar = (ms: number) => new Promise((r) => setTimeout(r, ms));

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(apiSst.cerrar).mockResolvedValue({} as never);
});
afterEach(() => reiniciarBloqueos());

describe("pausas activas automáticas", () => {
  it("muestra la pausa a una persona a la que le aplica y registra que la realizó", async () => {
    vi.mocked(apiSst.estado).mockResolvedValue(estado());
    vi.mocked(apiSst.iniciar).mockResolvedValue({ mostrar: true, pausa: PAUSA });
    abrir();

    expect(await screen.findByText("Estiramiento de cuello", {}, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Siéntate recto")).toBeInTheDocument();
    expect(screen.getByText("Apoya bien la espalda")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /realicé la pausa/i }));
    await waitFor(() => expect(apiSst.cerrar).toHaveBeenCalledWith(77, "realizada", expect.any(Number)));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(apiSst.iniciar).toHaveBeenCalledTimes(1);
  }, 15000);

  it("permite omitirla y queda registrada como omitida", async () => {
    vi.mocked(apiSst.estado).mockResolvedValue(estado());
    vi.mocked(apiSst.iniciar).mockResolvedValue({ mostrar: true, pausa: PAUSA });
    abrir();

    await screen.findByText("Estiramiento de cuello", {}, { timeout: 5000 });
    await userEvent.click(screen.getByRole("button", { name: /omitir/i }));
    await waitFor(() => expect(apiSst.cerrar).toHaveBeenCalledWith(77, "omitida", expect.any(Number)));
  }, 15000);

  it("no muestra nada a quien no le aplica (administración)", async () => {
    vi.mocked(apiSst.estado).mockResolvedValue(estado({ aplica: false }));
    abrir("admin");

    await waitFor(() => expect(apiSst.estado).toHaveBeenCalled());
    await esperar(2200);
    expect(apiSst.iniciar).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  }, 15000);

  it("no interrumpe mientras hay un formulario o una operación crítica en curso", async () => {
    vi.mocked(apiSst.estado).mockResolvedValue(estado());
    vi.mocked(apiSst.iniciar).mockResolvedValue({ mostrar: true, pausa: PAUSA });
    const liberar = bloquearPausas();
    abrir();

    await waitFor(() => expect(apiSst.estado).toHaveBeenCalled());
    await esperar(2200);
    expect(apiSst.iniciar).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    liberar();
  }, 15000);

  it("si el servidor responde que todavía no toca, no muestra nada", async () => {
    vi.mocked(apiSst.estado).mockResolvedValue(estado());
    vi.mocked(apiSst.iniciar).mockResolvedValue({ mostrar: false, pausa: null, proxima_en: new Date(Date.now() + 30 * 60_000).toISOString(), motivo: "intervalo" });
    abrir();

    await waitFor(() => expect(apiSst.iniciar).toHaveBeenCalled(), { timeout: 5000 });
    await esperar(300);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  }, 15000);

  it("no hace nada si la función está desactivada por la administración", async () => {
    vi.mocked(apiSst.estado).mockResolvedValue(estado({ activo: false }));
    abrir();

    await waitFor(() => expect(apiSst.estado).toHaveBeenCalled());
    await esperar(2200);
    expect(apiSst.iniciar).not.toHaveBeenCalled();
  }, 15000);
});
