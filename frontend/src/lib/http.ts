import { create, isAxiosError, type AxiosRequestConfig } from "axios";
import { ErrorApi, normalizarError } from "./errors";

const CLAVE_TOKEN = "inventia.token";
export const EVENTO_SESION_EXPIRADA = "inventia:sesion-expirada";

/* El token vive en sessionStorage (se pierde al cerrar la pestaña). Si la persona marca «mantener la
   sesión» se guarda en localStorage. Ambos accesos están protegidos: pueden fallar en modo privado. */
function leer(almacen: () => Storage): string | null {
  try {
    return almacen().getItem(CLAVE_TOKEN);
  } catch {
    return null;
  }
}

export function obtenerToken(): string | null {
  return leer(() => sessionStorage) ?? leer(() => localStorage);
}

export function guardarToken(token: string, persistente = false): void {
  limpiarToken();
  try {
    (persistente ? localStorage : sessionStorage).setItem(CLAVE_TOKEN, token);
  } catch {
    /* sin almacenamiento disponible: la sesión dura mientras no se recargue la página */
    memoria = token;
  }
}

export function limpiarToken(): void {
  memoria = null;
  for (const almacen of [() => sessionStorage, () => localStorage]) {
    try {
      almacen().removeItem(CLAVE_TOKEN);
    } catch {
      /* ignorar */
    }
  }
}

let memoria: string | null = null;
const token = () => obtenerToken() ?? memoria;

export const http = create({
  baseURL: import.meta.env.VITE_API_URL ?? "",
  timeout: 30_000,
  headers: { Accept: "application/json" },
});

http.interceptors.request.use((config) => {
  const t = token();
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

const RUTAS_PUBLICAS = ["/api/auth/login", "/api/auth/forgot-password", "/api/auth/verify-reset-code", "/api/auth/reset-password", "/api/setup"];

http.interceptors.response.use(
  (respuesta) => respuesta,
  (error: unknown) => {
    const normalizado = normalizarError(error);
    const url = isAxiosError(error) ? (error.config?.url ?? "") : "";
    if (normalizado.status === 401 && token() && !RUTAS_PUBLICAS.some((r) => url.startsWith(r))) {
      limpiarToken();
      window.dispatchEvent(new CustomEvent(EVENTO_SESION_EXPIRADA));
    }
    return Promise.reject(normalizado);
  },
);

export type Parametros = Record<string, string | number | boolean | null | undefined>;

/** Elimina vacíos para no enviar `?q=&sede_id=` al backend. */
export function limpiarParametros(p?: Parametros): Record<string, string | number | boolean> | undefined {
  if (!p) return undefined;
  const salida: Record<string, string | number | boolean> = {};
  for (const [k, v] of Object.entries(p)) {
    if (v === undefined || v === null || v === "") continue;
    salida[k] = v;
  }
  return salida;
}

export async function get<T>(url: string, params?: Parametros, config?: AxiosRequestConfig): Promise<T> {
  return (await http.get<T>(url, { ...config, params: limpiarParametros(params) })).data;
}
export async function post<T>(url: string, cuerpo?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return (await http.post<T>(url, cuerpo, config)).data;
}
export async function put<T>(url: string, cuerpo?: unknown): Promise<T> {
  return (await http.put<T>(url, cuerpo)).data;
}
export async function patch<T>(url: string, cuerpo?: unknown): Promise<T> {
  return (await http.patch<T>(url, cuerpo)).data;
}
export async function del<T>(url: string): Promise<T> {
  return (await http.delete<T>(url)).data;
}

/** Descarga un archivo (CSV/XLSX) respetando el nombre que sugiere el servidor. */
export async function descargar(url: string, params?: Parametros): Promise<string> {
  const respuesta = await http.get<Blob>(url, { params: limpiarParametros(params), responseType: "blob" });
  const disposicion = String(respuesta.headers["content-disposition"] ?? "");
  const nombre = /filename="?([^";]+)"?/i.exec(disposicion)?.[1] ?? "descarga";
  const enlace = document.createElement("a");
  const objeto = URL.createObjectURL(respuesta.data);
  enlace.href = objeto;
  enlace.download = nombre;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  setTimeout(() => URL.revokeObjectURL(objeto), 10_000);
  return nombre;
}

export { ErrorApi };
