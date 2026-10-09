import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { apiInventario } from "@/api/inventario";
import { Aviso } from "@/components/ui/Aviso";
import { Button } from "@/components/ui/Button";
import { agregarLinea, cantidadValida, EditorLineas, lineasAItems, type Linea } from "@/components/ui/EditorLineas";
import { Input, Select, Textarea } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";
import { SelectorProducto } from "@/components/ui/SelectorProducto";
import { useMutacion } from "@/hooks/useMutacion";
import { MOTIVO } from "@/lib/etiquetas";
import { entero } from "@/lib/format";
import { normalizarError } from "@/lib/errors";
import { aplicarErroresServidor, v } from "@/lib/formularios";
import type { InventarioFila, ResultadoOperacion } from "@/types/api";
import { buscarEnCatalogo, buscarEnSede } from "./fuentes";

const INVALIDAR = [["inventario"], ["movimientos"], ["alertas"], ["dashboard"], ["recomendaciones"]];

function mensajeOperacion(r: ResultadoOperacion): string {
  const extra = [
    r.alertas_abiertas ? `${r.alertas_abiertas} ${r.alertas_abiertas === 1 ? "alerta nueva" : "alertas nuevas"}` : "",
    r.alertas_resueltas ? `${r.alertas_resueltas} ${r.alertas_resueltas === 1 ? "alerta resuelta" : "alertas resueltas"}` : "",
  ].filter(Boolean);
  return extra.length ? `${r.mensaje} (${extra.join(", ")}).` : r.mensaje;
}

interface PropsLinea {
  sedeId: number;
  sedeNombre: string;
  onCerrar: () => void;
}

const MOTIVOS_ENTRADA = ["compra", "devolucion_cliente", "inventario_inicial", "produccion", "otro"] as const;
const MOTIVOS_SALIDA = ["perdida", "deterioro", "consumo_interno", "devolucion_proveedor", "otro"] as const;

