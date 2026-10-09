import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { apiInventario } from "@/api/inventario";
import { useAuth } from "@/auth/AuthContext";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Tabla } from "@/components/ui/DataTable";
import { FiltroFecha, FiltroSelect } from "@/components/ui/Field";
import { BarraFiltros } from "@/components/ui/FiltrosBarra";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { Paginacion } from "@/components/ui/Pagination";
import { aNumero, useFiltros } from "@/hooks/useFiltros";
import { useSedes } from "@/hooks/useCatalogos";
import { etiqueta, MOTIVO, TIPO_MOVIMIENTO } from "@/lib/etiquetas";
import { entero, fechaHora } from "@/lib/format";
import type { Movimiento } from "@/types/api";

function Referencia({ m }: { m: Movimiento }) {
  if (m.venta_id) return <Link className="text-accent-light hover:underline" to={`/ventas/${m.venta_id}`}>Venta #{m.venta_numero}</Link>;
  if (m.traslado_id) return <Link className="text-accent-light hover:underline" to={`/traslados/${m.traslado_id}`}>Traslado #{m.traslado_numero}</Link>;
  return <span className="text-ink-faint">—</span>;
}

export default function MovimientosPage() {
  const { sesion } = useAuth();
  const sedes = useSedes(false);
  const { filtros, pagina, tamano, cambiar, irAPagina, limpiar, hayFiltros } = useFiltros({ sede_id: "", tipo: "", desde: "", hasta: "" }, 25);
  const verSedes = sesion?.rol.alcance === "empresa";

  const lista = useQuery({
    queryKey: ["movimientos", filtros, pagina],
    queryFn: () => apiInventario.movimientos({ sede_id: aNumero(filtros.sede_id), tipo: filtros.tipo, desde: filtros.desde, hasta: filtros.hasta, pagina, tamano }),
    placeholderData: keepPreviousData,
  });

  return (
    <>
      <EncabezadoPagina titulo="Movimientos" descripcion="Historial inmutable de entradas, salidas, ajustes, ventas y traslados. Cada fila muestra el saldo antes y después." />
      <Card>
        <BarraFiltros hayFiltros={hayFiltros} onLimpiar={limpiar}>
          {verSedes && (
            <FiltroSelect etiqueta="Sede" value={filtros.sede_id} onChange={(e) => cambiar({ sede_id: e.target.value })}>
              <option value="">Todas las sedes</option>
              {sedes.data?.map((s) => (
                <option key={s.id} value={s.id}>{s.nombre}</option>
              ))}
            </FiltroSelect>
          )}
          <FiltroSelect etiqueta="Tipo de movimiento" value={filtros.tipo} onChange={(e) => cambiar({ tipo: e.target.value })}>
            <option value="">Todos los tipos</option>
            {Object.entries(TIPO_MOVIMIENTO).map(([k, n]) => (
              <option key={k} value={k}>{n}</option>
            ))}
          </FiltroSelect>
          <FiltroFecha etiqueta="Desde" value={filtros.desde} max={filtros.hasta || undefined} onChange={(e) => cambiar({ desde: e.target.value })} />
          <FiltroFecha etiqueta="Hasta" value={filtros.hasta} min={filtros.desde || undefined} onChange={(e) => cambiar({ hasta: e.target.value })} />
        </BarraFiltros>
        <Tabla
          descripcion="Historial de movimientos de inventario"
          idDe={(m) => m.id}
          filas={lista.data?.items}
          cargando={lista.isFetching}
          error={lista.error}
          onReintentar={() => lista.refetch()}
          vacio={{ titulo: hayFiltros ? "Sin resultados" : "Aún no hay movimientos", descripcion: hayFiltros ? "Pruebe con otros filtros o con otro rango de fechas." : "Cuando se registren entradas, salidas o ventas aparecerán aquí." }}
          columnas={[
            { clave: "fecha", encabezado: "Fecha", celda: (m) => <span className="whitespace-nowrap text-ink-dim">{fechaHora(m.fecha)}</span> },
            {
              clave: "producto",
              encabezado: "Producto",
              celda: (m) => (
                <div>
                  <span className="font-medium">{m.producto.nombre}</span>
                  <span className="block font-mono text-xs text-ink-faint">{m.producto.codigo}</span>
                </div>
              ),
            },
            {
              clave: "sede",
              encabezado: "Sede",
              desde: "md",
              celda: (m) => (
                <span>
                  {m.sede.nombre}
                  {m.sede_contraparte && <span className="block text-xs text-ink-faint">con {m.sede_contraparte.nombre}</span>}
                </span>
              ),
            },
            {
              clave: "tipo",
              encabezado: "Tipo",
              celda: (m) => (
                <div>
                  <Badge tono={m.delta > 0 ? "success" : m.delta < 0 ? "danger" : "neutral"}>{etiqueta(TIPO_MOVIMIENTO, m.tipo)}</Badge>
                  {m.motivo && <span className="mt-1 block text-xs text-ink-faint">{etiqueta(MOTIVO, m.motivo)}</span>}
                </div>
              ),
            },
            { clave: "delta", encabezado: "Variación", alinear: "derecha", celda: (m) => <span className={`tabular font-semibold ${m.delta >= 0 ? "text-success" : "text-danger"}`}>{m.delta > 0 ? "+" : ""}{entero(m.delta)}</span> },
            { clave: "saldo", encabezado: "Saldo", alinear: "derecha", desde: "sm", celda: (m) => <span className="tabular text-ink-dim">{entero(m.saldo_anterior)} → {entero(m.saldo_posterior)}</span> },
            { clave: "usuario", encabezado: "Usuario", desde: "lg", celda: (m) => <span className="text-ink-dim">{m.usuario_nombre ?? "—"}</span> },
            { clave: "ref", encabezado: "Referencia", desde: "lg", celda: (m) => <Referencia m={m} /> },
            { clave: "obs", encabezado: "Observación", desde: "lg", className: "max-w-56 truncate", celda: (m) => <span className="text-ink-dim" title={m.observacion ?? undefined}>{m.observacion ?? "—"}</span> },
          ]}
        />
        {lista.data && <Paginacion pagina={lista.data.pagina} paginas={lista.data.paginas} total={lista.data.total} tamano={lista.data.tamano} onCambiar={irAPagina} />}
      </Card>
    </>
  );
}
