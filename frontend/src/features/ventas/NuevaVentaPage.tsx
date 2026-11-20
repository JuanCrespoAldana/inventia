import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { apiVentas } from "@/api/operaciones";
import { Aviso } from "@/components/ui/Aviso";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { agregarLinea, cantidadValida, EditorLineas, type Linea } from "@/components/ui/EditorLineas";
import { FiltroSelect, Textarea } from "@/components/ui/Field";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { SelectorProducto } from "@/components/ui/SelectorProducto";
import { useMutacion } from "@/hooks/useMutacion";
import { useSedeActiva } from "@/hooks/useSedeActiva";
import { normalizarError } from "@/lib/errors";
import { buscarEnSede } from "@/features/inventario/fuentes";

export default function NuevaVentaPage() {
  const navegar = useNavigate();
  const sede = useSedeActiva();
  const [lineas, setLineas] = useState<Linea[]>([]);
  const [observacion, setObservacion] = useState("");
  const [intento, setIntento] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [erroresLinea, setErroresLinea] = useState<Record<string, string>>({});

  const registrar = useMutacion(
    () =>
      apiVentas.crear({
        sede_id: sede.sedeId!,
        observacion: observacion.trim() || null,
        items: lineas.map((l) => ({
          producto_id: l.producto.id,
          cantidad: Number(l.cantidad),
          precio_unitario: l.precio.trim() ? Number(l.precio.replace(",", ".")) : null,
        })),
      }),
    { exito: (v) => `Venta #${v.numero} registrada.`, invalidar: [["ventas"], ["inventario"], ["movimientos"], ["alertas"], ["dashboard"]], avisarError: false, onExito: (v) => navegar(`/ventas/${v.id}`) },
  );

  const hayErrores = lineas.some((l) => cantidadValida(l, true));

  async function enviar() {
    setIntento(true);
    setError(null);
    setErroresLinea({});
    if (lineas.length === 0 || hayErrores || sede.sedeId === null) return;
    try {
      await registrar.mutateAsync();
    } catch (e) {
      const err = normalizarError(e);
      setErroresLinea(err.campos);
      setError(err.message);
    }
  }

  function cambiarSede(id: number) {
    sede.elegir(id);
    setLineas([]); // las existencias disponibles dependen de la sede
  }

  return (
    <>
      <EncabezadoPagina
        titulo="Nueva venta"
        descripcion="Las unidades se descuentan de la sede al registrar la venta. Si deja el precio vacío se usa el precio del producto."
        acciones={<Button variante="ghost" icono={<ArrowLeft className="size-4" aria-hidden />} onClick={() => navegar("/ventas")}>Volver a ventas</Button>}
      />
      <div className="mx-auto max-w-3xl">
        <Card>
          <CardHeader titulo="Detalle de la venta" descripcion={sede.nombre ? `Sede: ${sede.nombre}` : undefined} />
          <div className="flex flex-col gap-5 p-5">
            {error && <Aviso tipo="error">{error}</Aviso>}
            {intento && lineas.length === 0 && <Aviso tipo="aviso">Agregue al menos un producto a la venta.</Aviso>}
            {!sede.fija && sede.sedes.length > 1 && (
              <div className="flex items-center gap-3 text-sm text-ink-dim">
                <span>Vender desde</span>
                <FiltroSelect etiqueta="Sede de la venta" value={sede.sedeId ?? ""} onChange={(e) => cambiarSede(Number(e.target.value))}>
                  {sede.sedes.map((s) => (
                    <option key={s.id} value={s.id}>{s.nombre}</option>
                  ))}
                </FiltroSelect>
              </div>
            )}
            {sede.sedeId !== null && (
              <SelectorProducto
                etiqueta="Agregar producto"
                origen={["venta", sede.sedeId]}
                buscar={(q) => buscarEnSede(sede.sedeId!, q, true)}
                onElegir={(o) => setLineas((prev) => agregarLinea(prev, o))}
              />
            )}
            <EditorLineas lineas={lineas} onChange={setLineas} conPrecio limitarADisponible errores={erroresLinea} />
            <Textarea etiqueta="Observación" value={observacion} maxLength={300} onChange={(e) => setObservacion(e.target.value)} placeholder="Opcional. Ej. cliente, forma de pago" />
          </div>
          <div className="flex justify-end gap-2 border-t border-line px-5 py-4">
            <Button variante="ghost" onClick={() => navegar("/ventas")} disabled={registrar.isPending}>Cancelar</Button>
            <Button onClick={enviar} cargando={registrar.isPending} disabled={sede.sedeId === null || (intento && (lineas.length === 0 || hayErrores))}>
              Registrar venta
            </Button>
          </div>
        </Card>
      </div>
    </>
  );
}
