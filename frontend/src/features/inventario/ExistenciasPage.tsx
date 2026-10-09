import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ArrowDownToLine, ArrowUpFromLine, ClipboardCheck, SlidersHorizontal } from "lucide-react";
import { apiInventario } from "@/api/inventario";
import { useAuth } from "@/auth/AuthContext";
import { Badge } from "@/components/ui/Badge";
import { Button, IconButton } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Tabla } from "@/components/ui/DataTable";
import { EstadoVacio } from "@/components/ui/EstadoVacio";
import { FiltroSelect } from "@/components/ui/Field";
import { BarraFiltros } from "@/components/ui/FiltrosBarra";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { Paginacion } from "@/components/ui/Pagination";
import { Busqueda } from "@/components/ui/SearchInput";
import { useCategorias } from "@/hooks/useCatalogos";
import { aNumero, useFiltros } from "@/hooks/useFiltros";
import { useSedeActiva } from "@/hooks/useSedeActiva";
import { ESTADO_STOCK, estado } from "@/lib/etiquetas";
import { entero, hace, moneda } from "@/lib/format";
import type { InventarioFila } from "@/types/api";
import { DialogoAjuste, DialogoEntrada, DialogoNiveles, DialogoSalida } from "./DialogosInventario";

type Dialogo = { tipo: "entrada" } | { tipo: "salida" } | { tipo: "ajuste"; fila: InventarioFila } | { tipo: "niveles"; fila: InventarioFila } | null;

