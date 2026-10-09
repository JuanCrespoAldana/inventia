import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { apiAmbiental } from "@/api/sig";
import { useAuth } from "@/auth/AuthContext";
import { Aviso } from "@/components/ui/Aviso";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Tabla } from "@/components/ui/DataTable";
import { FiltroFecha, FiltroSelect } from "@/components/ui/Field";
import { BarraFiltros } from "@/components/ui/FiltrosBarra";
import { Paginacion } from "@/components/ui/Pagination";
import { useSedes } from "@/hooks/useCatalogos";
import { aNumero, useFiltros } from "@/hooks/useFiltros";
import { cn } from "@/lib/cn";
import { etiqueta, PROPULSION, TIPO_VEHICULO } from "@/lib/etiquetas";
import { decimal, entero, fecha, fechaHora } from "@/lib/format";
import type { RegistroAmbiental } from "@/types/api";
import { formatoCo2 } from "./calculos";

/** Historial de las ventas contabilizadas: cada fila es una línea de venta de un vehículo, contada una sola vez. */
export function HistorialAmbiental() {
  const { sesion, tieneAlguno } = useAuth();
  const sedes = useSedes(false);
  const { filtros, pagina, tamano, cambiar, irAPagina, limpiar, hayFiltros } = useFiltros({ estado: "", tipo_vehiculo: "", sede_id: "", desde: "", hasta: "", co2: "" }, 15);
  const verSedes = sesion?.rol.alcance === "empresa";
  const puedeVerVenta = tieneAlguno("ventas.ver", "ventas.registrar");

  const lista = useQuery({
    queryKey: ["ambiental", "registros", filtros, pagina],
    queryFn: () =>
      apiAmbiental.registros({
        estado: filtros.estado,
        tipo_vehiculo: filtros.tipo_vehiculo,
        sede_id: aNumero(filtros.sede_id),
        desde: filtros.desde,
        hasta: filtros.hasta,
        pendientes: filtros.co2 === "pendiente" ? true : filtros.co2 === "calculado" ? false : "",
        pagina,
        tamano,
      }),
    placeholderData: keepPreviousData,
  });

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <BarraFiltros hayFiltros={hayFiltros} onLimpiar={limpiar}>
          <FiltroSelect etiqueta="Estado" value={filtros.estado} onChange={(e) => cambiar({ estado: e.target.value })}>
            <option value="">Activos y anulados</option>
            <option value="activo">Solo activos</option>
            <option value="anulado">Solo anulados</option>
          </FiltroSelect>
          <FiltroSelect etiqueta="Tipo de vehículo" value={filtros.tipo_vehiculo} onChange={(e) => cambiar({ tipo_vehiculo: e.target.value })}>
            <option value="">Todos los tipos</option>
            {Object.entries(TIPO_VEHICULO).map(([k, t]) => (
              <option key={k} value={k}>
                {t}
              </option>
            ))}
          </FiltroSelect>
          <FiltroSelect etiqueta="Estimación de CO₂" value={filtros.co2} onChange={(e) => cambiar({ co2: e.target.value })}>
            <option value="">Con y sin estimación</option>
            <option value="calculado">Con CO₂ estimado</option>
            <option value="pendiente">Pendientes de parametrización</option>
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
        </BarraFiltros>
        <Tabla<RegistroAmbiental>
          descripcion="Ventas de vehículos contabilizadas"
          idDe={(x) => x.id}
          filas={lista.data?.items}
          cargando={lista.isFetching}
          error={lista.error}
          onReintentar={() => lista.refetch()}
          vacio={{
            titulo: hayFiltros ? "Sin resultados" : "Aún no hay ventas contabilizadas",
            descripcion: hayFiltros ? "Prueba con otros filtros." : "Cuando se confirme una venta de un vehículo aparecerá aquí.",
          }}
          columnas={[
            { clave: "fecha", encabezado: "Fecha", celda: (x) => <span className="whitespace-nowrap">{fecha(x.fecha)}</span> },
            {
              clave: "venta",
              encabezado: "Venta",
              celda: (x) =>
                puedeVerVenta ? (
                  <Link to={`/ventas/${x.venta_id}`} className="tabular font-semibold text-accent-light hover:underline">
                    #{x.venta_numero ?? x.venta_id}
                  </Link>
                ) : (
                  <span className="tabular font-semibold">#{x.venta_numero ?? x.venta_id}</span>
                ),
            },
            {
              clave: "producto",
              encabezado: "Vehículo",
              celda: (x) => (
                <div className="min-w-0">
                  <p className="truncate font-medium">{x.producto.nombre}</p>
                  <p className="text-xs text-ink-faint">
                    {etiqueta(TIPO_VEHICULO, x.tipo_vehiculo)} · {etiqueta(PROPULSION, x.propulsion)}
                  </p>
                </div>
              ),
            },
            { clave: "sede", encabezado: "Sede", desde: "lg", celda: (x) => <span className="text-ink-dim">{x.sede.nombre}</span> },
            { clave: "unidades", encabezado: "Unidades", alinear: "derecha", celda: (x) => <span className={cn("tabular", x.estado === "anulado" && "text-ink-faint line-through")}>{entero(x.unidades)}</span> },
            {
              clave: "co2",
              encabezado: "CO₂ evitado (est.)",
              alinear: "derecha",
              desde: "sm",
              celda: (x) =>
                x.co2_estimado_kg === null ? (
                  <Badge tono="warning">Pendiente</Badge>
                ) : (
                  <span className={cn("tabular", x.estado === "anulado" && "text-ink-faint line-through")}>{formatoCo2(x.co2_estimado_kg, decimal)}</span>
                ),
            },
            {
              clave: "estado",
              encabezado: "Estado",
              celda: (x) =>
                x.estado === "anulado" ? (
                  <span title={x.anulado_en ? `Anulada el ${fechaHora(x.anulado_en)}` : undefined}>
                    <Badge tono="danger">Anulado</Badge>
                  </span>
                ) : (
                  <Badge tono="success">Activo</Badge>
                ),
            },
          ]}
        />
        {lista.data && <Paginacion pagina={lista.data.pagina} paginas={lista.data.paginas} total={lista.data.total} tamano={lista.data.tamano} onCambiar={irAPagina} />}
      </Card>
      <Aviso tipo="info">
        Cada línea de venta se cuenta una sola vez. Si una venta se anula, sus registros se conservan aquí como «Anulado» pero dejan de sumar en los indicadores. El CO₂ guardado en cada registro no cambia si más adelante se modifican los
        parámetros.
      </Aviso>
    </div>
  );
}
