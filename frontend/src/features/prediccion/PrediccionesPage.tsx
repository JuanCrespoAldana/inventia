import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { Loader2, Play } from "lucide-react";
import { apiPredicciones } from "@/api/analitica";
import { useAuth } from "@/auth/AuthContext";
import { Aviso } from "@/components/ui/Aviso";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Tabla } from "@/components/ui/DataTable";
import { EstadoVacio } from "@/components/ui/EstadoVacio";
import { FiltroSelect, Input } from "@/components/ui/Field";
import { BarraFiltros } from "@/components/ui/FiltrosBarra";
import { Modal } from "@/components/ui/Modal";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { Paginacion } from "@/components/ui/Pagination";
import { Busqueda } from "@/components/ui/SearchInput";
import { Pestanas } from "@/components/ui/Tabs";
import { useSedes } from "@/hooks/useCatalogos";
import { aNumero, useFiltros } from "@/hooks/useFiltros";
import { useMutacion } from "@/hooks/useMutacion";
import { CONFIANZA, ESTADO_EJECUCION, estado } from "@/lib/etiquetas";
import { decimal, entero, fecha, fechaHora, hace, porcentaje } from "@/lib/format";
import { mensajeDeError } from "@/lib/errors";
import type { Ejecucion, Prediccion } from "@/types/api";
import { DetalleSerieModal } from "./DetalleSerieModal";
import { nombreModelo, type MetricasPrediccion, type OmitidaDetalle, type ResumenEjecucion } from "./tipos";

type Pestana = "pronosticos" | "omitidas" | "ejecuciones" | "metodo";

const EN_CURSO = ["en_cola", "ejecutando"];

function DialogoEjecutar({ onCerrar }: { onCerrar: () => void }) {
  const [horizonte, setHorizonte] = useState("");
  const [error, setError] = useState<string | null>(null);
  const valido = horizonte === "" || (/^\d+$/.test(horizonte) && Number(horizonte) >= 1 && Number(horizonte) <= 90);
  const ejecutar = useMutacion(() => apiPredicciones.ejecutar(horizonte === "" ? null : Number(horizonte)), {
    exito: "Predicción en marcha. Se calcula en segundo plano; puede seguir trabajando.",
    invalidar: [["predicciones"]],
    avisarError: false,
    onExito: onCerrar,
  });
  return (
    <Modal
      abierto
      onCerrar={onCerrar}
      bloqueado={ejecutar.isPending}
      titulo="Generar predicción de demanda"
      descripcion="Usa las ventas registradas de cada producto en cada sede."
      pie={
        <>
          <Button variante="ghost" onClick={onCerrar} disabled={ejecutar.isPending}>Cancelar</Button>
          <Button
            cargando={ejecutar.isPending}
            disabled={!valido}
            icono={<Play className="size-4" aria-hidden />}
            onClick={async () => {
              setError(null);
              try {
                await ejecutar.mutateAsync();
              } catch (e) {
                setError(mensajeDeError(e));
              }
            }}
          >
            Generar
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <Aviso tipo="error">{error}</Aviso>}
        <Input
          etiqueta="Horizonte (días)"
          inputMode="numeric"
          placeholder="Predeterminado de la empresa"
          value={horizonte}
          onChange={(e) => setHorizonte(e.target.value.replace(/\D/g, ""))}
          error={valido ? undefined : "Escriba un número de días entre 1 y 90"}
          ayuda="Días hacia adelante que se pronostican. Déjelo vacío para usar el valor configurado en Empresa."
        />
        <Aviso tipo="info">
          Solo se pronostican series con al menos 28 días de historia y 5 días con ventas. Las demás se omiten y se explica el motivo; no se inventan cifras. Solo puede haber una ejecución a la vez.
        </Aviso>
      </div>
    </Modal>
  );
}

