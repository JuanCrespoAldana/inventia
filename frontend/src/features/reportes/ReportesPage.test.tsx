import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiReportes } from "@/api/analitica";
import { apiAuth } from "@/api/auth";
import { crearSesion, renderizar } from "@/test/utilidades";
import ReportesPage from "./ReportesPage";

vi.mock("@/api/auth", () => ({ apiAuth: { yo: vi.fn(), logout: vi.fn() } }));
vi.mock("@/api/analitica", () => ({ apiReportes: { catalogo: vi.fn(), vistaPrevia: vi.fn(), descargar: vi.fn() } }));
vi.mock("@/hooks/useCatalogos", () => ({
  useSedes: () => ({ data: [{ id: 1, nombre: "Sede Norte" }] }),
  useCategorias: () => ({ data: [] }),
}));

const vista = (total: number) => ({
  tipo: "predicciones",
  titulo: "Predicción de demanda",
  columnas: [
    { clave: "producto", titulo: "Producto", tipo: "texto" },
    { clave: "rmse", titulo: "RMSE (unid./día)", tipo: "decimal" },
    { clave: "mape", titulo: "MAPE (días con ventas)", tipo: "porcentaje" },
  ],
  filas: total ? [{ producto: "Bicicleta urbana", rmse: 2.25, mape: 0.3 }] : [],
  resumen: { "RMSE global (unid./día)": 2.5, "MAPE global (días con ventas)": 0.28 },
  total,
  truncado: false,
});

function abrir() {
  vi.mocked(apiAuth.yo).mockResolvedValue(crearSesion({ permisos: ["reportes.predicciones"] }));
  return renderizar(<ReportesPage />, { conSesion: true });
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(apiReportes.catalogo).mockResolvedValue([{ tipo: "predicciones", titulo: "Predicción de demanda", permiso: "reportes.predicciones" }] as never);
});

describe("reportes: descargas", () => {
  it("ofrece PDF, Excel y CSV, y el PDF pide el formato «pdf» al servidor", async () => {
    vi.mocked(apiReportes.vistaPrevia).mockResolvedValue(vista(1) as never);
    vi.mocked(apiReportes.descargar).mockResolvedValue("predicciones-2026-10-26.pdf");
    const u = userEvent.setup();
    abrir();

    const pdf = await screen.findByRole("button", { name: "PDF" });
    expect(screen.getByRole("button", { name: "Excel" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "CSV" })).toBeInTheDocument();
    await waitFor(() => expect(pdf).toBeEnabled());
    await u.click(pdf);

    expect(apiReportes.descargar).toHaveBeenCalledWith("predicciones", "pdf", expect.anything());
    expect(await screen.findByText(/predicciones-2026-10-26\.pdf descargado/)).toBeInTheDocument();
  });

  it("deshabilita las descargas cuando el reporte no tiene filas", async () => {
    vi.mocked(apiReportes.vistaPrevia).mockResolvedValue(vista(0) as never);
    abrir();
    expect(await screen.findByRole("button", { name: "PDF" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Excel" })).toBeDisabled();
  });

  it("muestra RMSE decimal y MAPE como porcentaje en la vista previa", async () => {
    vi.mocked(apiReportes.vistaPrevia).mockResolvedValue(vista(1) as never);
    abrir();
    expect(await screen.findByText("2,25")).toBeInTheDocument();
    expect(screen.getByText("30,0 %")).toBeInTheDocument();
    expect(screen.getByText("28,0 %")).toBeInTheDocument(); // MAPE global del resumen
    expect(screen.getByText("2,50")).toBeInTheDocument(); // RMSE global del resumen
  });
});

describe("reportes: paginado de la vista previa", () => {
  const vistaLarga = (n: number) => ({
    ...vista(1),
    filas: Array.from({ length: n }, (_, i) => ({ producto: `Producto ${i + 1}`, rmse: 1, mape: 0.1 })),
    total: n,
  });

  it("muestra 15 filas por página en lugar de alargar la pantalla con todas", async () => {
    vi.mocked(apiReportes.vistaPrevia).mockResolvedValue(vistaLarga(40) as never);
    const u = userEvent.setup();
    abrir();

    expect(await screen.findByText("Producto 15")).toBeInTheDocument();
    expect(screen.queryByText("Producto 16")).not.toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Paginación" });
    expect(within(nav).getByText("1–15 de 40")).toBeInTheDocument();
    expect(within(nav).getByText("Página 1 de 3")).toBeInTheDocument();

    await u.click(within(nav).getByRole("button", { name: "Página siguiente" }));
    expect(screen.getByText("Producto 16")).toBeInTheDocument();
    expect(screen.queryByText("Producto 15")).not.toBeInTheDocument();
    await u.click(within(nav).getByRole("button", { name: "Página siguiente" }));
    expect(screen.getByText("Producto 40")).toBeInTheDocument();
    expect(within(nav).getByText("31–40 de 40")).toBeInTheDocument();
  });

  it("vuelve a la primera página al cambiar un filtro", async () => {
    vi.mocked(apiReportes.vistaPrevia).mockResolvedValue(vistaLarga(40) as never);
    const u = userEvent.setup();
    abrir();

    const nav = await screen.findByRole("navigation", { name: "Paginación" });
    await u.click(within(nav).getByRole("button", { name: "Página siguiente" }));
    expect(within(nav).getByText("Página 2 de 3")).toBeInTheDocument();

    await u.selectOptions(screen.getByLabelText("Sede"), "1");
    await waitFor(() => expect(within(screen.getByRole("navigation", { name: "Paginación" })).getByText("Página 1 de 3")).toBeInTheDocument());
  });
});
