import { useState } from "react";
import { Link } from "react-router-dom";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, Boxes, CheckCircle2, RefreshCw, Receipt, Sparkles, TrendingDown, TrendingUp, Truck } from "lucide-react";
import { apiDashboard } from "@/api/analitica";
import { useAuth, useSesion } from "@/auth/AuthContext";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, Stat } from "@/components/ui/Card";
import { EstadoError, EstadoVacio } from "@/components/ui/EstadoVacio";
import { FiltroSelect } from "@/components/ui/Field";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { Tabla } from "@/components/ui/DataTable";
import { BarrasHorizontales } from "@/components/charts/Barras";
import { GraficoLineas } from "@/components/charts/GraficoLineas";
import { useSedes } from "@/hooks/useCatalogos";
import { aNumero } from "@/hooks/useFiltros";
import { estado, etiqueta, PRIORIDAD, TIPO_ALERTA, TIPO_MOVIMIENTO } from "@/lib/etiquetas";
import { entero, fecha, fechaHora, hace, moneda, monedaCompacta, parseDia, porcentaje } from "@/lib/format";
import type { Dashboard, Movimiento } from "@/types/api";

const PERIODOS = [
  { dias: 7, etiqueta: "Últimos 7 días" },
  { dias: 30, etiqueta: "Últimos 30 días" },
  { dias: 90, etiqueta: "Últimos 90 días" },
];

function Variacion({ valor }: { valor: number | null }) {
  if (valor === null) return <span>Sin datos del período anterior</span>;
  const sube = valor >= 0;
  const Icono = sube ? TrendingUp : TrendingDown;
  return (
    <span className={sube ? "text-success" : "text-danger"}>
      <Icono className="mr-1 inline size-3.5 align-[-2px]" aria-hidden />
      {sube ? "+" : ""}
      {porcentaje(valor)} <span className="text-ink-faint">frente al período anterior</span>
    </span>
  );
}

function Tarjetas({ d }: { d: Dashboard }) {
  const inv = d.inventario;
  const ven = d.ventas;
  const criticas = d.alertas?.por_prioridad?.critica ?? 0;
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {ven && (
        <Stat
          etiqueta={`Ventas (${d.periodo.dias} días)`}
          icono={<Receipt className="size-4" />}
          valor={moneda(ven.total)}
          detalle={
            <>
              {entero(ven.numero_ventas)} ventas · ticket {moneda(ven.ticket_promedio)}
              <br />
              <Variacion valor={ven.variacion_pct} />
            </>
          }
        />
      )}
      {inv && (
        <Stat
          etiqueta="Valor del inventario"
          icono={<Boxes className="size-4" />}
          valor={moneda(inv.valor_inventario)}
          detalle={
            inv.valor_completo ? (
              `${entero(inv.unidades_totales)} unidades en ${entero(inv.referencias_con_existencias)} referencias`
            ) : (
              <span className="text-warning">
                Incompleto: {entero(inv.productos_sin_costo)} {inv.productos_sin_costo === 1 ? "producto" : "productos"} con existencias sin costo registrado
              </span>
            )
          }
        />
      )}
      {d.alertas && (
        <Stat
          etiqueta="Alertas activas"
          icono={<AlertTriangle className="size-4" />}
          tono={criticas > 0 ? "danger" : d.alertas.total > 0 ? "warning" : "success"}
          valor={entero(d.alertas.total)}
          detalle={criticas > 0 ? `${entero(criticas)} críticas` : d.alertas.total > 0 ? "Ninguna crítica" : "Todo en orden"}
        />
      )}
      {inv && (
        <Stat
          etiqueta="Estado del stock"
          icono={<CheckCircle2 className="size-4" />}
          valor={
            <span className="flex flex-wrap items-baseline gap-x-3 text-lg">
              <span className="text-danger">{entero(inv.agotados)} <span className="text-xs font-normal text-ink-faint">agotados</span></span>
              <span className="text-warning">{entero(inv.bajos)} <span className="text-xs font-normal text-ink-faint">bajos</span></span>
              <span className="text-accent-light">{entero(inv.excesivos)} <span className="text-xs font-normal text-ink-faint">excesivos</span></span>
            </span>
          }
          detalle="Combinaciones producto–sede fuera de rango"
        />
      )}
    </div>
  );
}

