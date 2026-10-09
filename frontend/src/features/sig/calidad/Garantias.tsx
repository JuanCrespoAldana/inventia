import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { CheckCircle2, Link2, Plus } from "lucide-react";
import { apiVentas } from "@/api/operaciones";
import { apiCalidad, apiEntradas } from "@/api/sig";
import { useAuth } from "@/auth/AuthContext";
import { PanelAdjuntos, SelectorArchivos, subirArchivos } from "@/components/sig/Adjuntos";
import { LineaTiempo } from "@/components/sig/LineaTiempo";
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
import { DOCUMENTO_GARANTIA, estado, ESTADO_GARANTIA, etiqueta } from "@/lib/etiquetas";
import { entero, fecha, fechaHora, hoyISO } from "@/lib/format";
import type { GarantiaCrear, GarantiaDetalle, GarantiaGestionar, GarantiaResumen, ProductoResumen } from "@/types/api";
import { AVISO_SIN_INVENTARIO, Dato, FormularioObservacion, SelectorResponsable } from "./comunes";
import { requisitoGarantia, siguientesGarantia } from "./reglas";

const INVALIDAR = [["calidad"]];

export function InsigniaEstadoGarantia({ valor }: { valor: string }) {
  const e = estado(ESTADO_GARANTIA, valor);
  return <Badge tono={e.tono}>{e.etiqueta}</Badge>;
}

function Vigencia({ enGarantia, hasta }: { enGarantia: boolean | null | undefined; hasta?: string | null }) {
  if (enGarantia === null || enGarantia === undefined) return <span className="text-ink-faint">Sin vigencia registrada</span>;
  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <Badge tono={enGarantia ? "success" : "danger"}>{enGarantia ? "En garantía" : "Garantía vencida"}</Badge>
      {hasta && <span className="text-xs text-ink-faint">hasta {fecha(hasta)}</span>}
    </span>
  );
}

/* ------------------------------------------------------------------------------ nueva garantía */

