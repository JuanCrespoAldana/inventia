import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronRight } from "lucide-react";
import { apiInventario } from "@/api/inventario";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Casilla, FiltroSelect } from "@/components/ui/Field";
import { Tabla } from "@/components/ui/DataTable";
import { BarraFiltros } from "@/components/ui/FiltrosBarra";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { Paginacion } from "@/components/ui/Pagination";
import { Busqueda } from "@/components/ui/SearchInput";
import { useCategorias } from "@/hooks/useCatalogos";
import { aNumero, useFiltros } from "@/hooks/useFiltros";
import { ESTADO_STOCK, estado } from "@/lib/etiquetas";
import { entero, moneda } from "@/lib/format";
import type { ConsolidadoFila } from "@/types/api";

export default function ConsolidadoPage() {
  const categorias = useCategorias(false);
  const { filtros, pagina, tamano, cambiar, irAPagina, limpiar, hayFiltros } = useFiltros({ q: "", categoria_id: "", con_existencias: "" }, 25);
  const [abiertas, setAbiertas] = useState<Set<number>>(new Set());

  const lista = useQuery({
    queryKey: ["inventario", "consolidado", filtros, pagina],
    queryFn: () => apiInventario.consolidado({ q: filtros.q, categoria_id: aNumero(filtros.categoria_id), solo_con_existencias: filtros.con_existencias === "1", pagina, tamano }),
    placeholderData: keepPreviousData,
  });

  function alternar(f: ConsolidadoFila) {
    setAbiertas((prev) => {
      const siguiente = new Set(prev);
      if (!siguiente.delete(f.producto.id)) siguiente.add(f.producto.id);
      return siguiente;
    });
  }

  return (
    <>
      <EncabezadoPagina titulo="Inventario consolidado" descripcion="Existencias de todas las sedes sumadas por producto. El total se calcula al consultar; no se guarda un segundo inventario." />
      <Card>
        <BarraFiltros hayFiltros={hayFiltros} onLimpiar={limpiar}>
          <Busqueda valor={filtros.q} onCambiar={(q) => cambiar({ q })} placeholder="Buscar por código o nombre…" />
          <FiltroSelect etiqueta="Categoría" value={filtros.categoria_id} onChange={(e) => cambiar({ categoria_id: e.target.value })}>
            <option value="">Todas las categorías</option>
            {categorias.data?.map((c) => (
              <option key={c.id} value={c.id}>{c.nombre}</option>
            ))}
          </FiltroSelect>
          <Casilla etiqueta="Solo con existencias" checked={filtros.con_existencias === "1"} onChange={(e) => cambiar({ con_existencias: e.target.checked ? "1" : "" })} />
        </BarraFiltros>
        <Tabla
          descripcion="Inventario consolidado por producto"
          idDe={(f) => f.producto.id}
          filas={lista.data?.items}
          cargando={lista.isFetching}
          error={lista.error}
          onReintentar={() => lista.refetch()}
          onFila={alternar}
          abierta={(f) => abiertas.has(f.producto.id)}
          vacio={{ titulo: "Sin resultados", descripcion: "No hay productos que coincidan con los filtros." }}
          detalle={(f) => (
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
              {f.sedes.map((s) => {
                const e = estado(ESTADO_STOCK, s.estado);
                return (
                  <div key={s.sede_id} className="flex items-center justify-between gap-3 rounded-(--radius-control) border border-line bg-surface px-4 py-2.5">
                    <div>
                      <p className="text-sm font-medium text-ink">{s.sede}</p>
                      <p className="text-xs text-ink-faint">
                        Mín. {entero(s.stock_minimo)} · Máx. {s.stock_maximo == null ? "—" : entero(s.stock_maximo)}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="tabular text-base font-semibold">{entero(s.cantidad)}</span>
                      <Badge tono={e.tono}>{e.etiqueta}</Badge>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          columnas={[
            {
              clave: "producto",
              encabezado: "Producto",
              celda: (f) => (
                <div className="flex items-center gap-2">
                  {abiertas.has(f.producto.id) ? <ChevronDown className="size-4 text-ink-faint" aria-hidden /> : <ChevronRight className="size-4 text-ink-faint" aria-hidden />}
                  <div>
                    <span className="font-medium">{f.producto.nombre}</span>
                    <span className="block font-mono text-xs text-ink-faint">{f.producto.codigo}</span>
                  </div>
                </div>
              ),
            },
            { clave: "categoria", encabezado: "Categoría", desde: "md", celda: (f) => <span className="text-ink-dim">{f.categoria}</span> },
            { clave: "total", encabezado: "Total", alinear: "derecha", celda: (f) => <span className="tabular text-base font-semibold">{entero(f.total)}</span> },
            { clave: "costo", encabezado: "Costo unit.", alinear: "derecha", desde: "lg", celda: (f) => <span className="tabular text-ink-dim">{moneda(f.costo)}</span> },
            { clave: "valor", encabezado: "Valor", alinear: "derecha", desde: "sm", celda: (f) => <span className="tabular">{moneda(f.valor)}</span> },
            {
              clave: "alertas",
              encabezado: "Sedes en alerta",
              alinear: "derecha",
              celda: (f) => (f.sedes_en_alerta > 0 ? <Badge tono="warning">{f.sedes_en_alerta} de {f.sedes.length}</Badge> : <span className="text-ink-faint">Ninguna</span>),
            },
          ]}
        />
        {lista.data && <Paginacion pagina={lista.data.pagina} paginas={lista.data.paginas} total={lista.data.total} tamano={lista.data.tamano} onCambiar={irAPagina} />}
      </Card>
    </>
  );
}
