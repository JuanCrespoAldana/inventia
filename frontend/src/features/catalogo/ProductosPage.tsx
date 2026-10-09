import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Pencil, Plus, Power } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { apiProductos } from "@/api/catalogo";
import { useAuth } from "@/auth/AuthContext";
import { Aviso } from "@/components/ui/Aviso";
import { Badge } from "@/components/ui/Badge";
import { Button, IconButton } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Tabla } from "@/components/ui/DataTable";
import { FiltroSelect, Input, Select, Textarea } from "@/components/ui/Field";
import { BarraFiltros } from "@/components/ui/FiltrosBarra";
import { Modal } from "@/components/ui/Modal";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { Paginacion } from "@/components/ui/Pagination";
import { Busqueda } from "@/components/ui/SearchInput";
import { aBooleano, aNumero, useFiltros } from "@/hooks/useFiltros";
import { useCategorias } from "@/hooks/useCatalogos";
import { useMutacion } from "@/hooks/useMutacion";
import { UNIDADES_MEDIDA } from "@/lib/etiquetas";
import { entero, moneda } from "@/lib/format";
import { aDinero, aplicarErroresServidor, v } from "@/lib/formularios";
import type { Producto, UnidadMedida } from "@/types/api";

const esquema = z.object({
  codigo: z.string().trim().min(2, "El código es obligatorio (mínimo 2 caracteres)").max(50, "El código no puede superar los 50 caracteres"),
  nombre: v.texto("El nombre", 2, 150),
  descripcion: v.textoOpcional(500),
  categoria_id: z.string().min(1, "Elija una categoría"),
  unidad_medida: z.string().min(1),
  costo: v.dinero("Costo"),
  precio_venta: v.dinero("Precio de venta"),
});
type Datos = z.infer<typeof esquema>;

function FormularioProducto({ producto, onCerrar }: { producto: Producto | null; onCerrar: () => void }) {
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const categorias = useCategorias();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<Datos>({
    resolver: zodResolver(esquema),
    defaultValues: {
      codigo: producto?.codigo ?? "",
      nombre: producto?.nombre ?? "",
      descripcion: producto?.descripcion ?? "",
      categoria_id: producto ? String(producto.categoria.id) : "",
      unidad_medida: producto?.unidad_medida ?? "unidad",
      costo: producto?.costo != null ? String(producto.costo) : "",
      precio_venta: producto?.precio_venta != null ? String(producto.precio_venta) : "",
    },
  });

  const guardar = useMutacion(
    (d: Datos) => {
      const comunes = {
        nombre: d.nombre.trim(),
        descripcion: d.descripcion.trim() || null,
        categoria_id: Number(d.categoria_id),
        unidad_medida: d.unidad_medida as UnidadMedida,
        costo: aDinero(d.costo),
        precio_venta: aDinero(d.precio_venta),
      };
      return producto ? apiProductos.actualizar(producto.id, comunes) : apiProductos.crear({ codigo: d.codigo.trim(), ...comunes });
    },
    { exito: producto ? "Producto actualizado." : "Producto creado.", invalidar: [["productos"], ["catalogo", "productos"]], avisarError: false, onExito: onCerrar },
  );

  return (
    <Modal
      abierto
      onCerrar={onCerrar}
      bloqueado={guardar.isPending}
      ancho="lg"
      titulo={producto ? "Editar producto" : "Nuevo producto"}
      descripcion={producto ? "El código no se puede modificar porque identifica al producto en el historial." : undefined}
      pie={
        <>
          <Button variante="ghost" onClick={onCerrar} disabled={guardar.isPending}>Cancelar</Button>
          <Button type="submit" form="form-producto" cargando={guardar.isPending}>{producto ? "Guardar cambios" : "Crear producto"}</Button>
        </>
      }
    >
      <form
        id="form-producto"
        noValidate
        className="grid gap-4 sm:grid-cols-2"
        onSubmit={handleSubmit(async (d) => {
          setErrorGeneral(null);
          try {
            await guardar.mutateAsync(d);
          } catch (e) {
            setErrorGeneral(aplicarErroresServidor(e, setError, ["codigo", "nombre", "descripcion", "categoria_id", "unidad_medida", "costo", "precio_venta"]));
          }
        })}
      >
        {errorGeneral && <Aviso tipo="error" className="sm:col-span-2">{errorGeneral}</Aviso>}
        <Input etiqueta="Código" required disabled={producto !== null} maxLength={50} placeholder="Ej. BIC-001" error={errors.codigo?.message} {...register("codigo")} />
        <Input etiqueta="Nombre" required maxLength={150} error={errors.nombre?.message} {...register("nombre")} />
        <Select etiqueta="Categoría" required error={errors.categoria_id?.message} {...register("categoria_id")}>
          <option value="">Seleccione…</option>
          {categorias.data?.map((c) => (
            <option key={c.id} value={c.id}>{c.nombre}</option>
          ))}
          {producto && !categorias.data?.some((c) => c.id === producto.categoria.id) && <option value={producto.categoria.id}>{producto.categoria.nombre}</option>}
        </Select>
        <Select etiqueta="Unidad de medida" error={errors.unidad_medida?.message} {...register("unidad_medida")}>
          {Object.entries(UNIDADES_MEDIDA).map(([k, n]) => (
            <option key={k} value={k}>{n}</option>
          ))}
        </Select>
        <Input etiqueta="Costo unitario" inputMode="decimal" placeholder="0" ayuda="Con el costo se calcula el valor del inventario." error={errors.costo?.message} {...register("costo")} />
        <Input etiqueta="Precio de venta" inputMode="decimal" placeholder="0" ayuda="Se usa por defecto al registrar ventas." error={errors.precio_venta?.message} {...register("precio_venta")} />
        <Textarea etiqueta="Descripción" className="sm:col-span-2" maxLength={500} error={errors.descripcion?.message} {...register("descripcion")} />
      </form>
    </Modal>
  );
}

