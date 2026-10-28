import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { usePaginacionLocal } from "./usePaginacionLocal";

const numeros = (n: number) => Array.from({ length: n }, (_, i) => i + 1);

describe("usePaginacionLocal", () => {
  it("entrega solo la página pedida y calcula el total de páginas", () => {
    const { result } = renderHook(() => usePaginacionLocal(numeros(25), 10));
    expect(result.current.visibles).toEqual(numeros(10));
    expect(result.current.paginas).toBe(3);
    act(() => result.current.irAPagina(3));
    expect(result.current.visibles).toEqual([21, 22, 23, 24, 25]);
    expect(result.current.paginacion).toMatchObject({ pagina: 3, paginas: 3, total: 25, tamano: 10 });
  });

  it("vuelve a la página 1 cuando cambia la clave de reinicio", () => {
    const { result, rerender } = renderHook(({ clave }) => usePaginacionLocal(numeros(25), 10, clave), { initialProps: { clave: "a" } });
    act(() => result.current.irAPagina(2));
    expect(result.current.pagina).toBe(2);
    rerender({ clave: "b" });
    expect(result.current.pagina).toBe(1);
  });

  it("si la lista se acorta, queda en la última página que existe", () => {
    const { result, rerender } = renderHook(({ n }) => usePaginacionLocal(numeros(n), 10), { initialProps: { n: 25 } });
    act(() => result.current.irAPagina(3));
    rerender({ n: 12 });
    expect(result.current.pagina).toBe(2);
    expect(result.current.visibles).toEqual([11, 12]);
  });

  it("no pasa de los límites aunque se pida una página inexistente", () => {
    const { result } = renderHook(() => usePaginacionLocal(numeros(5), 10));
    act(() => result.current.irAPagina(9));
    expect(result.current.pagina).toBe(1);
    act(() => result.current.irAPagina(-2));
    expect(result.current.pagina).toBe(1);
  });

  it("sin tamaño devuelve la lista completa, y sin datos devuelve una lista vacía", () => {
    expect(renderHook(() => usePaginacionLocal(numeros(25), undefined)).result.current.visibles).toHaveLength(25);
    const vacio = renderHook(() => usePaginacionLocal(undefined, 10)).result.current;
    expect(vacio.visibles).toEqual([]);
    expect(vacio.paginacion).toMatchObject({ pagina: 1, paginas: 1, total: 0 });
  });
});
