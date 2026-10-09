import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { agregarLinea, cantidadValida, EditorLineas, type Linea } from "./EditorLineas";

const producto = (id: number, nombre = `Producto ${id}`) => ({ id, codigo: `P-${id}`, nombre, unidad_medida: "unidad" }) as never;

function Contenedor({ inicial, ...props }: { inicial: Linea[]; conPrecio?: boolean; limitarADisponible?: boolean }) {
  const [lineas, setLineas] = useState(inicial);
  return <EditorLineas lineas={lineas} onChange={setLineas} {...props} />;
}

describe("agregarLinea", () => {
  it("agrega un producto nuevo con cantidad 1", () => {
    const r = agregarLinea([], { producto: producto(1), disponible: 5, precio: 1000 });
    expect(r).toHaveLength(1);
    expect(r[0]).toMatchObject({ cantidad: "1", precio: "", disponible: 5, precioLista: 1000 });
  });

  it("si el producto ya está, suma una unidad en lugar de duplicar la línea", () => {
    const una = agregarLinea([], { producto: producto(1) });
    const dos = agregarLinea(una, { producto: producto(1) });
    expect(dos).toHaveLength(1);
    expect(dos[0].cantidad).toBe("2");
  });
});

describe("cantidadValida", () => {
  const base: Linea = { producto: producto(1), cantidad: "3", precio: "", disponible: 5 };
  it("acepta enteros positivos dentro de lo disponible", () => expect(cantidadValida(base, true)).toBeNull());
  it("rechaza cero, decimales y vacío", () => {
    for (const c of ["0", "1.5", "", "abc", "-2"]) expect(cantidadValida({ ...base, cantidad: c }, false)).toMatch(/entera mayor que 0/);
  });
  it("rechaza lo que supera las existencias solo cuando se pide limitar", () => {
    expect(cantidadValida({ ...base, cantidad: "9" }, true)).toBe("Solo hay 5 disponibles");
    expect(cantidadValida({ ...base, cantidad: "9" }, false)).toBeNull();
  });
});

describe("<EditorLineas>", () => {
  it("muestra una guía cuando no hay productos", () => {
    render(<Contenedor inicial={[]} />);
    expect(screen.getByText(/agregue al menos un producto/i)).toBeInTheDocument();
  });

  it("permite editar la cantidad (solo dígitos) y quitar la línea", async () => {
    const u = userEvent.setup();
    render(<Contenedor inicial={[{ producto: producto(1, "Arroz"), cantidad: "1", precio: "", disponible: 10 }]} />);
    const campo = screen.getByLabelText("Cantidad de Arroz");
    await u.clear(campo);
    await u.type(campo, "4a7");
    expect(campo).toHaveValue("47");
    await u.click(screen.getByRole("button", { name: "Quitar Arroz" }));
    expect(screen.getByText(/agregue al menos un producto/i)).toBeInTheDocument();
  });

  it("avisa cuando se supera lo disponible", async () => {
    const u = userEvent.setup();
    render(<Contenedor limitarADisponible inicial={[{ producto: producto(1, "Arroz"), cantidad: "1", precio: "", disponible: 3 }]} />);
    const campo = screen.getByLabelText("Cantidad de Arroz");
    await u.clear(campo);
    await u.type(campo, "8");
    expect(screen.getByRole("alert")).toHaveTextContent("Solo hay 3 disponibles");
    expect(campo).toBeInvalid();
  });

  it("calcula el total usando el precio escrito o, si falta, el de lista", () => {
    render(
      <Contenedor
        conPrecio
        inicial={[
          { producto: producto(1, "A"), cantidad: "2", precio: "1500", precioLista: 1000 },
          { producto: producto(2, "B"), cantidad: "3", precio: "", precioLista: 200 },
        ]}
      />,
    );
    // 2 × 1.500 + 3 × 200 = 3.600
    expect(screen.getByText(/Total estimado/).parentElement).toHaveTextContent(/3\.600/);
  });
});
