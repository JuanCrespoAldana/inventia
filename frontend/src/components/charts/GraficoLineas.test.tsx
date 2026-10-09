import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { GraficoLineas } from "./GraficoLineas";

const DIA = 86_400_000;
const puntos = (ys: number[], parcialUltimo = false) => ys.map((y, i) => ({ t: Date.UTC(2026, 9, 1) + i * DIA, y, parcial: parcialUltimo && i === ys.length - 1 }));

describe("<GraficoLineas>", () => {
  it("expone una descripción accesible y dibuja la serie", () => {
    const { container } = render(<GraficoLineas descripcion="Ventas diarias" capas={[{ nombre: "Ventas", puntos: puntos([1, 5, 3]), color: "#4C6FFF" }]} />);
    expect(screen.getByRole("img", { name: "Ventas diarias" })).toBeInTheDocument();
    expect(container.querySelectorAll("path[stroke='#4C6FFF']")).toHaveLength(1);
  });

  it("no dibuja nada sin datos", () => {
    const { container } = render(<GraficoLineas descripcion="Vacío" capas={[{ nombre: "x", puntos: [], color: "#fff" }]} />);
    expect(container.querySelector("svg")).toBeNull();
  });

  it("dibuja el día en curso como tramo punteado aparte, sin hundir la línea sólida", () => {
    const { container } = render(<GraficoLineas descripcion="Con día en curso" capas={[{ nombre: "Ventas", puntos: puntos([4, 6, 0], true), color: "#4C6FFF", area: true }]} />);
    const trazos = [...container.querySelectorAll("path[stroke='#4C6FFF']")];
    expect(trazos).toHaveLength(2);
    expect(trazos[0].getAttribute("d")?.match(/L/g)).toHaveLength(1); // solo los dos días completos
    expect(trazos[1].getAttribute("stroke-dasharray")).toBe("2 4");
  });

  it("usa un punto cuando solo hay un dato", () => {
    const { container } = render(<GraficoLineas descripcion="Un dato" capas={[{ nombre: "x", puntos: puntos([7]), color: "#4C6FFF" }]} />);
    expect(container.querySelector("circle")).not.toBeNull();
  });
});
