import { useState } from "react";
import { Link } from "react-router-dom";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ArrowRight, Check, ChevronDown, ShoppingCart, Sparkles, Truck, X } from "lucide-react";
import { apiRecomendaciones } from "@/api/analitica";
import { useAuth } from "@/auth/AuthContext";
import { Aviso } from "@/components/ui/Aviso";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EstadoError, EstadoVacio } from "@/components/ui/EstadoVacio";
import { FiltroSelect } from "@/components/ui/Field";
import { BarraFiltros } from "@/components/ui/FiltrosBarra";
import { Modal } from "@/components/ui/Modal";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { Paginacion } from "@/components/ui/Pagination";
import { Busqueda } from "@/components/ui/SearchInput";
import { Skeleton } from "@/components/ui/Skeleton";
import { Textarea } from "@/components/ui/Field";
import { useSedes } from "@/hooks/useCatalogos";
import { aNumero, useFiltros } from "@/hooks/useFiltros";
import { useMutacion } from "@/hooks/useMutacion";
import { cn } from "@/lib/cn";
import { mensajeDeError } from "@/lib/errors";
import { ESTADO_RECOMENDACION, estado, PRIORIDAD, TIPO_RECOMENDACION } from "@/lib/etiquetas";
import { decimal, entero, fechaHora, hace } from "@/lib/format";
import type { Recomendacion } from "@/types/api";
import { nombreModelo } from "@/features/prediccion/tipos";

type Accion = "aprobar" | "rechazar" | "ejecutar";

interface Justificacion {
  modelo?: string;
  confianza?: string;
  demanda_diaria?: number;
  demanda_horizonte?: number;
  horizonte_dias?: number;
  existencias?: number;
  en_camino?: number;
  stock_minimo?: number;
  stock_maximo?: number | null;
  plazo_entrega_dias?: number;
  dias_seguridad?: number;
  dias_cobertura_objetivo?: number;
  punto_reposicion?: number;
  nivel_objetivo?: number;
  cobertura_dias?: number | null;
  necesidad?: number;
  cubierto_con_traslados?: number;
  origen?: { sede?: string; existencias?: number; conservar?: number | null; motivo?: string };
}

function Dato({ etiqueta, valor }: { etiqueta: string; valor: string }) {
  return (
    <div>
      <dt className="text-xs text-ink-faint">{etiqueta}</dt>
      <dd className="tabular mt-0.5 text-sm text-ink">{valor}</dd>
    </div>
  );
}

function Justificacion({ r }: { r: Recomendacion }) {
  const j = r.justificacion as Justificacion;
  return (
    <div className="mt-4 rounded-(--radius-control) bg-surface-2/70 p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-ink-faint">Por qué se recomienda</p>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3 lg:grid-cols-4">
        <Dato etiqueta="Existencias actuales" valor={entero(j.existencias)} />
        {j.en_camino ? <Dato etiqueta="En camino" valor={entero(j.en_camino)} /> : null}
        <Dato etiqueta="Demanda diaria estimada" valor={`${decimal(j.demanda_diaria, 1)} u.`} />
        <Dato etiqueta={`Demanda en ${j.horizonte_dias ?? "—"} días`} valor={`${decimal(j.demanda_horizonte, 0)} u.`} />
        <Dato etiqueta="Cobertura actual" valor={j.cobertura_dias == null ? "—" : `${decimal(j.cobertura_dias, 1)} días`} />
        <Dato etiqueta="Plazo de entrega + seguridad" valor={`${j.plazo_entrega_dias ?? "—"} + ${j.dias_seguridad ?? "—"} días`} />
        <Dato etiqueta="Punto de reposición" valor={`${entero(j.punto_reposicion)} u.`} />
        <Dato etiqueta="Nivel objetivo" valor={`${entero(j.nivel_objetivo)} u.`} />
        <Dato etiqueta="Necesidad total" valor={`${entero(j.necesidad)} u.`} />
        <Dato etiqueta="Modelo de predicción" valor={`${nombreModelo(j.modelo)} (${j.confianza ?? "—"})`} />
        {j.origen && <Dato etiqueta={`Existencias en ${j.origen.sede ?? "origen"}`} valor={entero(j.origen.existencias)} />}
        {j.cubierto_con_traslados ? <Dato etiqueta="Cubierto con traslados" valor={`${entero(j.cubierto_con_traslados)} u.`} /> : null}
      </dl>
      {j.origen?.motivo && <p className="mt-3 text-xs text-ink-dim">Sede de origen: {j.origen.motivo}.</p>}
      <p className="mt-3 text-xs text-ink-faint">
        Calculada con la predicción #{r.ejecucion_id ?? "—"}. Recomendación generada {hace(r.generada_en)}.
      </p>
    </div>
  );
}

