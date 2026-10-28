import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, Check, X } from "lucide-react";
import { apiTraslados } from "@/api/operaciones";
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
import { cn } from "@/lib/cn";
import { mensajeDeError } from "@/lib/errors";
import { ESTADO_TRASLADO, estado } from "@/lib/etiquetas";
import { entero, fechaHora } from "@/lib/format";
import type { TrasladoDetalle } from "@/types/api";

type Accion = "aprobar" | "rechazar" | "confirmar" | "cancelar";

function Linea({ titulo, quien, cuando, hecho, activo }: { titulo: string; quien?: string | null; cuando?: string | null; hecho: boolean; activo?: boolean }) {
  return (
    <li className="relative flex gap-3 pb-6 last:pb-0">
      <span className="absolute left-[11px] top-6 h-full w-px bg-line last:hidden" aria-hidden />
      <span className={cn("relative z-10 flex size-6 shrink-0 items-center justify-center rounded-full text-xs", hecho ? "bg-success-dim text-success ring-1 ring-success/40" : activo ? "bg-warning-dim text-warning ring-1 ring-warning/40" : "bg-surface-3 text-ink-faint")}>
        {hecho ? <Check className="size-3.5" aria-hidden /> : null}
      </span>
      <div className="-mt-0.5">
        <p className={cn("text-sm font-semibold", hecho || activo ? "text-ink" : "text-ink-faint")}>{titulo}</p>
        {(quien || cuando) && <p className="text-xs text-ink-faint">{[quien, cuando ? fechaHora(cuando) : null].filter(Boolean).join(" · ")}</p>}
      </div>
    </li>
  );
}

function Cronologia({ t }: { t: TrasladoDetalle }) {
  const cerrado = t.estado === "rechazado" || t.estado === "cancelado";
  return (
    <ol aria-label="Cronología del traslado">
      <Linea titulo="Solicitado" quien={t.solicitado_por_nombre} cuando={t.solicitado_en} hecho />
      {cerrado ? (
        <Linea titulo={t.estado === "rechazado" ? "Rechazado" : "Cancelado"} quien={t.cerrado_por_nombre} cuando={t.cerrado_en} hecho />
      ) : (
        <>
          <Linea titulo="Aprobado por la sede de origen" quien={t.aprobado_por_nombre} cuando={t.aprobado_en} hecho={Boolean(t.aprobado_en)} activo={t.estado === "solicitado"} />
          <Linea titulo="Recepción confirmada por el destino" quien={t.confirmado_por_nombre} cuando={t.confirmado_en} hecho={Boolean(t.confirmado_en)} activo={t.estado === "aprobado"} />
        </>
      )}
    </ol>
  );
}