function ResumenUltima({ e }: { e: Ejecucion }) {
  const r = e.resumen as ResumenEjecucion;
  const est = estado(ESTADO_EJECUCION, e.estado);
  const enCurso = EN_CURSO.includes(e.estado);
  return (
    <Card className="mb-6">
      <CardHeader
        titulo="Última ejecución"
        descripcion={`Solicitada ${hace(e.creada_en)}${e.solicitada_por ? ` por ${e.solicitada_por}` : ""}${e.fecha_corte ? ` · datos hasta el ${fecha(e.fecha_corte)}` : ""}`}
        accion={
          <Badge tono={est.tono}>
            {enCurso && <Loader2 className="size-3 animate-spin" aria-hidden />}
            {est.etiqueta}
          </Badge>
        }
      />
      {enCurso && (
        <div className="px-5 py-6" role="status">
          <p className="text-sm text-ink-dim">Calculando pronósticos. Esta pantalla se actualiza sola cuando termina.</p>
          <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-3" aria-hidden>
            <div className="h-full w-1/3 animate-pulse rounded-full bg-accent" />
          </div>
        </div>
      )}
      {e.estado === "fallida" && (
        <div className="p-5">
          <Aviso tipo="error" titulo="La ejecución falló">{e.error ?? "Ocurrió un error durante el cálculo."}</Aviso>
        </div>
      )}
      {e.estado === "completada" && (
        <div className="p-5">
          {r.advertencia_global && <Aviso tipo="aviso" className="mb-5">{r.advertencia_global}</Aviso>}
          {r.truncado && <Aviso tipo="aviso" className="mb-5">Se alcanzó el límite de series por ejecución; algunas combinaciones quedaron fuera.</Aviso>}
          <dl className="grid gap-x-6 gap-y-5 sm:grid-cols-2 lg:grid-cols-5">
            <div>
              <dt className="text-xs text-ink-faint">Series con pronóstico</dt>
              <dd className="tabular mt-1 font-display text-2xl font-semibold">{entero(r.series_con_prediccion)}</dd>
              <dd className="text-xs text-ink-faint">de {entero(r.series_total)} evaluadas</dd>
            </div>
            <div>
              <dt className="text-xs text-ink-faint">Omitidas por datos insuficientes</dt>
              <dd className="tabular mt-1 font-display text-2xl font-semibold">{entero(r.series_omitidas)}</dd>
            </div>
            <div>
              <dt className="text-xs text-ink-faint">Error global (WAPE)</dt>
              <dd className="tabular mt-1 font-display text-2xl font-semibold">{r.wape_global == null ? "—" : porcentaje(r.wape_global * 100)}</dd>
              <dd className="text-xs text-ink-faint">Línea base: {r.wape_linea_base_global == null ? "—" : porcentaje(r.wape_linea_base_global * 100)}</dd>
            </div>
            <div>
              <dt className="text-xs text-ink-faint">Mejora frente a la línea base</dt>
              <dd className="tabular mt-1 font-display text-2xl font-semibold">{r.mejora_vs_linea_base_pct == null ? "—" : porcentaje(r.mejora_vs_linea_base_pct)}</dd>
              <dd className="text-xs text-ink-faint">{entero(r.series_mejor_que_linea_base ?? 0)} series usan un modelo mejor que la línea base</dd>
            </div>
            <div>
              <dt className="text-xs text-ink-faint">Confianza</dt>
              <dd className="mt-1 flex flex-wrap gap-1.5">
                {Object.entries(r.series_por_confianza ?? {}).map(([k, n]) => (
                  <Badge key={k} tono={estado(CONFIANZA, k).tono}>{estado(CONFIANZA, k).etiqueta}: {n}</Badge>
                ))}
              </dd>
            </div>
          </dl>
        </div>
      )}
    </Card>
  );
}

