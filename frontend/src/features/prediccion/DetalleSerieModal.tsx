import { useQuery } from "@tanstack/react-query";
import { apiPredicciones } from "@/api/analitica";
import { GraficoLineas } from "@/components/charts/GraficoLineas";
import { Aviso } from "@/components/ui/Aviso";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { PanelCargando } from "@/components/ui/Skeleton";
import { EstadoError } from "@/components/ui/EstadoVacio";
import { CONFIANZA, estado } from "@/lib/etiquetas";
import { decimal, entero, parseDia, porcentaje } from "@/lib/format";
import type { MetricasPrediccion } from "./tipos";
import { nombreModelo } from "./tipos";

function pares(datos: unknown[][]): { t: number; y: number }[] {
  return datos.map(([f, v]) => ({ t: parseDia(String(f)).getTime(), y: Number(v) }));
}

export function DetalleSerieModal({ sedeId, productoId, onCerrar }: { sedeId: number; productoId: number; onCerrar: () => void }) {
  const consulta = useQuery({ queryKey: ["predicciones", "serie", sedeId, productoId], queryFn: () => apiPredicciones.serie(sedeId, productoId, 90) });
  const s = consulta.data;
  const m = (s?.metricas ?? {}) as MetricasPrediccion;
  const conf = estado(CONFIANZA, s?.confianza);
  const historial = s ? pares(s.historial as unknown[][]) : [];
  const pronostico = s ? pares(s.pronostico as unknown[][]) : [];
  const corte = historial.length ? historial[historial.length - 1].t : undefined;

  return (
    <Modal abierto onCerrar={onCerrar} ancho="xl" titulo={s ? `${s.producto.nombre}` : "Detalle de la predicción"} descripcion={s ? `${s.sede.nombre} · ${s.producto.codigo}` : undefined}>
      {consulta.isPending && <PanelCargando etiqueta="Cargando la serie…" />}
      {consulta.isError && <EstadoError error={consulta.error} onReintentar={() => consulta.refetch()} />}
      {s && (
        <div className="flex flex-col gap-6">
          {s.motivo_sin_prediccion && <Aviso tipo="aviso" titulo="Sin pronóstico para esta serie">{s.motivo_sin_prediccion}</Aviso>}
          {s.advertencias.map((a) => (
            <Aviso key={a} tipo="aviso">{a}</Aviso>
          ))}
          {historial.length > 0 && (
            <div>
              <div className="mb-2 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-ink-dim">
                <span className="flex items-center gap-2"><span className="inline-block h-0.5 w-5 bg-[#A4A7B5]" /> Ventas diarias reales</span>
                {pronostico.length > 0 && <span className="flex items-center gap-2"><span className="inline-block h-0.5 w-5 border-t-2 border-dashed border-[#8AA3FF]" /> Pronóstico</span>}
              </div>
              <GraficoLineas
                alto={260}
                descripcion={`Ventas diarias de ${s.producto.nombre} en ${s.sede.nombre} y pronóstico`}
                formatoY={(v) => decimal(v, v % 1 === 0 ? 0 : 1)}
                capas={[
                  { nombre: "Ventas reales", puntos: historial, color: "#A4A7B5" },
                  ...(pronostico.length ? [{ nombre: "Pronóstico", puntos: pronostico, color: "#8AA3FF", punteada: true }] : []),
                ]}
                marcaVertical={corte && pronostico.length ? { t: corte, etiqueta: "Fecha de corte" } : undefined}
              />
            </div>
          )}
          {s.demanda_estimada !== null && (
            <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-(--radius-control) bg-surface-2 p-4">
                <dt className="text-xs text-ink-faint">Demanda estimada del período</dt>
                <dd className="tabular mt-1 font-display text-xl font-semibold">{entero(Math.round(s.demanda_estimada))} u.</dd>
                {s.limite_inferior !== null && s.limite_superior !== null && (
                  <dd className="tabular mt-0.5 text-xs text-ink-dim">Rango del 80 %: {entero(Math.round(s.limite_inferior))}–{entero(Math.round(s.limite_superior))}</dd>
                )}
              </div>
              <div className="rounded-(--radius-control) bg-surface-2 p-4">
                <dt className="text-xs text-ink-faint">Modelo elegido</dt>
                <dd className="mt-1 text-sm font-semibold">{nombreModelo(s.modelo)}</dd>
                <dd className="mt-1"><Badge tono={conf.tono}>Confianza {conf.etiqueta.toLowerCase()}</Badge></dd>
              </div>
              <div className="rounded-(--radius-control) bg-surface-2 p-4">
                <dt className="text-xs text-ink-faint">Error de validación (WAPE)</dt>
                <dd className="tabular mt-1 font-display text-xl font-semibold">{m.wape == null ? "—" : porcentaje(m.wape * 100)}</dd>
                <dd className="mt-0.5 text-xs text-ink-dim">Línea base: {m.wape_linea_base == null ? "—" : porcentaje(m.wape_linea_base * 100)}</dd>
                <dd className="tabular mt-0.5 text-xs text-ink-dim">
                  RMSE {m.rmse == null ? "—" : `${decimal(m.rmse, 2)} u./día`} · MAPE {m.mape == null ? "—" : porcentaje(m.mape * 100)}
                </dd>
              </div>
              <div className="rounded-(--radius-control) bg-surface-2 p-4">
                <dt className="text-xs text-ink-faint">Mejora frente a la línea base</dt>
                <dd className="tabular mt-1 font-display text-xl font-semibold">{m.mejora_vs_linea_base_pct == null ? "—" : porcentaje(m.mejora_vs_linea_base_pct)}</dd>
                <dd className="mt-0.5 text-xs text-ink-dim">{m.n_pliegues ?? 0} {m.n_pliegues === 1 ? "pliegue" : "pliegues"} · {m.dias_validados ?? 0} días validados</dd>
              </div>
            </dl>
          )}
          {m.candidatos && m.candidatos.length > 0 && (
            <div>
              <h3 className="mb-2 font-display text-sm font-semibold">Modelos comparados (validación temporal)</h3>
              <div className="overflow-x-auto rounded-(--radius-control) border border-line">
                <table className="w-full text-sm">
                  <caption className="sr-only">Error de cada modelo candidato en la validación</caption>
                  <thead>
                    <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-ink-faint">
                      <th scope="col" className="px-4 py-2.5 font-semibold">Modelo</th>
                      <th scope="col" className="px-4 py-2.5 text-right font-semibold">WAPE</th>
                      <th scope="col" className="px-4 py-2.5 text-right font-semibold">MAE (u./día)</th>
                      <th scope="col" className="px-4 py-2.5 text-right font-semibold">RMSE (u./día)</th>
                      <th scope="col" className="px-4 py-2.5 text-right font-semibold">MAPE</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {m.candidatos.map((c) => (
                      <tr key={c.modelo} className={c.modelo === s.modelo ? "bg-accent-dim/40" : undefined}>
                        <td className="px-4 py-2.5">
                          {nombreModelo(c.modelo)} {c.avanzado && <Badge tono="accent" className="ml-1">Avanzado</Badge>} {c.modelo === s.modelo && <Badge tono="success" className="ml-1">Elegido</Badge>}
                        </td>
                        <td className="tabular px-4 py-2.5 text-right">{c.wape == null ? "—" : porcentaje(c.wape * 100)}</td>
                        <td className="tabular px-4 py-2.5 text-right">{decimal(c.mae, 2)}</td>
                        <td className="tabular px-4 py-2.5 text-right">{c.rmse == null ? "—" : decimal(c.rmse, 2)}</td>
                        <td className="tabular px-4 py-2.5 text-right">{c.mape == null ? "—" : porcentaje(c.mape * 100)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-2 text-xs text-ink-faint">
                Un modelo avanzado solo se elige si reduce el WAPE al menos 3 % frente al mejor modelo simple en datos que no vio al entrenar. El MAPE se calcula solo sobre los días con ventas; RMSE y MAPE se muestran como complemento.
              </p>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}
