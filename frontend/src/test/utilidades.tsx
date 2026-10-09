import type { ReactElement, ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "@/auth/AuthContext";
import { ToastProvider } from "@/components/ui/Toast";
import { guardarToken } from "@/lib/http";
import type { Sesion } from "@/types/api";

/** Sesión de ejemplo; `permisos` y `rol` se pueden sobrescribir según el caso. */
export function crearSesion(cambios: Partial<Sesion> = {}): Sesion {
  return {
    id: 1,
    nombre: "Ana Pérez",
    email: "ana@empresa.com",
    empresa_id: 1,
    empresa_nombre: "Comercial Andina",
    rol: { id: 1, clave: "admin", nombre: "Administrador", alcance: "empresa" },
    sede: null,
    permisos: [],
    debe_cambiar_password: false,
    ...cambios,
  } as Sesion;
}

export function nuevoCliente() {
  return new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } } });
}

interface Opciones {
  ruta?: string;
  /** Si se indica, simula una sesión ya iniciada (el token y /api/auth/me se resuelven con el mock de `apiAuth.yo`). */
  conSesion?: boolean;
}

/** Renderiza con enrutador, caché de consultas, avisos y autenticación reales. */
export function renderizar(ui: ReactElement, { ruta = "/", conSesion = false }: Opciones = {}) {
  if (conSesion) guardarToken("token-de-prueba");
  const cliente = nuevoCliente();
  const Envoltorio = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={cliente}>
      <MemoryRouter initialEntries={[ruta]}>
        <ToastProvider>
          <AuthProvider>{children}</AuthProvider>
        </ToastProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
  return { cliente, ...render(ui, { wrapper: Envoltorio }) };
}
