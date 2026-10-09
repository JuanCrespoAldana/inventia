import { Trash2 } from "lucide-react";
import { cn } from "@/lib/cn";
import { entero, moneda } from "@/lib/format";
import { IconButton } from "./Button";
import type { OpcionProducto } from "./SelectorProducto";

export interface Linea {
  producto: OpcionProducto["producto"];
  disponible?: number;
  cantidad: string;
  precio: string;
  /** Precio de lista del producto, solo informativo. */
  precioLista?: number | null;
}

export function agregarLinea(lineas: Linea[], o: OpcionProducto): Linea[] {
  const existente = lineas.findIndex((l) => l.producto.id === o.producto.id);
  if (existente >= 0) {
    return lineas.map((l, i) => (i === existente ? { ...l, cantidad: String((Number(l.cantidad) || 0) + 1) } : l));
  }
  return [...lineas, { producto: o.producto, disponible: o.disponible, cantidad: "1", precio: "", precioLista: o.precio }];
}

interface Props {
  lineas: Linea[];
  onChange: (lineas: Linea[]) => void;
  conPrecio?: boolean;
  /** Valida que no se supere lo disponible. */
  limitarADisponible?: boolean;
  errores?: Record<string, string>;
}

export function cantidadValida(l: Linea, limitar: boolean): string | null {
  if (!/^\d+$/.test(l.cantidad.trim()) || Number(l.cantidad) < 1) return "Escriba una cantidad entera mayor que 0";
  if (limitar && l.disponible !== undefined && Number(l.cantidad) > l.disponible) return `Solo hay ${entero(l.disponible)} disponibles`;
  return null;
}

export function EditorLineas({ lineas, onChange, conPrecio = false, limitarADisponible = false, errores = {} }: Props) {
  if (lineas.length === 0) {
    return <p className="rounded-(--radius-control) border border-dashed border-line-strong px-4 py-6 text-center text-sm text-ink-faint">Busque y agregue al menos un producto.</p>;
  }
  const total = conPrecio ? lineas.reduce((s, l) => s + (Number(l.cantidad) || 0) * (l.precio.trim() ? Number(l.precio.replace(",", ".")) || 0 : (l.precioLista ?? 0)), 0) : null;

  return (
    <div className="flex flex-col gap-2">
      <ul className="flex flex-col gap-2" aria-label="Productos agregados">
        {lineas.map((l, i) => {
          const errorCantidad = errores[`items.${i}.cantidad`] ?? cantidadValida(l, limitarADisponible);
          const mostrarError = errores[`items.${i}.cantidad`] ?? (l.cantidad !== "" && errorCantidad);
          return (
            <li key={l.producto.id} className="rounded-(--radius-control) border border-line bg-surface-2/60 p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-ink">{l.producto.nombre}</p>
                  <p className="text-xs text-ink-faint">
                    {l.producto.codigo}
                    {l.disponible !== undefined && <> · {entero(l.disponible)} disponibles</>}
                    {conPrecio && l.precioLista != null && <> · lista {moneda(l.precioLista)}</>}
                  </p>
                </div>
                <IconButton etiqueta={`Quitar ${l.producto.nombre}`} onClick={() => onChange(lineas.filter((_, k) => k !== i))} className="-mr-1 -mt-1 size-8">
                  <Trash2 className="size-4" aria-hidden />
                </IconButton>
              </div>
              <div className={cn("mt-2 grid gap-3", conPrecio ? "grid-cols-2" : "grid-cols-1 sm:max-w-40")}>
                <label className="flex flex-col gap-1 text-xs text-ink-faint">
                  Cantidad
                  <input
                    inputMode="numeric"
                    aria-label={`Cantidad de ${l.producto.nombre}`}
                    aria-invalid={mostrarError ? true : undefined}
                    value={l.cantidad}
                    onChange={(e) => onChange(lineas.map((x, k) => (k === i ? { ...x, cantidad: e.target.value.replace(/[^\d]/g, "") } : x)))}
                    className={cn("tabular h-9 rounded-lg border bg-surface px-3 text-sm text-ink focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30", mostrarError ? "border-danger/70" : "border-line-strong")}
                  />
                </label>
                {conPrecio && (
                  <label className="flex flex-col gap-1 text-xs text-ink-faint">
                    Precio unitario (opcional)
                    <input
                      inputMode="decimal"
                      aria-label={`Precio de ${l.producto.nombre}`}
                      placeholder={l.precioLista != null ? String(l.precioLista) : "Precio del producto"}
                      value={l.precio}
                      onChange={(e) => onChange(lineas.map((x, k) => (k === i ? { ...x, precio: e.target.value.replace(/[^\d.,]/g, "") } : x)))}
                      className="tabular h-9 rounded-lg border border-line-strong bg-surface px-3 text-sm text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
                    />
                  </label>
                )}
              </div>
              {mostrarError && (
                <p role="alert" className="mt-1.5 text-xs text-danger">
                  {mostrarError}
                </p>
              )}
            </li>
          );
        })}
      </ul>
      {total !== null && (
        <p className="tabular flex items-center justify-between rounded-(--radius-control) bg-surface-2 px-4 py-2.5 text-sm">
          <span className="text-ink-dim">Total estimado</span>
          <span className="font-display text-base font-semibold text-ink">{moneda(total)}</span>
        </p>
      )}
    </div>
  );
}

/** Convierte las líneas del editor al cuerpo que espera la API. */
export function lineasAItems(lineas: Linea[]) {
  return lineas.map((l) => ({ producto_id: l.producto.id, cantidad: Number(l.cantidad) }));
}
