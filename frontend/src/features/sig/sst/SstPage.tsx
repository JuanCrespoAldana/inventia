import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Eye, Pencil, Plus, Timer, Trash2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { apiSst } from "@/api/sig";
import { useAuth } from "@/auth/AuthContext";
import { Aviso } from "@/components/ui/Aviso";
import { Badge } from "@/components/ui/Badge";
import { Button, IconButton } from "@/components/ui/Button";
import { Card, CardHeader, Stat } from "@/components/ui/Card";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Tabla } from "@/components/ui/DataTable";
import { EstadoError } from "@/components/ui/EstadoVacio";
import { Casilla, FiltroFecha, FiltroSelect, Input, Interruptor, Select, Textarea } from "@/components/ui/Field";
import { BarraFiltros } from "@/components/ui/FiltrosBarra";
import { Modal } from "@/components/ui/Modal";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { Paginacion } from "@/components/ui/Pagination";
import { PanelCargando } from "@/components/ui/Skeleton";
import { Pestanas } from "@/components/ui/Tabs";
import { useFiltros } from "@/hooks/useFiltros";
import { usePaginacionLocal } from "@/hooks/usePaginacionLocal";
import { useMutacion } from "@/hooks/useMutacion";
import { mensajeDeError } from "@/lib/errors";
import { AREA_PAUSA, ESTADO_PAUSA, estado, etiqueta } from "@/lib/etiquetas";
import { entero, fechaHora, porcentaje } from "@/lib/format";
import { aplicarErroresServidor, v } from "@/lib/formularios";
import type { ActividadSst, ActividadSstCrear, PausaRegistro } from "@/types/api";
import { ModalPausa } from "./ModalPausa";
import { formatoTemporizador } from "./programacion";

const INVALIDAR = [["sst"]];
const INTERVALOS_SUGERIDOS = [30, 45, 60, 90, 120];

function duracionTexto(s: number | null | undefined) {
  return s === null || s === undefined ? "—" : formatoTemporizador(s);
}

/* ------------------------------------------------------------------------------ ejercicios */

/** Seis tarjetas por página: llenan filas completas de 2 y de 3 columnas. */
const EJERCICIOS_POR_PAGINA = 6;

function Ejercicios({ gestor }: { gestor: boolean }) {
  const actividades = useQuery({ queryKey: ["sst", "actividades", false], queryFn: () => apiSst.actividades(false) });
  const configuracion = useQuery({ queryKey: ["sst", "configuracion"], queryFn: apiSst.configuracion });
  const [vista, setVista] = useState<ActividadSst | null>(null);
  const pagina = usePaginacionLocal(actividades.data, EJERCICIOS_POR_PAGINA);

  return (
    <div className="flex flex-col gap-6">
      {configuracion.data && (
        <Aviso tipo={configuracion.data.pausas_activas ? "info" : "aviso"} titulo={configuracion.data.pausas_activas ? "Pausas activas automáticas" : "Las pausas automáticas están desactivadas"}>
          {configuracion.data.pausas_activas
            ? gestor
              ? `Cada ${configuracion.data.intervalo_minutos} minutos de uso se muestra una pausa a las personas que usan el sistema. Las personas administradoras no reciben pausas automáticas, pero pueden ver todo el contenido aquí.`
              : `Cada ${configuracion.data.intervalo_minutos} minutos de uso verás una pausa activa. Se pospone si estás en medio de un formulario o guardando algo, y puedes omitirla si no es buen momento.`
            : "Mientras estén desactivadas no se mostrarán pausas. El contenido sigue disponible para consulta."}
        </Aviso>
      )}
      {actividades.isPending ? (
        <PanelCargando etiqueta="Cargando los ejercicios…" />
      ) : actividades.isError ? (
        <Card>
          <EstadoError error={actividades.error} onReintentar={() => actividades.refetch()} />
        </Card>
      ) : (
        <>
          <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" aria-label="Ejercicios de pausas activas">
            {pagina.visibles.map((a) => (
              <li key={a.id}>
                <Card className="flex h-full flex-col gap-3 p-5">
                  <div className="flex items-start justify-between gap-2">
                    <Badge tono="accent">{etiqueta(AREA_PAUSA, a.area)}</Badge>
                    <span className="tabular inline-flex items-center gap-1 text-xs text-ink-faint">
                      <Timer className="size-3.5" aria-hidden />
                      {duracionTexto(a.duracion_segundos)}
                    </span>
                  </div>
                  <div className="flex-1">
                    <h3 className="font-display text-base font-semibold text-ink">{a.titulo}</h3>
                    <p className="mt-1 text-sm text-ink-dim">{a.mensaje}</p>
                  </div>
                  <Button variante="secondary" tamano="sm" icono={<Eye className="size-4" aria-hidden />} onClick={() => setVista(a)}>
                    Ver ejercicio
                  </Button>
                </Card>
              </li>
            ))}
          </ul>
          {pagina.total > 0 && (
            <Card>
              <Paginacion {...pagina.paginacion} unidad="ejercicios" etiqueta="Paginación de ejercicios" />
            </Card>
          )}
        </>
      )}
      {vista && <ModalPausa key={vista.id} actividad={vista} vistaPrevia onCerrarVistaPrevia={() => setVista(null)} />}
    </div>
  );
}

