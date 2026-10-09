import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { bloquearPausas, hayBloqueos, reiniciarBloqueos, useBloquearPausas, useHayBloqueos } from "./bloqueoPausas";

afterEach(() => reiniciarBloqueos());

describe("bloqueo de pausas activas", () => {
  it("cuenta los bloqueos y los libera de uno en uno", () => {
    const a = bloquearPausas();
    const b = bloquearPausas();
    expect(hayBloqueos()).toBe(true);
    a();
    expect(hayBloqueos()).toBe(true);
    b();
    expect(hayBloqueos()).toBe(false);
  });

  it("liberar dos veces el mismo bloqueo no libera el de otro", () => {
    const a = bloquearPausas();
    const b = bloquearPausas();
    a();
    a();
    expect(hayBloqueos()).toBe(true);
    b();
    expect(hayBloqueos()).toBe(false);
  });

  it("useBloquearPausas bloquea mientras está activo y libera al desmontar", () => {
    const { rerender, unmount } = renderHook(({ activo }) => useBloquearPausas(activo), { initialProps: { activo: false } });
    expect(hayBloqueos()).toBe(false);
    rerender({ activo: true });
    expect(hayBloqueos()).toBe(true);
    rerender({ activo: false });
    expect(hayBloqueos()).toBe(false);
    rerender({ activo: true });
    unmount();
    expect(hayBloqueos()).toBe(false);
  });

  it("useHayBloqueos reacciona a los cambios", () => {
    const { result } = renderHook(() => useHayBloqueos());
    expect(result.current).toBe(false);
    let liberar = () => {};
    act(() => {
      liberar = bloquearPausas();
    });
    expect(result.current).toBe(true);
    act(() => liberar());
    expect(result.current).toBe(false);
  });
});
