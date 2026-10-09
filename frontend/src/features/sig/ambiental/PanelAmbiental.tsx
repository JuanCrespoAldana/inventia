import { useId, useState, type ReactNode } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Bike, CalendarDays, Leaf, Sigma } from "lucide-react";
import { apiAmbiental } from "@/api/sig";
import { useAuth } from "@/auth/AuthContext";
import { BarrasHorizontales } from "@/components/charts/Barras";
import { Columnas } from "@/components/charts/Columnas";
import { Aviso } from "@/components/ui/Aviso";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, Stat } from "@/components/ui/Card";
import { EstadoError, EstadoVacio } from "@/components/ui/EstadoVacio";
import { FiltroSelect } from "@/components/ui/Field";
import { PanelCargando } from "@/components/ui/Skeleton";
import { useSedes } from "@/hooks/useCatalogos";
import { aNumero } from "@/hooks/useFiltros";
import { etiqueta, TIPO_VEHICULO } from "@/lib/etiquetas";
import { decimal, entero, pluralizar } from "@/lib/format";
import type { CifrasAmbientales, ResumenAmbiental } from "@/types/api";
import { formatoCo2, formatoEjeCo2 } from "./calculos";

const MESES_CORTOS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
const MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];

type Parametrizacion = ResumenAmbiental["parametrizacion"];

/** Sin parámetros no existe estimación alguna: se muestra «pendiente», nunca un cero que parezca un resultado. */
function sinEstimacion(p: Parametrizacion): boolean {
  return p.estado === "pendiente" || p.estado === "sin_categorias";
}

const kg = (n: number) => formatoCo2(n, decimal);
const kgEje = (n: number) => formatoEjeCo2(n, decimal);

function AvisoParametrizacion({ p, puedeConfigurar, irAConfiguracion }: { p: Parametrizacion; puedeConfigurar: boolean; irAConfiguracion: () => void }) {
  const tipo = p.estado === "completa" ? "exito" : "aviso";
  const titulo = { completa: "Parametrización completa", parcial: "Parametrización parcial", pendiente: "Pendiente de parametrización", sin_categorias: "Pendiente de parametrización" }[p.estado];
  return (
    <Aviso tipo={tipo} titulo={titulo}>
      <p>{p.mensaje}</p>
      {p.estado !== "completa" &&
        (puedeConfigurar ? (
          <Button className="mt-2" variante="secondary" tamano="sm" onClick={irAConfiguracion}>
            Ir a la configuración
          </Button>
        ) : (
          <p className="mt-1 text-ink-faint">Solicita a una persona administradora que configure los parámetros.</p>
        ))}
    </Aviso>
  );
}

function Seccion({ titulo, insignia, descripcion, children }: { titulo: string; insignia: ReactNode; descripcion: string; children: ReactNode }) {
  const id = useId();
  return (
    <section aria-labelledby={id}>
      <div className="mb-3">
        <h2 id={id} className="flex flex-wrap items-center gap-2 font-display text-base font-semibold text-ink">
          {titulo} {insignia}
        </h2>
        <p className="mt-0.5 text-[13px] text-ink-faint">{descripcion}</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">{children}</div>
    </section>
  );
}

function StatCo2({ etiquetaStat, cifras, p, icono }: { etiquetaStat: string; cifras: CifrasAmbientales; p: Parametrizacion; icono: ReactNode }) {
  if (sinEstimacion(p)) {
    return (
      <Stat
        etiqueta={etiquetaStat}
        icono={icono}
        tono="warning"
        valor={<span className="text-base leading-snug">Pendiente de parametrización</span>}
        detalle={cifras.unidades > 0 ? `${pluralizar(cifras.unidades, "vehículo", "vehículos")} sin estimar` : "Sin cifras: faltan los parámetros"}
      />
    );
  }
  return (
    <Stat
      etiqueta={etiquetaStat}
      icono={icono}
      tono="success"
      valor={kg(cifras.co2_estimado_kg)}
      detalle={cifras.unidades_sin_parametrizar > 0 ? `No incluye ${pluralizar(cifras.unidades_sin_parametrizar, "vehículo sin parametrizar", "vehículos sin parametrizar")}` : "Estimación con los parámetros configurados"}
    />
  );
}

