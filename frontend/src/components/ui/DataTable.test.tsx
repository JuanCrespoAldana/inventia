import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { Tabla } from "./DataTable";

const filas = Array.from({ length: 25 }, (_, i) => ({ id: i + 1, nombre: `Elemento ${i + 1}` }));
const columnas = [{ clave: "n", encabezado: "Nombre", celda: (f: { nombre: string }) => f.nombre }];

function tabla(paginar?: number, datos: typeof filas | undefined = filas) {
  return <Tabla descripcion="Elementos de prueba" idDe={(f) => f.id} filas={datos} columnas={columnas} paginar={paginar} />;
}

describe("<Tabla paginar>", () => {
  it("sin «paginar» muestra todas las filas y ningún paginador", () => {
    render(tabla());
    expect(screen.getAllByRole("row")).toHaveLength(26); // encabezado + 25
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  });

  it("con «paginar» muestra solo la página actual y permite avanzar y retroceder", async () => {
    const u = userEvent.setup();
    render(tabla(10));
    expect(screen.getAllByRole("row")).toHaveLength(11);
    expect(screen.getByText("Elemento 10")).toBeInTheDocument();
    expect(screen.queryByText("Elemento 11")).not.toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: /Paginación: Elementos de prueba/ });
    expect(within(nav).getByText("1–10 de 25")).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: "Página anterior" })).toBeDisabled();

    await u.click(within(nav).getByRole("button", { name: "Página siguiente" }));
    expect(screen.getByText("Elemento 11")).toBeInTheDocument();
    expect(screen.queryByText("Elemento 1")).not.toBeInTheDocument();
    await u.click(within(nav).getByRole("button", { name: "Página siguiente" }));
    expect(screen.getAllByRole("row")).toHaveLength(6); // la última página trae 5
    expect(within(nav).getByText("21–25 de 25")).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: "Página siguiente" })).toBeDisabled();
    await u.click(within(nav).getByRole("button", { name: "Página anterior" }));
    expect(screen.getByText("Elemento 11")).toBeInTheDocument();
  });

  it("con la lista vacía muestra el estado vacío y no el paginador", () => {
    render(tabla(10, []));
    expect(screen.getByText("Sin resultados")).toBeInTheDocument();
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  });
});