function Pendientes({ d }: { d: Dashboard }) {
  const { tiene } = useAuth();
  const items = [
    d.recomendaciones_pendientes !== null && { a: "/recomendaciones?estado=pendiente", icono: Sparkles, n: d.recomendaciones_pendientes, texto: "recomendaciones por revisar", visible: tiene("recomendaciones.ver") },
    d.traslados_pendientes !== null && { a: "/traslados", icono: Truck, n: d.traslados_pendientes, texto: "traslados en curso", visible: tiene("traslados.ver") },
  ].filter(Boolean) as { a: string; icono: typeof Sparkles; n: number; texto: string; visible: boolean }[];
  if (items.length === 0) return null;
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {items.map((i) => (
        <Link key={i.a} to={i.a} className="group flex items-center justify-between gap-4 rounded-(--radius-panel) border border-line bg-surface px-5 py-4 transition hover:border-line-strong hover:bg-surface-2">
          <span className="flex items-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-xl bg-accent-dim text-accent-light">
              <i.icono className="size-5" aria-hidden />
            </span>
            <span>
              <span className="tabular block font-display text-xl font-semibold text-ink">{entero(i.n)}</span>
              <span className="text-[13px] text-ink-dim">{i.texto}</span>
            </span>
          </span>
          <ArrowRight className="size-4 text-ink-faint transition group-hover:translate-x-0.5 group-hover:text-ink" aria-hidden />
        </Link>
      ))}
    </div>
  );
}

function VentasDiarias({ d }: { d: Dashboard }) {
  const ven = d.ventas!;
  const puntos = ven.serie_diaria.map((p) => ({ t: parseDia(p.fecha).getTime(), y: p.total, parcial: p.fecha === d.periodo.hasta }));
  const hayVentas = ven.serie_diaria.some((p) => p.total > 0);
  return (
    <Card className="xl:col-span-2">
      <CardHeader titulo="Ventas por día" descripcion={`${entero(ven.unidades)} unidades vendidas · ${entero(ven.anuladas)} anuladas no se cuentan`} />
      <div className="p-5">
        {hayVentas ? (
          <GraficoLineas capas={[{ nombre: "Ventas", puntos, color: "#4C6FFF", area: true }]} formatoY={monedaCompacta} descripcion={`Ventas diarias de los últimos ${d.periodo.dias} días`} />
        ) : (
          <EstadoVacio titulo="Sin ventas en el período" descripcion="Cuando se registren ventas aparecerán aquí día a día." />
        )}
      </div>
    </Card>
  );
}

function TopProductos({ d }: { d: Dashboard }) {
  const top = d.ventas!.top_productos;
  return (
    <Card>
      <CardHeader titulo="Más vendidos" descripcion="Por unidades en el período" />
      <div className="p-5">
        {top.length === 0 ? (
          <p className="py-6 text-center text-sm text-ink-faint">Aún no hay ventas registradas.</p>
        ) : (
          <BarrasHorizontales
            descripcion="Productos más vendidos"
            formato={(n) => `${entero(n)} u.`}
            datos={top.map((t) => ({ clave: String(t.producto_id), etiqueta: t.nombre, valor: t.unidades, detalle: `${t.codigo} · ${moneda(t.total)}` }))}
          />
        )}
      </div>
    </Card>
  );
}

function PorSede({ d }: { d: Dashboard }) {
  const sedes = d.por_sede ?? [];
  if (sedes.length === 0) return null;
  return (
    <Card>
      <CardHeader titulo="Inventario por sede" descripcion="Unidades y valor a costo" />
      <div className="p-5">
        <BarrasHorizontales
          descripcion="Valor de inventario por sede"
          formato={monedaCompacta}
          datos={sedes.map((s) => ({
            clave: String(s.sede_id),
            etiqueta: s.sede,
            valor: s.valor,
            detalle: `${entero(s.unidades)} unidades · ${s.alertas > 0 ? `${s.alertas} ${s.alertas === 1 ? "alerta" : "alertas"}` : "sin alertas"}`,
            tono: s.alertas > 0 ? "warning" : "accent",
          }))}
        />
      </div>
    </Card>
  );
}