function Tarjeta({ r, onAccion }: { r: Recomendacion; onAccion: (r: Recomendacion, a: Accion) => void }) {
  const [abierta, setAbierta] = useState(false);
  const p = estado(PRIORIDAD, r.prioridad);
  const e = estado(ESTADO_RECOMENDACION, r.estado);
  const esTraslado = r.tipo === "traslado";
  const Icono = esTraslado ? Truck : ShoppingCart;
  const acciones = r.acciones ?? [];
  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 gap-4">
          <span className={cn("flex size-11 shrink-0 items-center justify-center rounded-xl", esTraslado ? "bg-accent-dim text-accent-light" : "bg-warning-dim text-warning")}>
            <Icono className="size-5" aria-hidden />
          </span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tono={p.tono}>Prioridad {p.etiqueta.toLowerCase()}</Badge>
              <Badge>{TIPO_RECOMENDACION[r.tipo] ?? r.tipo}</Badge>
              <Badge tono={e.tono}>{e.etiqueta}</Badge>
            </div>
            <h3 className="mt-2 font-display text-base font-semibold text-ink">
              {esTraslado ? (
                <>
                  Trasladar {entero(r.cantidad_sugerida)} u. de {r.producto.nombre}
                  <span className="mt-0.5 flex flex-wrap items-center gap-1.5 text-sm font-normal text-ink-dim">
                    {r.sede_origen?.nombre} <ArrowRight className="size-3.5" aria-label="hacia" /> {r.sede.nombre}
                  </span>
                </>
              ) : (
                <>
                  Reabastecer {entero(r.cantidad_sugerida)} u. de {r.producto.nombre}
                  <span className="mt-0.5 block text-sm font-normal text-ink-dim">{r.sede.nombre}</span>
                </>
              )}
            </h3>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-ink-dim">{r.resumen}</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {acciones.includes("rechazar") && <Button variante="secondary" tamano="sm" icono={<X className="size-4" aria-hidden />} onClick={() => onAccion(r, "rechazar")}>Rechazar</Button>}
          {acciones.includes("aprobar") && <Button tamano="sm" icono={<Check className="size-4" aria-hidden />} onClick={() => onAccion(r, "aprobar")}>{esTraslado ? "Aprobar y solicitar traslado" : "Aprobar"}</Button>}
          {acciones.includes("ejecutar") && <Button tamano="sm" icono={<ShoppingCart className="size-4" aria-hidden />} onClick={() => onAccion(r, "ejecutar")}>Registrar compra realizada</Button>}
        </div>
      </div>

      {(r.revisada_por_nombre || r.traslado_id) && (
        <p className="mt-3 text-xs text-ink-faint">
          {r.revisada_por_nombre && <>Revisada por {r.revisada_por_nombre} · {fechaHora(r.revisada_en)}{r.comentario_revision ? ` · «${r.comentario_revision}»` : ""}</>}
          {r.traslado_id && (
            <>
              {" "}· <Link to={`/traslados/${r.traslado_id}`} className="text-accent-light hover:underline">Traslado #{r.traslado_numero}</Link>
            </>
          )}
        </p>
      )}

      <button
        type="button"
        onClick={() => setAbierta((a) => !a)}
        aria-expanded={abierta}
        className="mt-3 flex items-center gap-1 text-[13px] font-semibold text-accent-light hover:underline"
      >
        {abierta ? "Ocultar justificación" : "Ver justificación"}
        <ChevronDown className={cn("size-4 transition-transform", abierta && "rotate-180")} aria-hidden />
      </button>
      {abierta && <Justificacion r={r} />}
    </Card>
  );
}

