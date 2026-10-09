import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { KeyRound, LockOpen, Pencil, Plus, Power, Wand2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { apiUsuarios } from "@/api/administracion";
import { useAuth } from "@/auth/AuthContext";
import { Aviso } from "@/components/ui/Aviso";
import { Badge } from "@/components/ui/Badge";
import { Button, IconButton } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Tabla } from "@/components/ui/DataTable";
import { Casilla, FiltroSelect, Input, Select } from "@/components/ui/Field";
import { BarraFiltros } from "@/components/ui/FiltrosBarra";
import { Modal } from "@/components/ui/Modal";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { Paginacion } from "@/components/ui/Pagination";
import { CampoPassword } from "@/components/ui/PasswordField";
import { Busqueda } from "@/components/ui/SearchInput";
import { useRoles, useSedes } from "@/hooks/useCatalogos";
import { aBooleano, useFiltros } from "@/hooks/useFiltros";
import { useMutacion } from "@/hooks/useMutacion";
import { mensajeDeError } from "@/lib/errors";
import { fechaHora, hace } from "@/lib/format";
import { aplicarErroresServidor, generarPassword, v } from "@/lib/formularios";
import type { Usuario } from "@/types/api";

const INVALIDAR = [["usuarios"], ["roles"], ["catalogo", "roles"], ["sedes"]];

const esquema = z.object({
  nombre: v.texto("El nombre", 2, 150),
  email: v.correo,
  rol_id: z.string().min(1, "Seleccione un rol"),
  sede_id: z.string(),
  password: z.string(),
  forzar: z.boolean(),
});
type Datos = z.infer<typeof esquema>;