function TablaPronosticos({ onAbrir }: { onAbrir: (p: Prediccion) => void }) {
  const { sesion } = useAuth();
  const sedes = useSedes(false);
  const { filtros, pagina, tamano, cambiar, irAPagina, limpiar, hayFiltros } = useFiltros({ sede_id: "", confianza: "", q: "", orden: "demanda" }, 20);
  const verSedes = sesion?.rol.alcance === "empresa";
  const lista = useQuery({
    queryKey: ["predicciones", "lista", filtros, pagina],
    queryFn: () => apiPredicciones.listar({ sede_id: aNumero(filtros.sede_id), confianza: filtros.confianza, q: filtros.q, orden: filtros.orden, pagina, tamano }),
    placeholderData: keepPreviousData,
  });
  return (
    <Card>
      <BarraFiltros hayFiltros={hayFiltros} onLimpiar={limpiar}>
        <Busqueda valor={filtros.q} onCambiar={(q) => cambiar({ q })} placeholder="Buscar producto…" />
        {verSedes && (
          <FiltroSelect etiqueta="Sede" value={filtros.sede_id} onChange={(e) => cambiar({ sede_id: e.target.value })}>
            <option value="">Todas las sedes</option>
            {sedes.data?.map((s) => (
              <option key={s.id} value={s.id}>{s.nombre}</option>
            ))}
          </FiltroSelect>
        )}
        <FiltroSelect etiqueta="Confianza" value={filtros.confianza} onChange={(e) => cambiar({ confianza: e.target.value })}>
          <option value="">Toda confianza</option>
          {Object.entries(CONFIANZA).map(([k, c]) => (
            <option key={k} value={k}>{c.etiqueta}</option>
          ))}
        </FiltroSelect>
        <FiltroSelect etiqueta="Orden" value={filtros.orden} onChange={(e) => cambiar({ orden: e.target.value })}>
          <option value="demanda">Mayor demanda primero</option>
          <option value="producto">Por producto</option>
        </FiltroSelect>
      </BarraFiltros>
      <Tabla
        descripcion="Predicciones de demanda por producto y sede"
        idDe={(p) => p.id}
        filas={lista.data?.items}
        cargando={lista.isFetching}
        error={lista.error}
        onReintentar={() => lista.refetch()}
        onFila={onAbrir}
        vacio={{ titulo: hayFiltros ? "Sin resultados" : "Aún no hay predicciones", descripcion: hayFiltros ? "Pruebe con otros filtros." : "Genere una predicción para ver la demanda estimada de cada producto." }}
        columnas={[
          { clave: "producto", encabezado: "Producto", celda: (p) => <div><span className="font-medium">{p.producto.nombre}</span><span className="block font-mono text-xs text-ink-faint">{p.producto.codigo}</span></div> },
          { clave: "sede", encabezado: "Sede", desde: "md", celda: (p) => p.sede.nombre },
          {
            clave: "demanda",
            encabezado: "Demanda estimada",
            alinear: "derecha",
            celda: (p) => (
              <div className="tabular">
                <span className="font-semibold">{entero(Math.round(p.demanda_estimada))} u.</span>
                {p.limite_inferior != null && p.limite_superior != null && <span className="block text-xs text-ink-faint">{entero(Math.round(p.limite_inferior))}–{entero(Math.round(p.limite_superior))}</span>}
              </div>
            ),
          },
          { clave: "diaria", encabezado: "Por día", alinear: "derecha", desde: "lg", celda: (p) => <span className="tabular text-ink-dim">{decimal(p.demanda_diaria, 1)}</span> },
          { clave: "stock", encabezado: "Existencias", alinear: "derecha", desde: "sm", celda: (p) => <span className="tabular">{p.existencias_actuales == null ? "—" : entero(p.existencias_actuales)}</span> },
          {
            clave: "cobertura",
            encabezado: "Cobertura",
            alinear: "derecha",
            desde: "md",
            celda: (p) => <span className={`tabular ${p.cobertura_dias != null && p.cobertura_dias < 7 ? "font-semibold text-warning" : ""}`}>{p.cobertura_dias == null ? "—" : `${decimal(p.cobertura_dias, 1)} d`}</span>,
          },
          { clave: "modelo", encabezado: "Modelo", desde: "lg", celda: (p) => <span className="text-ink-dim">{nombreModelo(p.modelo)}</span> },
          { clave: "confianza", encabezado: "Confianza", celda: (p) => { const c = estado(CONFIANZA, p.confianza); return <Badge tono={c.tono}>{c.etiqueta}</Badge>; } },
          { clave: "wape", encabezado: "Error", alinear: "derecha", desde: "lg", celda: (p) => { const w = (p.metricas as MetricasPrediccion).wape; return <span className="tabular text-ink-dim">{w == null ? "—" : porcentaje(w * 100, 0)}</span>; } },
        ]}
      />
      {lista.data && <Paginacion pagina={lista.data.pagina} paginas={lista.data.paginas} total={lista.data.total} tamano={lista.data.tamano} onCambiar={irAPagina} />}
    </Card>
  );
}

