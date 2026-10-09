import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Ban } from "lucide-react";
import { apiVentas } from "@/api/operaciones";
import { useAuth } from "@/auth/AuthContext";
import { Aviso } from "@/components/ui/Aviso";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Tabla } from "@/components/ui/DataTable";
import { EstadoError } from "@/components/ui/EstadoVacio";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { PanelCargando } from "@/components/ui/Skeleton";
import { useMutacion } from "@/hooks/useMutacion";
import { mensajeDeError } from "@/lib/errors";
import { ESTADO_VENTA, estado } from "@/lib/etiquetas";
import { entero, fechaHora, moneda } from "@/lib/format";

export default function VentaDetallePage() {
  const { id } = useParams();
  const navegar = useNavigate();
  const { tiene } = useAuth();
  const ventaId = Number(id);
  const [anulando, setAnulando] = useState(false);
  const [errorAnular, setErrorAnular] = useState<string | null>(null);

  const consulta = useQuery({ queryKey: ["ventas", "detalle", ventaId], queryFn: () => apiVentas.detalle(ventaId), enabled: Number.isFinite(ventaId) });
  const anular = useMutacion((motivo: string) => apiVentas.anular(ventaId, motivo), {
    exito: "Venta anulada. Las unidades volvieron al inventario.",
    invalidar: [["ventas"], ["inventario"], ["movimientos"], ["alertas"], ["dashboard"]],
    avisarError: false,
    onExito: () => setAnulando(false),
  });

  if (consulta.isPending) return <PanelCargando etiqueta="Cargando la venta…" />;
  if (consulta.isError) return <Card><EstadoError error={consulta.error} onReintentar={() => consulta.refetch()} /></Card>;
  const v = consulta.data;
  const e = estado(ESTADO_VENTA, v.estado);

  return (
    <>
      <EncabezadoPagina
        titulo={`Venta #${v.numero}`}
        descripcion={`${v.sede.nombre} · ${fechaHora(v.fecha)}${v.usuario_nombre ? ` · ${v.usuario_nombre}` : ""}`}
        acciones={
          <>
            <Button variante="ghost" icono={<ArrowLeft className="size-4" aria-hidden />} onClick={() => navegar("/ventas")}>Volver a ventas</Button>
            {v.estado === "registrada" && tiene("ventas.anular") && v.puede_anularse && (
              <Button variante="danger" icono={<Ban className="size-4" aria-hidden />} onClick={() => { setErrorAnular(null); setAnulando(true); }}>Anular venta</Button>
            )}
          </>
        }
      />
      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <Card>
          <CardHeader titulo="Productos vendidos" accion={<Badge tono={e.tono}>{e.etiqueta}</Badge>} />
          <Tabla
            descripcion={`Productos de la venta ${v.numero}`}
            idDe={(i) => i.producto.id}
            filas={v.items}
            columnas={[
              { clave: "producto", encabezado: "Producto", celda: (i) => <div><span className="font-medium">{i.producto.nombre}</span><span className="block font-mono text-xs text-ink-faint">{i.producto.codigo}</span></div> },
              { clave: "cantidad", encabezado: "Cantidad", alinear: "derecha", celda: (i) => <span className="tabular">{entero(i.cantidad)}</span> },
              { clave: "precio", encabezado: "Precio unit.", alinear: "derecha", desde: "sm", celda: (i) => <span className="tabular text-ink-dim">{moneda(i.precio_unitario)}</span> },
              { clave: "subtotal", encabezado: "Subtotal", alinear: "derecha", celda: (i) => <span className="tabular font-semibold">{moneda(i.subtotal)}</span> },
            ]}
          />
          <div className="flex items-center justify-between border-t border-line px-5 py-4">
            <span className="text-sm text-ink-dim">Total</span>
            <span className={`tabular font-display text-xl font-semibold ${v.estado === "anulada" ? "text-ink-faint line-through" : ""}`}>{moneda(v.total)}</span>
          </div>
        </Card>
        <div className="flex flex-col gap-4">
          {v.estado === "anulada" && (
            <Aviso tipo="aviso" titulo="Venta anulada">
              {v.anulada_por_nombre ?? "—"} · {fechaHora(v.anulada_en)}
              <br />
              Motivo: {v.motivo_anulacion}
            </Aviso>
          )}
          <Card className="p-5">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-4 text-sm">
              <div><dt className="text-xs text-ink-faint">Líneas</dt><dd className="tabular mt-0.5">{entero(v.lineas)}</dd></div>
              <div><dt className="text-xs text-ink-faint">Unidades</dt><dd className="tabular mt-0.5">{entero(v.unidades)}</dd></div>
              <div className="col-span-2"><dt className="text-xs text-ink-faint">Observación</dt><dd className="mt-0.5 text-ink-dim">{v.observacion ?? "—"}</dd></div>
            </dl>
            <p className="mt-4 text-xs text-ink-faint">
              Los movimientos de esta venta están en el <Link to="/movimientos" className="text-accent-light hover:underline">historial de movimientos</Link>.
            </p>
          </Card>
        </div>
      </div>
      <ConfirmDialog
        abierto={anulando}
        titulo={`Anular la venta #${v.numero}`}
        mensaje="Las unidades vuelven al inventario de la sede y la venta deja de contar en los totales. Esta acción no se puede deshacer."
        confirmarTexto="Anular venta"
        peligroso
        motivoEtiqueta="Motivo de la anulación"
        cargando={anular.isPending}
        error={errorAnular}
        onCancelar={() => setAnulando(false)}
        onConfirmar={async (motivo) => {
          setErrorAnular(null);
          try {
            await anular.mutateAsync(motivo);
          } catch (err) {
            setErrorAnular(mensajeDeError(err));
          }
        }}
      />
    </>
  );
}