function Graficos({ r }: { r: ResumenAmbiental }) {
  const sinCo2 = sinEstimacion(r.parametrizacion);
  const vehiculosMes = r.meses.map((m) => ({ clave: String(m.mes), etiqueta: MESES_CORTOS[m.mes - 1], valor: m.unidades, descripcion: `${MESES[m.mes - 1]}: ${pluralizar(m.unidades, "vehículo", "vehículos")}` }));
  const co2Mes = r.meses.map((m) => ({ clave: String(m.mes), etiqueta: MESES_CORTOS[m.mes - 1], valor: m.co2_estimado_kg, descripcion: `${MESES[m.mes - 1]}: ${kg(m.co2_estimado_kg)} de CO₂ evitado (estimado)` }));
  const vehiculosAnio = r.anios.map((a) => ({ clave: String(a.anio), etiqueta: String(a.anio), valor: a.unidades, descripcion: `${a.anio}: ${pluralizar(a.unidades, "vehículo", "vehículos")}` }));
  const co2Anio = r.anios.map((a) => ({ clave: String(a.anio), etiqueta: String(a.anio), valor: a.co2_estimado_kg, descripcion: `${a.anio}: ${kg(a.co2_estimado_kg)} de CO₂ evitado (estimado)` }));
  const pendienteGrafico = (
    <EstadoVacio titulo="Pendiente de parametrización" descripcion="Sin factor de la red ni parámetros del vehículo no se puede estimar el CO₂. Los vehículos vendidos sí se cuentan." icono={<Leaf className="size-5" aria-hidden />} />
  );

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader titulo="Vehículos vendidos por mes" descripcion={`Año ${r.anio} · dato real`} />
        <div className="p-5">
          <Columnas datos={vehiculosMes} formato={(n) => entero(n)} descripcion={`Vehículos vendidos por mes en ${r.anio}`} />
        </div>
      </Card>
      <Card>
        <CardHeader titulo="CO₂ evitado por mes" descripcion={`Año ${r.anio} · estimación`} />
        {sinCo2 ? pendienteGrafico : (
          <div className="p-5">
            <Columnas datos={co2Mes} formato={kg} formatoEje={kgEje} tono="success" descripcion={`CO₂ evitado estimado por mes en ${r.anio}`} />
          </div>
        )}
      </Card>
      <Card>
        <CardHeader titulo="Vehículos vendidos por año" descripcion="Dato real" />
        <div className="p-5">
          <Columnas datos={vehiculosAnio} formato={(n) => entero(n)} descripcion="Vehículos vendidos por año" />
        </div>
      </Card>
      <Card>
        <CardHeader titulo="CO₂ evitado por año" descripcion="Estimación" />
        {sinCo2 ? pendienteGrafico : (
          <div className="p-5">
            <Columnas datos={co2Anio} formato={kg} formatoEje={kgEje} tono="success" descripcion="CO₂ evitado estimado por año" />
          </div>
        )}
      </Card>
      {r.por_tipo.length > 0 && (
        <Card className="lg:col-span-2">
          <CardHeader titulo="Por tipo de vehículo" descripcion={`Año ${r.anio} · unidades vendidas${sinCo2 ? "" : " y CO₂ estimado"}`} />
          <div className="p-5">
            <BarrasHorizontales
              descripcion={`Vehículos vendidos por tipo en ${r.anio}`}
              formato={(n) => pluralizar(n, "vehículo", "vehículos")}
              datos={r.por_tipo.map((t) => ({
                clave: t.tipo_vehiculo,
                etiqueta: etiqueta(TIPO_VEHICULO, t.tipo_vehiculo),
                valor: t.unidades,
                detalle: sinCo2 ? undefined : t.unidades_sin_parametrizar === t.unidades ? "CO₂: pendiente de parametrización" : `CO₂ evitado (estimado): ${kg(t.co2_estimado_kg)}`,
              }))}
            />
          </div>
        </Card>
      )}
    </div>
  );
}

