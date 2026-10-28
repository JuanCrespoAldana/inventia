import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, Copy, Plus, ShieldOff } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { apiIntegraciones } from "@/api/analitica";
import { Aviso } from "@/components/ui/Aviso";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Tabla } from "@/components/ui/DataTable";
import { Casilla, Input, Select } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { useSedes } from "@/hooks/useCatalogos";
import { useMutacion } from "@/hooks/useMutacion";
import { mensajeDeError } from "@/lib/errors";
import { fecha, fechaHora, hace } from "@/lib/format";
import { aplicarErroresServidor, v } from "@/lib/formularios";
import type { AlcanceLlave, Llave, LlaveCreada } from "@/types/api";

const INVALIDAR = [["integraciones"]];
const VIGENCIAS = [
  { valor: "30", texto: "30 días" },
  { valor: "90", texto: "90 días (recomendado)" },
  { valor: "180", texto: "180 días" },
  { valor: "365", texto: "1 año" },
  { valor: "730", texto: "2 años (máximo)" },
];

const esquema = z.object({
  nombre: v.texto("El nombre", 3, 100),
  sede_id: z.string(),
  vigencia: z.string(),
  alcances: z.array(z.string()).min(1, "Seleccione al menos un permiso de consulta"),
});
type Datos = z.infer<typeof esquema>;

function FormularioLlave({ alcances, onCerrar, onCreada }: { alcances: AlcanceLlave[]; onCerrar: () => void; onCreada: (l: LlaveCreada) => void }) {
  const sedes = useSedes();
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<Datos>({ resolver: zodResolver(esquema), defaultValues: { nombre: "", sede_id: "", vigencia: "90", alcances: [] } });
  const crear = useMutacion(
    (d: Datos) =>
      apiIntegraciones.crear({ nombre: d.nombre.trim(), alcances: d.alcances, sede_id: d.sede_id ? Number(d.sede_id) : null, dias_vigencia: Number(d.vigencia) }),
    { invalidar: INVALIDAR, avisarError: false, onExito: onCreada },
  );
  return (
    <Modal
      abierto
      onCerrar={onCerrar}
      bloqueado={crear.isPending}
      titulo="Nueva llave de acceso"
      descripcion="Permite que un agente de IA consulte información de su empresa. Es de solo lectura: no puede registrar, modificar ni aprobar nada."
      pie={
        <>
          <Button variante="ghost" onClick={onCerrar} disabled={crear.isPending}>Cancelar</Button>
          <Button type="submit" form="form-llave" cargando={crear.isPending}>Crear llave</Button>
        </>
      }
    >
      <form
        id="form-llave"
        noValidate
        className="flex flex-col gap-4"
        onSubmit={handleSubmit(async (d) => {
          setErrorGeneral(null);
          try {
            await crear.mutateAsync(d);
          } catch (e) {
            setErrorGeneral(aplicarErroresServidor(e, setError, ["nombre", "alcances", "sede_id", "dias_vigencia"]));
          }
        })}
      >
        {errorGeneral && <Aviso tipo="error">{errorGeneral}</Aviso>}
        <Input etiqueta="Nombre de la llave" required placeholder="Ej. Asistente de compras" ayuda="Le ayuda a reconocer para qué se usa." error={errors.nombre?.message} {...register("nombre")} />
        <fieldset className="flex flex-col gap-3">
          <legend className="mb-1 text-[13px] font-medium text-ink-dim">Qué puede consultar <span className="text-accent-light" aria-hidden>*</span></legend>
          {alcances.map((a) => (
            <Casilla key={a.alcance} value={a.alcance} etiqueta={a.descripcion} descripcion={a.alcance} {...register("alcances")} />
          ))}
          {errors.alcances?.message && <p role="alert" className="text-xs text-danger">{errors.alcances.message}</p>}
        </fieldset>
        <Select etiqueta="Sede" ayuda="Limite la llave a una sola sede o déjela para toda la empresa." {...register("sede_id")}>
          <option value="">Todas las sedes</option>
          {(sedes.data ?? []).map((s) => (
            <option key={s.id} value={s.id}>{s.nombre}</option>
          ))}
        </Select>
        <Select etiqueta="Vigencia" ayuda="Al vencer, la llave deja de funcionar y debe crear otra." {...register("vigencia")}>
          {VIGENCIAS.map((o) => (
            <option key={o.valor} value={o.valor}>{o.texto}</option>
          ))}
        </Select>
      </form>
    </Modal>
  );
}

