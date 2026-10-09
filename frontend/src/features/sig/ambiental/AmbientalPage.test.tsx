import { screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiAuth } from "@/api/auth";
import { apiAmbiental } from "@/api/sig";
import { crearSesion, renderizar } from "@/test/utilidades";
import type { ResumenAmbiental } from "@/types/api";
import AmbientalPage from "./AmbientalPage";

vi.mock("@/api/auth", () => ({ apiAuth: { yo: vi.fn(), logout: vi.fn() } }));
vi.mock("@/api/sig", () => ({ apiAmbiental: { resumen: vi.fn(), registros: vi.fn(), configuracion: vi.fn() } }));

const cifras = (unidades: number, co2: number, sin = 0) => ({ unidades, co2_estimado_kg: co2, unidades_sin_parametrizar: sin });

function resumen(estado: ResumenAmbiental["parametrizacion"]["estado"], co2: number, sin = 0): ResumenAmbiental {
  return {
    anio: 2026,
    parametrizacion: {
      estado,
      mensaje: estado === "completa" ? "Parametrización completa: el CO₂ evitado es una estimación." : "Pendiente de parametrización: se cuentan los vehículos vendidos, pero el CO₂ no se puede estimar.",
      categorias_vehiculo: 1,
      categorias_parametrizadas: estado === "completa" ? 1 : 0,
      factor_red_definido: estado === "completa",
    },
    mes_actual: cifras(3, co2 ? 880 : 0, sin),
    anio_seleccionado: cifras(12, co2, sin),
    acumulado: cifras(20, co2 ? co2 + 500 : 0, sin),
    meses: Array.from({ length: 12 }, (_, i) => ({ mes: i + 1, ...cifras(i === 9 ? 3 : 0, 0) })),
    anios: [{ anio: 2026, ...cifras(12, co2, sin) }],
    por_tipo: [{ tipo_vehiculo: "bicicleta_electrica", ...cifras(12, co2, sin) }],
    anios_disponibles: [2026],
  } as ResumenAmbiental;
}

function abrir(permisos: string[]) {
  vi.mocked(apiAuth.yo).mockResolvedValue(crearSesion({ permisos }));
  return renderizar(<AmbientalPage />, { conSesion: true });
}

beforeEach(() => {
  vi.resetAllMocks();
});

describe("gestión ambiental", () => {
  it("sin parametrizar cuenta los vehículos pero NO inventa CO₂: muestra «pendiente de parametrización»", async () => {
    vi.mocked(apiAmbiental.resumen).mockResolvedValue(resumen("pendiente", 0));
    abrir(["ambiental.ver"]);

    const vehiculos = await screen.findByRole("region", { name: /Vehículos vendidos/ });
    // los tres indicadores de vehículos son datos reales
    expect(within(vehiculos).getByText("20")).toBeInTheDocument();
    expect(within(vehiculos).getByText("12")).toBeInTheDocument();
    expect(within(vehiculos).getByText("3")).toBeInTheDocument();
    // y los tres de CO₂ quedan pendientes, sin ninguna cifra
    const co2 = screen.getByRole("region", { name: /CO₂ evitado/ });
    expect(within(co2).getAllByText("Pendiente de parametrización")).toHaveLength(3);
    expect(within(co2).queryByText(/\d\s(kg|t)\b/)).not.toBeInTheDocument(); // ninguna cifra de CO₂
    expect(screen.getAllByText(/Pendiente de parametrización/).length).toBeGreaterThanOrEqual(4);
  });

  it("con parámetros distingue lo real de lo estimado y muestra el CO₂ calculado", async () => {
    vi.mocked(apiAmbiental.resumen).mockResolvedValue(resumen("completa", 3520));
    abrir(["ambiental.ver"]);

    const vehiculos = await screen.findByRole("region", { name: /Vehículos vendidos/ });
    expect(within(vehiculos).getByText("Dato real")).toBeInTheDocument();
    const co2 = screen.getByRole("region", { name: /CO₂ evitado/ });
    expect(within(co2).getByText("Estimación")).toBeInTheDocument();
    expect(within(co2).getByText("3,52 t")).toBeInTheDocument(); // año
    expect(within(co2).getByText("4,02 t")).toBeInTheDocument(); // acumulado
    expect(within(co2).getByText("880 kg")).toBeInTheDocument(); // mes actual
  });

  it("avisa de las unidades que quedaron fuera de la estimación cuando la parametrización es parcial", async () => {
    vi.mocked(apiAmbiental.resumen).mockResolvedValue(resumen("parcial", 1000, 4));
    abrir(["ambiental.ver"]);

    expect(await screen.findAllByText(/No incluye 4 vehículos sin parametrizar/)).not.toHaveLength(0);
  });

  it("la configuración solo se ofrece a quien puede configurar", async () => {
    vi.mocked(apiAmbiental.resumen).mockResolvedValue(resumen("pendiente", 0));
    const { unmount } = abrir(["ambiental.ver"]);
    const pestanas = await screen.findByRole("tablist");
    expect(within(pestanas).queryByRole("tab", { name: "Configuración" })).not.toBeInTheDocument();
    expect(within(pestanas).getByRole("tab", { name: "Historial" })).toBeInTheDocument();
    expect(within(pestanas).getByRole("tab", { name: "Metodología" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /ir a la configuración/i })).not.toBeInTheDocument();
    unmount();

    abrir(["ambiental.ver", "ambiental.configurar"]);
    expect(await screen.findByRole("tab", { name: "Configuración" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /ir a la configuración/i })).toBeInTheDocument();
  });
});