function TablaOmitidas({ ejecucionId }: { ejecucionId: number }) {
  const detalle = useQuery({ queryKey: ["predicciones", "ejecucion", ejecucionId], queryFn: () => apiPredicciones.ejecucion(ejecucionId) });
  const r = (detalle.data?.resumen ?? {}) as ResumenEjecucion;
  const filas = r.omitidas ?? [];
  return (
    <Card>
      <CardHeader titulo="Series sin pronóstico" descripcion="Estas combinaciones no se pronosticaron porque no hay datos suficientes. Es preferible no estimar a inventar un número." />
      <Tabla<OmitidaDetalle>
        descripcion="Series omitidas de la última ejecución"
        idDe={(o) => `${o.sede_id}-${o.producto_id}`}
        filas={detalle.data ? filas : undefined}
        cargando={detalle.isPending}
        error={detalle.error}
        onReintentar={() => detalle.refetch()}
        vacio={{ titulo: "Todas las series tienen pronóstico", descripcion: "No se omitió ninguna combinación de producto y sede." }}
        columnas={[
          { clave: "producto", encabezado: "Producto", celda: (o) => <div><span className="font-medium">{o.producto ?? `#${o.producto_id}`}</span><span className="block font-mono text-xs text-ink-faint">{o.codigo}</span></div> },
          { clave: "sede", encabezado: "Sede", desde: "sm", celda: (o) => o.sede ?? `#${o.sede_id}` },
          { clave: "motivo", encabezado: "Motivo", className: "min-w-64", celda: (o) => <span className="text-ink-dim">{o.motivo}</span> },
          { clave: "historia", encabezado: "Días de historia", alinear: "derecha", desde: "md", celda: (o) => <span className="tabular">{entero(o.dias_historia)}</span> },
          { clave: "ventas", encabezado: "Días con ventas", alinear: "derecha", desde: "md", celda: (o) => <span className="tabular">{entero(o.dias_con_ventas)}</span> },
        ]}
      />
      {r.truncado && <p className="border-t border-line px-5 py-3 text-xs text-ink-faint">El listado muestra las primeras series omitidas.</p>}
    </Card>
  );
}

