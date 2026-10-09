import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Pencil, Plus, Power } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { apiSedes } from "@/api/administracion";
import { useAuth } from "@/auth/AuthContext";
import { Aviso } from "@/components/ui/Aviso";
import { Badge } from "@/components/ui/Badge";
import { Button, IconButton } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Tabla } from "@/components/ui/DataTable";
import { FiltroSelect, Input } from "@/components/ui/Field";
import { BarraFiltros } from "@/components/ui/FiltrosBarra";
import { Modal } from "@/components/ui/Modal";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { Paginacion } from "@/components/ui/Pagination";
import { Busqueda } from "@/components/ui/SearchInput";
import { aBooleano, useFiltros } from "@/hooks/useFiltros";
import { useMutacion } from "@/hooks/useMutacion";
import { entero } from "@/lib/format";
import { aplicarErroresServidor, v } from "@/lib/formularios";
import type { Sede } from "@/types/api";

const esquema = z.object({ nombre: v.texto("El nombre", 2, 120), ciudad: v.texto("La ciudad", 2, 100), direccion: v.textoOpcional(200) });
type Datos = z.infer<typeof esquema>;

const INVALIDAR = [["sedes"], ["catalogo", "sedes"], ["catalogo", "directorio-sedes"]];

function FormularioSede({ sede, onCerrar }: { sede: Sede | null; onCerrar: () => void }) {
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<Datos>({ resolver: zodResolver(esquema), defaultValues: { nombre: sede?.nombre ?? "", ciudad: sede?.ciudad ?? "", direccion: sede?.direccion ?? "" } });
  const guardar = useMutacion(
    (d: Datos) => {
      const cuerpo = { nombre: d.nombre.trim(), ciudad: d.ciudad.trim(), direccion: d.direccion.trim() || null };
      return sede ? apiSedes.actualizar(sede.id, cuerpo) : apiSedes.crear(cuerpo);
    },
    { exito: sede ? "Sede actualizada." : "Sede creada.", invalidar: INVALIDAR, avisarError: false, onExito: onCerrar },
  );
  return (
    <Modal
      abierto
      onCerrar={onCerrar}
      bloqueado={guardar.isPending}
      titulo={sede ? "Editar sede" : "Nueva sede"}
      pie={
        <>
          <Button variante="ghost" onClick={onCerrar} disabled={guardar.isPending}>Cancelar</Button>
          <Button type="submit" form="form-sede" cargando={guardar.isPending}>{sede ? "Guardar cambios" : "Crear sede"}</Button>
        </>
      }
    >
      <form
        id="form-sede"
        noValidate
        className="flex flex-col gap-4"
        onSubmit={handleSubmit(async (d) => {
          setErrorGeneral(null);
          try {
            await guardar.mutateAsync(d);
          } catch (e) {
            setErrorGeneral(aplicarErroresServidor(e, setError, ["nombre", "ciudad", "direccion"]));
          }
        })}
      >
        {errorGeneral && <Aviso tipo="error">{errorGeneral}</Aviso>}
        <Input etiqueta="Nombre de la sede" required placeholder="Ej. Sede Norte" error={errors.nombre?.message} {...register("nombre")} />
        <Input etiqueta="Ciudad" required error={errors.ciudad?.message} {...register("ciudad")} />
        <Input etiqueta="Dirección" error={errors.direccion?.message} {...register("direccion")} />
      </form>
    </Modal>
  );
}