function DialogoMovimientoMultiple({
  tipo,
  sedeId,
  sedeNombre,
  onCerrar,
}: PropsLinea & { tipo: "entrada" | "salida" }) {
  const esEntrada = tipo === "entrada";
  const motivos = esEntrada ? MOTIVOS_ENTRADA : MOTIVOS_SALIDA;
  const [lineas, setLineas] = useState<Linea[]>([]);
  const [motivo, setMotivo] = useState<string>(motivos[0]);
  const [observacion, setObservacion] = useState("");
  const [intento, setIntento] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [erroresLinea, setErroresLinea] = useState<Record<string, string>>({});

  const guardar = useMutacion(
    () => {
      const items = lineasAItems(lineas);
      const comun = { sede_id: sedeId, observacion: observacion.trim() || null, items };
      return esEntrada
        ? apiInventario.entrada({ ...comun, motivo: motivo as (typeof MOTIVOS_ENTRADA)[number] })
        : apiInventario.salida({ ...comun, motivo: motivo as (typeof MOTIVOS_SALIDA)[number] });
    },
    { exito: mensajeOperacion, invalidar: INVALIDAR, avisarError: false, onExito: onCerrar },
  );

  const hayErrores = lineas.some((l) => cantidadValida(l, !esEntrada));
  const observacionObligatoria = motivo === "otro";

  async function enviar() {
    setIntento(true);
    setError(null);
    setErroresLinea({});
    if (lineas.length === 0 || hayErrores) return;
    if (observacionObligatoria && observacion.trim().length < 3) return;
    try {
      await guardar.mutateAsync();
    } catch (e) {
      const err = normalizarError(e);
      setErroresLinea(err.campos);
      setError(err.message);
    }
  }

  return (
    <Modal
      abierto
      onCerrar={onCerrar}
      ancho="lg"
      bloqueado={guardar.isPending}
      titulo={esEntrada ? "Registrar entrada de productos" : "Registrar salida de productos"}
      descripcion={`Sede: ${sedeNombre}. ${esEntrada ? "Suma existencias al inventario." : "Descuenta existencias del inventario."}`}
      pie={
        <>
          <Button variante="ghost" onClick={onCerrar} disabled={guardar.isPending}>Cancelar</Button>
          <Button onClick={enviar} cargando={guardar.isPending} disabled={intento && (lineas.length === 0 || hayErrores)}>
            {esEntrada ? "Registrar entrada" : "Registrar salida"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-5">
        {error && <Aviso tipo="error">{error}</Aviso>}
        {intento && lineas.length === 0 && <Aviso tipo="aviso">Agregue al menos un producto.</Aviso>}
        <div className="grid gap-4 sm:grid-cols-2">
          <Select etiqueta="Motivo" value={motivo} onChange={(e) => setMotivo(e.target.value)}>
            {motivos.map((m) => (
              <option key={m} value={m}>{MOTIVO[m]}</option>
            ))}
          </Select>
          <SelectorProducto
            etiqueta="Agregar producto"
            origen={esEntrada ? ["catalogo"] : ["sede", sedeId]}
            buscar={(q) => (esEntrada ? buscarEnCatalogo(q) : buscarEnSede(sedeId, q))}
            onElegir={(o) => setLineas((prev) => agregarLinea(prev, o))}
          />
        </div>
        <EditorLineas lineas={lineas} onChange={setLineas} limitarADisponible={!esEntrada} errores={erroresLinea} />
        <Textarea
          etiqueta={observacionObligatoria ? "Observación (obligatoria para «Otro»)" : "Observación"}
          value={observacion}
          maxLength={300}
          onChange={(e) => setObservacion(e.target.value)}
          placeholder="Ej. número de factura del proveedor"
          error={intento && observacionObligatoria && observacion.trim().length < 3 ? "Explique brevemente el motivo" : undefined}
        />
      </div>
    </Modal>
  );
}

export const DialogoEntrada = (p: PropsLinea) => <DialogoMovimientoMultiple tipo="entrada" {...p} />;
export const DialogoSalida = (p: PropsLinea) => <DialogoMovimientoMultiple tipo="salida" {...p} />;

/* ---------------------------------------------------------------- ajuste de existencias */

const esquemaAjuste = z.object({
  cantidad_real: v.entero("La cantidad contada", 0, 10_000_000),
  motivo: z.enum(["conteo_fisico", "correccion", "otro"]),
  observacion: z.string().trim().min(3, "Explique el motivo del ajuste (mínimo 3 caracteres)").max(300),
});
type DatosAjuste = z.infer<typeof esquemaAjuste>;

export function DialogoAjuste({ fila, sedeId, sedeNombre, onCerrar }: { fila: InventarioFila; sedeId: number; sedeNombre: string; onCerrar: () => void }) {
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    watch,
    formState: { errors },
  } = useForm<DatosAjuste>({
    resolver: zodResolver(esquemaAjuste),
    defaultValues: { cantidad_real: String(fila.cantidad), motivo: "conteo_fisico", observacion: "" },
  });
  const guardar = useMutacion(
    (d: DatosAjuste) => apiInventario.ajuste({ sede_id: sedeId, producto_id: fila.producto.id, cantidad_real: Number(d.cantidad_real), motivo: d.motivo, observacion: d.observacion.trim() }),
    { exito: mensajeOperacion, invalidar: INVALIDAR, avisarError: false, onExito: onCerrar },
  );
  const real = Number(watch("cantidad_real"));
  const diferencia = Number.isFinite(real) && /^\d+$/.test(String(watch("cantidad_real"))) ? real - fila.cantidad : null;

  return (
    <Modal
      abierto
      onCerrar={onCerrar}
      bloqueado={guardar.isPending}
      titulo="Ajustar existencias"
      descripcion={`${fila.producto.nombre} · ${sedeNombre}`}
      pie={
        <>
          <Button variante="ghost" onClick={onCerrar} disabled={guardar.isPending}>Cancelar</Button>
          <Button type="submit" form="form-ajuste" cargando={guardar.isPending}>Aplicar ajuste</Button>
        </>
      }
    >
      <form
        id="form-ajuste"
        noValidate
        className="flex flex-col gap-4"
        onSubmit={handleSubmit(async (d) => {
          setErrorGeneral(null);
          try {
            await guardar.mutateAsync(d);
          } catch (e) {
            setErrorGeneral(aplicarErroresServidor(e, setError, ["cantidad_real", "motivo", "observacion"]));
          }
        })}
      >
        {errorGeneral && <Aviso tipo="error">{errorGeneral}</Aviso>}
        <p className="rounded-(--radius-control) bg-surface-2 px-4 py-3 text-sm text-ink-dim">
          Existencias registradas: <strong className="tabular text-ink">{entero(fila.cantidad)}</strong>
        </p>
        <Input etiqueta="Cantidad real contada" required inputMode="numeric" error={errors.cantidad_real?.message} {...register("cantidad_real")} />
        {diferencia !== null && diferencia !== 0 && (
          <p className={`tabular -mt-2 text-sm font-semibold ${diferencia > 0 ? "text-success" : "text-danger"}`}>
            Diferencia: {diferencia > 0 ? "+" : ""}{entero(diferencia)} unidades
          </p>
        )}
        <Select etiqueta="Motivo" {...register("motivo")}>
          <option value="conteo_fisico">{MOTIVO.conteo_fisico}</option>
          <option value="correccion">{MOTIVO.correccion}</option>
          <option value="otro">{MOTIVO.otro}</option>
        </Select>
        <Textarea etiqueta="Observación" required maxLength={300} placeholder="Ej. conteo cíclico de octubre" error={errors.observacion?.message} {...register("observacion")} />
      </form>
    </Modal>
  );
}

/* ---------------------------------------------------------------- niveles mínimo y máximo */

const esquemaNiveles = z
  .object({ stock_minimo: v.entero("El stock mínimo", 0, 10_000_000), stock_maximo: z.string().trim().refine((t) => t === "" || /^\d+$/.test(t), "El stock máximo debe ser un número entero") })
  .refine((d) => d.stock_maximo === "" || Number(d.stock_maximo) >= Number(d.stock_minimo), { path: ["stock_maximo"], message: "El máximo no puede ser menor que el mínimo" });
type DatosNiveles = z.infer<typeof esquemaNiveles>;

export function DialogoNiveles({ fila, sedeId, sedeNombre, onCerrar }: { fila: InventarioFila; sedeId: number; sedeNombre: string; onCerrar: () => void }) {
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<DatosNiveles>({
    resolver: zodResolver(esquemaNiveles),
    defaultValues: { stock_minimo: String(fila.stock_minimo), stock_maximo: fila.stock_maximo != null ? String(fila.stock_maximo) : "" },
  });
  const guardar = useMutacion(
    (d: DatosNiveles) => apiInventario.niveles({ sede_id: sedeId, producto_id: fila.producto.id, stock_minimo: Number(d.stock_minimo), stock_maximo: d.stock_maximo === "" ? null : Number(d.stock_maximo) }),
    { exito: "Niveles de stock actualizados.", invalidar: INVALIDAR, avisarError: false, onExito: onCerrar },
  );

  return (
    <Modal
      abierto
      onCerrar={onCerrar}
      bloqueado={guardar.isPending}
      titulo="Niveles de stock"
      descripcion={`${fila.producto.nombre} · ${sedeNombre}`}
      pie={
        <>
          <Button variante="ghost" onClick={onCerrar} disabled={guardar.isPending}>Cancelar</Button>
          <Button type="submit" form="form-niveles" cargando={guardar.isPending}>Guardar niveles</Button>
        </>
      }
    >
      <form
        id="form-niveles"
        noValidate
        className="flex flex-col gap-4"
        onSubmit={handleSubmit(async (d) => {
          setErrorGeneral(null);
          try {
            await guardar.mutateAsync(d);
          } catch (e) {
            setErrorGeneral(aplicarErroresServidor(e, setError, ["stock_minimo", "stock_maximo"]));
          }
        })}
      >
        {errorGeneral && <Aviso tipo="error">{errorGeneral}</Aviso>}
        <Aviso tipo="info">Al guardar se recalculan las alertas de este producto en esta sede.</Aviso>
        <Input etiqueta="Stock mínimo" required inputMode="numeric" ayuda="Por debajo de este valor se genera una alerta de inventario bajo." error={errors.stock_minimo?.message} {...register("stock_minimo")} />
        <Input etiqueta="Stock máximo" inputMode="numeric" placeholder="Sin límite" ayuda="Por encima de este valor se genera una alerta de exceso. Déjelo vacío si no aplica." error={errors.stock_maximo?.message} {...register("stock_maximo")} />
      </form>
    </Modal>
  );
}
