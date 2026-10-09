import { useMemo, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Download, FileSpreadsheet } from "lucide-react";
import { apiReportes, type FiltroReporte } from "@/api/analitica";
import { useAuth } from "@/auth/AuthContext";
import { Aviso } from "@/components/ui/Aviso";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { EstadoError, EstadoVacio } from "@/components/ui/EstadoVacio";
import { FiltroFecha, FiltroSelect } from "@/components/ui/Field";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { useCategorias, useSedes } from "@/hooks/useCatalogos";
import { useToast } from "@/components/ui/Toast";
import { cn } from "@/lib/cn";
import { mensajeDeError } from "@/lib/errors";
import {
  CONFIANZA,
  ESTADO_ALERTA,
  ESTADO_RECOMENDACION,
  ESTADO_STOCK,
  ESTADO_TRASLADO,
  ESTADO_VENTA,
  MOTIVO,
  PRIORIDAD,
  TIPO_ALERTA,
  TIPO_MOVIMIENTO,
  TIPO_RECOMENDACION,
} from "@/lib/etiquetas";
import { decimal, entero, fecha, fechaHora, moneda, porcentaje } from "@/lib/format";
import type { ColumnaReporte } from "@/types/api";

interface Config {
  fechas?: boolean;
  categoria?: boolean;
  estados?: Record<string, { etiqueta: string }>;
  clase?: { etiqueta: string; opciones: Record<string, string> };
}

const CONFIG: Record<string, Config> = {
  inventario: { categoria: true, estados: ESTADO_STOCK },
  ventas: { fechas: true, estados: ESTADO_VENTA },
  movimientos: { fechas: true, clase: { etiqueta: "Tipo de movimiento", opciones: TIPO_MOVIMIENTO } },
  traslados: { fechas: true, estados: ESTADO_TRASLADO },
  alertas: { estados: ESTADO_ALERTA, clase: { etiqueta: "Tipo de alerta", opciones: TIPO_ALERTA } },
  predicciones: {},
  recomendaciones: { estados: ESTADO_RECOMENDACION, clase: { etiqueta: "Tipo de recomendación", opciones: TIPO_RECOMENDACION } },
};

const MAPAS_TEXTO: Record<string, Record<string, string>> = {
  tipo: { ...TIPO_MOVIMIENTO, ...TIPO_ALERTA, ...TIPO_RECOMENDACION },
  motivo: MOTIVO,
  prioridad: Object.fromEntries(Object.entries(PRIORIDAD).map(([k, v]) => [k, v.etiqueta])),
  confianza: Object.fromEntries(Object.entries(CONFIANZA).map(([k, v]) => [k, v.etiqueta])),
};
const ESTADOS_POR_REPORTE: Record<string, Record<string, { etiqueta: string }>> = {
  inventario: ESTADO_STOCK,
  ventas: ESTADO_VENTA,
  traslados: ESTADO_TRASLADO,
  alertas: ESTADO_ALERTA,
  recomendaciones: ESTADO_RECOMENDACION,
};

function celda(c: ColumnaReporte, valor: unknown, reporte: string): string {
  if (valor === null || valor === undefined || valor === "") return "—";
  switch (c.tipo) {
    case "entero": return entero(Number(valor));
    case "dinero": return moneda(Number(valor));
    case "decimal": return decimal(Number(valor), 2);
    case "porcentaje": return porcentaje(Number(valor) * 100);
    case "fecha": return fecha(String(valor));
    case "fechahora": return fechaHora(String(valor));
    default: {
      const texto = String(valor);
      if (c.clave === "estado") return ESTADOS_POR_REPORTE[reporte]?.[texto]?.etiqueta ?? texto;
      return MAPAS_TEXTO[c.clave]?.[texto] ?? texto;
    }
  }
}

/** Los resúmenes del backend son pares «etiqueta: valor»; la etiqueta indica si es dinero o proporción. */
function resumenLegible(clave: string, valor: unknown): string {
  if (typeof valor === "number") {
    if (/^(valor|total vendido)/i.test(clave)) return moneda(valor);
    if (/wape/i.test(clave)) return porcentaje(valor * 100);
    return Number.isInteger(valor) ? entero(valor) : decimal(valor, 2);
  }
  return String(valor ?? "—");
}

