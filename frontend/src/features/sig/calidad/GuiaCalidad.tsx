import { AlertTriangle, ClipboardCheck, FileSearch, Hourglass, PackageX, ShieldCheck } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Aviso } from "@/components/ui/Aviso";

function Paso({ n, titulo, children }: { n: number; titulo: string; children: React.ReactNode }) {
  return (
    <li className="flex gap-3">
      <span className="tabular flex size-7 shrink-0 items-center justify-center rounded-full bg-accent-dim text-sm font-semibold text-accent-light" aria-hidden>
        {n}
      </span>
      <div>
        <p className="text-sm font-semibold text-ink">{titulo}</p>
        <p className="mt-0.5 text-sm text-ink-dim">{children}</p>
      </div>
    </li>
  );
}

/** Material informativo del módulo: qué son una no conformidad y una garantía, cómo se gestionan y de qué dependen los plazos. */
export function GuiaCalidad({ irANoConformidades, irAGarantias }: { irANoConformidades?: () => void; irAGarantias?: () => void }) {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader titulo="¿Qué es una no conformidad?" descripcion="Un producto o una entrega que no cumple lo que se esperaba." />
        <div className="flex flex-col gap-4 p-5 text-sm text-ink-dim">
          <p>
            Una <strong className="text-ink">no conformidad</strong> es el incumplimiento de un requisito: el producto llegó con un defecto de fábrica, golpeado en el transporte, equivocado, incompleto, con el empaque dañado o
            sin cumplir la especificación acordada. Reportarla a tiempo permite reclamar al proveedor, evitar que el producto defectuoso llegue al cliente y aprender de lo ocurrido.
          </p>
          <ul className="flex flex-col gap-2">
            <li className="flex gap-2">
              <PackageX className="mt-0.5 size-4 shrink-0 text-ink-faint" aria-hidden /> Ejemplos: una batería que no carga, una caja aplastada, 8 unidades recibidas en lugar de 10.
            </li>
            <li className="flex gap-2">
              <ShieldCheck className="mt-0.5 size-4 shrink-0 text-ink-faint" aria-hidden /> Registrarla <strong className="text-ink">no cambia las existencias</strong>: es un registro de seguimiento. Si hay que dar de baja unidades, se hace con una salida o un ajuste de inventario.
            </li>
          </ul>
          {irANoConformidades && (
            <button type="button" onClick={irANoConformidades} className="self-start text-sm font-semibold text-accent-light hover:underline">
              Ir a no conformidades →
            </button>
          )}
        </div>
      </Card>

      <Card>
        <CardHeader titulo="¿Qué es una garantía?" descripcion="El respaldo del fabricante o proveedor frente a defectos del producto." />
        <div className="flex flex-col gap-4 p-5 text-sm text-ink-dim">
          <p>
            La <strong className="text-ink">garantía</strong> es el compromiso de quien fabrica o vende un producto de repararlo, cambiarlo o devolver el dinero si presenta fallas dentro de un periodo. Para reclamarla hace falta
            el documento que prueba la compra (factura, entrada de inventario o venta), la fecha, la descripción del defecto y, ojalá, fotos o evidencias.
          </p>
          <p className="flex gap-2">
            <Hourglass className="mt-0.5 size-4 shrink-0 text-ink-faint" aria-hidden />
            <span>
              Los plazos <strong className="text-ink">dependen del fabricante, del proveedor y de la normativa aplicable</strong> (en Colombia, el Estatuto del Consumidor, Ley 1480 de 2011) y cambian de un producto a otro. Por eso el
              sistema no asume ninguno: registra la fecha hasta la que cubre la garantía que tú indicas según la ficha del producto o el contrato con el proveedor.
            </span>
          </p>
          {irAGarantias && (
            <button type="button" onClick={irAGarantias} className="self-start text-sm font-semibold text-accent-light hover:underline">
              Ir a garantías →
            </button>
          )}
        </div>
      </Card>

      <Card className="lg:col-span-2">
        <CardHeader titulo="Procedimiento paso a paso" descripcion="Cómo se gestiona un caso desde que se detecta hasta que se cierra." />
        <ol className="grid gap-5 p-5 sm:grid-cols-2 xl:grid-cols-3">
          <Paso n={1} titulo="Detecta y separa el producto">
            Al recibir, vender o inspeccionar, identifica el producto con problema y apártalo para que no se despache.
          </Paso>
          <Paso n={2} titulo="Reporta el caso">
            Registra el producto, la cantidad afectada, la fecha en que lo detectaste y una descripción clara. Si nació de una entrada de mercancía, vincúlala. Adjunta fotos como evidencia.
          </Paso>
          <Paso n={3} titulo="Revisión">
            Calidad revisa el reporte, asigna un responsable y puede pedir más información. Cada cambio queda en el historial con fecha y autor.
          </Paso>
          <Paso n={4} titulo="Gestión con el proveedor">
            En una garantía, se envía al proveedor con los soportes y se registra su respuesta (aprobada o rechazada) y las fechas de envío y respuesta.
          </Paso>
          <Paso n={5} titulo="Solución">
            Se documenta qué se hizo: reposición, reparación, nota crédito o descarte. Si hay que ajustar existencias, se hace con una operación de inventario.
          </Paso>
          <Paso n={6} titulo="Cierre">
            Con la solución registrada, el caso se cierra. Un caso cerrado conserva todo su historial para consulta y auditoría.
          </Paso>
        </ol>
      </Card>

      <div className="lg:col-span-2">
        <Aviso tipo="info" titulo="Buenas prácticas">
          <div className="mt-1 flex flex-col gap-1.5">
            <div className="flex gap-2">
              <ClipboardCheck className="mt-0.5 size-4 shrink-0" aria-hidden /> Reporta el mismo día en que lo detectas: muchos proveedores limitan el tiempo para reclamar.
            </div>
            <div className="flex gap-2">
              <FileSearch className="mt-0.5 size-4 shrink-0" aria-hidden /> Conserva la factura y el número de lote o serie; adjunta fotos del empaque y del defecto.
            </div>
            <div className="flex gap-2">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden /> Esta guía es orientativa y no reemplaza la asesoría legal ni los términos de tu contrato con el proveedor.
            </div>
          </div>
        </Aviso>
      </div>
    </div>
  );
}
