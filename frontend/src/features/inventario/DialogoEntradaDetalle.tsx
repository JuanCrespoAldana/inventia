import { useQuery } from "@tanstack/react-query";
import { apiEntradas } from "@/api/inventario";
import { Button } from "@/components/ui/Button";
import { Tabla } from "@/components/ui/DataTable";
import { EstadoError } from "@/components/ui/EstadoVacio";
import { Modal } from "@/components/ui/Modal";
import { PanelCargando } from "@/components/ui/Skeleton";
import { etiqueta, MOTIVO } from "@/lib/etiquetas";
import { entero, fechaHora } from "@/lib/format";

/**
 * Detalle de una entrada de mercancía (solo lectura): número, sede, fecha, motivo, responsable y los productos
 * recibidos con su cantidad y el saldo que quedó después. La entrada no se edita ni se borra (RF-017).
 */
export function DialogoEntradaDetalle({ entradaId, onCerrar }: { entradaId: number; onCerrar: () => void }) {
  const consulta = useQuery({ queryKey: ["entradas", "detalle", entradaId], queryFn: () => apiEntradas.detalle(entradaId) });
  const e = consulta.data;

  return (
    <Modal
      abierto
      onCerrar={onCerrar}
      ancho="xl"
      titulo={e ? `Entrada #${e.numero}` : "Entrada de mercancía"}
      descripcion={e ? `${e.sede.nombre} · ${fechaHora(e.fecha)} · ${etiqueta(MOTIVO, e.motivo)} · ${e.usuario_nombre ?? "—"}` : undefined}
      pie={<Button onClick={onCerrar}>Cerrar</Button>}
    >
      {consulta.isPending ? (
        <PanelCargando etiqueta="Cargando la entrada…" />
      ) : consulta.isError ? (
        <EstadoError error={consulta.error} onReintentar={() => consulta.refetch()} />
      ) : (
        <section aria-label="Productos recibidos">
          <h3 className="mb-2 text-[13px] font-semibold uppercase tracking-wide text-ink-faint">Productos recibidos</h3>
          <div className="overflow-hidden rounded-(--radius-control) border border-line">
            <Tabla
              descripcion={`Productos de la entrada ${e!.numero}`}
              idDe={(l) => l.producto.id}
              filas={e!.detalle_lineas}
              paginar={10}
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
              ]}
            />
          </div>
        </section>
      )}
    </Modal>
  );
}
