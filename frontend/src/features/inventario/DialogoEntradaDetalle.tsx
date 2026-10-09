import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ClipboardList, Flag, Plus } from "lucide-react";
import { apiEntradas } from "@/api/sig";
import { Aviso } from "@/components/ui/Aviso";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Tabla } from "@/components/ui/DataTable";
import { EstadoError } from "@/components/ui/EstadoVacio";
import { Select, Textarea } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";
import { PanelCargando } from "@/components/ui/Skeleton";
import { DialogoNuevaNoConformidad, type PrefillNc } from "@/features/sig/calidad/NoConformidades";
import { useMutacion } from "@/hooks/useMutacion";
import { mensajeDeError } from "@/lib/errors";
import { ESTADO_NC, estado, etiqueta, MOTIVO } from "@/lib/etiquetas";
import { entero, fechaHora } from "@/lib/format";
import type { EntradaDetalle } from "@/types/api";

const INVALIDAR = [["entradas"], ["movimientos"]];

function EnlaceNc({ nc }: { nc: EntradaDetalle["no_conformidades_vinculadas"][number] }) {
  const e = estado(ESTADO_NC, nc.estado);
  return (
    <Link to={`/sig/calidad?tab=no-conformidades&nc=${nc.id}`} className="inline-flex items-center gap-1.5 rounded-full bg-surface-2 px-2.5 py-0.5 text-xs font-semibold text-ink ring-1 ring-inset ring-line-strong hover:text-accent-light">
      NC #{nc.numero}
      <Badge tono={e.tono} className="px-1.5 py-0 text-[10px]">{e.etiqueta}</Badge>
    </Link>
  );
}