function LlaveNueva({ llave, onCerrar }: { llave: LlaveCreada; onCerrar: () => void }) {
  const [copiada, setCopiada] = useState(false);
  const [falloCopia, setFalloCopia] = useState(false);
  async function copiar() {
    try {
      await navigator.clipboard.writeText(llave.llave);
      setCopiada(true);
      setFalloCopia(false);
      window.setTimeout(() => setCopiada(false), 2500);
    } catch {
      setFalloCopia(true);
    }
  }
  return (
    <Modal
      abierto
      onCerrar={onCerrar}
      titulo="Llave creada"
      descripcion={`«${llave.nombre}» ya está activa.`}
      pie={<Button onClick={onCerrar}>Ya la guardé</Button>}
    >
      <div className="flex flex-col gap-4">
        <Aviso tipo="aviso" titulo="Cópiela ahora">
          Esta llave se muestra una sola vez. Si la pierde, revóquela y cree otra. Trátela como una contraseña: no la comparta ni la publique.
        </Aviso>
        <div className="flex items-stretch gap-2">
          <code data-testid="llave-secreta" className="min-w-0 flex-1 select-all break-all rounded-(--radius-control) border border-line-strong bg-surface-2 px-3.5 py-2.5 font-mono text-[13px] text-ink">
            {llave.llave}
          </code>
          <Button variante="secondary" onClick={copiar} icono={copiada ? <Check className="size-4 text-success" aria-hidden /> : <Copy className="size-4" aria-hidden />}>
            {copiada ? "Copiada" : "Copiar"}
          </Button>
        </div>
        {falloCopia && <p role="alert" className="text-xs text-danger">No se pudo copiar automáticamente. Selecciónela y cópiela con el teclado.</p>}
        <div>
          <p className="mb-1.5 text-[13px] font-medium text-ink-dim">Uso desde un agente</p>
          <pre className="overflow-x-auto rounded-(--radius-control) border border-line bg-bg px-3.5 py-3 font-mono text-xs leading-relaxed text-ink-dim">{`GET /api/agentes/inventario
X-API-Key: <su llave>`}</pre>
        </div>
      </div>
    </Modal>
  );
}

function estadoLlave(l: Llave): { texto: string; tono: "success" | "neutral" | "warning" } {
  if (!l.activa) return { texto: "Revocada", tono: "neutral" };
  if (l.expira_en && new Date(l.expira_en).getTime() < Date.now()) return { texto: "Vencida", tono: "warning" };
  return { texto: "Activa", tono: "success" };
}

