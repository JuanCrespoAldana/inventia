import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Plus } from "lucide-react";
import { apiTraslados } from "@/api/operaciones";
import { useAuth } from "@/auth/AuthContext";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Tabla } from "@/components/ui/DataTable";
import { FiltroFecha, FiltroSelect } from "@/components/ui/Field";
import { BarraFiltros } from "@/components/ui/FiltrosBarra";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { Paginacion } from "@/components/ui/Pagination";
import { useSedes } from "@/hooks/useCatalogos";
import { aNumero, useFiltros } from "@/hooks/useFiltros";
import { ESTADO_TRASLADO, estado } from "@/lib/etiquetas";
import { entero, fechaHora } from "@/lib/format";

export default function TrasladosPage() {
  const { tiene, sesion } = useAuth();
  const navegar = useNavigate();
  const sedes = useSedes(false);
  const { filtros, pagina, tamano, cambiar, irAPagina, limpiar, hayFiltros } = useFiltros({ sede_id: "", estado: "", desde: "", hasta: "", numero: "" }, 20);
  const verSedes = sesion?.rol.alcance === "empresa";

  const lista = useQuery({
    queryKey: ["traslados", filtros, pagina],
    queryFn: () => apiTraslados.listar({ sede_id: aNumero(filtros.sede_id), estado: filtros.estado, desde: filtros.desde, hasta: filtros.hasta, numero: aNumero(filtros.numero), pagina, tamano }),
    placeholderData: keepPreviousData,
    enabled: tiene("traslados.ver"),
  });

  return (
    <>
      <EncabezadoPagina
        titulo="Traslados entre sedes"
        descripcion="Flujo: la sede solicita, la sede de origen aprueba y la sede de destino confirma la recepción. Las existencias solo se mueven al confirmar."
        acciones={tiene("traslados.solicitar") && <Button icono={<Plus className="size-4" aria-hidden />} onClick={() => navegar("/traslados/nuevo")}>Solicitar traslado</Button>}
      />
      <Card>
        <BarraFiltros hayFiltros={hayFiltros} onLimpiar={limpiar}>
          <input
            type="search"
            inputMode="numeric"
            aria-label="Buscar por número de traslado"
            placeholder="N.º de traslado"
            value={filtros.numero}
            onChange={(e) => cambiar({ numero: e.target.value.replace(/\D/g, "") })}
            className="h-9 w-36 rounded-(--radius-control) border border-line-strong bg-surface-2 px-3 text-[13px] text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
          {verSedes && (
            <FiltroSelect etiqueta="Sede" value={filtros.sede_id} onChange={(e) => cambiar({ sede_id: e.target.value })}>
              <option value="">Todas las sedes</option>
              {sedes.data?.map((s) => (
                <option key={s.id} value={s.id}>{s.nombre}</option>
              ))}
            </FiltroSelect>
          )}
          <FiltroSelect etiqueta="Estado" value={filtros.estado} onChange={(e) => cambiar({ estado: e.target.value })}>
            <option value="">Todos los estados</option>
            {Object.entries(ESTADO_TRASLADO).map(([k, e]) => (
              <option key={k} value={k}>{e.etiqueta}</option>
            ))}
          </FiltroSelect>
          <FiltroFecha etiqueta="Desde" value={filtros.desde} max={filtros.hasta || undefined} onChange={(e) => cambiar({ desde: e.target.value })} />
          <FiltroFecha etiqueta="Hasta" value={filtros.hasta} min={filtros.desde || undefined} onChange={(e) => cambiar({ hasta: e.target.value })} />
        </BarraFiltros>
        <Tabla
          descripcion="Listado de traslados"
          idDe={(t) => t.id}
          filas={lista.data?.items}
          cargando={lista.isFetching}
          error={lista.error}
          onReintentar={() => lista.refetch()}
          onFila={(t) => navegar(`/traslados/${t.id}`)}
          vacio={{
            titulo: hayFiltros ? "Sin resultados" : "Aún no hay traslados",
            descripcion: hayFiltros ? "Pruebe con otros filtros." : "Cuando una sede necesite mercancía de otra, solicite el traslado desde aquí.",
            accion: !hayFiltros && tiene("traslados.solicitar") ? <Button onClick={() => navegar("/traslados/nuevo")}>Solicitar traslado</Button> : undefined,
          }}
          columnas={[
            { clave: "numero", encabezado: "N.º", celda: (t) => <Link to={`/traslados/${t.id}`} className="font-semibold text-accent-light hover:underline" onClick={(e) => e.stopPropagation()}>#{t.numero}</Link> },
            {
              clave: "ruta",
              encabezado: "Origen → destino",
              celda: (t) => (
                <span className="flex items-center gap-2 whitespace-nowrap">
                  {t.origen.nombre}
                  <ArrowRight className="size-3.5 text-ink-faint" aria-label="hacia" />
                  {t.destino.nombre}
                </span>
              ),
            },
            { clave: "unidades", encabezado: "Unidades", alinear: "derecha", desde: "sm", celda: (t) => <span className="tabular">{entero(t.unidades)} <span className="text-ink-faint">({t.lineas} {t.lineas === 1 ? "línea" : "líneas"})</span></span> },
            { clave: "solicitado", encabezado: "Solicitado", desde: "md", celda: (t) => <span className="text-ink-dim">{fechaHora(t.solicitado_en)}</span> },
            { clave: "por", encabezado: "Solicitó", desde: "lg", celda: (t) => <span className="text-ink-dim">{t.solicitado_por_nombre ?? "—"}{t.recomendacion_id ? <Badge tono="accent" className="ml-2">Recomendación</Badge> : null}</span> },
            { clave: "estado", encabezado: "Estado", celda: (t) => { const e = estado(ESTADO_TRASLADO, t.estado); return <Badge tono={e.tono}>{e.etiqueta}</Badge>; } },
          ]}
        />
        {lista.data && <Paginacion pagina={lista.data.pagina} paginas={lista.data.paginas} total={lista.data.total} tamano={lista.data.tamano} onCambiar={irAPagina} />}
      </Card>
    </>
  );
}