const TEXTOS: Record<Accion, { titulo: (r: Recomendacion) => string; mensaje: (r: Recomendacion) => string; boton: string }> = {
  aprobar: {
    titulo: () => "Aprobar recomendación",
    mensaje: (r) =>
      r.tipo === "traslado"
        ? `Se creará la solicitud de traslado de ${entero(r.cantidad_sugerida)} unidades de ${r.producto.nombre} desde ${r.sede_origen?.nombre} hacia ${r.sede.nombre}. Las existencias solo se mueven cuando las sedes aprueben y confirmen.`
        : `Quedará aprobada la reposición de ${entero(r.cantidad_sugerida)} unidades de ${r.producto.nombre} en ${r.sede.nombre}. El sistema no hace pedidos: registre la compra cuando se realice.`,
    boton: "Aprobar",
  },
  rechazar: { titulo: () => "Rechazar recomendación", mensaje: () => "La recomendación se descarta. Puede indicar el motivo para que quede en el historial.", boton: "Rechazar" },
  ejecutar: { titulo: () => "Registrar compra realizada", mensaje: (r) => `Confirme que ya se hizo el pedido de ${entero(r.cantidad_sugerida)} unidades de ${r.producto.nombre}. Las existencias aumentan cuando registre la entrada de mercancía.`, boton: "Registrar compra" },
};