function AlertasPrincipales({ d }: { d: Dashboard }) {
  const a = d.alertas!;
  return (
    <Card>
      <CardHeader titulo="Alertas prioritarias" accion={<Link to="/alertas" className="text-[13px] font-semibold text-accent-light hover:underline">Ver todas</Link>} />
      {a.principales.length === 0 ? (
        <EstadoVacio titulo="Sin alertas activas" descripcion="El inventario está dentro de los rangos configurados." icono={<CheckCircle2 className="size-5 text-success" aria-hidden />} />
      ) : (
        <ul className="divide-y divide-line">
          {a.principales.map((x) => {
            const p = estado(PRIORIDAD, x.prioridad);
            return (
              <li key={x.id} className="flex items-start gap-3 px-5 py-3.5">
                <Badge tono={p.tono} className="mt-0.5">{p.etiqueta}</Badge>
                <div className="min-w-0">
                  <p className="text-sm text-ink">{x.mensaje}</p>
                  <p className="mt-0.5 text-xs text-ink-faint">
                    {etiqueta(TIPO_ALERTA, x.tipo)} · {x.sede}
                  </p>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}

function ResumenPrediccion({ d }: { d: Dashboard }) {
  const { tiene } = useAuth();
  const p = d.prediccion;
  return (
    <Card>
      <CardHeader titulo="Predicción de demanda" accion={<Link to="/predicciones" className="text-[13px] font-semibold text-accent-light hover:underline">Abrir</Link>} />
      {!p ? (
        <EstadoVacio
          titulo="Aún no hay predicciones"
          descripcion="Genere la primera predicción para ver la demanda estimada y recibir recomendaciones de reabastecimiento."
          accion={tiene("prediccion.ejecutar") ? <Link to="/predicciones" className="text-sm font-semibold text-accent-light hover:underline">Ir a predicciones</Link> : undefined}
        />
      ) : (
        <dl className="grid grid-cols-2 gap-x-6 gap-y-4 p-5 text-sm">
          <div>
            <dt className="text-xs text-ink-faint">Última ejecución</dt>
            <dd className="mt-0.5 text-ink">{hace(p.finalizada_en)}</dd>
          </div>
          <div>
            <dt className="text-xs text-ink-faint">Horizonte</dt>
            <dd className="mt-0.5 text-ink">{p.horizonte_dias} días</dd>
          </div>
          <div>
            <dt className="text-xs text-ink-faint">Series con pronóstico</dt>
            <dd className="tabular mt-0.5 text-ink">{entero(p.series_con_prediccion)}</dd>
          </div>
          <div>
            <dt className="text-xs text-ink-faint">Omitidas por datos insuficientes</dt>
            <dd className="tabular mt-0.5 text-ink">{entero(p.series_omitidas)}</dd>
          </div>
          <div>
            <dt className="text-xs text-ink-faint">Error global (WAPE)</dt>
            <dd className="tabular mt-0.5 text-ink">{p.wape_global === null ? "—" : porcentaje(p.wape_global * 100)}</dd>
          </div>
          <div>
            <dt className="text-xs text-ink-faint">Mejora frente a la línea base</dt>
            <dd className="tabular mt-0.5 text-ink">{p.mejora_vs_linea_base_pct === null ? "—" : porcentaje(p.mejora_vs_linea_base_pct)}</dd>
          </div>
        </dl>
      )}
    </Card>
  );
}

function MovimientosRecientes({ filas }: { filas: Movimiento[] }) {
  return (
    <Card>
      <CardHeader titulo="Movimientos recientes" accion={<Link to="/movimientos" className="text-[13px] font-semibold text-accent-light hover:underline">Ver historial</Link>} />
      <Tabla
        descripcion="Últimos movimientos de inventario"
        idDe={(m) => m.id}
        filas={filas}
        vacio={{ titulo: "Sin movimientos", descripcion: "Los movimientos de inventario aparecerán aquí." }}
        columnas={[
          { clave: "fecha", encabezado: "Fecha", celda: (m) => <span className="text-ink-dim">{fechaHora(m.fecha)}</span> },
          { clave: "producto", encabezado: "Producto", celda: (m) => <span className="font-medium">{m.producto.nombre}</span> },
          { clave: "sede", encabezado: "Sede", desde: "md", celda: (m) => m.sede.nombre },
          { clave: "tipo", encabezado: "Tipo", desde: "sm", celda: (m) => etiqueta(TIPO_MOVIMIENTO, m.tipo) },
          {
            clave: "delta",
            encabezado: "Variación",
            alinear: "derecha",
            celda: (m) => <span className={`tabular font-semibold ${m.delta >= 0 ? "text-success" : "text-danger"}`}>{m.delta > 0 ? "+" : ""}{entero(m.delta)}</span>,
          },
        ]}
      />
    </Card>
  );
}

function PrimerosPasos({ d }: { d: Dashboard }) {
  const { tiene } = useAuth();
  const pasos = [
    { ok: false, texto: "Cree las categorías de sus productos", a: "/categorias", visible: tiene("categorias.crear") },
    { ok: false, texto: "Registre sus productos", a: "/productos", visible: tiene("productos.crear") },
    { ok: false, texto: "Cree las sedes de su empresa", a: "/sedes", visible: tiene("sedes.crear") },
    { ok: false, texto: "Registre el inventario inicial de cada sede", a: "/inventario", visible: tiene("inventario.entrada") },
  ].filter((p) => p.visible);
  if (!d.inventario || d.inventario.productos_activos > 0 || pasos.length === 0) return null;
  return (
    <Card className="border-accent/30 bg-accent-dim/30">
      <CardHeader titulo="Primeros pasos" descripcion="Todavía no hay productos. Siga esta ruta para empezar a operar." />
      <ol className="flex flex-col gap-1 p-3">
        {pasos.map((p, i) => (
          <li key={p.a}>
            <Link to={p.a} className="flex items-center gap-3 rounded-(--radius-control) px-3 py-2.5 text-sm text-ink transition hover:bg-white/5">
              <span className="flex size-6 items-center justify-center rounded-full bg-accent text-xs font-semibold text-white">{i + 1}</span>
              {p.texto}
              <ArrowRight className="ml-auto size-4 text-ink-faint" aria-hidden />
            </Link>
          </li>
        ))}
      </ol>
    </Card>
  );
}

export default function PanelPage() {
  const sesion = useSesion();
  const { tiene } = useAuth();
  const [sedeId, setSedeId] = useState("");
  const [dias, setDias] = useState(30);
  const sedes = useSedes();
  const puedeElegirSede = sesion.rol.alcance === "empresa" && tiene("sedes.ver");

  const consulta = useQuery({
    queryKey: ["dashboard", sedeId, dias],
    queryFn: () => apiDashboard.obtener(aNumero(sedeId), dias),
    placeholderData: keepPreviousData,
    refetchInterval: 120_000,
  });
  const d = consulta.data;

  return (
    <>
      <EncabezadoPagina
        titulo="Panel de control"
        descripcion={`${sesion.empresa_nombre}${sesion.sede ? ` · ${sesion.sede.nombre}` : ""}. Todas las cifras se calculan en tiempo real con los datos registrados.`}
        acciones={
          <>
            {puedeElegirSede && (
              <FiltroSelect etiqueta="Sede" value={sedeId} onChange={(e) => setSedeId(e.target.value)}>
                <option value="">Todas las sedes</option>
                {sedes.data?.map((s) => (
                  <option key={s.id} value={s.id}>{s.nombre}</option>
                ))}
              </FiltroSelect>
            )}
            <FiltroSelect etiqueta="Período" value={dias} onChange={(e) => setDias(Number(e.target.value))}>
              {PERIODOS.map((p) => (
                <option key={p.dias} value={p.dias}>{p.etiqueta}</option>
              ))}
            </FiltroSelect>
            <Button variante="secondary" tamano="sm" onClick={() => consulta.refetch()} cargando={consulta.isFetching} icono={<RefreshCw className="size-4" aria-hidden />}>
              Actualizar
            </Button>
          </>
        }
      />

      {consulta.isError && !d && <Card><EstadoError error={consulta.error} onReintentar={() => consulta.refetch()} /></Card>}

      {!d && consulta.isPending && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" role="status" aria-label="Cargando el panel">
          {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-32" />)}
        </div>
      )}

      {d && (
        <div className="flex flex-col gap-6">
          <PrimerosPasos d={d} />
          <Tarjetas d={d} />
          <Pendientes d={d} />
          <div className="grid gap-6 xl:grid-cols-3">
            {d.ventas && <VentasDiarias d={d} />}
            {d.ventas && <TopProductos d={d} />}
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            {d.alertas && <AlertasPrincipales d={d} />}
            <PorSede d={d} />
          </div>
          <div className="grid gap-6 xl:grid-cols-3">
            {(d.prediccion !== null || tiene("prediccion.ver")) && <ResumenPrediccion d={d} />}
            {d.movimientos_recientes && (
              <div className="min-w-0 xl:col-span-2">
                <MovimientosRecientes filas={d.movimientos_recientes} />
              </div>
            )}
          </div>
          <p className="text-xs text-ink-faint">
            Datos generados {hace(d.generado_en)} · período del {fecha(d.periodo.desde)} al {fecha(d.periodo.hasta)}
          </p>
        </div>
      )}
    </>
  );
}
