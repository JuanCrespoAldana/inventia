/** Etiquetas en español para los valores controlados que devuelve el backend. */

export type Tono = "neutral" | "accent" | "success" | "warning" | "danger";

export const ESTADO_STOCK: Record<string, { etiqueta: string; tono: Tono }> = {
  agotado: { etiqueta: "Agotado", tono: "danger" },
  bajo: { etiqueta: "Bajo", tono: "warning" },
  normal: { etiqueta: "Normal", tono: "success" },
  excesivo: { etiqueta: "Excesivo", tono: "accent" },
};

export const TIPO_MOVIMIENTO: Record<string, string> = {
  entrada: "Entrada",
  salida: "Salida",
  ajuste: "Ajuste",
  venta: "Venta",
  anulacion_venta: "Anulación de venta",
  traslado_salida: "Traslado (salida)",
  traslado_entrada: "Traslado (entrada)",
};

export const MOTIVO: Record<string, string> = {
  compra: "Compra",
  devolucion_cliente: "Devolución de cliente",
  inventario_inicial: "Inventario inicial",
  produccion: "Producción",
  perdida: "Pérdida",
  deterioro: "Deterioro",
  consumo_interno: "Consumo interno",
  devolucion_proveedor: "Devolución a proveedor",
  conteo_fisico: "Conteo físico",
  correccion: "Corrección",
  otro: "Otro",
};

export const ESTADO_VENTA: Record<string, { etiqueta: string; tono: Tono }> = {
  registrada: { etiqueta: "Registrada", tono: "success" },
  anulada: { etiqueta: "Anulada", tono: "danger" },
};

export const ESTADO_TRASLADO: Record<string, { etiqueta: string; tono: Tono }> = {
  solicitado: { etiqueta: "Solicitado", tono: "warning" },
  aprobado: { etiqueta: "Aprobado", tono: "accent" },
  confirmado: { etiqueta: "Confirmado", tono: "success" },
  rechazado: { etiqueta: "Rechazado", tono: "danger" },
  cancelado: { etiqueta: "Cancelado", tono: "neutral" },
};

export const TIPO_ALERTA: Record<string, string> = {
  inventario_bajo: "Inventario bajo",
  inventario_excesivo: "Inventario excesivo",
  riesgo_desabastecimiento: "Riesgo de desabastecimiento",
  requiere_revision: "Requiere revisión",
};

export const PRIORIDAD: Record<string, { etiqueta: string; tono: Tono }> = {
  critica: { etiqueta: "Crítica", tono: "danger" },
  alta: { etiqueta: "Alta", tono: "warning" },
  media: { etiqueta: "Media", tono: "accent" },
  baja: { etiqueta: "Baja", tono: "neutral" },
};

export const ESTADO_ALERTA: Record<string, { etiqueta: string; tono: Tono }> = {
  activa: { etiqueta: "Activa", tono: "warning" },
  resuelta: { etiqueta: "Resuelta", tono: "success" },
};

export const ESTADO_EJECUCION: Record<string, { etiqueta: string; tono: Tono }> = {
  en_cola: { etiqueta: "En cola", tono: "neutral" },
  ejecutando: { etiqueta: "Ejecutando", tono: "accent" },
  completada: { etiqueta: "Completada", tono: "success" },
  fallida: { etiqueta: "Fallida", tono: "danger" },
};

export const TIPO_RECOMENDACION: Record<string, string> = {
  reabastecimiento: "Reabastecimiento",
  traslado: "Traslado entre sedes",
};

export const ESTADO_RECOMENDACION: Record<string, { etiqueta: string; tono: Tono }> = {
  pendiente: { etiqueta: "Pendiente", tono: "warning" },
  aprobada: { etiqueta: "Aprobada", tono: "accent" },
  rechazada: { etiqueta: "Rechazada", tono: "danger" },
  ejecutada: { etiqueta: "Ejecutada", tono: "success" },
  reemplazada: { etiqueta: "Reemplazada", tono: "neutral" },
};

export const CONFIANZA: Record<string, { etiqueta: string; tono: Tono }> = {
  alta: { etiqueta: "Alta", tono: "success" },
  media: { etiqueta: "Media", tono: "warning" },
  baja: { etiqueta: "Baja", tono: "danger" },
};

export const UNIDADES_MEDIDA: Record<string, string> = {
  unidad: "Unidad",
  caja: "Caja",
  paquete: "Paquete",
  docena: "Docena",
  par: "Par",
  bolsa: "Bolsa",
  rollo: "Rollo",
  frasco: "Frasco",
  kg: "Kilogramo",
  g: "Gramo",
  lb: "Libra",
  litro: "Litro",
  ml: "Mililitro",
  metro: "Metro",
};

export const ALCANCE_ROL: Record<string, string> = {
  empresa: "Toda la empresa",
  sede: "Una sede",
};

export const RESULTADO_AUDITORIA: Record<string, { etiqueta: string; tono: Tono }> = {
  exitoso: { etiqueta: "Exitoso", tono: "success" },
  fallido: { etiqueta: "Fallido", tono: "danger" },
};

export const PARAMETROS_EMPRESA: { clave: string; etiqueta: string; ayuda: string; min: number; max: number }[] = [
  { clave: "plazo_entrega_dias", etiqueta: "Plazo de entrega (días)", ayuda: "Días que tarda en llegar un pedido a proveedor.", min: 0, max: 180 },
  { clave: "dias_seguridad", etiqueta: "Días de seguridad", ayuda: "Colchón adicional de existencias sobre el plazo de entrega.", min: 0, max: 90 },
  { clave: "dias_cobertura_objetivo", etiqueta: "Cobertura objetivo (días)", ayuda: "Días de ventas que se desea cubrir al reabastecer.", min: 1, max: 365 },
  { clave: "horizonte_dias", etiqueta: "Horizonte de predicción (días)", ayuda: "Días hacia adelante que se pronostica la demanda.", min: 1, max: 90 },
  { clave: "umbral_cobertura_alerta_dias", etiqueta: "Umbral de alerta por cobertura (días)", ayuda: "Se alerta cuando la cobertura estimada baja de este valor.", min: 1, max: 90 },
  { clave: "dias_sin_rotacion", etiqueta: "Días sin rotación", ayuda: "Días sin ventas para considerar un producto sin rotación.", min: 7, max: 730 },
  { clave: "dias_max_anulacion", etiqueta: "Días máximos para anular una venta", ayuda: "Pasado este plazo ya no se puede anular una venta.", min: 0, max: 365 },
];

export function etiqueta(mapa: Record<string, string>, clave: string | null | undefined): string {
  if (!clave) return "—";
  return mapa[clave] ?? clave.replaceAll("_", " ");
}

export function estado(mapa: Record<string, { etiqueta: string; tono: Tono }>, clave: string | null | undefined): { etiqueta: string; tono: Tono } {
  if (!clave) return { etiqueta: "—", tono: "neutral" };
  return mapa[clave] ?? { etiqueta: clave.replaceAll("_", " "), tono: "neutral" };
}