function DialogoRevision({ r, accion, onCerrar }: { r: Recomendacion; accion: Accion; onCerrar: () => void }) {
  const [comentario, setComentario] = useState("");
  const [error, setError] = useState<string | null>(null);
  const t = TEXTOS[accion];
  const enviar = useMutacion(
    () => (accion === "aprobar" ? apiRecomendaciones.aprobar(r.id, comentario.trim()) : accion === "rechazar" ? apiRecomendaciones.rechazar(r.id, comentario.trim()) : apiRecomendaciones.ejecutar(r.id, comentario.trim())),
    {
      exito: accion === "aprobar" ? (r.tipo === "traslado" ? "Recomendación aprobada: traslado solicitado." : "Recomendación aprobada.") : accion === "rechazar" ? "Recomendación rechazada." : "Compra registrada.",
      invalidar: [["recomendaciones"], ["traslados"], ["dashboard"]],
      avisarError: false,
      onExito: onCerrar,
    },
  );
  return (
    <Modal
      abierto
      onCerrar={onCerrar}
      bloqueado={enviar.isPending}
      titulo={t.titulo(r)}
      ancho="sm"
      pie={
        <>
          <Button variante="ghost" onClick={onCerrar} disabled={enviar.isPending}>Cancelar</Button>
          <Button
            variante={accion === "rechazar" ? "danger" : "primary"}
            cargando={enviar.isPending}
            onClick={async () => {
              setError(null);
              try {
                await enviar.mutateAsync();
              } catch (e) {
                setError(mensajeDeError(e));
              }
            }}
          >
            {t.boton}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <p className="text-sm text-ink-dim">{t.mensaje(r)}</p>
        {error && <Aviso tipo="error">{error}</Aviso>}
        <Textarea etiqueta="Comentario (opcional)" value={comentario} maxLength={300} onChange={(e) => setComentario(e.target.value)} placeholder="Queda en el historial de la recomendación" />
      </div>
    </Modal>
  );
}

export default function RecomendacionesPage() {
  const { tiene, sesion } = useAuth();
  const sedes = useSedes(false);
  const { filtros, pagina, tamano, cambiar, irAPagina, limpiar, hayFiltros } = useFiltros({ estado: "pendiente", tipo: "", prioridad: "", sede_id: "", q: "" }, 10);
  const [revision, setRevision] = useState<{ r: Recomendacion; accion: Accion } | null>(null);
  const verSedes = sesion?.rol.alcance === "empresa";

  const lista = useQuery({
    queryKey: ["recomendaciones", filtros, pagina],
    queryFn: () => apiRecomendaciones.listar({ estado: filtros.estado, tipo: filtros.tipo, prioridad: filtros.prioridad, sede_id: aNumero(filtros.sede_id), q: filtros.q, pagina, tamano }),
    placeholderData: keepPreviousData,
  });

  const generar = useMutacion(apiRecomendaciones.generar, {
    exito: (r) =>
      r.generadas === 0
        ? `No hay necesidades de reabastecimiento con la última predicción${r.reemplazadas ? ` (${r.reemplazadas} pendientes anteriores se reemplazaron)` : ""}.`
        : `${r.generadas} recomendaciones generadas (${r.reabastecimientos} de reabastecimiento, ${r.traslados} traslados).`,
    invalidar: [["recomendaciones"], ["dashboard"]],
  });

  const filtrosActivos = hayFiltros && !(filtros.estado === "pendiente" && !filtros.tipo && !filtros.prioridad && !filtros.sede_id && !filtros.q);

  return (
    <>
      <EncabezadoPagina
        titulo="Recomendaciones"
        descripcion="Sugerencias de reabastecimiento y traslado calculadas con la última predicción. Ninguna se ejecuta sola: cada una requiere la decisión de una persona."
        acciones={
          tiene("recomendaciones.generar") && (
            <Button icono={<Sparkles className="size-4" aria-hidden />} cargando={generar.isPending} onClick={() => generar.mutate()}>
              Generar recomendaciones
            </Button>
          )
        }
      />
      <Card className="mb-6">
        <BarraFiltros hayFiltros={filtrosActivos} onLimpiar={limpiar}>
          <Busqueda valor={filtros.q} onCambiar={(q) => cambiar({ q })} placeholder="Buscar producto o sede…" />
          <FiltroSelect etiqueta="Estado" value={filtros.estado} onChange={(e) => cambiar({ estado: e.target.value })}>
            <option value="">Todos los estados</option>
            {Object.entries(ESTADO_RECOMENDACION).map(([k, e]) => (
              <option key={k} value={k}>{e.etiqueta}</option>
            ))}
          </FiltroSelect>
          <FiltroSelect etiqueta="Tipo" value={filtros.tipo} onChange={(e) => cambiar({ tipo: e.target.value })}>
            <option value="">Todos los tipos</option>
            {Object.entries(TIPO_RECOMENDACION).map(([k, n]) => (
              <option key={k} value={k}>{n}</option>
            ))}
          </FiltroSelect>
          <FiltroSelect etiqueta="Prioridad" value={filtros.prioridad} onChange={(e) => cambiar({ prioridad: e.target.value })}>
            <option value="">Toda prioridad</option>
            {Object.entries(PRIORIDAD).map(([k, p]) => (
              <option key={k} value={k}>{p.etiqueta}</option>
            ))}
          </FiltroSelect>
          {verSedes && (
            <FiltroSelect etiqueta="Sede" value={filtros.sede_id} onChange={(e) => cambiar({ sede_id: e.target.value })}>
              <option value="">Todas las sedes</option>
              {sedes.data?.map((s) => (
                <option key={s.id} value={s.id}>{s.nombre}</option>
              ))}
            </FiltroSelect>
          )}
        </BarraFiltros>
      </Card>

      {lista.isError && !lista.data && <Card><EstadoError error={lista.error} onReintentar={() => lista.refetch()} /></Card>}
      {lista.isPending && <div className="flex flex-col gap-4" role="status" aria-label="Cargando recomendaciones">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-40" />)}</div>}
      {lista.data && lista.data.items.length === 0 && (
        <Card>
          <EstadoVacio
            titulo={filtros.estado === "pendiente" && !filtrosActivos ? "No hay recomendaciones pendientes" : "Sin resultados"}
            descripcion={filtros.estado === "pendiente" && !filtrosActivos ? "Cuando la predicción detecte una necesidad de reabastecimiento o un excedente en otra sede, aparecerá aquí." : "Pruebe con otros filtros."}
            accion={tiene("recomendaciones.generar") && !filtrosActivos ? <Button variante="secondary" onClick={() => generar.mutate()} cargando={generar.isPending}>Generar recomendaciones</Button> : undefined}
          />
        </Card>
      )}
      {lista.data && lista.data.items.length > 0 && (
        <div className={cn("flex flex-col gap-4 transition-opacity", lista.isFetching && "opacity-60")}>
          {lista.data.items.map((r) => (
            <Tarjeta key={r.id} r={r} onAccion={(rec, accion) => setRevision({ r: rec, accion })} />
          ))}
          <Card>
            <Paginacion pagina={lista.data.pagina} paginas={lista.data.paginas} total={lista.data.total} tamano={lista.data.tamano} onCambiar={irAPagina} />
          </Card>
        </div>
      )}
      {revision && <DialogoRevision r={revision.r} accion={revision.accion} onCerrar={() => setRevision(null)} />}
    </>
  );
}