export default function SedesPage() {
  const { tiene } = useAuth();
  const { filtros, pagina, tamano, cambiar, irAPagina, limpiar, hayFiltros } = useFiltros({ q: "", activa: "" }, 20);
  const [edicion, setEdicion] = useState<Sede | "nueva" | null>(null);
  const [aCambiar, setACambiar] = useState<Sede | null>(null);
  const [errorEstado, setErrorEstado] = useState<string | null>(null);

  const lista = useQuery({
    queryKey: ["sedes", filtros, pagina],
    queryFn: () => apiSedes.listar({ q: filtros.q, activa: aBooleano(filtros.activa), pagina, tamano }),
    placeholderData: keepPreviousData,
  });
  const estado = useMutacion((s: Sede) => apiSedes.estado(s.id, !s.activa), {
    exito: (s) => (s.activa ? "Sede activada." : "Sede inhabilitada."),
    invalidar: [...INVALIDAR, ["dashboard"]],
    avisarError: false,
    onExito: () => setACambiar(null),
  });

  return (
    <>
      <EncabezadoPagina
        titulo="Sedes"
        descripcion="Puntos de venta o bodegas de la empresa. Cada sede tiene su propio inventario."
        acciones={tiene("sedes.crear") && <Button icono={<Plus className="size-4" aria-hidden />} onClick={() => setEdicion("nueva")}>Nueva sede</Button>}
      />
      <Card>
        <BarraFiltros hayFiltros={hayFiltros} onLimpiar={limpiar}>
          <Busqueda valor={filtros.q} onCambiar={(q) => cambiar({ q })} placeholder="Buscar por nombre, ciudad o dirección…" className="sm:max-w-sm" />
          <FiltroSelect etiqueta="Estado" value={filtros.activa} onChange={(e) => cambiar({ activa: e.target.value })}>
            <option value="">Todos los estados</option>
            <option value="true">Activas</option>
            <option value="false">Inhabilitadas</option>
          </FiltroSelect>
        </BarraFiltros>
        <Tabla
          descripcion="Listado de sedes"
          idDe={(s) => s.id}
          filas={lista.data?.items}
          cargando={lista.isFetching}
          error={lista.error}
          onReintentar={() => lista.refetch()}
          vacio={{
            titulo: hayFiltros ? "Sin resultados" : "Aún no hay sedes",
            descripcion: hayFiltros ? "Pruebe con otros filtros." : "Cree la primera sede para registrar inventario.",
            accion: !hayFiltros && tiene("sedes.crear") ? <Button onClick={() => setEdicion("nueva")}>Nueva sede</Button> : undefined,
          }}
          columnas={[
            { clave: "nombre", encabezado: "Sede", celda: (s) => <span className="font-medium">{s.nombre}</span> },
            { clave: "ciudad", encabezado: "Ciudad", desde: "sm", celda: (s) => s.ciudad ?? "—" },
            { clave: "direccion", encabezado: "Dirección", desde: "lg", celda: (s) => <span className="text-ink-dim">{s.direccion ?? "—"}</span> },
            { clave: "usuarios", encabezado: "Usuarios", alinear: "derecha", desde: "md", celda: (s) => <span className="tabular">{entero(s.total_usuarios ?? 0)}</span> },
            { clave: "unidades", encabezado: "Unidades", alinear: "derecha", desde: "md", celda: (s) => <span className="tabular">{entero(s.unidades_en_existencia ?? 0)}</span> },
            { clave: "estado", encabezado: "Estado", celda: (s) => <Badge tono={s.activa ? "success" : "neutral"}>{s.activa ? "Activa" : "Inhabilitada"}</Badge> },
            {
              clave: "acciones",
              encabezado: "Acciones",
              alinear: "derecha",
              celda: (s) => (
                <div className="flex justify-end gap-1">
                  {tiene("sedes.editar") && <IconButton etiqueta={`Editar ${s.nombre}`} onClick={() => setEdicion(s)}><Pencil className="size-4" aria-hidden /></IconButton>}
                  {tiene("sedes.inhabilitar") && <IconButton etiqueta={s.activa ? `Inhabilitar ${s.nombre}` : `Activar ${s.nombre}`} onClick={() => { setErrorEstado(null); setACambiar(s); }}><Power className="size-4" aria-hidden /></IconButton>}
                </div>
              ),
            },
          ]}
        />
        {lista.data && <Paginacion pagina={lista.data.pagina} paginas={lista.data.paginas} total={lista.data.total} tamano={lista.data.tamano} onCambiar={irAPagina} />}
      </Card>
      {edicion && <FormularioSede sede={edicion === "nueva" ? null : edicion} onCerrar={() => setEdicion(null)} />}
      <ConfirmDialog
        abierto={aCambiar !== null}
        titulo={aCambiar?.activa ? "Inhabilitar sede" : "Activar sede"}
        mensaje={aCambiar?.activa ? `«${aCambiar.nombre}» dejará de aceptar operaciones. Su historial se conserva. Si tiene existencias o traslados pendientes, el sistema le indicará qué resolver primero.` : `«${aCambiar?.nombre}» volverá a operar.`}
        confirmarTexto={aCambiar?.activa ? "Inhabilitar" : "Activar"}
        peligroso={aCambiar?.activa}
        cargando={estado.isPending}
        error={errorEstado}
        onConfirmar={async () => {
          if (!aCambiar) return;
          setErrorEstado(null);
          try {
            await estado.mutateAsync(aCambiar);
          } catch (e) {
            setErrorEstado(e instanceof Error ? e.message : "No se pudo completar la acción.");
          }
        }}
        onCancelar={() => setACambiar(null)}
      />
    </>
  );
}