function TablaEjecuciones() {
  const [pagina, setPagina] = useState(1);
  const lista = useQuery({ queryKey: ["predicciones", "ejecuciones", pagina], queryFn: () => apiPredicciones.ejecuciones(pagina, 10), placeholderData: keepPreviousData });
  return (
    <Card>
      <Tabla<Ejecucion>
        descripcion="Historial de ejecuciones de predicción"
        idDe={(e) => e.id}
        filas={lista.data?.items}
        cargando={lista.isFetching}
        error={lista.error}
        onReintentar={() => lista.refetch()}
        vacio={{ titulo: "Aún no se ha generado ninguna predicción" }}
        columnas={[
          { clave: "fecha", encabezado: "Solicitada", celda: (e) => <span className="whitespace-nowrap">{fechaHora(e.creada_en)}</span> },
          { clave: "por", encabezado: "Por", desde: "md", celda: (e) => <span className="text-ink-dim">{e.solicitada_por ?? "—"}</span> },
          { clave: "estado", encabezado: "Estado", celda: (e) => { const s = estado(ESTADO_EJECUCION, e.estado); return <Badge tono={s.tono}>{s.etiqueta}</Badge>; } },
          { clave: "horizonte", encabezado: "Horizonte", alinear: "derecha", desde: "sm", celda: (e) => <span className="tabular">{e.horizonte_dias} d</span> },
          { clave: "series", encabezado: "Series", alinear: "derecha", desde: "md", celda: (e) => { const r = e.resumen as ResumenEjecucion; return <span className="tabular">{entero(r.series_con_prediccion)} / {entero(r.series_total)}</span>; } },
          { clave: "wape", encabezado: "WAPE", alinear: "derecha", desde: "md", celda: (e) => { const r = e.resumen as ResumenEjecucion; return <span className="tabular">{r.wape_global == null ? "—" : porcentaje(r.wape_global * 100)}</span>; } },
        ]}
      />
      {lista.data && <Paginacion pagina={lista.data.pagina} paginas={lista.data.paginas} total={lista.data.total} tamano={lista.data.tamano} onCambiar={setPagina} />}
    </Card>
  );
}

function ComoSeCalcula() {
  const modelos = useQuery({ queryKey: ["predicciones", "modelos"], queryFn: apiPredicciones.modelos, staleTime: 3_600_000 });
  const c = modelos.data;
  return (
    <Card>
      <CardHeader titulo="Cómo se calcula" descripcion="Metodología aplicada a cada combinación de producto y sede." />
      <div className="flex flex-col gap-5 p-5 text-sm leading-relaxed text-ink-dim">
        <p>
          La demanda diaria se reconstruye únicamente con las <strong className="text-ink">ventas registradas</strong>. Los días en que el producto estaba agotado se tratan como «demanda no observada» y se sustituyen por el promedio reciente, para no confundir un faltante con falta de demanda.
        </p>
        <ol className="list-decimal space-y-1.5 pl-5">
          <li>Se exige historia mínima{c ? `: ${c.minimo_dias_historia} días, con ventas en al menos ${c.minimo_dias_con_ventas}` : ""}. Si no se cumple, la serie se omite y se informa el motivo.</li>
          <li>Se comparan varios modelos con una validación temporal: se entrena con el pasado y se evalúa en los días siguientes (nunca se mezcla futuro con pasado).</li>
          <li>La <strong className="text-ink">línea base</strong> es el promedio de los últimos 28 días. Un modelo avanzado solo se elige si reduce el error{c ? ` al menos ${c.mejora_minima_modelo_avanzado_pct} %` : ""} frente al mejor modelo simple.</li>
          <li>El error se reporta como WAPE (error absoluto ponderado) y MAE; el rango del 80 % describe la incertidumbre de la demanda del período.</li>
          <li>La <strong className="text-ink">confianza</strong> (alta, media o baja) resume cuánta historia hay y qué tan estable fue el error en la validación.</li>
        </ol>
        {modelos.isPending && <p>Cargando el catálogo de modelos…</p>}
        {c && (
          <ul className="grid gap-2 sm:grid-cols-2" aria-label="Modelos disponibles">
            {c.modelos.map((m) => (
              <li key={m.nombre} className="rounded-(--radius-control) border border-line bg-surface-2 px-4 py-3">
                <p className="flex items-center gap-2 font-semibold text-ink">
                  {nombreModelo(m.nombre)}
                  {m.es_linea_base && <Badge>Línea base</Badge>}
                  {m.avanzado && <Badge tono="accent">Avanzado</Badge>}
                </p>
                <p className="mt-1 text-xs">{m.descripcion}</p>
              </li>
            ))}
          </ul>
        )}
        <p className="text-xs text-ink-faint">Las predicciones son estimaciones: apoyan la decisión, no la reemplazan. Cualquier acción derivada (compra, traslado) requiere aprobación de una persona.</p>
      </div>
    </Card>
  );
}