export default function ReportesPage() {
  const { sesion } = useAuth();
  const toast = useToast();
  const sedes = useSedes(false);
  const categorias = useCategorias(false);
  const catalogo = useQuery({ queryKey: ["reportes", "catalogo"], queryFn: apiReportes.catalogo, staleTime: 300_000 });
  const [elegido, setElegido] = useState<string | null>(null);
  const [filtros, setFiltros] = useState<Record<string, string>>({});
  const [descargando, setDescargando] = useState<"csv" | "xlsx" | null>(null);
  const tipo = elegido ?? catalogo.data?.[0]?.tipo ?? null;
  const config = tipo ? (CONFIG[tipo] ?? {}) : {};
  const verSedes = sesion?.rol.alcance === "empresa";

  const parametros: FiltroReporte = useMemo(
    () => ({
      sede_id: filtros.sede_id ? Number(filtros.sede_id) : "",
      categoria_id: filtros.categoria_id ? Number(filtros.categoria_id) : "",
      desde: filtros.desde ?? "",
      hasta: filtros.hasta ?? "",
      estado: filtros.estado ?? "",
      clase: filtros.clase ?? "",
    }),
    [filtros],
  );

  const vista = useQuery({
    queryKey: ["reportes", tipo, parametros],
    queryFn: () => apiReportes.vistaPrevia(tipo!, parametros),
    enabled: tipo !== null,
    placeholderData: keepPreviousData,
  });

  function cambiarFiltro(clave: string, valor: string) {
    setFiltros((f) => ({ ...f, [clave]: valor }));
  }
  function elegirTipo(t: string) {
    setElegido(t);
    setFiltros({});
  }

  async function descargar(formato: "csv" | "xlsx") {
    if (!tipo) return;
    setDescargando(formato);
    try {
      const nombre = await apiReportes.descargar(tipo, formato, parametros);
      toast.exito(`Archivo ${nombre} descargado.`);
    } catch (e) {
      toast.error(mensajeDeError(e));
    } finally {
      setDescargando(null);
    }
  }

  const r = vista.data;
  const hayFiltros = Object.values(filtros).some(Boolean);

  return (
    <>
      <EncabezadoPagina titulo="Reportes" descripcion="Consulte una vista previa y descargue el informe en CSV o Excel. Cada descarga queda registrada en la auditoría." />
      {catalogo.isPending && <Skeleton className="h-48" />}
      {catalogo.isError && <Card><EstadoError error={catalogo.error} onReintentar={() => catalogo.refetch()} /></Card>}
      {catalogo.data && catalogo.data.length === 0 && <Card><EstadoVacio titulo="Sin reportes disponibles" descripcion="Su rol no incluye permisos de reportes." /></Card>}
      {catalogo.data && catalogo.data.length > 0 && (
        <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
          <nav aria-label="Tipos de reporte" className="h-fit min-w-0">
            <ul className="flex gap-2 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible lg:pb-0">
              {catalogo.data.map((t) => (
                <li key={t.tipo} className="shrink-0">
                  <button
                    type="button"
                    onClick={() => elegirTipo(t.tipo)}
                    aria-current={tipo === t.tipo ? "true" : undefined}
                    className={cn(
                      "w-full whitespace-nowrap rounded-(--radius-control) border px-4 py-2.5 text-left text-sm font-medium transition lg:whitespace-normal",
                      tipo === t.tipo ? "border-accent/50 bg-accent-dim text-accent-light" : "border-line bg-surface text-ink-dim hover:border-line-strong hover:text-ink",
                    )}
                  >
                    {t.titulo}
                  </button>
                </li>
              ))}
            </ul>
          </nav>

          <Card className="min-w-0">
            <CardHeader
              titulo={r?.titulo ?? catalogo.data.find((t) => t.tipo === tipo)?.titulo ?? "Reporte"}
              descripcion={r ? `${entero(r.total)} ${r.total === 1 ? "registro" : "registros"}` : undefined}
              accion={
                <div className="flex flex-wrap gap-2">
                  <Button variante="secondary" tamano="sm" icono={<Download className="size-4" aria-hidden />} cargando={descargando === "csv"} disabled={descargando !== null || !r?.total} onClick={() => descargar("csv")}>
                    CSV
                  </Button>
                  <Button tamano="sm" icono={<FileSpreadsheet className="size-4" aria-hidden />} cargando={descargando === "xlsx"} disabled={descargando !== null || !r?.total} onClick={() => descargar("xlsx")}>
                    Excel
                  </Button>
                </div>
              }
            />
            <div className="flex flex-wrap items-center gap-2.5 border-b border-line px-5 py-3.5">
              {verSedes && (
                <FiltroSelect etiqueta="Sede" value={filtros.sede_id ?? ""} onChange={(e) => cambiarFiltro("sede_id", e.target.value)}>
                  <option value="">Todas las sedes</option>
                  {sedes.data?.map((s) => (
                    <option key={s.id} value={s.id}>{s.nombre}</option>
                  ))}
                </FiltroSelect>
              )}
              {config.categoria && (
                <FiltroSelect etiqueta="Categoría" value={filtros.categoria_id ?? ""} onChange={(e) => cambiarFiltro("categoria_id", e.target.value)}>
                  <option value="">Todas las categorías</option>
                  {categorias.data?.map((c) => (
                    <option key={c.id} value={c.id}>{c.nombre}</option>
                  ))}
                </FiltroSelect>
              )}
              {config.estados && (
                <FiltroSelect etiqueta="Estado" value={filtros.estado ?? ""} onChange={(e) => cambiarFiltro("estado", e.target.value)}>
                  <option value="">Todos los estados</option>
                  {Object.entries(config.estados).map(([k, e]) => (
                    <option key={k} value={k}>{e.etiqueta}</option>
                  ))}
                </FiltroSelect>
              )}
              {config.clase && (
                <FiltroSelect etiqueta={config.clase.etiqueta} value={filtros.clase ?? ""} onChange={(e) => cambiarFiltro("clase", e.target.value)}>
                  <option value="">{config.clase.etiqueta}: todos</option>
                  {Object.entries(config.clase.opciones).map(([k, n]) => (
                    <option key={k} value={k}>{n}</option>
                  ))}
                </FiltroSelect>
              )}
              {config.fechas && (
                <>
                  <FiltroFecha etiqueta="Desde" value={filtros.desde ?? ""} max={filtros.hasta || undefined} onChange={(e) => cambiarFiltro("desde", e.target.value)} />
                  <FiltroFecha etiqueta="Hasta" value={filtros.hasta ?? ""} min={filtros.desde || undefined} onChange={(e) => cambiarFiltro("hasta", e.target.value)} />
                </>
              )}
              {hayFiltros && (
                <Button variante="ghost" tamano="sm" onClick={() => setFiltros({})}>Limpiar filtros</Button>
              )}
            </div>

            {vista.isError && !r && <EstadoError error={vista.error} onReintentar={() => vista.refetch()} />}
            {vista.isPending && <div className="p-5"><Skeleton className="h-56" /></div>}
            {r && (
              <div className={cn(vista.isFetching && "opacity-60 transition-opacity")}>
                {Object.keys(r.resumen).length > 0 && (
                  <dl className="grid gap-x-8 gap-y-3 border-b border-line px-5 py-4 sm:grid-cols-2 lg:grid-cols-4">
                    {Object.entries(r.resumen).map(([k, v]) => (
                      <div key={k}>
                        <dt className="text-xs text-ink-faint">{k}</dt>
                        <dd className="tabular mt-0.5 text-sm font-semibold text-ink">{resumenLegible(k, v)}</dd>
                      </div>
                    ))}
                  </dl>
                )}
                {r.truncado && <div className="px-5 pt-4"><Aviso tipo="aviso">La vista previa muestra solo los primeros {r.filas.length} de {entero(r.total)} registros. La descarga incluye todos.</Aviso></div>}
                {r.filas.length === 0 ? (
                  <EstadoVacio titulo="Sin datos para este reporte" descripcion="Pruebe con otros filtros o con un rango de fechas más amplio." />
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-max border-collapse text-sm">
                      <caption className="sr-only">{r.titulo}</caption>
                      <thead>
                        <tr className="border-b border-line text-xs uppercase tracking-wide text-ink-faint">
                          {r.columnas.map((c) => (
                            <th key={c.clave} scope="col" className={cn("px-4 py-3 font-semibold", ["entero", "dinero", "decimal", "porcentaje"].includes(c.tipo) ? "text-right" : "text-left")}>
                              {c.titulo}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-line">
                        {r.filas.map((f, i) => (
                          <tr key={i} className="hover:bg-white/3">
                            {r.columnas.map((c) => (
                              <td key={c.clave} className={cn("px-4 py-2.5", ["entero", "dinero", "decimal", "porcentaje"].includes(c.tipo) ? "tabular text-right" : "text-left text-ink")}>
                                {celda(c, f[c.clave], r.tipo)}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </Card>
        </div>
      )}
    </>
  );
}