/* ------------------------------------------------------------------------------ registro de pausas */

function Registro({ ambito }: { ambito: "mias" | "todas" }) {
  const { filtros, pagina, tamano, cambiar, irAPagina, limpiar, hayFiltros } = useFiltros({ estado: "", desde: "", hasta: "" }, 15);
  const lista = useQuery({
    queryKey: ["sst", "pausas", ambito, filtros, pagina],
    queryFn: () => apiSst.pausas({ ambito, estado: filtros.estado, desde: filtros.desde, hasta: filtros.hasta, pagina, tamano }),
    placeholderData: keepPreviousData,
  });
  return (
    <Card>
      <CardHeader titulo={ambito === "mias" ? "Mi historial de pausas" : "Registro de pausas"} descripcion={ambito === "mias" ? "Las pausas que se te han mostrado y cómo las cerraste." : "Cada pausa mostrada, con la persona, la fecha y el resultado."} />
      <BarraFiltros hayFiltros={hayFiltros} onLimpiar={limpiar}>
        <FiltroSelect etiqueta="Resultado" value={filtros.estado} onChange={(e) => cambiar({ estado: e.target.value })}>
          <option value="">Todos los resultados</option>
          {Object.entries(ESTADO_PAUSA).map(([k, t]) => (
            <option key={k} value={k}>
              {t.etiqueta}
            </option>
          ))}
        </FiltroSelect>
        <FiltroFecha etiqueta="Desde" value={filtros.desde} max={filtros.hasta || undefined} onChange={(e) => cambiar({ desde: e.target.value })} />
        <FiltroFecha etiqueta="Hasta" value={filtros.hasta} min={filtros.desde || undefined} onChange={(e) => cambiar({ hasta: e.target.value })} />
      </BarraFiltros>
      <Tabla<PausaRegistro>
        descripcion="Registro de pausas activas"
        idDe={(p) => p.id}
        filas={lista.data?.items}
        cargando={lista.isFetching}
        error={lista.error}
        onReintentar={() => lista.refetch()}
        vacio={{ titulo: hayFiltros ? "Sin resultados" : "Aún no hay pausas registradas", descripcion: hayFiltros ? "Prueba con otros filtros." : "Cuando se muestre la primera pausa quedará registrada aquí." }}
        columnas={[
          { clave: "fecha", encabezado: "Fecha", celda: (p) => <span className="whitespace-nowrap text-ink-dim">{fechaHora(p.mostrada_en)}</span> },
          ...(ambito === "todas" ? [{ clave: "usuario", encabezado: "Persona", celda: (p: PausaRegistro) => p.usuario_nombre ?? "—" }] : []),
          { clave: "actividad", encabezado: "Actividad", celda: (p) => <span className="font-medium">{p.actividad_titulo}</span> },
          { clave: "estado", encabezado: "Resultado", celda: (p) => <Badge tono={estado(ESTADO_PAUSA, p.estado).tono}>{estado(ESTADO_PAUSA, p.estado).etiqueta}</Badge> },
          { clave: "duracion", encabezado: "Duración", alinear: "derecha", desde: "sm", celda: (p) => <span className="tabular text-ink-dim">{duracionTexto(p.duracion_segundos)}</span> },
        ]}
      />
      {lista.data && <Paginacion pagina={lista.data.pagina} paginas={lista.data.paginas} total={lista.data.total} tamano={lista.data.tamano} onCambiar={irAPagina} />}
    </Card>
  );
}

