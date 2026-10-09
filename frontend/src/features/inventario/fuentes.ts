import { apiInventario } from "@/api/inventario";
import { apiProductos } from "@/api/catalogo";
import type { OpcionProducto } from "@/components/ui/SelectorProducto";

/** Productos activos del catálogo (para entradas: aún pueden no tener existencias en la sede). */
export async function buscarEnCatalogo(q: string): Promise<OpcionProducto[]> {
  const r = await apiProductos.listar({ q, activo: true, tamano: 12 });
  return r.items.map((p) => ({
    producto: { id: p.id, codigo: p.codigo, nombre: p.nombre, unidad_medida: p.unidad_medida },
    precio: p.precio_venta,
  }));
}

/** Productos con su disponibilidad en una sede (para salidas, ventas y traslados). */
export async function buscarEnSede(sedeId: number, q: string, conPrecio = false): Promise<OpcionProducto[]> {
  const [inventario, catalogo] = await Promise.all([
    apiInventario.porSede({ sede_id: sedeId, q, tamano: 12 }),
    conPrecio ? apiProductos.listar({ q, activo: true, tamano: 24 }) : Promise.resolve(null),
  ]);
  const precios = new Map(catalogo?.items.map((p) => [p.id, p.precio_venta]) ?? []);
  return inventario.items
    .filter((f) => f.producto_activo)
    .map((f) => ({ producto: f.producto, disponible: f.cantidad, precio: precios.get(f.producto.id) ?? null }));
}