function FormularioUsuario({ usuario, onCerrar }: { usuario: Usuario | null; onCerrar: () => void }) {
  const roles = useRoles();
  const sedes = useSedes();
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    setValue,
    watch,
    formState: { errors },
  } = useForm<Datos>({
    resolver: zodResolver(esquema),
    defaultValues: {
      nombre: usuario?.nombre ?? "",
      email: usuario?.email ?? "",
      rol_id: usuario ? String(usuario.rol.id) : "",
      sede_id: usuario?.sede ? String(usuario.sede.id) : "",
      password: "",
      forzar: true,
    },
  });

  const rolesActivos = (roles.data ?? []).filter((r) => r.activo || r.id === usuario?.rol.id);
  const rolElegido = (roles.data ?? []).find((r) => String(r.id) === watch("rol_id"));
  const requiereSede = rolElegido?.alcance === "sede";
  const opcionesSede: { id: number; nombre: string }[] = (sedes.data ?? []).map((s) => ({ id: s.id, nombre: s.nombre }));
  if (usuario?.sede && !opcionesSede.some((s) => s.id === usuario.sede?.id)) opcionesSede.push({ id: usuario.sede.id, nombre: usuario.sede.nombre });

  const guardar = useMutacion(
    (d: Datos) => {
      const rol_id = Number(d.rol_id);
      const sede = requiereSede && d.sede_id ? Number(d.sede_id) : null;
      if (!usuario) {
        return apiUsuarios.crear({ nombre: d.nombre.trim(), email: d.email.trim().toLowerCase(), password: d.password, rol_id, sede_id: sede, forzar_cambio_password: d.forzar });
      }
      return apiUsuarios.actualizar(usuario.id, {
        nombre: d.nombre.trim(),
        email: d.email.trim().toLowerCase(),
        rol_id,
        sede_id: sede,
        quitar_sede: sede === null,
      });
    },
    { exito: usuario ? "Usuario actualizado." : "Usuario creado.", invalidar: INVALIDAR, avisarError: false, onExito: onCerrar },
  );

  return (
    <Modal
      abierto
      onCerrar={onCerrar}
      bloqueado={guardar.isPending}
      titulo={usuario ? "Editar usuario" : "Nuevo usuario"}
      descripcion={usuario ? undefined : "La persona podrá ingresar con su correo y la contraseña que defina aquí."}
      pie={
        <>
          <Button variante="ghost" onClick={onCerrar} disabled={guardar.isPending}>Cancelar</Button>
          <Button type="submit" form="form-usuario" cargando={guardar.isPending}>{usuario ? "Guardar cambios" : "Crear usuario"}</Button>
        </>
      }
    >
      <form
        id="form-usuario"
        noValidate
        className="flex flex-col gap-4"
        onSubmit={handleSubmit(async (d) => {
          setErrorGeneral(null);
          if (requiereSede && !d.sede_id) {
            setError("sede_id", { message: "Este rol opera dentro de una sede: seleccione cuál" });
            return;
          }
          if (!usuario) {
            const r = v.password.safeParse(d.password);
            if (!r.success) {
              setError("password", { message: r.error.issues[0]?.message ?? "Contraseña no válida" });
              return;
            }
          }
          try {
            await guardar.mutateAsync(d);
          } catch (e) {
            setErrorGeneral(aplicarErroresServidor(e, setError, ["nombre", "email", "rol_id", "sede_id", "password"]));
          }
        })}
      >
        {errorGeneral && <Aviso tipo="error">{errorGeneral}</Aviso>}
        <Input etiqueta="Nombre completo" required autoComplete="off" error={errors.nombre?.message} {...register("nombre")} />
        <Input etiqueta="Correo electrónico" type="email" required autoComplete="off" placeholder="nombre@empresa.com" error={errors.email?.message} {...register("email")} />
        <Select etiqueta="Rol" required error={errors.rol_id?.message} disabled={roles.isLoading} {...register("rol_id")}>
          <option value="">{roles.isLoading ? "Cargando roles…" : "Seleccione un rol"}</option>
          {rolesActivos.map((r) => (
            <option key={r.id} value={r.id}>{r.nombre}</option>
          ))}
        </Select>
        {rolElegido && (
          <p className="-mt-2 text-xs text-ink-faint">
            {rolElegido.descripcion ? `${rolElegido.descripcion} ` : ""}
            {requiereSede ? "Este rol trabaja únicamente dentro de su sede." : "Este rol ve la información de todas las sedes."}
          </p>
        )}
        {requiereSede && (
          <Select etiqueta="Sede" required error={errors.sede_id?.message} disabled={sedes.isLoading} {...register("sede_id")}>
            <option value="">{sedes.isLoading ? "Cargando sedes…" : "Seleccione una sede"}</option>
            {opcionesSede.map((s) => (
              <option key={s.id} value={s.id}>{s.nombre}</option>
            ))}
          </Select>
        )}
        {!usuario && (
          <>
            <div className="flex flex-col gap-2">
              <CampoPassword
                etiqueta="Contraseña inicial"
                required
                autoComplete="new-password"
                mostrarRequisitos
                valorActual={watch("password")}
                error={errors.password?.message}
                {...register("password")}
              />
              <Button variante="secondary" tamano="sm" className="self-start" icono={<Wand2 className="size-3.5" aria-hidden />} onClick={() => setValue("password", generarPassword(), { shouldValidate: true })}>
                Generar contraseña segura
              </Button>
            </div>
            <Casilla etiqueta="Pedir que la cambie al ingresar por primera vez" descripcion="Recomendado: así solo la persona conoce su contraseña final." {...register("forzar")} />
          </>
        )}
      </form>
    </Modal>
  );
}

function DialogoRestablecer({ usuario, onCerrar }: { usuario: Usuario; onCerrar: () => void }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const restablecer = useMutacion((clave: string) => apiUsuarios.restablecerPassword(usuario.id, clave), {
    exito: "Contraseña restablecida. La persona deberá cambiarla al ingresar.",
    invalidar: [["usuarios"]],
    avisarError: false,
    onExito: onCerrar,
  });
  return (
    <Modal
      abierto
      onCerrar={onCerrar}
      bloqueado={restablecer.isPending}
      titulo="Restablecer contraseña"
      descripcion={`Defina una contraseña temporal para ${usuario.nombre}. Se le pedirá cambiarla en su próximo ingreso y se cerrarán sus sesiones abiertas.`}
      pie={
        <>
          <Button variante="ghost" onClick={onCerrar} disabled={restablecer.isPending}>Cancelar</Button>
          <Button type="submit" form="form-restablecer" cargando={restablecer.isPending}>Restablecer</Button>
        </>
      }
    >
      <form
        id="form-restablecer"
        noValidate
        className="flex flex-col gap-3"
        onSubmit={async (e) => {
          e.preventDefault();
          setError(null);
          const r = v.password.safeParse(password);
          if (!r.success) {
            setError(r.error.issues[0]?.message ?? "Contraseña no válida");
            return;
          }
          try {
            await restablecer.mutateAsync(password);
          } catch (err) {
            setError(mensajeDeError(err));
          }
        }}
      >
        <CampoPassword etiqueta="Contraseña temporal" required autoComplete="new-password" mostrarRequisitos valorActual={password} value={password} onChange={(e) => setPassword(e.target.value)} error={error ?? undefined} />
        <Button variante="secondary" tamano="sm" className="self-start" icono={<Wand2 className="size-3.5" aria-hidden />} onClick={() => { setPassword(generarPassword()); setError(null); }}>
          Generar contraseña segura
        </Button>
        <p className="text-xs text-ink-faint">Entréguela por un canal seguro. Por seguridad no se vuelve a mostrar.</p>
      </form>
    </Modal>
  );
}

