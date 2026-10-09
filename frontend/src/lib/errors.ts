import { isAxiosError } from "axios";

/** Error normalizado de la API: mensaje legible en español, código estable y errores por campo. */
export class ErrorApi extends Error {
  readonly status: number;
  readonly codigo: string;
  readonly campos: Record<string, string>;
  readonly requestId?: string;

  constructor(mensaje: string, opciones: { status?: number; codigo?: string; campos?: Record<string, string>; requestId?: string } = {}) {
    super(mensaje);
    this.name = "ErrorApi";
    this.status = opciones.status ?? 0;
    this.codigo = opciones.codigo ?? "desconocido";
    this.campos = opciones.campos ?? {};
    this.requestId = opciones.requestId;
  }
}

interface CuerpoError {
  detail?: unknown;
  codigo?: string;
  request_id?: string;
  errores?: { campo?: string; mensaje?: string }[];
}

const MENSAJE_RED = "No se pudo conectar con el servidor. Verifique su conexión e inténtelo de nuevo.";
const MENSAJE_GENERICO = "Ocurrió un error inesperado. Inténtelo de nuevo.";

export function normalizarError(error: unknown): ErrorApi {
  if (error instanceof ErrorApi) return error;
  if (isAxiosError(error)) {
    if (!error.response) {
      return new ErrorApi(error.code === "ECONNABORTED" ? "La solicitud tardó demasiado. Inténtelo de nuevo." : MENSAJE_RED, {
        codigo: "sin_conexion",
      });
    }
    const { status, data } = error.response;
    const cuerpo = (typeof data === "object" && data !== null ? data : {}) as CuerpoError;
    const campos: Record<string, string> = {};
    for (const e of cuerpo.errores ?? []) {
      if (e.campo && e.mensaje && !(e.campo in campos)) campos[e.campo] = e.mensaje;
    }
    const detalle = typeof cuerpo.detail === "string" ? cuerpo.detail : undefined;
    let mensaje = detalle;
    if (!mensaje) {
      mensaje =
        status === 429
          ? "Demasiados intentos. Espere un momento antes de volver a intentarlo."
          : status >= 500
            ? "El servidor tuvo un problema al procesar la solicitud. Inténtelo de nuevo en unos minutos."
            : MENSAJE_GENERICO;
    }
    return new ErrorApi(mensaje, { status, codigo: cuerpo.codigo ?? `http_${status}`, campos, requestId: cuerpo.request_id });
  }
  if (error instanceof Error) return new ErrorApi(error.message || MENSAJE_GENERICO);
  return new ErrorApi(MENSAJE_GENERICO);
}

export function mensajeDeError(error: unknown): string {
  return normalizarError(error).message;
}
