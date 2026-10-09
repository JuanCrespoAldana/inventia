import { get, post } from "@/lib/http";
import type { ConfiguracionInicial, EstadoInstalacion, Sesion, TokenSalida } from "@/types/api";

export const apiAuth = {
  estadoInstalacion: () => get<EstadoInstalacion>("/api/setup/estado"),
  configurar: (datos: ConfiguracionInicial) => post<TokenSalida>("/api/setup", datos),
  login: (email: string, password: string) => post<TokenSalida>("/api/auth/login", { email, password }),
  logout: () => post<{ mensaje: string }>("/api/auth/logout"),
  yo: () => get<Sesion>("/api/auth/me"),
  cambiarPassword: (password_actual: string, nueva_password: string) => post<TokenSalida>("/api/auth/cambiar-password", { password_actual, nueva_password }),
  olvide: (email: string) => post<{ mensaje: string }>("/api/auth/forgot-password", { email }),
  verificarCodigo: (email: string, codigo: string) => post<{ session_token: string }>("/api/auth/verify-reset-code", { email, codigo }),
  restablecer: (session_token: string, nueva_password: string) => post<{ mensaje: string }>("/api/auth/reset-password", { session_token, nueva_password }),
};