export function DialogoNuevaGarantia({ onCerrar }: { onCerrar: () => void }) {
  const { sesion } = useAuth();
  const sedes = useSedes();
  const sedeFija = sesion?.rol.alcance === "sede" && sesion.sede !== null;

  const [producto, setProducto] = useState<ProductoResumen | null>(null);
  const [sedeId, setSedeId] = useState("");
  const [cantidad, setCantidad] = useState("1");
  const [documentoTipo, setDocumentoTipo] = useState<GarantiaCrear["documento_tipo"]>("factura_compra");
  const [documento, setDocumento] = useState("");
  const [fechaCompra, setFechaCompra] = useState("");
  const [garantiaHasta, setGarantiaHasta] = useState("");
  const [fechaReporte, setFechaReporte] = useState(hoyISO());
  const [defecto, setDefecto] = useState("");
  const [proveedor, setProveedor] = useState("");
  const [observaciones, setObservaciones] = useState("");
  const [archivos, setArchivos] = useState<File[]>([]);
  const [intento, setIntento] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [creada, setCreada] = useState<{ numero: number; fallos: string[] } | null>(null);

  const usaNumero = documentoTipo === "entrada_inventario" || documentoTipo === "venta";
  const errores = {
    producto: producto ? null : "Elige el producto con la falla",
    sede: sedeFija || usaNumero || sedeId ? null : "Elige la sede",
    cantidad: /^\d+$/.test(cantidad.trim()) && Number(cantidad) >= 1 ? null : "Escribe una cantidad entera mayor que 0",
    documento: documento.trim().length === 0 ? (usaNumero ? "Escribe el número del documento" : "Indica el número o la referencia del documento") : usaNumero && !/^\d+$/.test(documento.trim()) ? "Escribe solo el número" : null,
    fechaCompra: !fechaCompra ? "Indica la fecha de compra o recepción" : fechaCompra > hoyISO() ? "No puede ser futura" : fechaReporte && fechaCompra > fechaReporte ? "No puede ser posterior al reporte" : null,
    garantiaHasta: garantiaHasta && fechaCompra && garantiaHasta < fechaCompra ? "No puede ser anterior a la compra" : null,
    fechaReporte: !fechaReporte ? "Indica la fecha del reporte" : fechaReporte > hoyISO() ? "No puede ser futura" : null,
    defecto: defecto.trim().length >= 10 ? null : "Describe el defecto (mínimo 10 caracteres)",
  };
  const hayErrores = Object.values(errores).some(Boolean);

  const crear = useMutacion(
    async () => {
      let entradaId: number | null = null;
      let ventaId: number | null = null;
      if (documentoTipo === "entrada_inventario") {
        const r = await apiEntradas.listar({ numero: Number(documento), sede_id: sedeId ? Number(sedeId) : "", tamano: 5 });
        const hallada = r.items.find((e) => e.numero === Number(documento));
        if (!hallada) throw new Error(`No se encontró la entrada de inventario #${documento.trim()}.`);
        entradaId = hallada.id;
      } else if (documentoTipo === "venta") {
        const r = await apiVentas.listar({ numero: Number(documento), sede_id: sedeId ? Number(sedeId) : "", tamano: 5 });
        const hallada = r.items.find((v) => v.numero === Number(documento));
        if (!hallada) throw new Error(`No se encontró la venta #${documento.trim()}.`);
        ventaId = hallada.id;
      }
      const g = await apiCalidad.crearGarantia({
        producto_id: producto!.id,
        sede_id: usaNumero || sedeFija ? null : Number(sedeId),
        cantidad: Number(cantidad),
        documento_tipo: documentoTipo,
        documento_referencia: usaNumero ? null : documento.trim(),
        entrada_id: entradaId,
        venta_id: ventaId,
        fecha_compra: fechaCompra,
        garantia_hasta: garantiaHasta || null,
        fecha_reporte: fechaReporte,
        defecto: defecto.trim(),
        proveedor: proveedor.trim() || null,
        observaciones: observaciones.trim() || null,
      });
      const fallos = archivos.length > 0 ? await subirArchivos("garantia", g.id, archivos) : [];
      return { numero: g.numero, fallos };
    },
    { invalidar: INVALIDAR, avisarError: false, onExito: setCreada },
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
      <Modal abierto onCerrar={onCerrar} titulo="Garantía reportada" pie={<Button onClick={onCerrar}>Entendido</Button>}>
        <div className="flex flex-col items-center gap-3 py-2 text-center">
          <div className="flex size-12 items-center justify-center rounded-2xl bg-success-dim text-success ring-1 ring-success/30">
            <CheckCircle2 className="size-6" aria-hidden />
          </div>
          <p className="font-display text-lg font-semibold text-ink">Se registró la garantía #{creada.numero}</p>
          <p className="max-w-sm text-sm text-ink-dim">El inventario no se modificó. Calidad la revisará y podrás seguir su estado desde el listado.</p>
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

  return (
    <Modal
      abierto
      onCerrar={onCerrar}
      bloqueado={crear.isPending}
      ancho="lg"
      titulo="Reportar garantía"
      descripcion="Registra un producto con falla que está cubierto (o podría estarlo) por la garantía del fabricante o proveedor."
      pie={
        <>
          <Button variante="ghost" onClick={onCerrar} disabled={crear.isPending}>
            Cancelar
          </Button>
          <Button onClick={() => void enviar()} cargando={crear.isPending}>
            Registrar garantía
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <Aviso tipo="info">{AVISO_SIN_INVENTARIO}</Aviso>
        {error && <Aviso tipo="error">{error}</Aviso>}

        {producto ? (
          <div className="flex items-end justify-between gap-3 rounded-(--radius-control) border border-line bg-surface-2 px-4 py-2.5">
            <div className="min-w-0">
              <p className="text-xs font-medium text-ink-faint">Producto con la falla</p>
              <p className="truncate text-sm font-semibold text-ink">{producto.nombre}</p>
              <p className="font-mono text-xs text-ink-faint">{producto.codigo}</p>
            </div>
            <Button variante="ghost" tamano="sm" onClick={() => setProducto(null)}>
              Cambiar
            </Button>
          </div>
        ) : (
          <div>
            <SelectorProducto etiqueta="Producto con la falla" origen={["catalogo"]} buscar={buscarEnCatalogo} onElegir={(o) => setProducto(o.producto)} />
            {intento && errores.producto && <p role="alert" className="mt-1.5 text-xs text-danger">{errores.producto}</p>}
          </div>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          {!sedeFija && (
            <Select etiqueta="Sede" required value={sedeId} onChange={(e) => setSedeId(e.target.value)} error={intento ? (errores.sede ?? undefined) : undefined} ayuda={usaNumero ? "Opcional: ayuda a ubicar el documento; si no, se toma del documento." : undefined}>
              <option value="">{usaNumero ? "Cualquiera (según el documento)" : "Elige la sede"}</option>
              {sedes.data?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nombre}
                </option>
              ))}
            </Select>
          )}
          <Input etiqueta="Cantidad afectada" required inputMode="numeric" value={cantidad} onChange={(e) => setCantidad(e.target.value)} error={intento ? (errores.cantidad ?? undefined) : undefined} />
          <Select etiqueta="Documento que respalda la compra" required value={documentoTipo} onChange={(e) => { setDocumentoTipo(e.target.value as GarantiaCrear["documento_tipo"]); setDocumento(""); }}>
            {Object.entries(DOCUMENTO_GARANTIA).map(([k, n]) => (
              <option key={k} value={k}>
                {n}
              </option>
            ))}
          </Select>
          <Input
            etiqueta={documentoTipo === "entrada_inventario" ? "N.° de la entrada de inventario" : documentoTipo === "venta" ? "N.° de la venta" : "N.° o referencia del documento"}
            required
            inputMode={usaNumero ? "numeric" : undefined}
            maxLength={100}
            value={documento}
            onChange={(e) => setDocumento(e.target.value)}
            error={intento ? (errores.documento ?? undefined) : undefined}
            ayuda={usaNumero ? "Se busca en el sistema y queda vinculada." : undefined}
          />
          <Input etiqueta="Fecha de compra o recepción" required type="date" max={hoyISO()} value={fechaCompra} onChange={(e) => setFechaCompra(e.target.value)} error={intento ? (errores.fechaCompra ?? undefined) : undefined} />
          <Input etiqueta="La garantía cubre hasta (opcional)" type="date" min={fechaCompra || undefined} value={garantiaHasta} onChange={(e) => setGarantiaHasta(e.target.value)} error={intento ? (errores.garantiaHasta ?? undefined) : undefined} ayuda="Según la ficha del producto o el contrato con el proveedor." />
          <Input etiqueta="Fecha del reporte" required type="date" max={hoyISO()} value={fechaReporte} onChange={(e) => setFechaReporte(e.target.value)} error={intento ? (errores.fechaReporte ?? undefined) : undefined} />
          <Input etiqueta="Proveedor o fabricante" maxLength={150} value={proveedor} onChange={(e) => setProveedor(e.target.value)} />
        </div>
        <Textarea etiqueta="Defecto o falla" required rows={4} maxLength={2000} value={defecto} onChange={(e) => setDefecto(e.target.value)} placeholder="Qué falla presenta, desde cuándo y en qué condiciones" error={intento ? (errores.defecto ?? undefined) : undefined} />
        <Textarea etiqueta="Observaciones (opcional)" rows={2} maxLength={1000} value={observaciones} onChange={(e) => setObservaciones(e.target.value)} />
        <SelectorArchivos archivos={archivos} onChange={setArchivos} />
      </div>
    </Modal>
  );
}

/* ------------------------------------------------------------------------------ detalle */

function FormularioGestionGarantia({ g }: { g: GarantiaDetalle }) {
  const siguientes = siguientesGarantia(g.estado);
  const [nuevoEstado, setNuevoEstado] = useState("");
  const [responsable, setResponsable] = useState("");
  const [proveedor, setProveedor] = useState(g.proveedor ?? "");
  const [fechaEnvio, setFechaEnvio] = useState(g.fecha_envio_proveedor ?? "");
  const [respuesta, setRespuesta] = useState(g.respuesta_proveedor ?? "");
  const [fechaRespuesta, setFechaRespuesta] = useState(g.fecha_respuesta_proveedor ?? "");
  const [solucion, setSolucion] = useState(g.solucion ?? "");
  const [fechaSolucion, setFechaSolucion] = useState(g.fecha_solucion ?? "");
  const [comentario, setComentario] = useState("");
  const [error, setError] = useState<string | null>(null);

  const cambioTexto = (nuevo: string, previo: string | null) => (nuevo.trim() !== (previo ?? "") ? nuevo.trim() : null);
  const cambioFecha = (nuevo: string, previo: string | null) => (nuevo && nuevo !== (previo ?? "") ? nuevo : null);

  const cuerpo: GarantiaGestionar = {
    estado: (nuevoEstado || null) as GarantiaGestionar["estado"],
    responsable_id: responsable ? Number(responsable) : null,
    proveedor: cambioTexto(proveedor, g.proveedor),
    fecha_envio_proveedor: cambioFecha(fechaEnvio, g.fecha_envio_proveedor),
    respuesta_proveedor: cambioTexto(respuesta, g.respuesta_proveedor),
    fecha_respuesta_proveedor: cambioFecha(fechaRespuesta, g.fecha_respuesta_proveedor),
    solucion: cambioTexto(solucion, g.solucion),
    fecha_solucion: cambioFecha(fechaSolucion, g.fecha_solucion),
    comentario: comentario.trim() || null,
  };
  const hayCambios = Object.values(cuerpo).some((v) => v !== null && v !== undefined);
  const requisito = nuevoEstado ? requisitoGarantia(nuevoEstado, { proveedor, respuesta, solucion }) : null;

  const guardar = useMutacion(() => apiCalidad.gestionarGarantia(g.id, cuerpo), { exito: "Garantía actualizada.", invalidar: INVALIDAR, avisarError: false });

  return (
    <section aria-label="Gestionar garantía" className="flex flex-col gap-3 rounded-(--radius-control) border border-line bg-surface-2/50 p-4">
      <h3 className="text-[13px] font-semibold uppercase tracking-wide text-ink-faint">Gestionar con el proveedor</h3>
      {error && <Aviso tipo="error">{error}</Aviso>}
      {requisito && <Aviso tipo="aviso">{requisito}</Aviso>}
      <div className="grid gap-3 sm:grid-cols-2">
        <Select etiqueta="Cambiar estado a" value={nuevoEstado} onChange={(e) => setNuevoEstado(e.target.value)}>
          <option value="">Mantener «{estado(ESTADO_GARANTIA, g.estado).etiqueta}»</option>
          {siguientes.map((e) => (
            <option key={e} value={e}>
              {ESTADO_GARANTIA[e].etiqueta}
            </option>
          ))}
        </Select>
        <SelectorResponsable valor={responsable} onChange={setResponsable} actual={g.responsable_nombre} />
        <Input etiqueta="Proveedor" maxLength={150} value={proveedor} onChange={(e) => setProveedor(e.target.value)} />
        <Input etiqueta="Fecha de envío al proveedor" type="date" max={hoyISO()} value={fechaEnvio} onChange={(e) => setFechaEnvio(e.target.value)} ayuda="Si no la indicas, se toma la de hoy al marcarla como enviada." />
      </div>
      <Textarea etiqueta="Respuesta del proveedor" rows={2} maxLength={2000} value={respuesta} onChange={(e) => setRespuesta(e.target.value)} ayuda="Obligatoria para aprobar o rechazar." />
      <div className="grid gap-3 sm:grid-cols-2">
        <Input etiqueta="Fecha de la respuesta" type="date" max={hoyISO()} value={fechaRespuesta} onChange={(e) => setFechaRespuesta(e.target.value)} />
        <Input etiqueta="Fecha de la solución" type="date" max={hoyISO()} value={fechaSolucion} onChange={(e) => setFechaSolucion(e.target.value)} />
      </div>
      <Textarea etiqueta="Solución (reposición, reparación, nota crédito…)" rows={2} maxLength={2000} value={solucion} onChange={(e) => setSolucion(e.target.value)} ayuda="Obligatoria para marcarla como solucionada." />
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

export function DetalleGarantia({ id, onCerrar, onAbrirEntrada }: { id: number; onCerrar: () => void; onAbrirEntrada?: (entradaId: number) => void }) {
  const consulta = useQuery({ queryKey: ["calidad", "garantia", id], queryFn: () => apiCalidad.detalleGarantia(id) });
  const observar = useMutacion((texto: string) => apiCalidad.observarGarantia(id, texto), { exito: "Observación agregada.", invalidar: INVALIDAR, avisarError: false });
  const g = consulta.data;

  return (
    <Modal
      abierto
      onCerrar={onCerrar}
      ancho="xl"
      titulo={g ? `Garantía #${g.numero}` : "Garantía"}
      descripcion={g ? `Reportada por ${g.usuario_nombre ?? "—"} · ${fechaHora(g.created_at)}` : undefined}
      pie={<Button variante="secondary" onClick={onCerrar}>Cerrar</Button>}
    >
      {consulta.isPending ? (
        <PanelCargando etiqueta="Cargando la garantía…" />
      ) : consulta.isError ? (
        <EstadoError error={consulta.error} onReintentar={() => consulta.refetch()} />
      ) : (
        <div className="flex flex-col gap-6">
          <div className="flex flex-wrap items-center gap-2">
            <InsigniaEstadoGarantia valor={g!.estado} />
            <Vigencia enGarantia={g!.en_garantia} hasta={g!.garantia_hasta} />
            {g!.entrada && (
              <button
                type="button"
                onClick={() => onAbrirEntrada?.(g!.entrada!.id)}
                disabled={!onAbrirEntrada}
                className="inline-flex items-center gap-1 rounded-full bg-accent-dim px-2.5 py-0.5 text-xs font-semibold text-accent-light ring-1 ring-inset ring-accent/30 enabled:hover:underline"
              >
                <Link2 className="size-3" aria-hidden />
                Entrada #{g!.entrada.numero}
              </button>
            )}
          </div>
          <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Dato etiqueta="Producto">
              {g!.producto.nombre}
              <span className="block font-mono text-xs text-ink-faint">{g!.producto.codigo}</span>
            </Dato>
            <Dato etiqueta="Sede">{g!.sede.nombre}</Dato>
            <Dato etiqueta="Cantidad">{entero(g!.cantidad)}</Dato>
            <Dato etiqueta="Documento">
              {etiqueta(DOCUMENTO_GARANTIA, g!.documento_tipo)}
              {g!.documento_referencia ? ` · ${g!.documento_referencia}` : g!.venta_numero ? ` · venta #${g!.venta_numero}` : g!.entrada ? ` · entrada #${g!.entrada.numero}` : ""}
            </Dato>
            <Dato etiqueta="Compra o recepción">{fecha(g!.fecha_compra)}</Dato>
            <Dato etiqueta="Fecha del reporte">{fecha(g!.fecha_reporte)}</Dato>
            <Dato etiqueta="Proveedor">{g!.proveedor}</Dato>
            <Dato etiqueta="Responsable">{g!.responsable_nombre}</Dato>
            <Dato etiqueta="Enviada al proveedor">{g!.fecha_envio_proveedor ? fecha(g!.fecha_envio_proveedor) : null}</Dato>
            <Dato etiqueta="Respuesta del proveedor">{g!.fecha_respuesta_proveedor ? fecha(g!.fecha_respuesta_proveedor) : null}</Dato>
            <Dato etiqueta="Fecha de solución">{g!.fecha_solucion ? fecha(g!.fecha_solucion) : null}</Dato>
            <Dato etiqueta="Cerrada">{g!.cerrada_en ? fechaHora(g!.cerrada_en) : null}</Dato>
          </dl>
          <div>
            <h3 className="mb-1 text-[13px] font-semibold uppercase tracking-wide text-ink-faint">Defecto o falla</h3>
            <p className="whitespace-pre-line text-sm text-ink">{g!.defecto}</p>
          </div>
          {g!.respuesta_proveedor && (
            <Aviso tipo="info" titulo="Respuesta del proveedor">
              <span className="whitespace-pre-line">{g!.respuesta_proveedor}</span>
            </Aviso>
          )}
          {g!.solucion && (
            <Aviso tipo="exito" titulo="Solución">
              <span className="whitespace-pre-line">{g!.solucion}</span>
            </Aviso>
          )}
          <Aviso tipo="info">{AVISO_SIN_INVENTARIO}</Aviso>
          {g!.puede_gestionar && g!.estado !== "cerrada" && <FormularioGestionGarantia key={`${g!.estado}-${g!.historial.length}`} g={g!} />}
          <PanelAdjuntos entidad="garantia" entidadId={g!.id} archivos={g!.archivos} puedeAdjuntar={g!.puede_adjuntar} invalidar={INVALIDAR} />
          <section aria-label="Historial y observaciones" className="flex flex-col gap-4">
            <h3 className="text-[13px] font-semibold uppercase tracking-wide text-ink-faint">Historial y observaciones</h3>
            <LineaTiempo eventos={g!.historial.map((e) => ({ ...e, texto: e.contenido }))} estados={ESTADO_GARANTIA} />
            {g!.puede_observar && g!.estado !== "cerrada" ? (
              <FormularioObservacion onEnviar={(t) => observar.mutateAsync(t)} />
            ) : (
              g!.estado === "cerrada" && <p className="text-xs text-ink-faint">La garantía está cerrada: ya no admite observaciones.</p>
            )}
          </section>
        </div>
      )}
    </Modal>
  );
}

/* ------------------------------------------------------------------------------ listado */

export function Garantias({ abrirDetalle, onAbrirEntrada }: { abrirDetalle?: number | null; onAbrirEntrada?: (entradaId: number) => void }) {
  const { tieneAlguno, sesion } = useAuth();
  const sedes = useSedes(false);
  const { filtros, pagina, tamano, cambiar, irAPagina, limpiar, hayFiltros } = useFiltros({ estado: "", sede_id: "", proveedor: "", desde: "", hasta: "", q: "" }, 15);
  const [nueva, setNueva] = useState(false);
  const [abierta, setAbierta] = useState<number | null>(abrirDetalle ?? null);
  const verSedes = sesion?.rol.alcance === "empresa";

  const lista = useQuery({
    queryKey: ["calidad", "garantias-lista", filtros, pagina],
    queryFn: () => apiCalidad.listarGarantias({ estado: filtros.estado, sede_id: aNumero(filtros.sede_id), proveedor: filtros.proveedor, desde: filtros.desde, hasta: filtros.hasta, q: filtros.q, pagina, tamano }),
    placeholderData: keepPreviousData,
  });

  return (
    <>
      <Card>
        <BarraFiltros hayFiltros={hayFiltros} onLimpiar={limpiar}>
          <Busqueda valor={filtros.q} onCambiar={(q) => cambiar({ q })} placeholder="Producto, documento o número…" etiqueta="Buscar garantías" />
          <FiltroSelect etiqueta="Estado" value={filtros.estado} onChange={(e) => cambiar({ estado: e.target.value })}>
            <option value="">Todos los estados</option>
            {Object.entries(ESTADO_GARANTIA).map(([k, t]) => (
              <option key={k} value={k}>
                {t.etiqueta}
              </option>
            ))}
          </FiltroSelect>
          <Busqueda valor={filtros.proveedor} onCambiar={(proveedor) => cambiar({ proveedor })} placeholder="Proveedor…" etiqueta="Filtrar por proveedor" className="sm:max-w-44" />
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
              Reportar garantía
            </Button>
          )}
        </BarraFiltros>
        <Tabla<GarantiaResumen>
          descripcion="Garantías"
          idDe={(g) => g.id}
          filas={lista.data?.items}
          cargando={lista.isFetching}
          error={lista.error}
          onReintentar={() => lista.refetch()}
          onFila={(g) => setAbierta(g.id)}
          vacio={{ titulo: hayFiltros ? "Sin resultados" : "Aún no hay garantías", descripcion: hayFiltros ? "Prueba con otros filtros." : "Cuando se reporte una garantía aparecerá aquí." }}
          columnas={[
            { clave: "numero", encabezado: "N.°", celda: (g) => <span className="tabular font-semibold">#{g.numero}</span> },
            {
              clave: "producto",
              encabezado: "Producto",
              celda: (g) => (
                <div className="min-w-0">
                  <p className="truncate font-medium">{g.producto.nombre}</p>
                  <p className="font-mono text-xs text-ink-faint">{g.producto.codigo}</p>
                </div>
              ),
            },
            { clave: "estado", encabezado: "Estado", celda: (g) => <InsigniaEstadoGarantia valor={g.estado} /> },
            { clave: "vig", encabezado: "Vigencia", desde: "md", celda: (g) => <Vigencia enGarantia={g.en_garantia} /> },
            { clave: "prov", encabezado: "Proveedor", desde: "lg", celda: (g) => <span className="text-ink-dim">{g.proveedor ?? "—"}</span> },
            { clave: "sede", encabezado: "Sede", desde: "lg", celda: (g) => <span className="text-ink-dim">{g.sede.nombre}</span> },
            { clave: "fecha", encabezado: "Reporte", desde: "sm", celda: (g) => <span className="whitespace-nowrap text-ink-dim">{fecha(g.fecha_reporte)}</span> },
            { clave: "resp", encabezado: "Responsable", desde: "lg", celda: (g) => <span className="text-ink-dim">{g.responsable_nombre ?? "—"}</span> },
          ]}
        />
        {lista.data && <Paginacion pagina={lista.data.pagina} paginas={lista.data.paginas} total={lista.data.total} tamano={lista.data.tamano} onCambiar={irAPagina} />}
      </Card>
      {nueva && <DialogoNuevaGarantia onCerrar={() => setNueva(false)} />}
      {abierta !== null && <DetalleGarantia id={abierta} onCerrar={() => setAbierta(null)} onAbrirEntrada={onAbrirEntrada} />}
    </>
  );
}
