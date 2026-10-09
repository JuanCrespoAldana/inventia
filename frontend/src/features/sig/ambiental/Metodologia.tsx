import { useQuery } from "@tanstack/react-query";
import { apiAmbiental } from "@/api/sig";
import { Aviso } from "@/components/ui/Aviso";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { Tabla } from "@/components/ui/DataTable";
import { EstadoError } from "@/components/ui/EstadoVacio";
import { PanelCargando } from "@/components/ui/Skeleton";
import { etiqueta, PROPULSION, TIPO_VEHICULO } from "@/lib/etiquetas";
import { decimal, entero } from "@/lib/format";
import type { CategoriaAmbiental } from "@/types/api";
import { co2PorUnidadKg, formatoCo2 } from "./calculos";

/** Ejemplo con números redondos para entender la fórmula. NO son datos ni parámetros de la empresa. */
const EJEMPLO = { distanciaAnualKm: 2000, horizonteAnios: 1, consumoKwh100km: 1.5, emisionReferenciaGco2Km: 150, factorRed: 0.22 };

function Termino({ simbolo, children }: { simbolo: string; children: React.ReactNode }) {
  return (
    <li className="flex flex-col gap-0.5 sm:flex-row sm:gap-3">
      <code className="shrink-0 font-mono text-[13px] text-accent-light sm:w-48">{simbolo}</code>
      <span>{children}</span>
    </li>
  );
}

function ParametrosVigentes() {
  const configuracion = useQuery({ queryKey: ["ambiental", "configuracion"], queryFn: apiAmbiental.configuracion });
  if (configuracion.isPending) return <PanelCargando etiqueta="Cargando los parámetros vigentes…" />;
  if (configuracion.isError)
    return (
      <Card>
        <EstadoError error={configuracion.error} onReintentar={() => configuracion.refetch()} />
      </Card>
    );
  const { factor_red: factor, categorias } = configuracion.data;
  const vehiculos = categorias.filter((c) => c.es_vehiculo);

  return (
    <Card>
      <CardHeader titulo="Parámetros vigentes" descripcion="Los valores que se están usando hoy para las ventas nuevas. Cada registro conserva los que se usaron al calcularlo." />
      <div className="flex flex-col gap-2 border-b border-line px-5 py-4 text-sm">
        <p className="font-semibold text-ink">Factor de emisión de la red eléctrica</p>
        {factor.valor === null ? (
          <p className="text-ink-dim">
            <Badge tono="warning">Pendiente de parametrización</Badge> <span className="ml-1">Todavía no se ha definido; sin este dato no se estima el CO₂.</span>
          </p>
        ) : (
          <p className="text-ink-dim">
            <span className="tabular font-semibold text-ink">{decimal(factor.valor, 3)} kg CO₂e/kWh</span> · año {factor.anio} · <span className="text-ink-faint">{factor.fuente}</span>
          </p>
        )}
      </div>
      <Tabla<CategoriaAmbiental>
        descripcion="Parámetros de cálculo por categoría de vehículo"
        idDe={(c) => c.categoria_id}
        filas={vehiculos}
        vacio={{ titulo: "Aún no hay categorías de vehículos", descripcion: "Una persona administradora debe marcar qué categorías son vehículos para que se cuenten las ventas." }}
        columnas={[
          {
            clave: "c",
            encabezado: "Categoría",
            celda: (c) => (
              <div>
                <p className="font-medium">{c.categoria_nombre}</p>
                <p className="text-xs text-ink-faint">
                  {etiqueta(TIPO_VEHICULO, c.tipo_vehiculo)} · {etiqueta(PROPULSION, c.propulsion)}
                  {!c.activa && " · inactiva"}
                </p>
              </div>
            ),
          },
          { clave: "d", encabezado: "Recorrido anual", alinear: "derecha", desde: "sm", celda: (c) => <Valor n={c.distancia_anual_km} unidad="km" /> },
          { clave: "h", encabezado: "Horizonte", alinear: "derecha", desde: "lg", celda: (c) => <span className="tabular text-ink-dim">{entero(c.horizonte_anios)} {c.horizonte_anios === 1 ? "año" : "años"}</span> },
          { clave: "k", encabezado: "Consumo", alinear: "derecha", desde: "md", celda: (c) => <Valor n={c.consumo_kwh_100km} unidad="kWh/100 km" /> },
          { clave: "e", encabezado: "Emisión de referencia", alinear: "derecha", desde: "md", celda: (c) => <Valor n={c.emision_referencia_gco2_km} unidad="g CO₂/km" /> },
          {
            clave: "r",
            encabezado: "CO₂ por unidad",
            alinear: "derecha",
            celda: (c) =>
              c.co2_por_unidad_kg === null || c.co2_por_unidad_kg === undefined ? <Badge tono="warning">Pendiente</Badge> : <span className="tabular font-semibold">{formatoCo2(c.co2_por_unidad_kg, decimal)}</span>,
          },
          { clave: "f", encabezado: "Fuente", desde: "lg", className: "max-w-64", celda: (c) => <span className="line-clamp-2 text-xs text-ink-faint">{c.fuente ?? "—"}</span> },
        ]}
      />
    </Card>
  );
}

function Valor({ n, unidad }: { n: number | null | undefined; unidad: string }) {
  if (n === null || n === undefined) return <span className="text-ink-faint">—</span>;
  return (
    <span className="tabular text-ink-dim">
      {decimal(n, Number.isInteger(n) ? 0 : 2)} <span className="text-xs text-ink-faint">{unidad}</span>
    </span>
  );
}

