import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Lock, Pencil, Plus, Power, Trash2, Users } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { apiRoles } from "@/api/administracion";
import { useAuth } from "@/auth/AuthContext";
import { Aviso } from "@/components/ui/Aviso";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { EstadoError } from "@/components/ui/EstadoVacio";
import { Casilla, Input, Select, Textarea } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { useMutacion } from "@/hooks/useMutacion";
import { cn } from "@/lib/cn";
import { mensajeDeError } from "@/lib/errors";
import { aplicarErroresServidor, v } from "@/lib/formularios";
import type { Permiso, Rol } from "@/types/api";

const INVALIDAR = [["roles"], ["catalogo", "roles"], ["usuarios"]];
const ALCANCE: Record<string, string> = { empresa: "Todas las sedes", sede: "Una sede" };

const esquema = z.object({
  nombre: v.texto("El nombre", 3, 80),
  descripcion: v.textoOpcional(300),
  alcance: z.enum(["empresa", "sede"]),
});
type Datos = z.infer<typeof esquema>;

function FormularioRol({ rol, onCerrar, onCreado }: { rol: Rol | null; onCerrar: () => void; onCreado?: (r: Rol) => void }) {
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<Datos>({
    resolver: zodResolver(esquema),
    defaultValues: { nombre: rol?.nombre ?? "", descripcion: rol?.descripcion ?? "", alcance: (rol?.alcance as Datos["alcance"]) ?? "sede" },
  });
  const alcanceFijo = Boolean(rol && (rol.es_sistema || rol.total_usuarios > 0));
  const guardar = useMutacion(
    (d: Datos) => {
      const descripcion = d.descripcion.trim() || null;
      return rol
        ? apiRoles.actualizar(rol.id, { nombre: rol.es_sistema ? undefined : d.nombre.trim(), descripcion, alcance: alcanceFijo ? undefined : d.alcance })
        : apiRoles.crear({ nombre: d.nombre.trim(), descripcion, alcance: d.alcance, permisos: [] });
    },
    { exito: rol ? "Rol actualizado." : "Rol creado. Ahora asigne sus permisos.", invalidar: INVALIDAR, avisarError: false, onExito: (r) => { onCerrar(); if (!rol) onCreado?.(r); } },
  );
  return (
    <Modal
      abierto
      onCerrar={onCerrar}
      bloqueado={guardar.isPending}
      titulo={rol ? "Editar rol" : "Nuevo rol"}
      descripcion={rol ? undefined : "Defina el nombre y el alcance. Los permisos se asignan después."}
      pie={
        <>
          <Button variante="ghost" onClick={onCerrar} disabled={guardar.isPending}>Cancelar</Button>
          <Button type="submit" form="form-rol" cargando={guardar.isPending}>{rol ? "Guardar cambios" : "Crear rol"}</Button>
        </>
      }
    >
      <form
        id="form-rol"
        noValidate
        className="flex flex-col gap-4"
        onSubmit={handleSubmit(async (d) => {
          setErrorGeneral(null);
          try {
            await guardar.mutateAsync(d);
          } catch (e) {
            setErrorGeneral(aplicarErroresServidor(e, setError, ["nombre", "descripcion", "alcance"]));
          }
        })}
      >
        {errorGeneral && <Aviso tipo="error">{errorGeneral}</Aviso>}
        <Input etiqueta="Nombre del rol" required disabled={rol?.es_sistema} placeholder="Ej. Auxiliar de bodega" error={errors.nombre?.message} ayuda={rol?.es_sistema ? "Los roles del sistema conservan su nombre." : undefined} {...register("nombre")} />
        <Textarea etiqueta="Descripción" rows={2} placeholder="Qué responsabilidades cubre este rol" error={errors.descripcion?.message} {...register("descripcion")} />
        <Select
          etiqueta="Alcance"
          disabled={alcanceFijo}
          error={errors.alcance?.message}
          ayuda={alcanceFijo ? "No se puede cambiar en roles del sistema ni en roles con usuarios asignados." : "«Una sede»: la persona solo ve y opera su sede. «Todas las sedes»: ve la información consolidada."}
          {...register("alcance")}
        >
          <option value="sede">Una sede</option>
          <option value="empresa">Todas las sedes</option>
        </Select>
      </form>
    </Modal>
  );
}

