import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Pencil, Plus, Power } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { apiCategorias } from "@/api/catalogo";
import { useAuth } from "@/auth/AuthContext";
import { Aviso } from "@/components/ui/Aviso";
import { Badge } from "@/components/ui/Badge";
import { Button, IconButton } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Tabla } from "@/components/ui/DataTable";
import { FiltroSelect, Input, Textarea } from "@/components/ui/Field";
import { BarraFiltros } from "@/components/ui/FiltrosBarra";
import { Modal } from "@/components/ui/Modal";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { Paginacion } from "@/components/ui/Pagination";
import { Busqueda } from "@/components/ui/SearchInput";
import { aBooleano, useFiltros } from "@/hooks/useFiltros";
import { useMutacion } from "@/hooks/useMutacion";
import { entero, fecha } from "@/lib/format";
import { aplicarErroresServidor, v } from "@/lib/formularios";
import type { Categoria } from "@/types/api";

const esquema = z.object({ nombre: v.texto("El nombre", 2, 100), descripcion: v.textoOpcional(255) });
type Datos = z.infer<typeof esquema>;

function FormularioCategoria({ categoria, onCerrar }: { categoria: Categoria | null; onCerrar: () => void }) {
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<Datos>({ resolver: zodResolver(esquema), defaultValues: { nombre: categoria?.nombre ?? "", descripcion: categoria?.descripcion ?? "" } });

  const guardar = useMutacion(
    (d: Datos) => {
      const cuerpo = { nombre: d.nombre.trim(), descripcion: d.descripcion.trim() || null };
      return categoria ? apiCategorias.actualizar(categoria.id, cuerpo) : apiCategorias.crear(cuerpo);
    },
    { exito: categoria ? "Categoría actualizada." : "Categoría creada.", invalidar: [["categorias"], ["catalogo", "categorias"]], avisarError: false, onExito: onCerrar },
  );

  return (
    <Modal
      abierto
      onCerrar={onCerrar}
      bloqueado={guardar.isPending}
      titulo={categoria ? "Editar categoría" : "Nueva categoría"}
      pie={
        <>
          <Button variante="ghost" onClick={onCerrar} disabled={guardar.isPending}>Cancelar</Button>
          <Button type="submit" form="form-categoria" cargando={guardar.isPending}>{categoria ? "Guardar cambios" : "Crear categoría"}</Button>
        </>
      }
    >
      <form
        id="form-categoria"
        noValidate
        className="flex flex-col gap-4"
        onSubmit={handleSubmit(async (d) => {
          setErrorGeneral(null);
          try {
            await guardar.mutateAsync(d);
          } catch (e) {
            setErrorGeneral(aplicarErroresServidor(e, setError, ["nombre", "descripcion"]));
          }
        })}
      >
        {errorGeneral && <Aviso tipo="error">{errorGeneral}</Aviso>}
        <Input etiqueta="Nombre" required maxLength={100} error={errors.nombre?.message} {...register("nombre")} />
        <Textarea etiqueta="Descripción" maxLength={255} placeholder="Opcional. Ayuda a distinguir esta categoría." error={errors.descripcion?.message} {...register("descripcion")} />
      </form>
    </Modal>
  );
}

