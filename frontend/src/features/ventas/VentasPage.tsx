import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { Plus } from "lucide-react";
import { apiVentas } from "@/api/operaciones";
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
import { ESTADO_VENTA, estado } from "@/lib/etiquetas";
import { entero, fechaHora, moneda } from "@/lib/format";

export default function VentasPage() {
  const { tiene, sesion } = useAuth();
  const navegar = useNavigate();
  const sedes = useSedes(false);
  const { filtros, pagina, tamano, cambiar, irAPagina, limpiar, hayFiltros } = useFiltros({ sede_id: "", estado: "", desde: "", hasta: "", numero: "" }, 20);
  const verSedes = sesion?.rol.alcance === "empresa";

  const lista = useQuery({
    queryKey: ["ventas", filtros, pagina],
    queryFn: () => apiVentas.listar({ sede_id: aNumero(filtros.sede_id), estado: filtros.estado, desde: filtros.desde, hasta: filtros.hasta, numero: aNumero(filtros.numero), pagina, tamano }),
    placeholderData: keepPreviousData,
    enabled: tiene("ventas.ver"),
  });

  return (
    <>
      <EncabezadoPagina
        titulo="Ventas"
        descripcion="Cada venta descuenta existencias de su sede. Las ventas anuladas devuelven las unidades al inventario y no cuentan en los totales."
        acciones={tiene("ventas.registrar") && <Button icono={<Plus className="size-4" aria-hidden />} onClick={() => navegar("/ventas/nueva")}>Nueva venta</Button>}
      />
      <Card>
        <BarraFiltros hayFiltros={hayFiltros} onLimpiar={limpiar}>
          <input
            type="search"
            inputMode="numeric"
            aria-label="Buscar por número de venta"
            placeholder="N.º de venta"
            value={filtros.numero}
            onChange={(e) => cambiar({ numero: e.target.value.replace(/\D/g, "") })}
            className="h-9 w-32 rounded-(--radius-control) border border-line-strong bg-surface-2 px-3 text-[13px] text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
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
            <option value="registrada">Registradas</option>
            <option value="anulada">Anuladas</option>
          </FiltroSelect>
          <FiltroFecha etiqueta="Desde" value={filtros.desde} max={filtros.hasta || undefined} onChange={(e) => cambiar({ desde: e.target.value })} />
          <FiltroFecha etiqueta="Hasta" value={filtros.hasta} min={filtros.desde || undefined} onChange={(e) => cambiar({ hasta: e.target.value })} />
        </BarraFiltros>
        <Tabla
          descripcion="Listado de ventas"
          idDe={(v) => v.id}
          filas={lista.data?.items}
          cargando={lista.isFetching}
          error={lista.error}
          onReintentar={() => lista.refetch()}
          onFila={(v) => navegar(`/ventas/${v.id}`)}
          vacio={{
            titulo: hayFiltros ? "Sin resultados" : "Aún no hay ventas",
            descripcion: hayFiltros ? "Pruebe con otros filtros o con otro rango de fechas." : "Registre la primera venta para empezar a construir el historial de demanda.",
            accion: !hayFiltros && tiene("ventas.registrar") ? <Button onClick={() => navegar("/ventas/nueva")}>Nueva venta</Button> : undefined,
          }}
          columnas={[
            { clave: "numero", encabezado: "N.º", celda: (v) => <Link to={`/ventas/${v.id}`} className="font-semibold text-accent-light hover:underline" onClick={(e) => e.stopPropagation()}>#{v.numero}</Link> },
            { clave: "fecha", encabezado: "Fecha", celda: (v) => <span className="whitespace-nowrap text-ink-dim">{fechaHora(v.fecha)}</span> },
            { clave: "sede", encabezado: "Sede", desde: "md", celda: (v) => v.sede.nombre },
            { clave: "usuario", encabezado: "Registró", desde: "lg", celda: (v) => <span className="text-ink-dim">{v.usuario_nombre ?? "—"}</span> },
            { clave: "unidades", encabezado: "Unidades", alinear: "derecha", desde: "sm", celda: (v) => <span className="tabular">{entero(v.unidades)}</span> },
            { clave: "total", encabezado: "Total", alinear: "derecha", celda: (v) => <span className={`tabular font-semibold ${v.estado === "anulada" ? "text-ink-faint line-through" : ""}`}>{moneda(v.total)}</span> },
            { clave: "estado", encabezado: "Estado", celda: (v) => { const e = estado(ESTADO_VENTA, v.estado); return <Badge tono={e.tono}>{e.etiqueta}</Badge>; } },
          ]}
        />
        {lista.data && <Paginacion pagina={lista.data.pagina} paginas={lista.data.paginas} total={lista.data.total} tamano={lista.data.tamano} onCambiar={irAPagina} />}
      </Card>
    </>
  );
}
