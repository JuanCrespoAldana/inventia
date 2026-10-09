import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { apiTraslados } from "@/api/operaciones";
import { useAuth } from "@/auth/AuthContext";
import { Aviso } from "@/components/ui/Aviso";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { agregarLinea, cantidadValida, EditorLineas, lineasAItems, type Linea } from "@/components/ui/EditorLineas";
import { Select, Textarea } from "@/components/ui/Field";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { SelectorProducto } from "@/components/ui/SelectorProducto";
import { PanelCargando } from "@/components/ui/Skeleton";
import { buscarEnSede } from "@/features/inventario/fuentes";
import { useDirectorioSedes } from "@/hooks/useCatalogos";
import { useMutacion } from "@/hooks/useMutacion";
import { normalizarError } from "@/lib/errors";

export default function NuevoTrasladoPage() {
  const navegar = useNavigate();
  const { sesion } = useAuth();
  const directorio = useDirectorioSedes();
  const sedes = useMemo(() => directorio.data ?? [], [directorio.data]);
  const propia = sesion?.rol.alcance === "sede" ? (sesion.sede?.id ?? null) : null;

  const [origenElegido, setOrigen] = useState<number | null>(null);
  const [destinoElegido, setDestino] = useState<number | null>(null);
  // Un usuario de sede normalmente pide mercancía para su sede: por defecto es el destino.
  const destino = destinoElegido ?? propia ?? sedes.find((s) => s.id !== origenElegido)?.id ?? null;
  const origen = origenElegido ?? sedes.find((s) => s.id !== destino)?.id ?? null;
  const [lineas, setLineas] = useState<Linea[]>([]);
  const [observacion, setObservacion] = useState("");
  const [intento, setIntento] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [erroresLinea, setErroresLinea] = useState<Record<string, string>>({});

  const solicitar = useMutacion(
    () => apiTraslados.crear({ sede_origen_id: origen!, sede_destino_id: destino!, observacion: observacion.trim() || null, items: lineasAItems(lineas) }),
    { exito: (t) => `Traslado #${t.numero} solicitado.`, invalidar: [["traslados"], ["dashboard"]], avisarError: false, onExito: (t) => navegar(`/traslados/${t.id}`) },
  );

  const hayErrores = lineas.some((l) => cantidadValida(l, true));
  const mismaSede = origen !== null && origen === destino;
  const fueraDeAlcance = propia !== null && origen !== propia && destino !== propia;

  async function enviar() {
    setIntento(true);
    setError(null);
    setErroresLinea({});
    if (lineas.length === 0 || hayErrores || mismaSede || fueraDeAlcance || origen === null || destino === null) return;
    try {
      await solicitar.mutateAsync();
    } catch (e) {
      const err = normalizarError(e);
      setErroresLinea(err.campos);
      setError(err.message);
    }
  }

  if (directorio.isPending) return <PanelCargando etiqueta="Cargando sedes…" />;

  return (
    <>
      <EncabezadoPagina
        titulo="Solicitar traslado"
        descripcion="Pida mercancía a otra sede. La sede de origen debe aprobar y la de destino confirmar la recepción."
        acciones={<Button variante="ghost" icono={<ArrowLeft className="size-4" aria-hidden />} onClick={() => navegar("/traslados")}>Volver a traslados</Button>}
      />
      <div className="mx-auto max-w-3xl">
        <Card>
          <CardHeader titulo="Datos del traslado" />
          <div className="flex flex-col gap-5 p-5">
            {sedes.length < 2 && <Aviso tipo="aviso" titulo="Se necesitan al menos dos sedes activas">Cree o active otra sede para poder trasladar mercancía.</Aviso>}
            {error && <Aviso tipo="error">{error}</Aviso>}
            {intento && mismaSede && <Aviso tipo="aviso">El origen y el destino deben ser sedes distintas.</Aviso>}
            {intento && fueraDeAlcance && <Aviso tipo="aviso">Solo puede solicitar traslados que salgan de su sede o lleguen a ella.</Aviso>}
            {intento && lineas.length === 0 && <Aviso tipo="aviso">Agregue al menos un producto.</Aviso>}
            <div className="grid items-end gap-4 sm:grid-cols-[1fr_auto_1fr]">
              <Select
                etiqueta="Sede de origen (entrega)"
                value={origen ?? ""}
                onChange={(e) => {
                  setOrigen(Number(e.target.value));
                  setLineas([]);
                }}
              >
                {sedes.map((s) => (
                  <option key={s.id} value={s.id}>{s.nombre}</option>
                ))}
              </Select>
              <ArrowRight className="mb-3 hidden size-5 text-ink-faint sm:block" aria-hidden />
              <Select etiqueta="Sede de destino (recibe)" value={destino ?? ""} onChange={(e) => setDestino(Number(e.target.value))}>
                {sedes.map((s) => (
                  <option key={s.id} value={s.id}>{s.nombre}</option>
                ))}
              </Select>
            </div>
            {origen !== null && (
              <SelectorProducto
                etiqueta="Agregar producto"
                origen={["traslado", origen]}
                buscar={(q) => buscarEnSede(origen, q)}
                onElegir={(o) => setLineas((prev) => agregarLinea(prev, o))}
                ayuda="Se muestran las existencias disponibles en la sede de origen."
              />
            )}
            <EditorLineas lineas={lineas} onChange={setLineas} limitarADisponible errores={erroresLinea} />
            <Textarea etiqueta="Observación" value={observacion} maxLength={300} onChange={(e) => setObservacion(e.target.value)} placeholder="Opcional. Ej. urgente por promoción" />
          </div>
          <div className="flex justify-end gap-2 border-t border-line px-5 py-4">
            <Button variante="ghost" onClick={() => navegar("/traslados")} disabled={solicitar.isPending}>Cancelar</Button>
            <Button onClick={enviar} cargando={solicitar.isPending} disabled={sedes.length < 2}>Solicitar traslado</Button>
          </div>
        </Card>
      </div>
    </>
  );
}