function EstadoUsuario({ u }: { u: Usuario }) {
  if (!u.activo) return <Badge>Inhabilitado</Badge>;
  return (
    <div className="flex flex-wrap gap-1.5">
      {u.bloqueado ? <Badge tono="danger">Bloqueado</Badge> : <Badge tono="success">Activo</Badge>}
      {u.debe_cambiar_password && <Badge tono="warning">Contraseña temporal</Badge>}
    </div>
  );
}

export default function UsuariosPage() {
  const { tiene, sesion } = useAuth();
  const roles = useRoles();
  const sedes = useSedes(false);
  const { filtros, pagina, tamano, cambiar, irAPagina, limpiar, hayFiltros } = useFiltros({ q: "", rol_id: "", sede_id: "", activo: "" }, 20);
  const [edicion, setEdicion] = useState<Usuario | "nuevo" | null>(null);
  const [restablecer, setRestablecer] = useState<Usuario | null>(null);
  const [aCambiar, setACambiar] = useState<Usuario | null>(null);
  const [errorEstado, setErrorEstado] = useState<string | null>(null);

  const lista = useQuery({
    queryKey: ["usuarios", filtros, pagina],
    queryFn: () =>
      apiUsuarios.listar({
        q: filtros.q,
        rol_id: filtros.rol_id ? Number(filtros.rol_id) : "",
        sede_id: filtros.sede_id ? Number(filtros.sede_id) : "",
        activo: aBooleano(filtros.activo),
        pagina,
        tamano,
      }),
    placeholderData: keepPreviousData,
  });
  const estado = useMutacion((u: Usuario) => apiUsuarios.estado(u.id, !u.activo), {
    exito: (u) => (u.activo ? "Usuario activado." : "Usuario inhabilitado."),
    invalidar: INVALIDAR,
    avisarError: false,
    onExito: () => setACambiar(null),
  });
  const desbloquear = useMutacion((u: Usuario) => apiUsuarios.desbloquear(u.id), { exito: "Usuario desbloqueado.", invalidar: [["usuarios"]] });

  return (
    <>
      <EncabezadoPagina
        titulo="Usuarios"
        descripcion="Personas con acceso al sistema. El rol define qué pueden hacer y la sede, dónde."
        acciones={tiene("usuarios.crear") && <Button icono={<Plus className="size-4" aria-hidden />} onClick={() => setEdicion("nuevo")}>Nuevo usuario</Button>}
      />
      <Card>
        <BarraFiltros hayFiltros={hayFiltros} onLimpiar={limpiar}>
          <Busqueda valor={filtros.q} onCambiar={(q) => cambiar({ q })} placeholder="Buscar por nombre o correo…" className="sm:max-w-sm" />
          <FiltroSelect etiqueta="Rol" value={filtros.rol_id} onChange={(e) => cambiar({ rol_id: e.target.value })}>
            <option value="">Todos los roles</option>
            {(roles.data ?? []).map((r) => (
              <option key={r.id} value={r.id}>{r.nombre}</option>
            ))}
          </FiltroSelect>
          <FiltroSelect etiqueta="Sede" value={filtros.sede_id} onChange={(e) => cambiar({ sede_id: e.target.value })}>
            <option value="">Todas las sedes</option>
            {(sedes.data ?? []).map((s) => (
              <option key={s.id} value={s.id}>{s.nombre}</option>
            ))}
          </FiltroSelect>
          <FiltroSelect etiqueta="Estado" value={filtros.activo} onChange={(e) => cambiar({ activo: e.target.value })}>
            <option value="">Todos los estados</option>
            <option value="true">Activos</option>
            <option value="false">Inhabilitados</option>
          </FiltroSelect>
        </BarraFiltros>
        <Tabla
          descripcion="Listado de usuarios"
          idDe={(u) => u.id}
          filas={lista.data?.items}
          cargando={lista.isFetching}
          error={lista.error}
          onReintentar={() => lista.refetch()}
          vacio={{
            titulo: hayFiltros ? "Sin resultados" : "Aún no hay usuarios",
            descripcion: hayFiltros ? "Pruebe con otros filtros." : "Cree usuarios para que su equipo pueda ingresar.",
          }}
          columnas={[
            {
              clave: "nombre",
              encabezado: "Usuario",
              celda: (u) => (
                <div className="min-w-0">
                  <div className="font-medium">
                    {u.nombre}
                    {u.id === sesion?.id && <span className="ml-2 text-xs font-normal text-ink-faint">(usted)</span>}
                  </div>
                  <div className="truncate text-xs text-ink-faint">{u.email}</div>
                </div>
              ),
            },
            { clave: "rol", encabezado: "Rol", celda: (u) => <Badge tono="accent">{u.rol.nombre}</Badge> },
            { clave: "sede", encabezado: "Sede", desde: "md", celda: (u) => (u.sede ? u.sede.nombre : <span className="text-ink-faint">Todas</span>) },
            { clave: "estado", encabezado: "Estado", celda: (u) => <EstadoUsuario u={u} /> },
            {
              clave: "acceso",
              encabezado: "Último acceso",
              desde: "lg",
              celda: (u) => <span className="text-ink-dim" title={u.ultimo_acceso ? fechaHora(u.ultimo_acceso) : undefined}>{u.ultimo_acceso ? hace(u.ultimo_acceso) : "Nunca"}</span>,
            },
            {
              clave: "acciones",
              encabezado: "Acciones",
              alinear: "derecha",
              celda: (u) => (
                <div className="flex justify-end gap-1">
                  {tiene("usuarios.editar") && u.bloqueado && (
                    <IconButton etiqueta={`Desbloquear a ${u.nombre}`} disabled={desbloquear.isPending} onClick={() => desbloquear.mutate(u)}>
                      <LockOpen className="size-4" aria-hidden />
                    </IconButton>
                  )}
                  {tiene("usuarios.editar") && (
                    <IconButton etiqueta={`Editar a ${u.nombre}`} onClick={() => setEdicion(u)}>
                      <Pencil className="size-4" aria-hidden />
                    </IconButton>
                  )}
                  {tiene("usuarios.editar") && u.id !== sesion?.id && (
                    <IconButton etiqueta={`Restablecer contraseña de ${u.nombre}`} onClick={() => setRestablecer(u)}>
                      <KeyRound className="size-4" aria-hidden />
                    </IconButton>
                  )}
                  {tiene("usuarios.inhabilitar") && u.id !== sesion?.id && (
                    <IconButton etiqueta={u.activo ? `Inhabilitar a ${u.nombre}` : `Activar a ${u.nombre}`} onClick={() => { setErrorEstado(null); setACambiar(u); }}>
                      <Power className="size-4" aria-hidden />
                    </IconButton>
                  )}
                </div>
              ),
            },
          ]}
        />
        {lista.data && <Paginacion pagina={lista.data.pagina} paginas={lista.data.paginas} total={lista.data.total} tamano={lista.data.tamano} onCambiar={irAPagina} />}
      </Card>
      {edicion && <FormularioUsuario usuario={edicion === "nuevo" ? null : edicion} onCerrar={() => setEdicion(null)} />}
      {restablecer && <DialogoRestablecer usuario={restablecer} onCerrar={() => setRestablecer(null)} />}
      <ConfirmDialog
        abierto={aCambiar !== null}
        titulo={aCambiar?.activo ? "Inhabilitar usuario" : "Activar usuario"}
        mensaje={
          aCambiar?.activo
            ? `${aCambiar.nombre} no podrá ingresar y se cerrarán sus sesiones abiertas. Su historial de operaciones se conserva.`
            : `${aCambiar?.nombre} podrá volver a ingresar con su contraseña actual.`
        }
        confirmarTexto={aCambiar?.activo ? "Inhabilitar" : "Activar"}
        peligroso={aCambiar?.activo}
        cargando={estado.isPending}
        error={errorEstado}
        onConfirmar={async () => {
          if (!aCambiar) return;
          setErrorEstado(null);
          try {
            await estado.mutateAsync(aCambiar);
          } catch (e) {
            setErrorEstado(mensajeDeError(e));
          }
        }}
        onCancelar={() => setACambiar(null)}
      />
    </>
  );
}
