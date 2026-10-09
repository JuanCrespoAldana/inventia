import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { CheckCircle2, Plus, Send } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { apiUsuarios } from "@/api/administracion";
import { apiPqrs } from "@/api/sig";
import { useAuth } from "@/auth/AuthContext";
import { PanelAdjuntos, SelectorArchivos, subirArchivos } from "@/components/sig/Adjuntos";
import { LineaTiempo } from "@/components/sig/LineaTiempo";
import { Aviso } from "@/components/ui/Aviso";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, Stat } from "@/components/ui/Card";
import { Tabla } from "@/components/ui/DataTable";
import { EstadoError } from "@/components/ui/EstadoVacio";
import { FiltroFecha, FiltroSelect, Input, Select, Textarea } from "@/components/ui/Field";
import { BarraFiltros } from "@/components/ui/FiltrosBarra";
import { Modal } from "@/components/ui/Modal";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { Paginacion } from "@/components/ui/Pagination";
import { Pestanas } from "@/components/ui/Tabs";
import { Busqueda } from "@/components/ui/SearchInput";
import { PanelCargando } from "@/components/ui/Skeleton";
import { aNumero, useFiltros } from "@/hooks/useFiltros";
import { useMutacion } from "@/hooks/useMutacion";
import { mensajeDeError } from "@/lib/errors";
import { ESTADO_PQRS, estado, TIPO_PQRS } from "@/lib/etiquetas";
import { fechaHora, hace } from "@/lib/format";
import { aplicarErroresServidor, v } from "@/lib/formularios";
import type { PqrsCrear, PqrsDetalle, PqrsResumen } from "@/types/api";

const INVALIDAR = [["pqrs"]];
const ESTADOS_GESTION = ["pendiente", "en_revision", "en_proceso", "resuelta"] as const;

function InsigniaTipo({ tipo }: { tipo: string }) {
  const t = TIPO_PQRS[tipo];
  return <Badge tono={t?.tono ?? "neutral"}>{t?.etiqueta ?? tipo}</Badge>;
}

function InsigniaEstado({ valor }: { valor: string }) {
  const e = estado(ESTADO_PQRS, valor);
  return <Badge tono={e.tono}>{e.etiqueta}</Badge>;
}

/* ------------------------------------------------------------------------------ nueva solicitud */

const esquemaNueva = z.object({
  tipo: z.enum(["peticion", "queja", "reclamo", "sugerencia"]),
  asunto: v.texto("El asunto", 5, 150),
  descripcion: v.texto("La descripción", 10, 2000),
});
type DatosNueva = z.infer<typeof esquemaNueva>;