export default function PrediccionesPage() {
  const { tiene } = useAuth();
  const [params, setParams] = useSearchParams();
  const pestana = (params.get("vista") as Pestana | null) ?? "pronosticos";
  const [ejecutando, setEjecutando] = useState(false);
  const [detalle, setDetalle] = useState<Prediccion | null>(null);

  const ultimas = useQuery({
    queryKey: ["predicciones", "ejecuciones", "ultima"],
    queryFn: () => apiPredicciones.ejecuciones(1, 1),
    refetchInterval: (q) => (q.state.data?.items[0] && EN_CURSO.includes(q.state.data.items[0].estado) ? 3000 : false),
  });
  const ultima = ultimas.data?.items[0];
  const ultimaCompletada = useQuery({
    queryKey: ["predicciones", "ejecuciones", "ultima-completada", ultima?.id, ultima?.estado],
    queryFn: async () => (ultima?.estado === "completada" ? ultima : ((await apiPredicciones.ejecuciones(1, 10)).items.find((e) => e.estado === "completada") ?? null)),
    enabled: Boolean(ultima),
  });
  const idParaOmitidas = ultimaCompletada.data?.id;

  function cambiarPestana(p: Pestana) {
    setParams((prev) => {
      const s = new URLSearchParams(prev);
      if (p === "pronosticos") s.delete("vista");
      else s.set("vista", p);
      s.delete("pagina");
      return s;
    }, { replace: true });
  }

  return (
    <>
      <EncabezadoPagina
        titulo="Predicción de demanda"
        descripcion="Demanda esperada por producto y sede, calculada con las ventas registradas y validada contra una línea base."
        acciones={tiene("prediccion.ejecutar") && (
          <Button icono={<Play className="size-4" aria-hidden />} onClick={() => setEjecutando(true)} disabled={ultima ? EN_CURSO.includes(ultima.estado) : false}>
            Generar predicción
          </Button>
        )}
      />
      {ultima && <ResumenUltima e={ultima} />}
      {!ultima && !ultimas.isPending && (
        <Card className="mb-6">
          <EstadoVacio
            titulo="Aún no se ha generado ninguna predicción"
            descripcion="La predicción necesita ventas registradas (al menos 28 días por producto y sede). Cuando haya historial, genérela desde aquí."
            accion={tiene("prediccion.ejecutar") ? <Button onClick={() => setEjecutando(true)}>Generar predicción</Button> : undefined}
          />
        </Card>
      )}
      {ultima && (
        <>
          <div className="mb-4">
            <Pestanas<Pestana>
              etiqueta="Vistas de predicción"
              activa={pestana}
              onCambiar={cambiarPestana}
              pestanas={[
                { clave: "pronosticos", etiqueta: "Pronósticos" },
                { clave: "omitidas", etiqueta: "Series omitidas" },
                { clave: "ejecuciones", etiqueta: "Ejecuciones" },
                { clave: "metodo", etiqueta: "Cómo se calcula" },
              ]}
            />
          </div>
          {pestana === "pronosticos" && <TablaPronosticos onAbrir={setDetalle} />}
          {pestana === "omitidas" && (idParaOmitidas ? <TablaOmitidas ejecucionId={idParaOmitidas} /> : <Card><EstadoVacio titulo="Sin ejecuciones completadas" descripcion="Cuando termine una ejecución se listarán aquí las series que no se pudieron pronosticar." /></Card>)}
          {pestana === "ejecuciones" && <TablaEjecuciones />}
          {pestana === "metodo" && <ComoSeCalcula />}
        </>
      )}
      {!ultima && pestana === "metodo" && <ComoSeCalcula />}
      {ejecutando && <DialogoEjecutar onCerrar={() => setEjecutando(false)} />}
      {detalle && <DetalleSerieModal sedeId={detalle.sede.id} productoId={detalle.producto.id} onCerrar={() => setDetalle(null)} />}
    </>
  );
}