function agruparPorModulo(permisos: Permiso[]): [string, Permiso[]][] {
  const mapa = new Map<string, Permiso[]>();
  for (const p of permisos) mapa.set(p.modulo, [...(mapa.get(p.modulo) ?? []), p]);
  return [...mapa.entries()];
}

function EditorPermisos({ rol, catalogo }: { rol: Rol; catalogo: Permiso[] }) {
  const { tiene, sesion } = useAuth();
  const propios = useMemo(() => new Set(sesion?.permisos ?? []), [sesion]);
  const [seleccion, setSeleccion] = useState<Set<string>>(() => new Set(rol.permisos));
  const [error, setError] = useState<string | null>(null);
  const esAdmin = rol.clave === "admin";
  const puedeEditar = tiene("roles.asignar_permisos") && !esAdmin;
  const grupos = useMemo(() => agruparPorModulo(catalogo), [catalogo]);
  const original = useMemo(() => new Set(rol.permisos), [rol.permisos]);
  const hayCambios = seleccion.size !== original.size || [...seleccion].some((p) => !original.has(p));

  const guardar = useMutacion(
    // Solo se envían permisos que quien edita posee; el servidor conserva los demás que el rol ya tenía.
    () => apiRoles.asignarPermisos(rol.id, [...seleccion].filter((p) => propios.has(p))),
    { exito: "Permisos actualizados.", invalidar: INVALIDAR, avisarError: false },
  );

  const editable = (codigo: string) => puedeEditar && propios.has(codigo);
  function alternar(codigo: string) {
    setSeleccion((previa) => {
      const nueva = new Set(previa);
      if (nueva.has(codigo)) nueva.delete(codigo);
      else nueva.add(codigo);
      return nueva;
    });
  }
  function alternarGrupo(permisos: Permiso[]) {
    const editables = permisos.filter((p) => editable(p.codigo));
    const todosMarcados = editables.every((p) => seleccion.has(p.codigo));
    setSeleccion((previa) => {
      const nueva = new Set(previa);
      for (const p of editables) {
        if (todosMarcados) nueva.delete(p.codigo);
        else nueva.add(p.codigo);
      }
      return nueva;
    });
  }

  return (
    <div className="flex flex-col">
      {esAdmin && <Aviso tipo="info" className="m-5 mb-0">El rol Administrador siempre tiene todos los permisos y no se puede modificar.</Aviso>}
      {!esAdmin && !puedeEditar && <Aviso tipo="info" className="m-5 mb-0">Su rol puede consultar los permisos, pero no modificarlos.</Aviso>}
      {puedeEditar && catalogo.some((p) => !propios.has(p.codigo)) && (
        <Aviso tipo="info" className="m-5 mb-0">Solo puede conceder permisos que usted mismo tiene. Los demás aparecen bloqueados.</Aviso>
      )}
      {error && <Aviso tipo="error" className="m-5 mb-0">{error}</Aviso>}
      <div className="flex flex-col gap-6 p-5">
        {grupos.map(([modulo, permisos]) => {
          const marcados = permisos.filter((p) => seleccion.has(p.codigo)).length;
          const editables = permisos.filter((p) => editable(p.codigo));
          return (
            <fieldset key={modulo} className="min-w-0">
              <legend className="mb-3 flex w-full items-center justify-between gap-3">
                <span className="font-display text-sm font-semibold text-ink">
                  {modulo} <span className="tabular ml-1 text-xs font-normal text-ink-faint">{marcados}/{permisos.length}</span>
                </span>
                {editables.length > 0 && (
                  <button type="button" onClick={() => alternarGrupo(permisos)} className="text-xs font-semibold text-accent-light hover:underline">
                    {editables.every((p) => seleccion.has(p.codigo)) ? "Quitar todos" : "Marcar todos"}
                  </button>
                )}
              </legend>
              <div className="grid grid-cols-1 gap-x-6 gap-y-3 md:grid-cols-2">
                {permisos.map((p) => (
                  <Casilla
                    key={p.codigo}
                    checked={seleccion.has(p.codigo)}
                    disabled={!editable(p.codigo)}
                    onChange={() => alternar(p.codigo)}
                    etiqueta={p.descripcion}
                    descripcion={p.codigo}
                  />
                ))}
              </div>
            </fieldset>
          );
        })}
      </div>
      {puedeEditar && (
        <div className="sticky bottom-0 flex flex-wrap items-center justify-between gap-3 rounded-b-(--radius-panel) border-t border-line bg-surface/95 px-5 py-3 backdrop-blur">
          <span className="text-[13px] text-ink-dim" aria-live="polite">
            {hayCambios ? "Hay cambios sin guardar." : "Sin cambios pendientes."} <span className="tabular text-ink-faint">{seleccion.size} permisos activos</span>
          </span>
          <div className="flex gap-2">
            <Button variante="ghost" disabled={!hayCambios || guardar.isPending} onClick={() => { setSeleccion(new Set(original)); setError(null); }}>Descartar</Button>
            <Button
              disabled={!hayCambios}
              cargando={guardar.isPending}
              onClick={async () => {
                setError(null);
                try {
                  await guardar.mutateAsync(undefined);
                } catch (e) {
                  setError(mensajeDeError(e));
                }
              }}
            >
              Guardar permisos
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function RolesPage() {
  const { tiene } = useAuth();
  const roles = useQuery({ queryKey: ["roles"], queryFn: apiRoles.listar });
  const permisos = useQuery({ queryKey: ["roles", "permisos"], queryFn: apiRoles.permisos, staleTime: 10 * 60_000, enabled: tiene("roles.ver") });
  const [elegido, setElegido] = useState<number | null>(null);
  const [edicion, setEdicion] = useState<Rol | "nuevo" | null>(null);
  const [aEliminar, setAEliminar] = useState<Rol | null>(null);
  const [aCambiar, setACambiar] = useState<Rol | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);

  const lista = roles.data ?? [];
  const actual = lista.find((r) => r.id === elegido) ?? lista[0];

  const eliminar = useMutacion((r: Rol) => apiRoles.eliminar(r.id), { exito: "Rol eliminado.", invalidar: INVALIDAR, avisarError: false, onExito: () => { setAEliminar(null); setElegido(null); } });
  const estado = useMutacion((r: Rol) => apiRoles.actualizar(r.id, { activo: !r.activo }), {
    exito: (r) => (r.activo ? "Rol activado." : "Rol inhabilitado."),
    invalidar: INVALIDAR,
    avisarError: false,
    onExito: () => setACambiar(null),
  });

  return (
    <>
      <EncabezadoPagina
        titulo="Roles y permisos"
        descripcion="Cada rol agrupa lo que una persona puede hacer. Los cambios aplican a todos sus usuarios en su próximo ingreso o renovación de sesión."
        acciones={tiene("roles.crear") && <Button icono={<Plus className="size-4" aria-hidden />} onClick={() => setEdicion("nuevo")}>Nuevo rol</Button>}
      />
      {roles.isError && !roles.data ? (
        <Card><EstadoError error={roles.error} onReintentar={() => roles.refetch()} /></Card>
      ) : (
        <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[300px_1fr]">
          <Card className="overflow-hidden">
            <ul aria-label="Roles de la empresa" className="divide-y divide-line">
              {roles.isLoading
                ? Array.from({ length: 5 }, (_, i) => (
                    <li key={i} className="p-4"><Skeleton className="h-4 w-32" /><Skeleton className="mt-2 h-3 w-24" /></li>
                  ))
                : lista.map((r) => (
                    <li key={r.id}>
                      <button
                        type="button"
                        onClick={() => setElegido(r.id)}
                        aria-current={actual?.id === r.id ? "true" : undefined}
                        className={cn(
                          "flex w-full flex-col gap-1.5 px-4 py-3.5 text-left transition hover:bg-white/4",
                          actual?.id === r.id && "bg-accent-dim/60 shadow-[inset_3px_0_0_0_var(--color-accent)]",
                        )}
                      >
                        <span className="flex items-center gap-2 text-sm font-semibold text-ink">
                          {r.nombre}
                          {r.es_sistema && <Lock className="size-3.5 text-ink-faint" aria-label="Rol del sistema" />}
                          {!r.activo && <Badge>Inhabilitado</Badge>}
                        </span>
                        <span className="flex items-center gap-3 text-xs text-ink-faint">
                          <span className="inline-flex items-center gap-1"><Users className="size-3.5" aria-hidden />{r.total_usuarios}</span>
                          <span>{ALCANCE[r.alcance] ?? r.alcance}</span>
                          <span className="tabular">{r.permisos.length} permisos</span>
                        </span>
                      </button>
                    </li>
                  ))}
            </ul>
          </Card>

          {actual && (
            <Card>
              <CardHeader
                titulo={actual.nombre}
                descripcion={actual.descripcion ?? "Sin descripción."}
                accion={
                  <div className="flex flex-wrap items-center gap-2">
                    {actual.es_sistema && <Badge tono="accent">Rol del sistema</Badge>}
                    {tiene("roles.editar") && actual.clave !== "admin" && (
                      <>
                        <Button variante="secondary" tamano="sm" icono={<Pencil className="size-3.5" aria-hidden />} onClick={() => setEdicion(actual)}>Editar</Button>
                        <Button variante="secondary" tamano="sm" icono={<Power className="size-3.5" aria-hidden />} onClick={() => { setErrorAccion(null); setACambiar(actual); }}>
                          {actual.activo ? "Inhabilitar" : "Activar"}
                        </Button>
                        {!actual.es_sistema && (
                          <Button variante="danger" tamano="sm" icono={<Trash2 className="size-3.5" aria-hidden />} onClick={() => { setErrorAccion(null); setAEliminar(actual); }}>Eliminar</Button>
                        )}
                      </>
                    )}
                  </div>
                }
              />
              <div className="flex flex-wrap gap-x-6 gap-y-1 border-b border-line px-5 py-3 text-[13px] text-ink-dim">
                <span>Alcance: <strong className="font-semibold text-ink">{ALCANCE[actual.alcance] ?? actual.alcance}</strong></span>
                <span>Usuarios asignados: <strong className="tabular font-semibold text-ink">{actual.total_usuarios}</strong></span>
              </div>
              {permisos.isLoading ? (
                <div className="grid gap-3 p-5 md:grid-cols-2">{Array.from({ length: 8 }, (_, i) => <Skeleton key={i} className="h-5 w-full" />)}</div>
              ) : permisos.isError ? (
                <EstadoError error={permisos.error} onReintentar={() => permisos.refetch()} />
              ) : (
                <EditorPermisos key={`${actual.id}-${actual.permisos.join(",")}`} rol={actual} catalogo={permisos.data ?? []} />
              )}
            </Card>
          )}
        </div>
      )}

      {edicion && <FormularioRol rol={edicion === "nuevo" ? null : edicion} onCerrar={() => setEdicion(null)} onCreado={(r) => setElegido(r.id)} />}
      <ConfirmDialog
        abierto={aEliminar !== null}
        titulo="Eliminar rol"
        mensaje={`Se eliminará el rol «${aEliminar?.nombre}». Solo es posible si no tiene usuarios asignados. Esta acción no se puede deshacer.`}
        confirmarTexto="Eliminar"
        peligroso
        cargando={eliminar.isPending}
        error={errorAccion}
        onConfirmar={async () => {
          if (!aEliminar) return;
          setErrorAccion(null);
          try {
            await eliminar.mutateAsync(aEliminar);
          } catch (e) {
            setErrorAccion(mensajeDeError(e));
          }
        }}
        onCancelar={() => setAEliminar(null)}
      />
      <ConfirmDialog
        abierto={aCambiar !== null}
        titulo={aCambiar?.activo ? "Inhabilitar rol" : "Activar rol"}
        mensaje={aCambiar?.activo ? `«${aCambiar.nombre}» no podrá asignarse a nuevos usuarios. Solo es posible si no tiene usuarios asignados.` : `«${aCambiar?.nombre}» volverá a poder asignarse.`}
        confirmarTexto={aCambiar?.activo ? "Inhabilitar" : "Activar"}
        peligroso={aCambiar?.activo}
        cargando={estado.isPending}
        error={errorAccion}
        onConfirmar={async () => {
          if (!aCambiar) return;
          setErrorAccion(null);
          try {
            await estado.mutateAsync(aCambiar);
          } catch (e) {
            setErrorAccion(mensajeDeError(e));
          }
        }}
        onCancelar={() => setACambiar(null)}
      />
    </>
  );
}
