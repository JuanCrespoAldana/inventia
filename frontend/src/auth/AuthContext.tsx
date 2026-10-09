import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { apiAuth } from "@/api/auth";
import { EVENTO_SESION_EXPIRADA, guardarToken, limpiarToken, obtenerToken } from "@/lib/http";
import { tieneAlguno, tienePermiso } from "@/lib/permisos";
import type { Sesion, TokenSalida } from "@/types/api";

type Estado = "cargando" | "autenticado" | "anonimo";

interface ContextoAuth {
  estado: Estado;
  sesion: Sesion | null;
  /** true cuando la sesión terminó porque el token venció o fue revocado. */
  sesionExpirada: boolean;
  iniciarSesion: (email: string, password: string, persistente: boolean) => Promise<Sesion>;
  aplicarToken: (token: TokenSalida, persistente?: boolean) => void;
  cerrarSesion: () => Promise<void>;
  tiene: (...codigos: string[]) => boolean;
  tieneAlguno: (...codigos: string[]) => boolean;
}

const Contexto = createContext<ContextoAuth | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const cliente = useQueryClient();
  const [estado, setEstado] = useState<Estado>(() => (obtenerToken() ? "cargando" : "anonimo"));
  const [sesion, setSesion] = useState<Sesion | null>(null);
  const [sesionExpirada, setSesionExpirada] = useState(false);

  const terminar = useCallback(
    (expirada: boolean) => {
      limpiarToken();
      cliente.clear();
      setSesion(null);
      setEstado("anonimo");
      setSesionExpirada(expirada);
    },
    [cliente],
  );

  useEffect(() => {
    if (estado !== "cargando") return;
    let vigente = true;
    apiAuth
      .yo()
      .then((s) => {
        if (!vigente) return;
        setSesion(s);
        setEstado("autenticado");
      })
      .catch(() => vigente && terminar(false));
    return () => {
      vigente = false;
    };
  }, [estado, terminar]);

  useEffect(() => {
    const alExpirar = () => terminar(true);
    window.addEventListener(EVENTO_SESION_EXPIRADA, alExpirar);
    return () => window.removeEventListener(EVENTO_SESION_EXPIRADA, alExpirar);
  }, [terminar]);

  const aplicarToken = useCallback((t: TokenSalida, persistente = false) => {
    guardarToken(t.access_token, persistente);
    setSesion(t.usuario);
    setEstado("autenticado");
    setSesionExpirada(false);
  }, []);

  const iniciarSesion = useCallback(
    async (email: string, password: string, persistente: boolean) => {
      const t = await apiAuth.login(email, password);
      cliente.clear();
      aplicarToken(t, persistente);
      return t.usuario;
    },
    [aplicarToken, cliente],
  );

  const cerrarSesion = useCallback(async () => {
    try {
      await apiAuth.logout();
    } catch {
      /* si el servidor no responde igualmente se cierra la sesión local */
    }
    terminar(false);
  }, [terminar]);

  const valor = useMemo<ContextoAuth>(
    () => ({
      estado,
      sesion,
      sesionExpirada,
      iniciarSesion,
      aplicarToken,
      cerrarSesion,
      tiene: (...c) => tienePermiso(sesion, ...c),
      tieneAlguno: (...c) => tieneAlguno(sesion, ...c),
    }),
    [estado, sesion, sesionExpirada, iniciarSesion, aplicarToken, cerrarSesion],
  );

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): ContextoAuth {
  const ctx = useContext(Contexto);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}

/** Devuelve la sesión garantizando que existe (solo dentro de rutas protegidas). */
// eslint-disable-next-line react-refresh/only-export-components
export function useSesion(): Sesion {
  const { sesion } = useAuth();
  if (!sesion) throw new Error("useSesion requiere una sesión activa");
  return sesion;
}
