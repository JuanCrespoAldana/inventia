import { screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiPredicciones } from "@/api/analitica";
import { renderizar } from "@/test/utilidades";
import type { SerieDemanda } from "@/types/api";
import { DetalleSerieModal } from "./DetalleSerieModal";

vi.mock("@/api/analitica", () => ({ apiPredicciones: { serie: vi.fn() } }));

function serie(metricas: Record<string, unknown>): SerieDemanda {
  return {
    producto: { id: 1, codigo: "BIC-01", nombre: "Bicicleta urbana" },
    sede: { id: 1, nombre: "Sede Norte" },
    modelo: "ets_semanal",
    confianza: "alta",
    demanda_estimada: 42,
    limite_inferior: 30,
    limite_superior: 55,
    advertencias: [],
    motivo_sin_prediccion: null,
    historial: [["2026-09-01", 3]],
    pronostico: [["2026-09-02", 4]],
    metricas,
  } as unknown as SerieDemanda;
}

beforeEach(() => {
  vi.resetAllMocks();
});

describe("detalle de una predicción: métricas de error", () => {
  it("muestra WAPE, RMSE y MAPE del modelo y de cada candidato", async () => {
    vi.mocked(apiPredicciones.serie).mockResolvedValue(
      serie({
        wape: 0.25,
        wape_linea_base: 0.4,
        mae: 1.5,
        rmse: 2.25,
        mape: 0.3,
        mejora_vs_linea_base_pct: 37.5,
        n_pliegues: 3,
        dias_validados: 21,
        candidatos: [
          { modelo: "ets_semanal", avanzado: true, wape: 0.25, mae: 1.5, rmse: 2.25, mape: 0.3 },
          { modelo: "media_28", avanzado: false, wape: 0.4, mae: 2.4, rmse: 3.1, mape: null },
        ],
      }),
    );
    renderizar(<DetalleSerieModal sedeId={1} productoId={1} onCerrar={() => {}} />);

    expect(await screen.findByText(/RMSE 2,25 u\.\/día/)).toBeInTheDocument();
    expect(screen.getByText(/MAPE 30/)).toBeInTheDocument();

    const tabla = screen.getByRole("table", { name: /Error de cada modelo candidato/ });
    expect(within(tabla).getByRole("columnheader", { name: "RMSE (u./día)" })).toBeInTheDocument();
    expect(within(tabla).getByRole("columnheader", { name: "MAPE" })).toBeInTheDocument();
    const filas = within(tabla).getAllByRole("row");
    // la línea base no tuvo días con ventas en esta validación: el MAPE no existe y se muestra «—», no 0 %
    expect(within(filas[2]).getAllByRole("cell").at(-1)).toHaveTextContent("—");
    expect(within(filas[1]).getAllByRole("cell").at(-1)).toHaveTextContent("30");
  });

  it("no falla con ejecuciones antiguas que no guardaron RMSE ni MAPE", async () => {
    vi.mocked(apiPredicciones.serie).mockResolvedValue(
      serie({ wape: 0.25, wape_linea_base: 0.4, mae: 1.5, candidatos: [{ modelo: "media_28", avanzado: false, wape: 0.4, mae: 2.4 }] }),
    );
    renderizar(<DetalleSerieModal sedeId={1} productoId={1} onCerrar={() => {}} />);

    expect(await screen.findByText(/RMSE — · MAPE —/)).toBeInTheDocument();
  });
});
