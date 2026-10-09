import type { ReactNode } from "react";
import { act, renderHook } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { aBooleano, aNumero, useFiltros } from "./useFiltros";

const envoltorio = (ruta: string) => ({ children }: { children: ReactNode }) => <MemoryRouter initialEntries={[ruta]}>{children}</MemoryRouter>;

describe("useFiltros", () => {
  it("lee los filtros y la página desde la URL", () => {
    const { result } = renderHook(() => useFiltros({ q: "", estado: "" }), { wrapper: envoltorio("/x?q=arroz&pagina=3") });
    expect(result.current.filtros).toEqual({ q: "arroz", estado: "" });
    expect(result.current.pagina).toBe(3);
    expect(result.current.hayFiltros).toBe(true);
  });

  it("cambiar un filtro reinicia la página y limpiar quita todo", () => {
    const { result } = renderHook(() => useFiltros({ q: "", estado: "" }), { wrapper: envoltorio("/x?pagina=4") });
    act(() => result.current.cambiar({ estado: "activo" }));
    expect(result.current.filtros.estado).toBe("activo");
    expect(result.current.pagina).toBe(1);
    act(() => result.current.limpiar());
    expect(result.current.hayFiltros).toBe(false);
  });

  it("un valor igual al inicial no ensucia la URL", () => {
    const { result } = renderHook(() => useFiltros({ q: "" }), { wrapper: envoltorio("/x?q=a") });
    act(() => result.current.cambiar({ q: "" }));
    expect(result.current.hayFiltros).toBe(false);
  });

  it("convierte filtros de texto para la API", () => {
    expect(aNumero("12")).toBe(12);
    expect(aNumero("")).toBe("");
    expect(aNumero("abc")).toBe("");
    expect(aBooleano("true")).toBe(true);
    expect(aBooleano("false")).toBe(false);
    expect(aBooleano("")).toBe("");
  });
});
