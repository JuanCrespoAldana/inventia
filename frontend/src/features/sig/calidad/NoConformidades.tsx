import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { CheckCircle2, Link2, Plus } from "lucide-react";
import { apiEntradas, apiCalidad } from "@/api/sig";
import { PanelAdjuntos, SelectorArchivos, subirArchivos } from "@/components/sig/Adjuntos";
import { LineaTiempo } from "@/components/sig/LineaTiempo";
import { useAuth } from "@/auth/AuthContext";
import { Aviso } from "@/components/ui/Aviso";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Tabla } from "@/components/ui/DataTable";
import { EstadoError } from "@/components/ui/EstadoVacio";
import { FiltroFecha, FiltroSelect, Input, Select, Textarea } from "@/components/ui/Field";
import { BarraFiltros } from "@/components/ui/FiltrosBarra";
import { Modal } from "@/components/ui/Modal";
import { Paginacion } from "@/components/ui/Pagination";
import { Busqueda } from "@/components/ui/SearchInput";
import { PanelCargando } from "@/components/ui/Skeleton";
import { SelectorProducto } from "@/components/ui/SelectorProducto";
import { buscarEnCatalogo } from "@/features/inventario/fuentes";
import { useSedes } from "@/hooks/useCatalogos";
import { aNumero, useFiltros } from "@/hooks/useFiltros";
import { useMutacion } from "@/hooks/useMutacion";
import { mensajeDeError, normalizarError } from "@/lib/errors";
import { estado, ESTADO_NC, etiqueta, TIPO_NC } from "@/lib/etiquetas";
import { entero, fecha, fechaHora, hoyISO } from "@/lib/format";
import type { EntradaDetalle, NoConformidadCrear, NoConformidadDetalle, NoConformidadGestionar, NoConformidadResumen, ProductoResumen } from "@/types/api";
import { AVISO_SIN_INVENTARIO, Dato, FormularioObservacion, SelectorResponsable } from "./comunes";
import { requisitoNc, siguientesNc } from "./reglas";

const INVALIDAR = [["calidad"], ["entradas"]];

export function InsigniaEstadoNc({ valor }: { valor: string }) {
  const e = estado(ESTADO_NC, valor);
  return <Badge tono={e.tono}>{e.etiqueta}</Badge>;
}

/* ------------------------------------------------------------------------------ nueva no conformidad */

export interface PrefillNc {
  /** Entrada de inventario de la que nace el reporte (trae sus líneas y observaciones). */
  entrada: EntradaDetalle;
  productoId?: number;
  /** Observación concreta de la entrada que originó el reporte. */
  observacionId?: number;
}