export function Metodologia() {
  const ejemplo = co2PorUnidadKg(EJEMPLO);
  const referenciaKg = (EJEMPLO.distanciaAnualKm * EJEMPLO.horizonteAnios * EJEMPLO.emisionReferenciaGco2Km) / 1000;
  const electricoKg = EJEMPLO.distanciaAnualKm * EJEMPLO.horizonteAnios * (EJEMPLO.consumoKwh100km / 100) * EJEMPLO.factorRed;

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader titulo="Qué es real y qué es estimado" />
          <div className="flex flex-col gap-4 p-5 text-sm text-ink-dim">
            <div>
              <p className="mb-1 flex items-center gap-2 font-semibold text-ink">
                Vehículos vendidos <Badge tono="success">Dato real</Badge>
              </p>
              <p>Es el número de unidades de ventas confirmadas, de las categorías que la administración marcó como vehículo. Siempre se cuenta, haya o no parámetros configurados.</p>
            </div>
            <div>
              <p className="mb-1 flex items-center gap-2 font-semibold text-ink">
                CO₂ evitado <Badge tono="warning">Estimación</Badge>
              </p>
              <p>
                Es un cálculo, no una medición: compara lo que emitiría recorrer cierta distancia con un vehículo de combustión de referencia frente a lo que genera la electricidad que consume el vehículo eléctrico. Solo existe si
                se definen el factor de la red y los parámetros del vehículo; mientras tanto el panel muestra «pendiente de parametrización» y nunca una cifra inventada.
              </p>
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader titulo="Fórmula" descripcion="Se aplica por cada unidad vendida y la calcula el servidor." />
          <div className="flex flex-col gap-4 p-5 text-sm text-ink-dim">
            <pre className="overflow-x-auto rounded-(--radius-control) border border-line bg-surface-2 px-4 py-3 font-mono text-[13px] leading-relaxed text-ink">
              {`CO₂ evitado (kg) = recorrido_anual × horizonte
                 × ( emisión_ref / 1000
                   − consumo / 100 × FE_red )`}
            </pre>
            <ul className="flex flex-col gap-2">
              <Termino simbolo="recorrido_anual">Kilómetros que se estima recorre el vehículo en un año (km).</Termino>
              <Termino simbolo="horizonte">Años de uso que se consideran (por defecto 1).</Termino>
              <Termino simbolo="emisión_ref">Emisión del vehículo de combustión de referencia (g CO₂ por km).</Termino>
              <Termino simbolo="consumo">Energía que gasta el vehículo eléctrico (kWh por cada 100 km).</Termino>
              <Termino simbolo="FE_red">Factor de emisión de la red eléctrica (kg CO₂e por kWh).</Termino>
            </ul>
          </div>
        </Card>
      </div>

      <Card>
        <CardHeader titulo="Ejemplo para entender el cálculo" descripcion="Números redondos solo para ilustrar. No son datos ni parámetros de la empresa." />
        <div className="grid gap-4 p-5 text-sm text-ink-dim md:grid-cols-3">
          <div>
            <p className="font-semibold text-ink">Si un vehículo de combustión de referencia emite…</p>
            <p className="mt-1">
              {entero(EJEMPLO.emisionReferenciaGco2Km)} g/km durante {entero(EJEMPLO.distanciaAnualKm)} km: <span className="tabular font-semibold text-ink">{formatoCo2(referenciaKg, decimal)}</span>
            </p>
          </div>
          <div>
            <p className="font-semibold text-ink">…y el eléctrico consume y carga con una red que emite…</p>
            <p className="mt-1">
              {decimal(EJEMPLO.consumoKwh100km, 1)} kWh/100 km con {decimal(EJEMPLO.factorRed, 2)} kg/kWh: <span className="tabular font-semibold text-ink">{formatoCo2(electricoKg, decimal)}</span>
            </p>
          </div>
          <div>
            <p className="font-semibold text-ink">…el CO₂ evitado por unidad es la diferencia</p>
            <p className="mt-1">
              <span className="tabular font-semibold text-success">{ejemplo === null ? "—" : formatoCo2(ejemplo, decimal)}</span> por vehículo y por año de uso.
            </p>
          </div>
        </div>
      </Card>

      <ParametrosVigentes />

      <Card>
        <CardHeader titulo="Reglas de conteo" />
        <ul className="flex list-disc flex-col gap-2 p-5 pl-9 text-sm text-ink-dim">
          <li>Solo cuentan las ventas confirmadas, y solo de las categorías que la administración marcó como vehículo.</li>
          <li>Cada línea de venta se cuenta una sola vez, aunque se recargue la pantalla o se vuelvan a ejecutar procesos.</li>
          <li>Al anular una venta, sus registros dejan de sumar en las cifras y se conservan en el historial como «Anulado».</li>
          <li>Cada registro guarda los parámetros que se usaron al calcularlo: modificar la configuración después no altera cifras ya calculadas.</li>
          <li>Las ventas que ocurrieron antes de configurar los parámetros se cuentan como vehículos y, cuando se configuran, se calcula su CO₂.</li>
        </ul>
      </Card>

      <Aviso tipo="info" titulo="Sobre los valores de referencia">
        El factor de emisión de la red eléctrica y las emisiones del vehículo de combustión de referencia deben tomarse de fuentes oficiales o técnicas y quedar documentados al configurarlos. La estimación depende de esas
        hipótesis y no sustituye una medición ni una huella de carbono certificada.
      </Aviso>
    </div>
  );
}