export function PanelAmbiental({ puedeConfigurar, irAConfiguracion }: { puedeConfigurar: boolean; irAConfiguracion: () => void }) {
  const { sesion } = useAuth();
  const sedes = useSedes(false);
  const [anio, setAnio] = useState<number | "">("");
  const [sede, setSede] = useState("");
  const verSedes = sesion?.rol.alcance === "empresa";

  const consulta = useQuery({
    queryKey: ["ambiental", "resumen", anio, sede],
    queryFn: () => apiAmbiental.resumen(anio === "" ? undefined : anio, aNumero(sede)),
    placeholderData: keepPreviousData,
  });
  const r = consulta.data;

  if (!r) {
    return consulta.isError ? (
      <Card>
        <EstadoError error={consulta.error} onReintentar={() => consulta.refetch()} />
      </Card>
    ) : (
      <PanelCargando etiqueta="Cargando indicadores…" />
    );
  }

  const p = r.parametrizacion;
  return (
    <div className="flex flex-col gap-6" aria-busy={consulta.isFetching || undefined}>
      <AvisoParametrizacion p={p} puedeConfigurar={puedeConfigurar} irAConfiguracion={irAConfiguracion} />

      <div className="flex flex-wrap items-center gap-2.5">
        <FiltroSelect etiqueta="Año del panel" className="min-w-28" value={String(r.anio)} onChange={(e) => setAnio(Number(e.target.value))}>
          {r.anios_disponibles.map((a) => (
            <option key={a} value={a}>
              Año {a}
            </option>
          ))}
        </FiltroSelect>
        {verSedes && (
          <FiltroSelect etiqueta="Sede" value={sede} onChange={(e) => setSede(e.target.value)}>
            <option value="">Todas las sedes</option>
            {sedes.data?.map((s) => (
              <option key={s.id} value={s.id}>
                {s.nombre}
              </option>
            ))}
          </FiltroSelect>
        )}
        <p className="text-xs text-ink-faint">El año y la sede se aplican a las cifras del año y a los gráficos.</p>
      </div>

      <Seccion
        titulo="Vehículos vendidos"
        insignia={<Badge tono="success">Dato real</Badge>}
        descripcion="Unidades de ventas confirmadas en categorías marcadas como vehículo. Las ventas anuladas no cuentan."
      >
        <Stat etiqueta="Mes actual" valor={entero(r.mes_actual.unidades)} icono={<CalendarDays className="size-4" />} detalle="Unidades vendidas este mes" />
        <Stat etiqueta={`Año ${r.anio}`} valor={entero(r.anio_seleccionado.unidades)} icono={<Bike className="size-4" />} detalle="Unidades vendidas en el año" />
        <Stat etiqueta="Acumulado" valor={entero(r.acumulado.unidades)} icono={<Sigma className="size-4" />} detalle="Desde el primer registro" />
      </Seccion>

      <Seccion
        titulo="CO₂ evitado"
        insignia={<Badge tono="warning">Estimación</Badge>}
        descripcion="No es una medición: es un cálculo con los parámetros que configura la administración (consulta la pestaña Metodología)."
      >
        <StatCo2 etiquetaStat="Mes actual" cifras={r.mes_actual} p={p} icono={<CalendarDays className="size-4" />} />
        <StatCo2 etiquetaStat={`Año ${r.anio}`} cifras={r.anio_seleccionado} p={p} icono={<Leaf className="size-4" />} />
        <StatCo2 etiquetaStat="Acumulado" cifras={r.acumulado} p={p} icono={<Sigma className="size-4" />} />
      </Seccion>

      {r.acumulado.unidades === 0 ? (
        <Card>
          <EstadoVacio
            titulo="Todavía no hay vehículos contabilizados"
            descripcion={
              p.estado === "sin_categorias"
                ? "Marca como vehículo las categorías correspondientes en la pestaña Configuración; las ventas anteriores se incorporan y las nuevas se cuentan solas."
                : "Cada vez que se confirme una venta de un vehículo aparecerá aquí, sin que tengas que registrar nada más."
            }
            icono={<Leaf className="size-5" aria-hidden />}
          />
        </Card>
      ) : (
        <Graficos r={r} />
      )}
    </div>
  );
}