function DialogoNuevaPqrs({ onCerrar }: { onCerrar: () => void }) {
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const [archivos, setArchivos] = useState<File[]>([]);
  const [radicada, setRadicada] = useState<{ numero: number; fallos: string[] } | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    watch,
    formState: { errors },
  } = useForm<DatosNueva>({ resolver: zodResolver(esquemaNueva), defaultValues: { tipo: "peticion", asunto: "", descripcion: "" } });
  const tipo = watch("tipo");

  const crear = useMutacion(
    async (d: PqrsCrear) => {
      const creada = await apiPqrs.crear(d);
      const fallos = archivos.length > 0 ? await subirArchivos("pqrs", creada.id, archivos) : [];
      return { numero: creada.numero, fallos };
    },
    { invalidar: INVALIDAR, avisarError: false, onExito: setRadicada },
  );

  if (radicada) {
    return (
      <Modal abierto onCerrar={onCerrar} titulo="Solicitud enviada" pie={<Button onClick={onCerrar}>Entendido</Button>}>
        <div className="flex flex-col items-center gap-3 py-2 text-center">
          <div className="flex size-12 items-center justify-center rounded-2xl bg-success-dim text-success ring-1 ring-success/30">
            <CheckCircle2 className="size-6" aria-hidden />
          </div>
          <p className="font-display text-lg font-semibold text-ink">Tu solicitud quedó radicada con el número #{radicada.numero}</p>
          <p className="max-w-sm text-sm text-ink-dim">Puedes consultar su estado y la respuesta en «Mis solicitudes». Te responderemos por este mismo medio.</p>
        </div>
        {radicada.fallos.length > 0 && (
          <Aviso tipo="aviso" titulo="Algunas evidencias no se pudieron adjuntar" className="mt-4">
            <ul className="list-disc pl-4">
              {radicada.fallos.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
            <p className="mt-1">Puedes volver a adjuntarlas desde el detalle de la solicitud.</p>
          </Aviso>
        )}
      </Modal>
    );
  }

  return (
    <Modal
      abierto
      onCerrar={onCerrar}
      bloqueado={crear.isPending}
      ancho="lg"
      titulo="Nueva solicitud"
      descripcion="Cuéntanos tu petición, queja, reclamo o sugerencia. Se registra a tu nombre con la fecha de hoy."
      pie={
        <>
          <Button variante="ghost" onClick={onCerrar} disabled={crear.isPending}>
            Cancelar
          </Button>
          <Button type="submit" form="form-pqrs" cargando={crear.isPending} icono={<Send className="size-4" aria-hidden />}>
            Enviar solicitud
          </Button>
        </>
      }
    >
      <form
        id="form-pqrs"
        noValidate
        className="flex flex-col gap-4"
        onSubmit={handleSubmit(async (d) => {
          setErrorGeneral(null);
          try {
            await crear.mutateAsync(d);
          } catch (e) {
            setErrorGeneral(aplicarErroresServidor(e, setError, ["tipo", "asunto", "descripcion"]));
          }
        })}
      >
        {errorGeneral && <Aviso tipo="error">{errorGeneral}</Aviso>}
        <Select etiqueta="Tipo de solicitud" required ayuda={TIPO_PQRS[tipo]?.ayuda} error={errors.tipo?.message} {...register("tipo")}>
          {Object.entries(TIPO_PQRS).map(([k, t]) => (
            <option key={k} value={k}>
              {t.etiqueta}
            </option>
          ))}
        </Select>
        <Input etiqueta="Asunto" required maxLength={150} placeholder="Resumen en una frase" error={errors.asunto?.message} {...register("asunto")} />
        <Textarea etiqueta="Descripción" required rows={5} maxLength={2000} placeholder="Explica con detalle qué ocurrió o qué necesitas" error={errors.descripcion?.message} {...register("descripcion")} />
        <SelectorArchivos archivos={archivos} onChange={setArchivos} />
      </form>
    </Modal>
  );
}

/* ------------------------------------------------------------------------------ detalle y gestión */

