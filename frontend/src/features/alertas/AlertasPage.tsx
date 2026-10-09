import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { apiAlertas } from "@/api/inventario";
import { useAuth } from "@/auth/AuthContext";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Tabla } from "@/components/ui/DataTable";
import { FiltroSelect } from "@/components/ui/Field";
import { BarraFiltros } from "@/components/ui/FiltrosBarra";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { Paginacion } from "@/components/ui/Pagination";
import { Busqueda } from "@/components/ui/SearchInput";
import { useSedes } from "@/hooks/useCatalogos";
import { aNumero, useFiltros } from "@/hooks/useFiltros";
import { useMutacion } from "@/hooks/useMutacion";
import { ESTADO_ALERTA, estado, etiqueta, PRIORIDAD, TIPO_ALERTA } from "@/lib/etiquetas";
import { entero, hace } from "@/lib/format";

export default function AlertasPage() {
  const { tiene, sesion } = useAuth();
  const sedes = useSedes(false);
  const { filtros, pagina, tamano, cambiar, irAPagina, limpiar, hayFiltros } = useFiltros({ estado: "activa", tipo: "", prioridad: "", sede_id: "", q: "" }, 20);
  const verSedes = sesion?.rol.alcance === "empresa";

  const lista = useQuery({
    queryKey: ["alertas", filtros, pagina],
    queryFn: () => apiAlertas.listar({ estado: filtros.estado, tipo: filtros.tipo, prioridad: filtros.prioridad, sede_id: aNumero(filtros.sede_id), q: filtros.q, pagina, tamano }),
    placeholderData: keepPreviousData,
  });
  const resumen = useQuery({ queryKey: ["alertas", "resumen", filtros.sede_id], queryFn: () => apiAlertas.resumen(aNumero(filtros.sede_id)) });

  const recalcular = useMutacion(apiAlertas.recalcular, {
    exito: (r) => `Alertas recalculadas: ${r.abiertas} nuevas, ${r.resueltas} resueltas, ${r.activas} activas en total.`,
    invalidar: [["alertas"], ["dashboard"]],
  });

  const porPrioridad = resumen.data?.por_prioridad ?? {};

  return (
    <>
      <EncabezadoPagina
        titulo="Alertas de inventario"
        descripcion="Se calculan con las existencias reales, los niveles mínimo y máximo y la demanda prevista. Se resuelven solas cuando la situación se corrige."
        acciones={
          tiene("alertas.recalcular") && (
            <Button variante="secondary" icono={<RefreshCw className="size-4" aria-hidden />} cargando={recalcular.isPending} onClick={() => recalcular.mutate()}>
              Recalcular alertas
            </Button>
          )
        }
      />
      {resumen.data && (
        <ul className="mb-5 flex flex-wrap gap-2" aria-label="Alertas activas por prioridad">
          {Object.entries(PRIORIDAD).map(([clave, p]) => (
            <li key={clave}>
              <button
                type="button"
                onClick={() => cambiar({ prioridad: filtros.prioridad === clave ? "" : clave, estado: "activa" })}
                aria-pressed={filtros.prioridad === clave}
                className={`flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-[13px] transition ${filtros.prioridad === clave ? "border-accent bg-accent-dim text-accent-light" : "border-line bg-surface text-ink-dim hover:border-line-strong hover:text-ink"}`}
              >
                <Badge tono={p.tono}>{p.etiqueta}</Badge>
                <span className="tabular font-semibold text-ink">{entero(porPrioridad[clave] ?? 0)}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      <Card>
        <BarraFiltros hayFiltros={hayFiltros && !(filtros.estado === "activa" && !filtros.tipo && !filtros.prioridad && !filtros.sede_id && !filtros.q)} onLimpiar={limpiar}>
          <Busqueda valor={filtros.q} onCambiar={(q) => cambiar({ q })} placeholder="Buscar producto o sede…" />
          <FiltroSelect etiqueta="Estado" value={filtros.estado} onChange={(e) => cambiar({ estado: e.target.value })}>
            <option value="activa">Activas</option>
            <option value="resuelta">Resueltas</option>
            <option value="">Todas</option>
          </FiltroSelect>
          <FiltroSelect etiqueta="Tipo de alerta" value={filtros.tipo} onChange={(e) => cambiar({ tipo: e.target.value })}>
            <option value="">Todos los tipos</option>
            {Object.entries(TIPO_ALERTA).map(([k, n]) => (
              <option key={k} value={k}>{n}</option>
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
        <Tabla
          descripcion="Listado de alertas de inventario"
          idDe={(a) => a.id}
          filas={lista.data?.items}
          cargando={lista.isFetching}
          error={lista.error}
          onReintentar={() => lista.refetch()}
          vacio={{
            titulo: filtros.estado === "activa" && !hayFiltros ? "Sin alertas activas" : "Sin resultados",
            descripcion: filtros.estado === "activa" && !hayFiltros ? "El inventario está dentro de los rangos configurados." : "No hay alertas con los filtros aplicados.",
          }}
          columnas={[
            { clave: "prioridad", encabezado: "Prioridad", celda: (a) => { const p = estado(PRIORIDAD, a.prioridad); return <Badge tono={p.tono}>{p.etiqueta}</Badge>; } },
            {
              clave: "mensaje",
              encabezado: "Alerta",
              className: "min-w-72 max-w-xl",
              celda: (a) => (
                <div>
                  <p className="text-ink">{a.mensaje}</p>
                  <p className="mt-0.5 text-xs text-ink-faint">{etiqueta(TIPO_ALERTA, a.tipo)}</p>
                </div>
              ),
            },
            { clave: "producto", encabezado: "Producto", desde: "lg", celda: (a) => <div><span className="font-medium">{a.producto.nombre}</span><span className="block font-mono text-xs text-ink-faint">{a.producto.codigo}</span></div> },
            { clave: "sede", encabezado: "Sede", desde: "md", celda: (a) => a.sede.nombre },
            { clave: "abierta", encabezado: "Detectada", desde: "md", celda: (a) => <span className="text-ink-dim">{hace(a.abierta_en)}</span> },
            { clave: "estado", encabezado: "Estado", celda: (a) => { const e = estado(ESTADO_ALERTA, a.estado); return <Badge tono={e.tono}>{e.etiqueta}</Badge>; } },
          ]}
        />
        {lista.data && <Paginacion pagina={lista.data.pagina} paginas={lista.data.paginas} total={lista.data.total} tamano={lista.data.tamano} onCambiar={irAPagina} />}
      </Card>
    </>
  );
}
