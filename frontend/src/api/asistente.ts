import { get, post } from "@/lib/http";
import type { AyudaAsistente, ContextoAsistente, RespuestaAsistente } from "@/types/api";

export const apiAsistente = {
  /** `contexto` es lo que devolvió la respuesta anterior: permite entender «¿y en la Sede Sur?». */
  preguntar: (mensaje: string, contexto?: ContextoAsistente | null) => post<RespuestaAsistente>("/api/asistente/preguntar", { mensaje, contexto: contexto ?? null }),
  ayuda: () => get<AyudaAsistente>("/api/asistente/ayuda"),
};