export default function ProductosPage() {
  const { tiene } = useAuth();
  const categorias = useCategorias(false);
  const { filtros, pagina, tamano, cambiar, irAPagina, limpiar, hayFiltros } = useFiltros({ q: "", categoria_id: "", activo: "" });
  const [edicion, setEdicion] = useState<Producto | "nuevo" | null>(null);
  const [aCambiar, setACambiar] = useState<Producto | null>(null);

  const lista = useQuery({
    queryKey: ["productos", filtros, pagina],
    queryFn: () => apiProductos.listar({ q: filtros.q, categoria_id: aNumero(filtros.categoria_id), activo: aBooleano(filtros.activo), pagina, tamano }),
    placeholderData: keepPreviousData,
  });

  const estado = useMutacion((p: Producto) => apiProductos.estado(p.id, !p.activo), {
    exito: (p) => (p.activo ? "Producto activado." : "Producto inhabilitado."),
    invalidar: [["productos"], ["catalogo", "productos"], ["inventario"]],
    onExito: () => setACambiar(null),
  });

  const puedeEditar = tiene("productos.editar");
  const puedeInhabilitar = tiene("productos.inhabilitar");

  return (
    <>
      <EncabezadoPagina
        titulo="Productos"
        descripcion="Catálogo de productos de la empresa. Las existencias se registran por sede desde la sección Existencias."
        acciones={tiene("productos.crear") && <Button icono={<Plus className="size-4" aria-hidden />} onClick={() => setEdicion("nuevo")}>Nuevo producto</Button>}
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
          <FiltroSelect etiqueta="Estado" value={filtros.activo} onChange={(e) => cambiar({ activo: e.target.value })}>
            <option value="">Todos los estados</option>
            <option value="true">Activos</option>
            <option value="false">Inhabilitados</option>
          </FiltroSelect>
        </BarraFiltros>
        <Tabla
          descripcion="Listado de productos"
          idDe={(p) => p.id}
          filas={lista.data?.items}
          cargando={lista.isFetching}
          error={lista.error}
          onReintentar={() => lista.refetch()}
          vacio={{
            titulo: hayFiltros ? "Sin resultados" : "Aún no hay productos",
            descripcion: hayFiltros ? "Pruebe con otros filtros." : "Registre el primer producto para comenzar a controlar su inventario.",
            accion: !hayFiltros && tiene("productos.crear") ? <Button onClick={() => setEdicion("nuevo")}>Nuevo producto</Button> : undefined,
          }}
          columnas={[
            { clave: "codigo", encabezado: "Código", celda: (p) => <span className="font-mono text-[13px] text-ink-dim">{p.codigo}</span> },
            { clave: "nombre", encabezado: "Producto", celda: (p) => <span className="font-medium">{p.nombre}</span> },
            { clave: "categoria", encabezado: "Categoría", desde: "md", celda: (p) => p.categoria.nombre },
            { clave: "unidad", encabezado: "Unidad", desde: "lg", celda: (p) => <span className="text-ink-dim">{UNIDADES_MEDIDA[p.unidad_medida] ?? p.unidad_medida}</span> },
            { clave: "costo", encabezado: "Costo", alinear: "derecha", desde: "lg", celda: (p) => <span className="tabular">{moneda(p.costo)}</span> },
            { clave: "precio", encabezado: "Precio", alinear: "derecha", desde: "md", celda: (p) => <span className="tabular">{moneda(p.precio_venta)}</span> },
            { clave: "existencias", encabezado: "Existencias", alinear: "derecha", desde: "sm", celda: (p) => <span className="tabular">{entero(p.existencias_total ?? 0)}</span> },
            { clave: "estado", encabezado: "Estado", celda: (p) => <Badge tono={p.activo ? "success" : "neutral"}>{p.activo ? "Activo" : "Inhabilitado"}</Badge> },
            {
              clave: "acciones",
              encabezado: "Acciones",
              alinear: "derecha",
              celda: (p) => (
                <div className="flex justify-end gap-1">
                  {puedeEditar && <IconButton etiqueta={`Editar ${p.nombre}`} onClick={() => setEdicion(p)}><Pencil className="size-4" aria-hidden /></IconButton>}
                  {puedeInhabilitar && <IconButton etiqueta={p.activo ? `Inhabilitar ${p.nombre}` : `Activar ${p.nombre}`} onClick={() => setACambiar(p)}><Power className="size-4" aria-hidden /></IconButton>}
                </div>
              ),
            },
          ]}
        />
        {lista.data && <Paginacion pagina={lista.data.pagina} paginas={lista.data.paginas} total={lista.data.total} tamano={lista.data.tamano} onCambiar={irAPagina} />}
      </Card>

      {edicion && <FormularioProducto producto={edicion === "nuevo" ? null : edicion} onCerrar={() => setEdicion(null)} />}
      <ConfirmDialog
        abierto={aCambiar !== null}
        titulo={aCambiar?.activo ? "Inhabilitar producto" : "Activar producto"}
        mensaje={
          aCambiar?.activo
            ? `«${aCambiar.nombre}» no podrá usarse en nuevas ventas, entradas ni traslados. El historial se conserva.`
            : `«${aCambiar?.nombre}» volverá a estar disponible para operar.`
        }
        confirmarTexto={aCambiar?.activo ? "Inhabilitar" : "Activar"}
        peligroso={aCambiar?.activo}
        cargando={estado.isPending}
        onConfirmar={() => aCambiar && estado.mutate(aCambiar)}
        onCancelar={() => setACambiar(null)}
      />
    </>
  );
}