export default function CategoriasPage() {
  const { tiene } = useAuth();
  const { filtros, pagina, tamano, cambiar, irAPagina, limpiar, hayFiltros } = useFiltros({ q: "", activa: "" });
  const [edicion, setEdicion] = useState<Categoria | "nueva" | null>(null);
  const [aCambiar, setACambiar] = useState<Categoria | null>(null);

  const lista = useQuery({
    queryKey: ["categorias", filtros, pagina],
    queryFn: () => apiCategorias.listar({ q: filtros.q, activa: aBooleano(filtros.activa), pagina, tamano }),
    placeholderData: keepPreviousData,
  });

  const estado = useMutacion((c: Categoria) => apiCategorias.estado(c.id, !c.activa), {
    exito: (c) => (c.activa ? "Categoría activada." : "Categoría inhabilitada."),
    invalidar: [["categorias"], ["catalogo", "categorias"]],
    onExito: () => setACambiar(null),
  });

  return (
    <>
      <EncabezadoPagina
        titulo="Categorías"
        descripcion="Agrupe sus productos para filtrarlos y reportarlos con facilidad."
        acciones={tiene("categorias.crear") && <Button icono={<Plus className="size-4" aria-hidden />} onClick={() => setEdicion("nueva")}>Nueva categoría</Button>}
      />
      <Card>
        <BarraFiltros hayFiltros={hayFiltros} onLimpiar={limpiar}>
          <Busqueda valor={filtros.q} onCambiar={(q) => cambiar({ q })} placeholder="Buscar categoría…" />
          <FiltroSelect etiqueta="Estado" value={filtros.activa} onChange={(e) => cambiar({ activa: e.target.value })}>
            <option value="">Todos los estados</option>
            <option value="true">Activas</option>
            <option value="false">Inhabilitadas</option>
          </FiltroSelect>
        </BarraFiltros>
        <Tabla
          descripcion="Listado de categorías"
          idDe={(c) => c.id}
          filas={lista.data?.items}
          cargando={lista.isFetching}
          error={lista.error}
          onReintentar={() => lista.refetch()}
          vacio={{
            titulo: hayFiltros ? "Sin resultados" : "Aún no hay categorías",
            descripcion: hayFiltros ? "Pruebe con otros filtros." : "Cree la primera categoría para empezar a organizar su catálogo.",
            accion: !hayFiltros && tiene("categorias.crear") ? <Button onClick={() => setEdicion("nueva")}>Nueva categoría</Button> : undefined,
          }}
          columnas={[
            { clave: "nombre", encabezado: "Nombre", celda: (c) => <span className="font-medium">{c.nombre}</span> },
            { clave: "descripcion", encabezado: "Descripción", desde: "md", celda: (c) => <span className="text-ink-dim">{c.descripcion ?? "—"}</span> },
            { clave: "productos", encabezado: "Productos", alinear: "derecha", celda: (c) => <span className="tabular">{entero(c.total_productos ?? 0)}</span> },
            { clave: "creada", encabezado: "Creada", desde: "lg", celda: (c) => <span className="text-ink-dim">{fecha(c.created_at)}</span> },
            { clave: "estado", encabezado: "Estado", celda: (c) => <Badge tono={c.activa ? "success" : "neutral"}>{c.activa ? "Activa" : "Inhabilitada"}</Badge> },
            {
              clave: "acciones",
              encabezado: "Acciones",
              alinear: "derecha",
              celda: (c) => (
                <div className="flex justify-end gap-1">
                  {tiene("categorias.editar") && (
                    <>
                      <IconButton etiqueta={`Editar ${c.nombre}`} onClick={() => setEdicion(c)}><Pencil className="size-4" aria-hidden /></IconButton>
                      <IconButton etiqueta={c.activa ? `Inhabilitar ${c.nombre}` : `Activar ${c.nombre}`} onClick={() => setACambiar(c)}><Power className="size-4" aria-hidden /></IconButton>
                    </>
                  )}
                </div>
              ),
            },
          ]}
        />
        {lista.data && <Paginacion pagina={lista.data.pagina} paginas={lista.data.paginas} total={lista.data.total} tamano={lista.data.tamano} onCambiar={irAPagina} />}
      </Card>

      {edicion && <FormularioCategoria categoria={edicion === "nueva" ? null : edicion} onCerrar={() => setEdicion(null)} />}
      <ConfirmDialog
        abierto={aCambiar !== null}
        titulo={aCambiar?.activa ? "Inhabilitar categoría" : "Activar categoría"}
        mensaje={
          aCambiar?.activa
            ? `«${aCambiar.nombre}» dejará de estar disponible para productos nuevos. Los productos existentes no se modifican.`
            : `«${aCambiar?.nombre}» volverá a estar disponible.`
        }
        confirmarTexto={aCambiar?.activa ? "Inhabilitar" : "Activar"}
        peligroso={aCambiar?.activa}
        cargando={estado.isPending}
        onConfirmar={() => aCambiar && estado.mutate(aCambiar)}
        onCancelar={() => setACambiar(null)}
      />
    </>
  );
}