export function DialogoNuevaNoConformidad({ prefill, onCerrar, onCreada }: { prefill?: PrefillNc; onCerrar: () => void; onCreada?: (nc: NoConformidadDetalle) => void }) {
  const { sesion } = useAuth();
  const sedes = useSedes();
  const entrada = prefill?.entrada;
  const lineas = entrada?.detalle_lineas ?? [];
  const sedeFija = Boolean(entrada) || (sesion?.rol.alcance === "sede" && sesion.sede !== null);

  const [producto, setProducto] = useState<ProductoResumen | null>(() => lineas.find((l) => l.producto.id === prefill?.productoId)?.producto ?? (lineas.length === 1 ? lineas[0].producto : null));
  const [sedeId, setSedeId] = useState("");
  const [numeroEntrada, setNumeroEntrada] = useState(entrada ? String(entrada.numero) : "");
  const [observacionId, setObservacionId] = useState(prefill?.observacionId ? String(prefill.observacionId) : "");
  const [referencia, setReferencia] = useState("");
  const [tipo, setTipo] = useState("defecto_de_fabrica");
  const [descripcion, setDescripcion] = useState("");
  const [fechaDeteccion, setFechaDeteccion] = useState(hoyISO());
  const [cantidad, setCantidad] = useState("1");
  const [proveedor, setProveedor] = useState("");
  const [observaciones, setObservaciones] = useState("");
  const [archivos, setArchivos] = useState<File[]>([]);
  const [intento, setIntento] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [creada, setCreada] = useState<{ nc: NoConformidadDetalle; fallos: string[] } | null>(null);

  const errores = {
    producto: producto ? null : "Elige el producto afectado",
    sede: sedeFija || sedeId || numeroEntrada.trim() ? null : "Elige la sede donde ocurrió",
    descripcion: descripcion.trim().length >= 10 ? null : "Describe lo ocurrido (mínimo 10 caracteres)",
    cantidad: /^\d+$/.test(cantidad.trim()) && Number(cantidad) >= 1 ? null : "Escribe una cantidad entera mayor que 0",
    fecha: fechaDeteccion && fechaDeteccion <= hoyISO() ? null : "La fecha no puede estar vacía ni ser futura",
    entrada: numeroEntrada.trim() === "" || /^\d+$/.test(numeroEntrada.trim()) ? null : "Escribe solo el número de la entrada",
  };
  const hayErrores = Object.values(errores).some(Boolean);

  const crear = useMutacion(
    async () => {
      // Si indicó el número de una entrada, se resuelve a la entrada real (el servidor valida que contenga el producto).
      let entradaId = entrada?.id ?? null;
      if (!entrada && numeroEntrada.trim()) {
        const r = await apiEntradas.listar({ numero: Number(numeroEntrada), sede_id: sedeId ? Number(sedeId) : "", tamano: 5 });
        const hallada = r.items.find((e) => e.numero === Number(numeroEntrada));
        if (!hallada) throw new Error(`No se encontró la entrada de inventario #${numeroEntrada.trim()}${sedeId ? " en esa sede" : ""}.`);
        entradaId = hallada.id;
      }
      const nc = await apiCalidad.crearNc({
        producto_id: producto!.id,
        sede_id: entradaId ? null : sedeFija ? null : Number(sedeId),
        referencia: referencia.trim() || null,
        tipo: tipo as NoConformidadCrear["tipo"],
        descripcion: descripcion.trim(),
        fecha_deteccion: fechaDeteccion,
        cantidad_afectada: Number(cantidad),
        proveedor: proveedor.trim() || null,
        observaciones: observaciones.trim() || null,
        entrada_id: entradaId,
        entrada_observacion_id: entradaId && observacionId ? Number(observacionId) : null,
      });
      const fallos = archivos.length > 0 ? await subirArchivos("no_conformidad", nc.id, archivos) : [];
      return { nc, fallos };
    },
    { invalidar: INVALIDAR, avisarError: false, onExito: (r) => { setCreada(r); onCreada?.(r.nc); } },
  );

  async function enviar() {
    setIntento(true);
    setError(null);
    if (hayErrores) return;
    try {
      await crear.mutateAsync();
    } catch (e) {
      setError(normalizarError(e).message);
    }
  }

  if (creada) {
    return (
      <Modal abierto onCerrar={onCerrar} titulo="No conformidad registrada" pie={<Button onClick={onCerrar}>Entendido</Button>}>
        <div className="flex flex-col items-center gap-3 py-2 text-center">
          <div className="flex size-12 items-center justify-center rounded-2xl bg-success-dim text-success ring-1 ring-success/30">
            <CheckCircle2 className="size-6" aria-hidden />
          </div>
          <p className="font-display text-lg font-semibold text-ink">Se registró la no conformidad #{creada.nc.numero}</p>
          <p className="max-w-sm text-sm text-ink-dim">El inventario no se modificó. Puedes seguir el caso y agregar observaciones desde el listado.</p>
        </div>
        {creada.fallos.length > 0 && (
          <Aviso tipo="aviso" titulo="Algunas evidencias no se pudieron adjuntar" className="mt-4">
            <ul className="list-disc pl-4">
              {creada.fallos.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
          </Aviso>
        )}
      </Modal>
    );
  }

  const observacionesEntrada = entrada?.historial_observaciones.filter((o) => !producto || !o.producto || o.producto.id === producto.id) ?? [];

  return (
    <Modal
      abierto
      onCerrar={onCerrar}
      bloqueado={crear.isPending}
      ancho="lg"
      titulo="Reportar no conformidad"
      descripcion={entrada ? `Originada en la entrada #${entrada.numero} · ${entrada.sede.nombre}` : "Registra un producto o una entrega que no cumple lo esperado."}
      pie={
        <>
          <Button variante="ghost" onClick={onCerrar} disabled={crear.isPending}>
            Cancelar
          </Button>
          <Button onClick={() => void enviar()} cargando={crear.isPending}>
            Registrar no conformidad
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <Aviso tipo="info">{AVISO_SIN_INVENTARIO}</Aviso>
        {error && <Aviso tipo="error">{error}</Aviso>}

        {entrada ? (
          <Select etiqueta="Producto afectado" required value={producto?.id ?? ""} onChange={(e) => setProducto(lineas.find((l) => l.producto.id === Number(e.target.value))?.producto ?? null)} error={intento ? (errores.producto ?? undefined) : undefined}>
            <option value="">Elige un producto de la entrada</option>
            {lineas.map((l) => (
              <option key={l.producto.id} value={l.producto.id}>
                {l.producto.nombre} ({l.producto.codigo}) · recibidas {entero(l.cantidad)}
              </option>
            ))}
          </Select>
        ) : producto ? (
          <div className="flex items-end justify-between gap-3 rounded-(--radius-control) border border-line bg-surface-2 px-4 py-2.5">
            <div className="min-w-0">
              <p className="text-xs font-medium text-ink-faint">Producto afectado</p>
              <p className="truncate text-sm font-semibold text-ink">{producto.nombre}</p>
              <p className="font-mono text-xs text-ink-faint">{producto.codigo}</p>
            </div>
            <Button variante="ghost" tamano="sm" onClick={() => setProducto(null)}>
              Cambiar
            </Button>
          </div>
        ) : (
          <div>
            <SelectorProducto etiqueta="Producto afectado" origen={["catalogo"]} buscar={buscarEnCatalogo} onElegir={(o) => setProducto(o.producto)} />
            {intento && errores.producto && <p role="alert" className="mt-1.5 text-xs text-danger">{errores.producto}</p>}
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          {!sedeFija && (
            <Select etiqueta="Sede donde ocurrió" required value={sedeId} onChange={(e) => setSedeId(e.target.value)} error={intento ? (errores.sede ?? undefined) : undefined}>
              <option value="">Elige la sede</option>
              {sedes.data?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nombre}
                </option>
              ))}
            </Select>
          )}
          <Select etiqueta="Tipo de no conformidad" required value={tipo} onChange={(e) => setTipo(e.target.value)}>
            {Object.entries(TIPO_NC).map(([k, n]) => (
              <option key={k} value={k}>
                {n}
              </option>
            ))}
          </Select>
          <Input etiqueta="Cantidad afectada" required inputMode="numeric" value={cantidad} onChange={(e) => setCantidad(e.target.value)} error={intento ? (errores.cantidad ?? undefined) : undefined} />
          <Input etiqueta="Fecha de detección" required type="date" max={hoyISO()} value={fechaDeteccion} onChange={(e) => setFechaDeteccion(e.target.value)} error={intento ? (errores.fecha ?? undefined) : undefined} />
          <Input etiqueta="Referencia (lote, serie, factura u orden)" maxLength={100} value={referencia} onChange={(e) => setReferencia(e.target.value)} />
          <Input etiqueta="Proveedor" maxLength={150} value={proveedor} onChange={(e) => setProveedor(e.target.value)} />
        </div>

        {!entrada && (
          <Input
            etiqueta="Entrada de inventario relacionada (opcional)"
            inputMode="numeric"
            placeholder="Número de la entrada, por ejemplo 12"
            value={numeroEntrada}
            onChange={(e) => setNumeroEntrada(e.target.value)}
            error={intento ? (errores.entrada ?? undefined) : undefined}
            ayuda="Si el producto llegó en una entrada de mercancía, vincúlala: así no hay que repetir lo que ya se anotó al recibir. La sede se toma de la entrada."
          />
        )}
        {entrada && observacionesEntrada.length > 0 && (
          <Select etiqueta="Observación de la entrada que originó el reporte (opcional)" value={observacionId} onChange={(e) => setObservacionId(e.target.value)} ayuda="Se enlaza sin volver a escribirla.">
            <option value="">Ninguna en particular</option>
            {observacionesEntrada.map((o) => (
              <option key={o.id} value={o.id}>
                {fechaHora(o.fecha)} · {o.usuario_nombre ?? "—"}: {o.contenido.length > 70 ? `${o.contenido.slice(0, 70)}…` : o.contenido}
              </option>
            ))}
          </Select>
        )}

        <Textarea etiqueta="Descripción" required rows={4} maxLength={2000} value={descripcion} onChange={(e) => setDescripcion(e.target.value)} placeholder="Qué pasó, cómo se detectó y cuál es el estado del producto" error={intento ? (errores.descripcion ?? undefined) : undefined} />
        <Textarea etiqueta="Observaciones (opcional)" rows={2} maxLength={1000} value={observaciones} onChange={(e) => setObservaciones(e.target.value)} />
        <SelectorArchivos archivos={archivos} onChange={setArchivos} />
      </div>
    </Modal>
  );
}

/* ------------------------------------------------------------------------------ detalle */

function FormularioGestionNc({ nc }: { nc: NoConformidadDetalle }) {
  const siguientes = siguientesNc(nc.estado);
  const [nuevoEstado, setNuevoEstado] = useState("");
  const [responsable, setResponsable] = useState("");
  const [proveedor, setProveedor] = useState(nc.proveedor ?? "");
  const [solucion, setSolucion] = useState(nc.solucion ?? "");
  const [comentario, setComentario] = useState("");
  const [error, setError] = useState<string | null>(null);

  const guardar = useMutacion(
    () =>
      apiCalidad.gestionarNc(nc.id, {
        estado: (nuevoEstado || null) as NoConformidadGestionar["estado"],
        responsable_id: responsable ? Number(responsable) : null,
        proveedor: proveedor.trim() !== (nc.proveedor ?? "") ? proveedor.trim() : null,
        solucion: solucion.trim() !== (nc.solucion ?? "") ? solucion.trim() : null,
        comentario: comentario.trim() || null,
      }),
    { exito: "Caso actualizado.", invalidar: INVALIDAR, avisarError: false },
  );
  const requisito = nuevoEstado ? requisitoNc(nuevoEstado, solucion) : null;
  const hayCambios = Boolean(nuevoEstado || responsable || comentario.trim() || proveedor.trim() !== (nc.proveedor ?? "") || solucion.trim() !== (nc.solucion ?? ""));

  return (
    <section aria-label="Gestionar no conformidad" className="flex flex-col gap-3 rounded-(--radius-control) border border-line bg-surface-2/50 p-4">
      <h3 className="text-[13px] font-semibold uppercase tracking-wide text-ink-faint">Gestionar</h3>
      {error && <Aviso tipo="error">{error}</Aviso>}
      {requisito && <Aviso tipo="aviso">{requisito}</Aviso>}
      <div className="grid gap-3 sm:grid-cols-2">
        <Select etiqueta="Cambiar estado a" value={nuevoEstado} onChange={(e) => setNuevoEstado(e.target.value)}>
          <option value="">Mantener «{estado(ESTADO_NC, nc.estado).etiqueta}»</option>
          {siguientes.map((e) => (
            <option key={e} value={e}>
              {ESTADO_NC[e].etiqueta}
            </option>
          ))}
        </Select>
        <SelectorResponsable valor={responsable} onChange={setResponsable} actual={nc.responsable_nombre} />
        <Input etiqueta="Proveedor" maxLength={150} value={proveedor} onChange={(e) => setProveedor(e.target.value)} />
      </div>
      <Textarea etiqueta="Solución" rows={2} maxLength={2000} value={solucion} onChange={(e) => setSolucion(e.target.value)} ayuda="Obligatoria para marcarla como resuelta o cerrada." />
      <Textarea etiqueta="Comentario del cambio" rows={2} maxLength={1000} value={comentario} onChange={(e) => setComentario(e.target.value)} />
      <div className="flex justify-end">
        <Button
          cargando={guardar.isPending}
          disabled={!hayCambios || Boolean(requisito)}
          onClick={async () => {
            setError(null);
            try {
              await guardar.mutateAsync();
              setNuevoEstado("");
              setResponsable("");
              setComentario("");
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

export function DetalleNoConformidad({ id, onCerrar, onAbrirEntrada }: { id: number; onCerrar: () => void; onAbrirEntrada?: (entradaId: number) => void }) {
  const consulta = useQuery({ queryKey: ["calidad", "nc", id], queryFn: () => apiCalidad.detalleNc(id) });
  const observar = useMutacion((texto: string) => apiCalidad.observarNc(id, texto), { exito: "Observación agregada.", invalidar: INVALIDAR, avisarError: false });
  const nc = consulta.data;

  return (
    <Modal
      abierto
      onCerrar={onCerrar}
      ancho="xl"
      titulo={nc ? `No conformidad #${nc.numero}` : "No conformidad"}
      descripcion={nc ? `Reportada por ${nc.usuario_nombre ?? "—"} · ${fechaHora(nc.created_at)}` : undefined}
      pie={<Button variante="secondary" onClick={onCerrar}>Cerrar</Button>}
    >
      {consulta.isPending ? (
        <PanelCargando etiqueta="Cargando la no conformidad…" />
      ) : consulta.isError ? (
        <EstadoError error={consulta.error} onReintentar={() => consulta.refetch()} />
      ) : (
        <div className="flex flex-col gap-6">
          <div className="flex flex-wrap items-center gap-2">
            <InsigniaEstadoNc valor={nc!.estado} />
            <Badge>{etiqueta(TIPO_NC, nc!.tipo)}</Badge>
            {nc!.entrada && (
              <button
                type="button"
                onClick={() => onAbrirEntrada?.(nc!.entrada!.id)}
                disabled={!onAbrirEntrada}
                className="inline-flex items-center gap-1 rounded-full bg-accent-dim px-2.5 py-0.5 text-xs font-semibold text-accent-light ring-1 ring-inset ring-accent/30 enabled:hover:underline"
              >
                <Link2 className="size-3" aria-hidden />
                Entrada #{nc!.entrada.numero}
              </button>
            )}
          </div>
          <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Dato etiqueta="Producto">
              {nc!.producto.nombre}
              <span className="block font-mono text-xs text-ink-faint">{nc!.producto.codigo}</span>
            </Dato>
            <Dato etiqueta="Sede">{nc!.sede.nombre}</Dato>
            <Dato etiqueta="Cantidad afectada">{entero(nc!.cantidad_afectada)}</Dato>
            <Dato etiqueta="Fecha de detección">{fecha(nc!.fecha_deteccion)}</Dato>
            <Dato etiqueta="Referencia">{nc!.referencia}</Dato>
            <Dato etiqueta="Proveedor">{nc!.proveedor}</Dato>
            <Dato etiqueta="Responsable">{nc!.responsable_nombre}</Dato>
            <Dato etiqueta="Resuelta">{nc!.resuelta_en ? fechaHora(nc!.resuelta_en) : null}</Dato>
            <Dato etiqueta="Cerrada">{nc!.cerrada_en ? fechaHora(nc!.cerrada_en) : null}</Dato>
          </dl>
          <div>
            <h3 className="mb-1 text-[13px] font-semibold uppercase tracking-wide text-ink-faint">Descripción</h3>
            <p className="whitespace-pre-line text-sm text-ink">{nc!.descripcion}</p>
          </div>
          {nc!.observacion_origen && (
            <Aviso tipo="info" titulo={`Observación de la entrada de la que nació${nc!.entrada ? ` (#${nc!.entrada.numero})` : ""}`}>
              <span className="whitespace-pre-line">{nc!.observacion_origen}</span>
            </Aviso>
          )}
          {nc!.solucion && (
            <Aviso tipo="exito" titulo="Solución">
              <span className="whitespace-pre-line">{nc!.solucion}</span>
            </Aviso>
          )}
          <Aviso tipo="info">{AVISO_SIN_INVENTARIO}</Aviso>
          {nc!.puede_gestionar && nc!.estado !== "cerrado" && <FormularioGestionNc key={`${nc!.estado}-${nc!.historial.length}`} nc={nc!} />}
          <PanelAdjuntos entidad="no_conformidad" entidadId={nc!.id} archivos={nc!.archivos} puedeAdjuntar={nc!.puede_adjuntar} invalidar={INVALIDAR} />
          <section aria-label="Historial y observaciones" className="flex flex-col gap-4">
            <h3 className="text-[13px] font-semibold uppercase tracking-wide text-ink-faint">Historial y observaciones</h3>
            <LineaTiempo eventos={nc!.historial.map((e) => ({ ...e, texto: e.contenido }))} estados={ESTADO_NC} />
            {nc!.puede_observar && nc!.estado !== "cerrado" ? (
              <FormularioObservacion onEnviar={(t) => observar.mutateAsync(t)} />
            ) : (
              nc!.estado === "cerrado" && <p className="text-xs text-ink-faint">El caso está cerrado: ya no admite observaciones.</p>
            )}
          </section>
        </div>
      )}
    </Modal>
  );
}

/* ------------------------------------------------------------------------------ listado */

export function NoConformidades({ abrirDetalle, inicial, onAbrirEntrada }: { abrirDetalle?: number | null; inicial?: boolean; onAbrirEntrada?: (entradaId: number) => void }) {
  const { tieneAlguno, sesion } = useAuth();
  const sedes = useSedes(false);
  const { filtros, pagina, tamano, cambiar, irAPagina, limpiar, hayFiltros } = useFiltros({ estado: "", tipo: "", sede_id: "", desde: "", hasta: "", q: "" }, 15);
  const [nueva, setNueva] = useState(Boolean(inicial));
  const [abierta, setAbierta] = useState<number | null>(abrirDetalle ?? null);
  const verSedes = sesion?.rol.alcance === "empresa";

  const lista = useQuery({
    queryKey: ["calidad", "nc-lista", filtros, pagina],
    queryFn: () => apiCalidad.listarNc({ estado: filtros.estado, tipo: filtros.tipo, sede_id: aNumero(filtros.sede_id), desde: filtros.desde, hasta: filtros.hasta, q: filtros.q, pagina, tamano }),
    placeholderData: keepPreviousData,
  });

  return (
    <>
      <Card>
        <BarraFiltros hayFiltros={hayFiltros} onLimpiar={limpiar}>
          <Busqueda valor={filtros.q} onCambiar={(q) => cambiar({ q })} placeholder="Producto, código o número…" etiqueta="Buscar no conformidades" />
          <FiltroSelect etiqueta="Estado" value={filtros.estado} onChange={(e) => cambiar({ estado: e.target.value })}>
            <option value="">Todos los estados</option>
            {Object.entries(ESTADO_NC).map(([k, t]) => (
              <option key={k} value={k}>
                {t.etiqueta}
              </option>
            ))}
          </FiltroSelect>
          <FiltroSelect etiqueta="Tipo" value={filtros.tipo} onChange={(e) => cambiar({ tipo: e.target.value })}>
            <option value="">Todos los tipos</option>
            {Object.entries(TIPO_NC).map(([k, n]) => (
              <option key={k} value={k}>
                {n}
              </option>
            ))}
          </FiltroSelect>
          {verSedes && (
            <FiltroSelect etiqueta="Sede" value={filtros.sede_id} onChange={(e) => cambiar({ sede_id: e.target.value })}>
              <option value="">Todas las sedes</option>
              {sedes.data?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nombre}
                </option>
              ))}
            </FiltroSelect>
          )}
          <FiltroFecha etiqueta="Desde" value={filtros.desde} max={filtros.hasta || undefined} onChange={(e) => cambiar({ desde: e.target.value })} />
          <FiltroFecha etiqueta="Hasta" value={filtros.hasta} min={filtros.desde || undefined} onChange={(e) => cambiar({ hasta: e.target.value })} />
          {tieneAlguno("calidad.reportar", "calidad.gestionar") && (
            <Button className="ml-auto" tamano="sm" icono={<Plus className="size-4" aria-hidden />} onClick={() => setNueva(true)}>
              Reportar no conformidad
            </Button>
          )}
        </BarraFiltros>
        <Tabla<NoConformidadResumen>
          descripcion="No conformidades"
          idDe={(n) => n.id}
          filas={lista.data?.items}
          cargando={lista.isFetching}
          error={lista.error}
          onReintentar={() => lista.refetch()}
          onFila={(n) => setAbierta(n.id)}
          vacio={{ titulo: hayFiltros ? "Sin resultados" : "Aún no hay no conformidades", descripcion: hayFiltros ? "Prueba con otros filtros." : "Cuando se reporte una no conformidad aparecerá aquí." }}
          columnas={[
            { clave: "numero", encabezado: "N.°", celda: (n) => <span className="tabular font-semibold">#{n.numero}</span> },
            {
              clave: "producto",
              encabezado: "Producto",
              celda: (n) => (
                <div className="min-w-0">
                  <p className="truncate font-medium">{n.producto.nombre}</p>
                  <p className="font-mono text-xs text-ink-faint">{n.producto.codigo}</p>
                </div>
              ),
            },
            { clave: "tipo", encabezado: "Tipo", desde: "md", celda: (n) => <span className="text-ink-dim">{etiqueta(TIPO_NC, n.tipo)}</span> },
            { clave: "cant", encabezado: "Afectadas", alinear: "derecha", desde: "sm", celda: (n) => <span className="tabular">{entero(n.cantidad_afectada)}</span> },
            { clave: "estado", encabezado: "Estado", celda: (n) => <InsigniaEstadoNc valor={n.estado} /> },
            {
              clave: "origen",
              encabezado: "Entrada",
              desde: "lg",
              celda: (n) => (n.entrada ? <span className="tabular text-accent-light">#{n.entrada.numero}</span> : <span className="text-ink-faint">—</span>),
            },
            { clave: "sede", encabezado: "Sede", desde: "lg", celda: (n) => <span className="text-ink-dim">{n.sede.nombre}</span> },
            { clave: "fecha", encabezado: "Detección", desde: "sm", celda: (n) => <span className="whitespace-nowrap text-ink-dim">{fecha(n.fecha_deteccion)}</span> },
            { clave: "hist", encabezado: "Obs.", alinear: "derecha", desde: "lg", celda: (n) => <span className="tabular text-ink-faint" title="Observaciones en el historial">{n.observaciones}</span> },
          ]}
        />
        {lista.data && <Paginacion pagina={lista.data.pagina} paginas={lista.data.paginas} total={lista.data.total} tamano={lista.data.tamano} onCambiar={irAPagina} />}
      </Card>
      {nueva && <DialogoNuevaNoConformidad onCerrar={() => setNueva(false)} />}
      {abierta !== null && <DetalleNoConformidad id={abierta} onCerrar={() => setAbierta(null)} onAbrirEntrada={onAbrirEntrada} />}
    </>
  );
}