function FormularioGestion({ pqrs }: { pqrs: PqrsDetalle }) {
  const [nuevoEstado, setNuevoEstado] = useState<string>(pqrs.estado);
  const [respuesta, setRespuesta] = useState("");
  const [error, setError] = useState<string | null>(null);

  const guardar = useMutacion(() => apiPqrs.gestionar(pqrs.id, { estado: nuevoEstado === pqrs.estado ? null : (nuevoEstado as (typeof ESTADOS_GESTION)[number]), respuesta: respuesta.trim() || null }), {
    exito: "Solicitud actualizada.",
    invalidar: INVALIDAR,
    avisarError: false,
    onExito: () => setRespuesta(""),
  });
  const resolviendoSinRespuesta = nuevoEstado === "resuelta" && !pqrs.respuesta && respuesta.trim().length < 3;
  const sinCambios = nuevoEstado === pqrs.estado && respuesta.trim().length < 3;

  return (
    <section aria-label="Gestionar solicitud" className="flex flex-col gap-3 rounded-(--radius-control) border border-line bg-surface-2/50 p-4">
      <h3 className="text-[13px] font-semibold uppercase tracking-wide text-ink-faint">Gestionar</h3>
      {error && <Aviso tipo="error">{error}</Aviso>}
      <div className="grid gap-3 sm:grid-cols-[220px_1fr]">
        <Select etiqueta="Estado" value={nuevoEstado} onChange={(e) => setNuevoEstado(e.target.value)}>
          {ESTADOS_GESTION.map((e) => (
            <option key={e} value={e}>
              {ESTADO_PQRS[e].etiqueta}
            </option>
          ))}
        </Select>
        <Textarea
          etiqueta={pqrs.respuesta ? "Nueva respuesta o comentario" : "Respuesta a la persona"}
          rows={3}
          maxLength={2000}
          value={respuesta}
          onChange={(e) => setRespuesta(e.target.value)}
          ayuda={nuevoEstado === "resuelta" && !pqrs.respuesta ? "Para marcarla como resuelta debes escribir la respuesta." : "Queda en el historial con tu nombre y la fecha."}
        />
      </div>
      <div className="flex justify-end">
        <Button
          cargando={guardar.isPending}
          disabled={sinCambios || resolviendoSinRespuesta}
          onClick={async () => {
            setError(null);
            try {
              await guardar.mutateAsync();
            } catch (e) {
              setError(mensajeDeError(e));
            }
          }}
        >
          Guardar cambios
        </Button>
      </div>
    </section>
  );
}

function DetallePqrs({ id, onCerrar }: { id: number; onCerrar: () => void }) {
  const consulta = useQuery({ queryKey: ["pqrs", "detalle", id], queryFn: () => apiPqrs.detalle(id) });
  const p = consulta.data;
  return (
    <Modal abierto onCerrar={onCerrar} ancho="xl" titulo={p ? `Solicitud #${p.numero}` : "Solicitud"} descripcion={p ? `${p.usuario_nombre ?? "—"}${p.sede ? ` · ${p.sede.nombre}` : ""} · ${fechaHora(p.created_at)}` : undefined} pie={<Button variante="secondary" onClick={onCerrar}>Cerrar</Button>}>
      {consulta.isPending ? (
        <PanelCargando etiqueta="Cargando la solicitud…" />
      ) : consulta.isError ? (
        <EstadoError error={consulta.error} onReintentar={() => consulta.refetch()} />
      ) : (
        <div className="flex flex-col gap-6">
          <div className="flex flex-wrap items-center gap-2">
            <InsigniaTipo tipo={p!.tipo} />
            <InsigniaEstado valor={p!.estado} />
          </div>
          <div>
            <h3 className="font-display text-lg font-semibold text-ink">{p!.asunto}</h3>
            <p className="mt-2 whitespace-pre-line text-sm text-ink-dim">{p!.descripcion}</p>
          </div>
          {p!.respuesta && (
            <Aviso tipo="exito" titulo={`Respuesta${p!.respondida_por_nombre ? ` de ${p!.respondida_por_nombre}` : ""}${p!.respondida_en ? ` · ${fechaHora(p!.respondida_en)}` : ""}`}>
              <span className="whitespace-pre-line">{p!.respuesta}</span>
            </Aviso>
          )}
          {p!.puede_gestionar && <FormularioGestion key={`${p!.estado}-${p!.updated_at}`} pqrs={p!} />}
          <PanelAdjuntos entidad="pqrs" entidadId={p!.id} archivos={p!.archivos} puedeAdjuntar={p!.puede_adjuntar} invalidar={INVALIDAR} />
          <section aria-label="Historial de la solicitud">
            <h3 className="mb-3 text-[13px] font-semibold uppercase tracking-wide text-ink-faint">Historial de estados</h3>
            <LineaTiempo eventos={p!.historial.map((e) => ({ ...e, texto: e.comentario }))} estados={ESTADO_PQRS} />
          </section>
        </div>
      )}
    </Modal>
  );
}