function FormularioObservacionEntrada({ entrada }: { entrada: EntradaDetalle }) {
  const [contenido, setContenido] = useState("");
  const [productoId, setProductoId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const guardar = useMutacion(() => apiEntradas.observar(entrada.id, contenido.trim(), productoId ? Number(productoId) : null), {
    exito: "Observación agregada a la entrada.",
    invalidar: INVALIDAR,
    avisarError: false,
  });

  return (
    <div className="flex flex-col gap-2 rounded-(--radius-control) border border-line bg-surface-2/50 p-4">
      {error && <Aviso tipo="error">{error}</Aviso>}
      <div className="grid gap-3 sm:grid-cols-[1fr_240px]">
        <Textarea
          etiqueta="Agregar una observación a esta entrada"
          rows={2}
          maxLength={1000}
          value={contenido}
          onChange={(e) => setContenido(e.target.value)}
          placeholder="Ej. caja con el empaque golpeado, falta el manual…"
          ayuda="Queda en el historial de la entrada con tu nombre y la fecha. No reemplaza las observaciones anteriores."
        />
        {entrada.detalle_lineas.length > 1 && (
          <Select etiqueta="Se refiere a (opcional)" value={productoId} onChange={(e) => setProductoId(e.target.value)}>
            <option value="">Toda la entrada</option>
            {entrada.detalle_lineas.map((l) => (
              <option key={l.producto.id} value={l.producto.id}>
                {l.producto.nombre}
              </option>
            ))}
          </Select>
        )}
      </div>
      <div className="flex justify-end">
        <Button
          tamano="sm"
          icono={<Plus className="size-4" aria-hidden />}
          disabled={contenido.trim().length < 3}
          cargando={guardar.isPending}
          onClick={async () => {
            setError(null);
            try {
              await guardar.mutateAsync();
              setContenido("");
              setProductoId("");
            } catch (e) {
              setError(mensajeDeError(e));
            }
          }}
        >
          Agregar observación
        </Button>
      </div>
    </div>
  );
}

/**
 * Detalle de una entrada de mercancía: líneas recibidas, historial de observaciones (con fecha y autor) y las no
 * conformidades vinculadas. Desde aquí se puede reportar una no conformidad sin volver a digitar lo ya observado.
 */
export function DialogoEntradaDetalle({ entradaId, onCerrar }: { entradaId: number; onCerrar: () => void }) {
  const consulta = useQuery({ queryKey: ["entradas", "detalle", entradaId], queryFn: () => apiEntradas.detalle(entradaId) });
  const [reportando, setReportando] = useState<Pick<PrefillNc, "productoId" | "observacionId"> | null>(null);
  const e = consulta.data;

  return (
    <>
      <Modal
        abierto
        onCerrar={onCerrar}
        ancho="xl"
        titulo={e ? `Entrada #${e.numero}` : "Entrada de mercancía"}
        descripcion={e ? `${e.sede.nombre} · ${fechaHora(e.fecha)} · ${etiqueta(MOTIVO, e.motivo)} · ${e.usuario_nombre ?? "—"}` : undefined}
        pie={
          <>
            {e?.puede_reportar_calidad && (
              <Button variante="secondary" icono={<Flag className="size-4" aria-hidden />} onClick={() => setReportando({})}>
                Reportar no conformidad
              </Button>
            )}
            <Button onClick={onCerrar}>Cerrar</Button>
          </>
        }
      >
        {consulta.isPending ? (
          <PanelCargando etiqueta="Cargando la entrada…" />
        ) : consulta.isError ? (
          <EstadoError error={consulta.error} onReintentar={() => consulta.refetch()} />
        ) : (
          <div className="flex flex-col gap-6">
            <section aria-label="Productos recibidos">
              <h3 className="mb-2 text-[13px] font-semibold uppercase tracking-wide text-ink-faint">Productos recibidos</h3>
              <div className="overflow-hidden rounded-(--radius-control) border border-line">
                <Tabla
                  descripcion={`Productos de la entrada ${e!.numero}`}
                  idDe={(l) => l.producto.id}
                  filas={e!.detalle_lineas}
                  columnas={[
                    {
                      clave: "p",
                      encabezado: "Producto",
                      celda: (l) => (
                        <div>
                          <span className="font-medium">{l.producto.nombre}</span>
                          <span className="block font-mono text-xs text-ink-faint">{l.producto.codigo}</span>
                        </div>
                      ),
                    },
                    { clave: "c", encabezado: "Cantidad", alinear: "derecha", celda: (l) => <span className="tabular font-semibold text-success">+{entero(l.cantidad)}</span> },
                    { clave: "s", encabezado: "Saldo después", alinear: "derecha", desde: "sm", celda: (l) => <span className="tabular text-ink-dim">{entero(l.saldo_posterior)}</span> },
                    ...(e!.puede_reportar_calidad
                      ? [
                          {
                            clave: "nc",
                            encabezado: "",
                            alinear: "derecha" as const,
                            celda: (l: EntradaDetalle["detalle_lineas"][number]) => (
                              <Button variante="ghost" tamano="sm" onClick={() => setReportando({ productoId: l.producto.id })}>
                                Reportar problema
                              </Button>
                            ),
                          },
                        ]
                      : []),
                  ]}
                />
              </div>
            </section>

            {e!.no_conformidades_vinculadas.length > 0 && (
              <section aria-label="No conformidades vinculadas" className="flex flex-col gap-2">
                <h3 className="text-[13px] font-semibold uppercase tracking-wide text-ink-faint">No conformidades vinculadas</h3>
                <div className="flex flex-wrap gap-2">
                  {e!.no_conformidades_vinculadas.map((nc) => (
                    <EnlaceNc key={nc.id} nc={nc} />
                  ))}
                </div>
              </section>
            )}

            <section aria-label="Observaciones de la entrada" className="flex flex-col gap-3">
              <h3 className="flex items-center gap-2 text-[13px] font-semibold uppercase tracking-wide text-ink-faint">
                <ClipboardList className="size-4" aria-hidden />
                Observaciones ({e!.historial_observaciones.length})
              </h3>
              {e!.historial_observaciones.length === 0 ? (
                <p className="text-sm text-ink-faint">Esta entrada no tiene observaciones todavía.</p>
              ) : (
                <ol className="flex flex-col gap-3">
                  {e!.historial_observaciones.map((o) => (
                    <li key={o.id} className="rounded-(--radius-control) border border-line bg-surface-2 px-4 py-3">
                      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-ink-faint">
                        <span>
                          <strong className="font-semibold text-ink-dim">{o.usuario_nombre ?? "—"}</strong> · {fechaHora(o.fecha)}
                          {o.producto && <> · sobre «{o.producto.nombre}»</>}
                        </span>
                        <span className="flex flex-wrap items-center gap-2">
                          {o.no_conformidades.map((nc) => (
                            <EnlaceNc key={nc.id} nc={nc} />
                          ))}
                          {e!.puede_reportar_calidad && o.no_conformidades.length === 0 && (
                            <button type="button" className="font-semibold text-accent-light hover:underline" onClick={() => setReportando({ observacionId: o.id, productoId: o.producto?.id })}>
                              Reportar como no conformidad
                            </button>
                          )}
                        </span>
                      </div>
                      <p className="mt-1.5 whitespace-pre-line text-sm text-ink">{o.contenido}</p>
                    </li>
                  ))}
                </ol>
              )}
              {e!.puede_observar && <FormularioObservacionEntrada key={e!.historial_observaciones.length} entrada={e!} />}
            </section>
          </div>
        )}
      </Modal>
      {reportando && e && <DialogoNuevaNoConformidad prefill={{ entrada: e, ...reportando }} onCerrar={() => setReportando(null)} />}
    </>
  );
}