export default function TrasladoDetallePage() {
  const { id } = useParams();
  const navegar = useNavigate();
  const trasladoId = Number(id);
  const [accion, setAccion] = useState<Accion | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);

  const consulta = useQuery({ queryKey: ["traslados", "detalle", trasladoId], queryFn: () => apiTraslados.detalle(trasladoId), enabled: Number.isFinite(trasladoId) });

  const ejecutar = useMutacion(
    ({ tipo, motivo }: { tipo: Accion; motivo: string }) => {
      switch (tipo) {
        case "aprobar": return apiTraslados.aprobar(trasladoId);
        case "rechazar": return apiTraslados.rechazar(trasladoId, motivo);
        case "confirmar": return apiTraslados.confirmar(trasladoId);
        case "cancelar": return apiTraslados.cancelar(trasladoId, motivo);
      }
    },
    {
      exito: "Traslado actualizado.",
      invalidar: [["traslados"], ["inventario"], ["movimientos"], ["alertas"], ["dashboard"], ["recomendaciones"]],
      avisarError: false,
      onExito: () => setAccion(null),
    },
  );

  if (consulta.isPending) return <PanelCargando etiqueta="Cargando el traslado…" />;
  if (consulta.isError) return <Card><EstadoError error={consulta.error} onReintentar={() => consulta.refetch()} /></Card>;
  const t = consulta.data;
  const e = estado(ESTADO_TRASLADO, t.estado);
  const acciones = t.acciones ?? [];

  const textos: Record<Accion, { titulo: string; mensaje: string; boton: string; peligroso: boolean; motivo?: string }> = {
    aprobar: { titulo: "Aprobar traslado", mensaje: `Autoriza que ${t.origen.nombre} entregue la mercancía. Las existencias aún no se mueven hasta que ${t.destino.nombre} confirme la recepción.`, boton: "Aprobar", peligroso: false },
    rechazar: { titulo: "Rechazar traslado", mensaje: "El traslado se cierra sin mover existencias.", boton: "Rechazar", peligroso: true, motivo: "Motivo del rechazo" },
    confirmar: { titulo: "Confirmar recepción", mensaje: `Se descontarán las unidades de ${t.origen.nombre} y se sumarán a ${t.destino.nombre} en una sola operación. Si el origen ya no tiene suficiente stock, no se mueve nada.`, boton: "Confirmar recepción", peligroso: false },
    cancelar: { titulo: "Cancelar traslado", mensaje: "El traslado se cierra sin mover existencias.", boton: "Cancelar traslado", peligroso: true, motivo: "Motivo de la cancelación" },
  };

  return (
    <>
      <EncabezadoPagina
        titulo={`Traslado #${t.numero}`}
        descripcion={`Solicitado ${fechaHora(t.solicitado_en)}${t.solicitado_por_nombre ? ` por ${t.solicitado_por_nombre}` : ""}`}
        acciones={
          <>
            <Button variante="ghost" icono={<ArrowLeft className="size-4" aria-hidden />} onClick={() => navegar("/traslados")}>Volver a traslados</Button>
            {acciones.includes("rechazar") && <Button variante="danger" icono={<X className="size-4" aria-hidden />} onClick={() => { setErrorAccion(null); setAccion("rechazar"); }}>Rechazar</Button>}
            {acciones.includes("cancelar") && <Button variante="secondary" onClick={() => { setErrorAccion(null); setAccion("cancelar"); }}>Cancelar traslado</Button>}
            {acciones.includes("aprobar") && <Button icono={<Check className="size-4" aria-hidden />} onClick={() => { setErrorAccion(null); setAccion("aprobar"); }}>Aprobar</Button>}
            {acciones.includes("confirmar") && <Button icono={<Check className="size-4" aria-hidden />} onClick={() => { setErrorAccion(null); setAccion("confirmar"); }}>Confirmar recepción</Button>}
          </>
        }
      />
      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader
              titulo="Mercancía a trasladar"
              descripcion={`${entero(t.unidades)} unidades en ${t.lineas} ${t.lineas === 1 ? "línea" : "líneas"}`}
              accion={<Badge tono={e.tono}>{e.etiqueta}</Badge>}
            />
            <div className="flex items-center gap-3 border-b border-line px-5 py-3.5 text-sm">
              <span className="font-semibold">{t.origen.nombre}</span>
              <ArrowRight className="size-4 text-ink-faint" aria-label="hacia" />
              <span className="font-semibold">{t.destino.nombre}</span>
            </div>
            <Tabla
              descripcion={`Productos del traslado ${t.numero}`}
              idDe={(i) => i.producto.id}
              filas={t.items}
              paginar={10}
              columnas={[
                { clave: "producto", encabezado: "Producto", celda: (i) => <div><span className="font-medium">{i.producto.nombre}</span><span className="block font-mono text-xs text-ink-faint">{i.producto.codigo}</span></div> },
                { clave: "cantidad", encabezado: "Cantidad", alinear: "derecha", celda: (i) => <span className="tabular font-semibold">{entero(i.cantidad)}</span> },
                { clave: "origen", encabezado: `En ${t.origen.nombre}`, alinear: "derecha", desde: "sm", celda: (i) => <span className={cn("tabular", i.existencias_origen < i.cantidad && t.estado !== "confirmado" ? "text-danger" : "text-ink-dim")}>{entero(i.existencias_origen)}</span> },
                { clave: "destino", encabezado: `En ${t.destino.nombre}`, alinear: "derecha", desde: "sm", celda: (i) => <span className="tabular text-ink-dim">{entero(i.existencias_destino)}</span> },
              ]}
            />
          </Card>
          {t.motivo_cierre && <Aviso tipo="aviso" titulo={t.estado === "rechazado" ? "Motivo del rechazo" : "Motivo de la cancelación"}>{t.motivo_cierre}</Aviso>}
          {t.observacion && <Card className="p-5"><p className="text-xs text-ink-faint">Observación</p><p className="mt-1 text-sm text-ink">{t.observacion}</p></Card>}
        </div>
        <Card className="h-fit p-5">
          <h2 className="mb-5 font-display text-base font-semibold">Seguimiento</h2>
          <Cronologia t={t} />
          {t.recomendacion_id && <p className="mt-5 text-xs text-ink-faint">Origen: recomendación #{t.recomendacion_id}, aprobada por una persona.</p>}
        </Card>
      </div>
      {accion && (
        <ConfirmDialog
          abierto
          titulo={textos[accion].titulo}
          mensaje={textos[accion].mensaje}
          confirmarTexto={textos[accion].boton}
          peligroso={textos[accion].peligroso}
          motivoEtiqueta={textos[accion].motivo}
          cargando={ejecutar.isPending}
          error={errorAccion}
          onCancelar={() => setAccion(null)}
          onConfirmar={async (motivo) => {
            setErrorAccion(null);
            try {
              await ejecutar.mutateAsync({ tipo: accion, motivo });
            } catch (err) {
              setErrorAccion(mensajeDeError(err));
            }
          }}
        />
      )}
    </>
  );
}