/* ------------------------------------------------------------------------------ listado */

type Ambito = "mias" | "todas";

function Listado({ ambito, abrir }: { ambito: Ambito; abrir: (id: number) => void }) {
  const { tiene } = useAuth();
  const { filtros, pagina, tamano, cambiar, irAPagina, limpiar, hayFiltros } = useFiltros({ tipo: "", estado: "", usuario_id: "", desde: "", hasta: "", q: "" }, 15);
  const usuarios = useQuery({
    queryKey: ["usuarios", "selector-pqrs"],
    queryFn: async () => (await apiUsuarios.listar({ tamano: 100 })).items,
    enabled: ambito === "todas" && tiene("usuarios.ver"),
    staleTime: 5 * 60_000,
  });

  const lista = useQuery({
    queryKey: ["pqrs", "lista", ambito, filtros, pagina],
    queryFn: () =>
      apiPqrs.listar({ ambito, tipo: filtros.tipo, estado: filtros.estado, usuario_id: ambito === "todas" ? aNumero(filtros.usuario_id) : "", desde: filtros.desde, hasta: filtros.hasta, q: filtros.q, pagina, tamano }),
    placeholderData: keepPreviousData,
  });

  return (
    <Card>
      <BarraFiltros hayFiltros={hayFiltros} onLimpiar={limpiar}>
        <Busqueda valor={filtros.q} onCambiar={(q) => cambiar({ q })} placeholder="Asunto o número…" etiqueta="Buscar por asunto o número" />
        <FiltroSelect etiqueta="Tipo" value={filtros.tipo} onChange={(e) => cambiar({ tipo: e.target.value })}>
          <option value="">Todos los tipos</option>
          {Object.entries(TIPO_PQRS).map(([k, t]) => (
            <option key={k} value={k}>
              {t.etiqueta}
            </option>
          ))}
        </FiltroSelect>
        <FiltroSelect etiqueta="Estado" value={filtros.estado} onChange={(e) => cambiar({ estado: e.target.value })}>
          <option value="">Todos los estados</option>
          {Object.entries(ESTADO_PQRS).map(([k, t]) => (
            <option key={k} value={k}>
              {t.etiqueta}
            </option>
          ))}
        </FiltroSelect>
        {ambito === "todas" && usuarios.data && (
          <FiltroSelect etiqueta="Usuario" value={filtros.usuario_id} onChange={(e) => cambiar({ usuario_id: e.target.value })}>
            <option value="">Todas las personas</option>
            {usuarios.data.map((u) => (
              <option key={u.id} value={u.id}>
                {u.nombre}
              </option>
            ))}
          </FiltroSelect>
        )}
        <FiltroFecha etiqueta="Desde" value={filtros.desde} max={filtros.hasta || undefined} onChange={(e) => cambiar({ desde: e.target.value })} />
        <FiltroFecha etiqueta="Hasta" value={filtros.hasta} min={filtros.desde || undefined} onChange={(e) => cambiar({ hasta: e.target.value })} />
      </BarraFiltros>
      <Tabla<PqrsResumen>
        descripcion={ambito === "mias" ? "Mis solicitudes" : "Todas las solicitudes"}
        idDe={(p) => p.id}
        filas={lista.data?.items}
        cargando={lista.isFetching}
        error={lista.error}
        onReintentar={() => lista.refetch()}
        onFila={(p) => abrir(p.id)}
        vacio={{
          titulo: hayFiltros ? "Sin resultados" : ambito === "mias" ? "Aún no has enviado solicitudes" : "No hay solicitudes registradas",
          descripcion: hayFiltros ? "Prueba con otros filtros." : ambito === "mias" ? "Usa «Nueva solicitud» para enviar una petición, queja, reclamo o sugerencia." : "Cuando las personas envíen solicitudes aparecerán aquí.",
        }}
        columnas={[
          { clave: "numero", encabezado: "N.°", celda: (p) => <span className="tabular font-semibold">#{p.numero}</span> },
          {
            clave: "asunto",
            encabezado: "Asunto",
            className: "max-w-72",
            celda: (p) => (
              <div className="min-w-0">
                <p className="truncate font-medium">{p.asunto}</p>
                {ambito === "todas" && <p className="truncate text-xs text-ink-faint">{p.usuario_nombre ?? "—"}{p.sede ? ` · ${p.sede.nombre}` : ""}</p>}
              </div>
            ),
          },
          { clave: "tipo", encabezado: "Tipo", celda: (p) => <InsigniaTipo tipo={p.tipo} /> },
          { clave: "estado", encabezado: "Estado", celda: (p) => <InsigniaEstado valor={p.estado} /> },
          { clave: "resp", encabezado: "Respuesta", desde: "md", celda: (p) => (p.respondida ? <Badge tono="success">Respondida</Badge> : <span className="text-ink-faint">—</span>) },
          { clave: "fecha", encabezado: "Enviada", desde: "sm", celda: (p) => <span className="whitespace-nowrap text-ink-dim" title={fechaHora(p.created_at)}>{hace(p.created_at)}</span> },
        ]}
      />
      {lista.data && <Paginacion pagina={lista.data.pagina} paginas={lista.data.paginas} total={lista.data.total} tamano={lista.data.tamano} onCambiar={irAPagina} />}
    </Card>
  );
}

function Resumen() {
  const conteo = useQuery({ queryKey: ["pqrs", "conteo"], queryFn: apiPqrs.conteo });
  if (!conteo.data) return null;
  const c = conteo.data;
  return (
    <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-5">
      <Stat etiqueta="Total" valor={c.total} />
      <Stat etiqueta="Pendientes" valor={c.pendiente} tono={c.pendiente > 0 ? "warning" : "neutral"} />
      <Stat etiqueta="En revisión" valor={c.en_revision} tono="accent" />
      <Stat etiqueta="En proceso" valor={c.en_proceso} tono="accent" />
      <Stat etiqueta="Resueltas" valor={c.resuelta} tono="success" />
    </div>
  );
}

export default function PqrsPage() {
  const { tiene } = useAuth();
  const gestiona = tiene("pqrs.gestionar");
  const puedeCrear = tiene("pqrs.crear");
  const [ambito, setAmbito] = useState<Ambito>(gestiona ? "todas" : "mias");
  const [nueva, setNueva] = useState(false);
  const [abierta, setAbierta] = useState<number | null>(null);

  return (
    <>
      <EncabezadoPagina
        titulo="PQRS y sugerencias"
        descripcion={gestiona ? "Peticiones, quejas, reclamos y sugerencias de las personas del sistema. Cambia su estado y respóndelas; cada cambio queda en el historial." : "Envía una petición, queja, reclamo o sugerencia y consulta cómo va su trámite."}
        acciones={
          puedeCrear && (
            <Button icono={<Plus className="size-4" aria-hidden />} onClick={() => setNueva(true)}>
              Nueva solicitud
            </Button>
          )
        }
      />
      {gestiona && <Resumen />}
      {gestiona && puedeCrear && (
        <div className="mb-4">
          <Pestanas
            etiqueta="Ámbito de las solicitudes"
            activa={ambito}
            onCambiar={setAmbito}
            pestanas={[
              { clave: "todas", etiqueta: "Todas las solicitudes" },
              { clave: "mias", etiqueta: "Mis solicitudes" },
            ]}
          />
        </div>
      )}
      <Listado key={ambito} ambito={gestiona && !puedeCrear ? "todas" : ambito} abrir={setAbierta} />
      {nueva && <DialogoNuevaPqrs onCerrar={() => setNueva(false)} />}
      {abierta !== null && <DetallePqrs id={abierta} onCerrar={() => setAbierta(null)} />}
    </>
  );
}