export default function ExistenciasPage() {
  const { tiene } = useAuth();
  const sede = useSedeActiva();
  const categorias = useCategorias(false);
  const { filtros, pagina, tamano, cambiar, irAPagina, limpiar, hayFiltros } = useFiltros({ q: "", categoria_id: "", estado: "" }, 25);
  const [dialogo, setDialogo] = useState<Dialogo>(null);

  const lista = useQuery({
    queryKey: ["inventario", "sede", sede.sedeId, filtros, pagina],
    queryFn: () => apiInventario.porSede({ sede_id: sede.sedeId ?? "", q: filtros.q, categoria_id: aNumero(filtros.categoria_id), estado: filtros.estado, pagina, tamano }),
    enabled: sede.sedeId !== null,
    placeholderData: keepPreviousData,
  });

  const puedeAjustar = tiene("inventario.ajustar");
  const puedeNiveles = tiene("inventario.niveles");
  const nombreSede = lista.data?.sede.nombre ?? sede.nombre ?? "";

  if (!sede.cargando && sede.sedeId === null) {
    return (
      <>
        <EncabezadoPagina titulo="Existencias" />
        <Card>
          <EstadoVacio titulo="No hay sedes disponibles" descripcion="Cree una sede activa para registrar su inventario." />
        </Card>
      </>
    );
  }

  return (
    <>
      <EncabezadoPagina
        titulo="Existencias"
        descripcion="Inventario por sede. Cada movimiento queda registrado en el historial."
        acciones={
          <>
            {!sede.fija && (
              <FiltroSelect etiqueta="Sede" value={sede.sedeId ?? ""} onChange={(e) => sede.elegir(Number(e.target.value))}>
                {sede.sedes.map((s) => (
                  <option key={s.id} value={s.id}>{s.nombre}</option>
                ))}
              </FiltroSelect>
            )}
            {tiene("inventario.salida") && sede.sedeId !== null && (
              <Button variante="secondary" icono={<ArrowUpFromLine className="size-4" aria-hidden />} onClick={() => setDialogo({ tipo: "salida" })}>
                Registrar salida
              </Button>
            )}
            {tiene("inventario.entrada") && sede.sedeId !== null && (
              <Button icono={<ArrowDownToLine className="size-4" aria-hidden />} onClick={() => setDialogo({ tipo: "entrada" })}>
                Registrar entrada
              </Button>
            )}
          </>
        }
      />
      <Card>
        <BarraFiltros hayFiltros={hayFiltros} onLimpiar={limpiar}>
          <Busqueda valor={filtros.q} onCambiar={(q) => cambiar({ q })} placeholder="Buscar por código o nombre…" />
          <FiltroSelect etiqueta="Categoría" value={filtros.categoria_id} onChange={(e) => cambiar({ categoria_id: e.target.value })}>
            <option value="">Todas las categorías</option>
            {categorias.data?.map((c) => (
              <option key={c.id} value={c.id}>{c.nombre}</option>
            ))}
          </FiltroSelect>
          <FiltroSelect etiqueta="Estado del stock" value={filtros.estado} onChange={(e) => cambiar({ estado: e.target.value })}>
            <option value="">Todos los estados</option>
            {Object.entries(ESTADO_STOCK).map(([k, e]) => (
              <option key={k} value={k}>{e.etiqueta}</option>
            ))}
          </FiltroSelect>
        </BarraFiltros>
        <Tabla
          descripcion={`Existencias de la sede ${nombreSede}`}
          idDe={(f) => f.producto.id}
          filas={lista.data?.items}
          cargando={lista.isFetching || sede.cargando}
          error={lista.error}
          onReintentar={() => lista.refetch()}
          vacio={{
            titulo: hayFiltros ? "Sin resultados" : "Esta sede aún no tiene productos",
            descripcion: hayFiltros ? "Pruebe con otros filtros." : "Registre una entrada de inventario para empezar a controlar las existencias.",
            accion: !hayFiltros && tiene("inventario.entrada") ? <Button onClick={() => setDialogo({ tipo: "entrada" })}>Registrar entrada</Button> : undefined,
          }}
          columnas={[
            {
              clave: "producto",
              encabezado: "Producto",
              celda: (f) => (
                <div>
                  <span className="font-medium">{f.producto.nombre}</span>
                  <span className="block font-mono text-xs text-ink-faint">{f.producto.codigo}</span>
                </div>
              ),
            },
            { clave: "categoria", encabezado: "Categoría", desde: "lg", celda: (f) => <span className="text-ink-dim">{f.categoria}</span> },
            { clave: "cantidad", encabezado: "Cantidad", alinear: "derecha", celda: (f) => <span className="tabular text-base font-semibold">{entero(f.cantidad)}</span> },
            { clave: "minimo", encabezado: "Mínimo", alinear: "derecha", desde: "md", celda: (f) => <span className="tabular text-ink-dim">{entero(f.stock_minimo)}</span> },
            { clave: "maximo", encabezado: "Máximo", alinear: "derecha", desde: "md", celda: (f) => <span className="tabular text-ink-dim">{f.stock_maximo == null ? "—" : entero(f.stock_maximo)}</span> },
            { clave: "valor", encabezado: "Valor", alinear: "derecha", desde: "lg", celda: (f) => <span className="tabular">{moneda(f.valor)}</span> },
            {
              clave: "estado",
              encabezado: "Estado",
              celda: (f) => {
                const e = estado(ESTADO_STOCK, f.estado);
                return (
                  <div className="flex items-center gap-2">
                    <Badge tono={e.tono}>{e.etiqueta}</Badge>
                    {!f.producto_activo && <Badge>Inhabilitado</Badge>}
                  </div>
                );
              },
            },
            { clave: "actualizado", encabezado: "Actualizado", desde: "lg", celda: (f) => <span className="text-ink-faint">{hace(f.actualizado_en)}</span> },
            {
              clave: "acciones",
              encabezado: "Acciones",
              alinear: "derecha",
              celda: (f) => (
                <div className="flex justify-end gap-1">
                  {puedeAjustar && (
                    <IconButton etiqueta={`Ajustar existencias de ${f.producto.nombre}`} onClick={() => setDialogo({ tipo: "ajuste", fila: f })}>
                      <ClipboardCheck className="size-4" aria-hidden />
                    </IconButton>
                  )}
                  {puedeNiveles && (
                    <IconButton etiqueta={`Configurar niveles de ${f.producto.nombre}`} onClick={() => setDialogo({ tipo: "niveles", fila: f })}>
                      <SlidersHorizontal className="size-4" aria-hidden />
                    </IconButton>
                  )}
                </div>
              ),
            },
          ]}
        />
        {lista.data && <Paginacion pagina={lista.data.pagina} paginas={lista.data.paginas} total={lista.data.total} tamano={lista.data.tamano} onCambiar={irAPagina} />}
      </Card>

      {sede.sedeId !== null && dialogo?.tipo === "entrada" && <DialogoEntrada sedeId={sede.sedeId} sedeNombre={nombreSede} onCerrar={() => setDialogo(null)} />}
      {sede.sedeId !== null && dialogo?.tipo === "salida" && <DialogoSalida sedeId={sede.sedeId} sedeNombre={nombreSede} onCerrar={() => setDialogo(null)} />}
      {sede.sedeId !== null && dialogo?.tipo === "ajuste" && <DialogoAjuste fila={dialogo.fila} sedeId={sede.sedeId} sedeNombre={nombreSede} onCerrar={() => setDialogo(null)} />}
      {sede.sedeId !== null && dialogo?.tipo === "niveles" && <DialogoNiveles fila={dialogo.fila} sedeId={sede.sedeId} sedeNombre={nombreSede} onCerrar={() => setDialogo(null)} />}
    </>
  );
}