export default function IntegracionesPage() {
  const llaves = useQuery({ queryKey: ["integraciones", "llaves"], queryFn: apiIntegraciones.llaves });
  const alcances = useQuery({ queryKey: ["integraciones", "alcances"], queryFn: apiIntegraciones.alcances, staleTime: 10 * 60_000 });
  const sedes = useSedes(false);
  const [creando, setCreando] = useState(false);
  const [nueva, setNueva] = useState<LlaveCreada | null>(null);
  const [aRevocar, setARevocar] = useState<Llave | null>(null);
  const [errorRevocar, setErrorRevocar] = useState<string | null>(null);

  const revocar = useMutacion((l: Llave) => apiIntegraciones.revocar(l.id), { exito: "Llave revocada. Dejó de funcionar de inmediato.", invalidar: INVALIDAR, avisarError: false, onExito: () => setARevocar(null) });
  const nombreSede = (id: number | null) => (id === null ? "Todas las sedes" : (sedes.data ?? []).find((s) => s.id === id)?.nombre ?? `Sede ${id}`);
  const etiquetaAlcance = (clave: string) => (alcances.data ?? []).find((a) => a.alcance === clave)?.descripcion ?? clave;

  return (
    <>
      <EncabezadoPagina
        titulo="Agentes de IA"
        descripcion="Llaves de acceso de solo lectura para que asistentes externos consulten inventario, alertas, predicciones y recomendaciones."
        acciones={<Button icono={<Plus className="size-4" aria-hidden />} onClick={() => setCreando(true)} disabled={!alcances.data}>Nueva llave</Button>}
      />
      <Aviso tipo="info" className="mb-5" titulo="Los agentes consultan, las personas deciden">
        Una llave nunca puede registrar movimientos, aprobar recomendaciones ni cambiar datos. Toda aprobación sigue siendo de una persona con el rol adecuado.
      </Aviso>
      <Card>
        <CardHeader titulo="Llaves emitidas" descripcion="Por seguridad solo se guarda una huella de cada llave; el valor completo no se puede recuperar." />
        <Tabla
          descripcion="Llaves de acceso para agentes de IA"
          idDe={(l) => l.id}
          filas={llaves.data}
          paginar={10}
          cargando={llaves.isFetching}
          error={llaves.error}
          onReintentar={() => llaves.refetch()}
          vacio={{ titulo: "Aún no hay llaves", descripcion: "Cree una llave para conectar un agente de IA con permisos de consulta.", accion: <Button onClick={() => setCreando(true)} disabled={!alcances.data}>Nueva llave</Button> }}
          columnas={[
            {
              clave: "nombre",
              encabezado: "Llave",
              celda: (l) => (
                <div>
                  <div className="font-medium">{l.nombre}</div>
                  <div className="font-mono text-xs text-ink-faint">{l.prefijo}…</div>
                </div>
              ),
            },
            {
              clave: "alcances",
              encabezado: "Puede consultar",
              desde: "md",
              celda: (l) => (
                <div className="flex max-w-xs flex-wrap gap-1.5">
                  {l.alcances.map((a) => <Badge key={a}>{etiquetaAlcance(a)}</Badge>)}
                </div>
              ),
            },
            { clave: "sede", encabezado: "Sede", desde: "lg", celda: (l) => nombreSede(l.sede_id) },
            { clave: "vence", encabezado: "Vence", desde: "lg", celda: (l) => (l.expira_en ? fecha(l.expira_en) : "Sin vencimiento") },
            { clave: "uso", encabezado: "Último uso", desde: "lg", celda: (l) => <span className="text-ink-dim" title={l.ultimo_uso_en ? fechaHora(l.ultimo_uso_en) : undefined}>{l.ultimo_uso_en ? hace(l.ultimo_uso_en) : "Sin uso"}</span> },
            {
              clave: "estado",
              encabezado: "Estado",
              celda: (l) => {
                const e = estadoLlave(l);
                return <Badge tono={e.tono}>{e.texto}</Badge>;
              },
            },
            {
              clave: "acciones",
              encabezado: "Acciones",
              alinear: "derecha",
              celda: (l) =>
                l.activa ? (
                  <Button variante="danger" tamano="sm" icono={<ShieldOff className="size-3.5" aria-hidden />} onClick={() => { setErrorRevocar(null); setARevocar(l); }}>
                    Revocar
                  </Button>
                ) : null,
            },
          ]}
        />
      </Card>

      {creando && alcances.data && (
        <FormularioLlave alcances={alcances.data} onCerrar={() => setCreando(false)} onCreada={(l) => { setCreando(false); setNueva(l); }} />
      )}
      {nueva && <LlaveNueva llave={nueva} onCerrar={() => setNueva(null)} />}
      <ConfirmDialog
        abierto={aRevocar !== null}
        titulo="Revocar llave"
        mensaje={`«${aRevocar?.nombre}» dejará de funcionar de inmediato y no se puede reactivar. Si el agente la sigue usando, recibirá errores de acceso.`}
        confirmarTexto="Revocar"
        peligroso
        cargando={revocar.isPending}
        error={errorRevocar}
        onConfirmar={async () => {
          if (!aRevocar) return;
          setErrorRevocar(null);
          try {
            await revocar.mutateAsync(aRevocar);
          } catch (e) {
            setErrorRevocar(mensajeDeError(e));
          }
        }}
        onCancelar={() => setARevocar(null)}
      />
    </>
  );
}