/* ------------------------------------------------------------------------------ cumplimiento (administración) */

function Cumplimiento() {
  const [dias, setDias] = useState("30");
  const resumen = useQuery({ queryKey: ["sst", "resumen", dias], queryFn: () => apiSst.resumen(Number(dias)), placeholderData: keepPreviousData });
  const r = resumen.data;
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-3">
        <FiltroSelect etiqueta="Periodo" value={dias} onChange={(e) => setDias(e.target.value)} className="w-52">
          <option value="7">Últimos 7 días</option>
          <option value="30">Últimos 30 días</option>
          <option value="90">Últimos 90 días</option>
          <option value="365">Último año</option>
        </FiltroSelect>
      </div>
      {resumen.isError && (
        <Card>
          <EstadoError error={resumen.error} onReintentar={() => resumen.refetch()} />
        </Card>
      )}
      {r && (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
            <Stat etiqueta="Pausas mostradas" valor={entero(r.mostradas)} />
            <Stat etiqueta="Realizadas" valor={entero(r.realizadas)} tono="success" />
            <Stat etiqueta="Omitidas" valor={entero(r.omitidas)} tono={r.omitidas > 0 ? "warning" : "neutral"} />
            <Stat etiqueta="Sin responder" valor={entero(r.sin_responder)} />
            <Stat etiqueta="Cumplimiento" valor={r.cumplimiento === null ? "—" : porcentaje(r.cumplimiento, 0)} tono="accent" detalle="Realizadas sobre las pausas mostradas" />
          </div>
          <Card>
            <CardHeader titulo="Cumplimiento por persona" descripcion="Pausas del periodo seleccionado." />
            <Tabla
              descripcion="Cumplimiento de pausas por persona"
              idDe={(u) => u.usuario_id}
              filas={r.por_usuario}
              paginar={10}
              reiniciarCon={dias}
              vacio={{ titulo: "Sin pausas en el periodo", descripcion: "Todavía no se ha mostrado ninguna pausa en estas fechas." }}
              columnas={[
                { clave: "u", encabezado: "Persona", celda: (u) => <span className="font-medium">{u.usuario_nombre ?? "—"}</span> },
                { clave: "m", encabezado: "Mostradas", alinear: "derecha", celda: (u) => <span className="tabular">{entero(u.mostradas)}</span> },
                { clave: "r", encabezado: "Realizadas", alinear: "derecha", celda: (u) => <span className="tabular text-success">{entero(u.realizadas)}</span> },
                { clave: "o", encabezado: "Omitidas", alinear: "derecha", desde: "sm", celda: (u) => <span className="tabular text-ink-dim">{entero(u.omitidas)}</span> },
              ]}
            />
          </Card>
        </>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------------------ frecuencia (administración) */

function Frecuencia() {
  const configuracion = useQuery({ queryKey: ["sst", "configuracion"], queryFn: apiSst.configuracion });
  const [activas, setActivas] = useState<boolean | null>(null);
  const [intervalo, setIntervalo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const guardar = useMutacion((d: { pausas_activas?: boolean; intervalo_minutos?: number }) => apiSst.guardarConfiguracion(d), {
    exito: "Configuración de pausas guardada.",
    invalidar: INVALIDAR,
    avisarError: false,
    onExito: () => {
      setActivas(null);
      setIntervalo(null);
    },
  });

  if (configuracion.isPending) return <PanelCargando etiqueta="Cargando la configuración…" />;
  if (configuracion.isError)
    return (
      <Card>
        <EstadoError error={configuracion.error} onReintentar={() => configuracion.refetch()} />
      </Card>
    );
  const cfg = configuracion.data;
  const valorActivas = activas ?? cfg.pausas_activas;
  const valorIntervalo = intervalo ?? String(cfg.intervalo_minutos);
  const minutos = Number(valorIntervalo);
  const intervaloValido = /^\d+$/.test(valorIntervalo) && minutos >= 1 && minutos <= 480;
  const hayCambios = valorActivas !== cfg.pausas_activas || (intervaloValido && minutos !== cfg.intervalo_minutos);

  return (
    <Card>
      <CardHeader titulo="Frecuencia de las pausas" descripcion="Se aplica a todas las personas de la empresa, excepto a quienes administran este módulo." />
      <div className="flex flex-col gap-6 p-5">
        {error && <Aviso tipo="error">{error}</Aviso>}
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-ink">Pausas activas automáticas</p>
            <p className="text-[13px] text-ink-faint">Si las desactivas, no se muestra ninguna pausa; el contenido sigue disponible para consulta.</p>
          </div>
          <Interruptor activo={valorActivas} onChange={setActivas} etiqueta="Pausas activas automáticas" />
        </div>
        <div className="grid gap-3 sm:max-w-md">
          <Input
            etiqueta="Cada cuántos minutos"
            inputMode="numeric"
            value={valorIntervalo}
            onChange={(e) => setIntervalo(e.target.value)}
            error={!intervaloValido ? "Escribe un número entero entre 1 y 480" : undefined}
            ayuda="Tiempo de uso entre una pausa y la siguiente. Por defecto, 60 minutos."
          />
          <div className="flex flex-wrap gap-2" role="group" aria-label="Frecuencias sugeridas">
            {INTERVALOS_SUGERIDOS.map((m) => (
              <Button key={m} variante={minutos === m ? "primary" : "secondary"} tamano="sm" onClick={() => setIntervalo(String(m))}>
                {m} min
              </Button>
            ))}
          </div>
        </div>
        <Aviso tipo="info">Las sesiones que ya están abiertas recogen el cambio en pocos minutos. La pausa nunca interrumpe un formulario abierto ni un guardado en curso.</Aviso>
        <div className="flex justify-end">
          <Button
            cargando={guardar.isPending}
            disabled={!hayCambios || !intervaloValido}
            onClick={async () => {
              setError(null);
              try {
                await guardar.mutateAsync({ pausas_activas: valorActivas, intervalo_minutos: minutos });
              } catch (e) {
                setError(mensajeDeError(e));
              }
            }}
          >
            Guardar
          </Button>
        </div>
      </div>
    </Card>
  );
}

/* ------------------------------------------------------------------------------ contenido (administración) */

const esquemaActividad = z.object({
  titulo: v.texto("El título", 3, 120),
  area: z.enum(["cuello", "hombros", "espalda", "manos_munecas", "ojos", "piernas", "respiracion"]),
  mensaje: v.texto("El mensaje", 5, 300),
  instrucciones: v.texto("Las instrucciones", 10, 2000),
  duracion_segundos: v.entero("La duración", 10, 900),
  recomendaciones: v.textoOpcional(1500),
  orden: v.entero("El orden", 0, 999),
  activa: z.boolean(),
});
type DatosActividad = z.infer<typeof esquemaActividad>;

function FormularioActividad({ actividad, onCerrar }: { actividad: ActividadSst | null; onCerrar: () => void }) {
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<DatosActividad>({
    resolver: zodResolver(esquemaActividad),
    defaultValues: {
      titulo: actividad?.titulo ?? "",
      area: (actividad?.area as DatosActividad["area"]) ?? "cuello",
      mensaje: actividad?.mensaje ?? "",
      instrucciones: actividad?.instrucciones ?? "",
      duracion_segundos: String(actividad?.duracion_segundos ?? 60),
      recomendaciones: actividad?.recomendaciones ?? "",
      orden: String(actividad?.orden ?? 0),
      activa: actividad?.activa ?? true,
    },
  });
  const guardar = useMutacion(
    (d: DatosActividad) => {
      const cuerpo: ActividadSstCrear = { ...d, duracion_segundos: Number(d.duracion_segundos), orden: Number(d.orden), recomendaciones: d.recomendaciones.trim() || null };
      return actividad ? apiSst.actualizarActividad(actividad.id, cuerpo) : apiSst.crearActividad(cuerpo);
    },
    { exito: actividad ? "Actividad actualizada." : "Actividad creada.", invalidar: INVALIDAR, avisarError: false, onExito: onCerrar },
  );

  return (
    <Modal
      abierto
      onCerrar={onCerrar}
      bloqueado={guardar.isPending}
      ancho="lg"
      titulo={actividad ? "Editar actividad" : "Nueva actividad"}
      descripcion="Escribe un paso por línea en las instrucciones y un consejo por línea en las recomendaciones."
      pie={
        <>
          <Button variante="ghost" onClick={onCerrar} disabled={guardar.isPending}>
            Cancelar
          </Button>
          <Button type="submit" form="form-actividad" cargando={guardar.isPending}>
            Guardar
          </Button>
        </>
      }
    >
      <form
        id="form-actividad"
        noValidate
        className="flex flex-col gap-4"
        onSubmit={handleSubmit(async (d) => {
          setErrorGeneral(null);
          try {
            await guardar.mutateAsync(d);
          } catch (e) {
            setErrorGeneral(aplicarErroresServidor(e, setError, ["titulo", "area", "mensaje", "instrucciones", "duracion_segundos", "recomendaciones", "orden"]));
          }
        })}
      >
        {errorGeneral && <Aviso tipo="error">{errorGeneral}</Aviso>}
        <div className="grid gap-4 sm:grid-cols-[1fr_200px]">
          <Input etiqueta="Título" required maxLength={120} error={errors.titulo?.message} {...register("titulo")} />
          <Select etiqueta="Zona del cuerpo" required error={errors.area?.message} {...register("area")}>
            {Object.entries(AREA_PAUSA).map(([k, n]) => (
              <option key={k} value={k}>
                {n}
              </option>
            ))}
          </Select>
        </div>
        <Input etiqueta="Mensaje que se muestra" required maxLength={300} error={errors.mensaje?.message} {...register("mensaje")} />
        <Textarea etiqueta="Instrucciones (un paso por línea)" required rows={5} maxLength={2000} error={errors.instrucciones?.message} {...register("instrucciones")} />
        <Textarea etiqueta="Recomendaciones de postura, ojos, manos y forma de sentarse (una por línea)" rows={3} maxLength={1500} error={errors.recomendaciones?.message} {...register("recomendaciones")} />
        <div className="grid gap-4 sm:grid-cols-2">
          <Input etiqueta="Duración (segundos)" required inputMode="numeric" error={errors.duracion_segundos?.message} ayuda="Entre 10 y 900 segundos." {...register("duracion_segundos")} />
          <Input etiqueta="Orden" required inputMode="numeric" error={errors.orden?.message} ayuda="Las pausas rotan entre las actividades activas." {...register("orden")} />
        </div>
        <Casilla etiqueta="Actividad activa" descripcion="Solo las activas se muestran en las pausas." {...register("activa")} />
      </form>
    </Modal>
  );
}

function Contenido() {
  const actividades = useQuery({ queryKey: ["sst", "actividades", true], queryFn: () => apiSst.actividades(true) });
  const [editando, setEditando] = useState<ActividadSst | "nueva" | null>(null);
  const [eliminando, setEliminando] = useState<ActividadSst | null>(null);
  const [errorEliminar, setErrorEliminar] = useState<string | null>(null);
  const eliminar = useMutacion((id: number) => apiSst.eliminarActividad(id), { exito: "Actividad eliminada.", invalidar: INVALIDAR, avisarError: false, onExito: () => setEliminando(null) });

  return (
    <Card>
      <CardHeader
        titulo="Ejercicios y recomendaciones"
        descripcion="El contenido que ven las personas en las pausas. Las pausas rotan entre las actividades activas."
        accion={
          <Button tamano="sm" icono={<Plus className="size-4" aria-hidden />} onClick={() => setEditando("nueva")}>
            Nueva actividad
          </Button>
        }
      />
      <Tabla<ActividadSst>
        descripcion="Actividades de pausas activas"
        idDe={(a) => a.id}
        filas={actividades.data}
        paginar={10}
        cargando={actividades.isPending}
        error={actividades.error}
        onReintentar={() => actividades.refetch()}
        vacio={{ titulo: "No hay actividades", descripcion: "Crea al menos una actividad para que las pausas puedan mostrarse." }}
        columnas={[
          { clave: "orden", encabezado: "Orden", celda: (a) => <span className="tabular text-ink-dim">{a.orden}</span> },
          { clave: "titulo", encabezado: "Actividad", celda: (a) => <span className="font-medium">{a.titulo}</span> },
          { clave: "area", encabezado: "Zona", desde: "sm", celda: (a) => etiqueta(AREA_PAUSA, a.area) },
          { clave: "dur", encabezado: "Duración", alinear: "derecha", desde: "md", celda: (a) => <span className="tabular text-ink-dim">{duracionTexto(a.duracion_segundos)}</span> },
          { clave: "estado", encabezado: "Estado", celda: (a) => <Badge tono={a.activa ? "success" : "neutral"}>{a.activa ? "Activa" : "Inactiva"}</Badge> },
          {
            clave: "acc",
            encabezado: "",
            alinear: "derecha",
            celda: (a) => (
              <div className="flex justify-end gap-1">
                <IconButton etiqueta={`Editar ${a.titulo}`} onClick={() => setEditando(a)}>
                  <Pencil className="size-4" aria-hidden />
                </IconButton>
                <IconButton etiqueta={`Eliminar ${a.titulo}`} className="hover:text-danger" onClick={() => { setErrorEliminar(null); setEliminando(a); }}>
                  <Trash2 className="size-4" aria-hidden />
                </IconButton>
              </div>
            ),
          },
        ]}
      />
      {editando && <FormularioActividad actividad={editando === "nueva" ? null : editando} onCerrar={() => setEditando(null)} />}
      <ConfirmDialog
        abierto={eliminando !== null}
        peligroso
        titulo="Eliminar actividad"
        mensaje={`Se eliminará «${eliminando?.titulo ?? ""}». Las pausas ya registradas conservan su nombre en el historial. Si solo quieres dejar de usarla, desactívala.`}
        confirmarTexto="Eliminar"
        cargando={eliminar.isPending}
        error={errorEliminar}
        onCancelar={() => setEliminando(null)}
        onConfirmar={async () => {
          if (!eliminando) return;
          try {
            await eliminar.mutateAsync(eliminando.id);
          } catch (e) {
            setErrorEliminar(mensajeDeError(e));
          }
        }}
      />
    </Card>
  );
}

/* ------------------------------------------------------------------------------ página */

type Pestana = "ejercicios" | "historial" | "cumplimiento" | "frecuencia" | "contenido";

export default function SstPage() {
  const { tiene } = useAuth();
  const gestor = tiene("sst.gestionar");
  const [pestana, setPestana] = useState<Pestana>("ejercicios");

  return (
    <>
      <EncabezadoPagina
        titulo="Seguridad y Salud en el Trabajo"
        descripcion="Pausas activas para cuidar tu cuerpo durante la jornada: ejercicios guiados, recomendaciones de postura y descanso visual."
      />
      <div className="mb-5">
        <Pestanas
          etiqueta="Secciones de SST"
          activa={pestana}
          onCambiar={setPestana}
          pestanas={[
            { clave: "ejercicios", etiqueta: "Ejercicios" },
            ...(gestor
              ? ([
                  { clave: "cumplimiento", etiqueta: "Cumplimiento" },
                  { clave: "frecuencia", etiqueta: "Frecuencia" },
                  { clave: "contenido", etiqueta: "Contenido" },
                ] as const)
              : ([{ clave: "historial", etiqueta: "Mi historial" }] as const)),
          ]}
        />
      </div>
      {pestana === "ejercicios" && <Ejercicios gestor={gestor} />}
      {pestana === "historial" && !gestor && <Registro ambito="mias" />}
      {pestana === "cumplimiento" && gestor && (
        <div className="flex flex-col gap-6">
          <Cumplimiento />
          <Registro ambito="todas" />
        </div>
      )}
      {pestana === "frecuencia" && gestor && <Frecuencia />}
      {pestana === "contenido" && gestor && <Contenido />}
    </>
  );
}
