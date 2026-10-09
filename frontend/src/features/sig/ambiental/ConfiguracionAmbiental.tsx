import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Calculator, Pencil, RefreshCw } from "lucide-react";
import { apiAmbiental } from "@/api/sig";
import { Aviso } from "@/components/ui/Aviso";
import { Badge } from "@/components/ui/Badge";
import { Button, IconButton } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Tabla } from "@/components/ui/DataTable";
import { EstadoError } from "@/components/ui/EstadoVacio";
import { Casilla, Input, Select, Textarea } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";
import { PanelCargando } from "@/components/ui/Skeleton";
import { useMutacion } from "@/hooks/useMutacion";
import { mensajeDeError } from "@/lib/errors";
import { etiqueta, PROPULSION, TIPO_VEHICULO } from "@/lib/etiquetas";
import { decimal, entero } from "@/lib/format";
import type { CategoriaAmbiental, CategoriaAmbientalActualizar, ResultadoSincronizacion } from "@/types/api";
import { aNumeroDecimal, co2PorUnidadKg, emisionDesdeConsumoCombustible, FACTOR_GASOLINA_KG_POR_LITRO, formatoCo2 } from "./calculos";

const INVALIDAR = [["ambiental"]];

/** Valores publicados que se ofrecen como PUNTO DE PARTIDA. No se guardan solos: la administración los revisa y los confirma. */
const REFERENCIA_FACTOR_RED = {
  valor: "0,220",
  anio: "2024",
  fuente: "UPME, factor de emisión del Sistema Interconectado Nacional (SIN) para 2024: 0,220 kg CO₂eq/kWh (Resolución UPME 000085 de 2026). Verificar la cifra vigente en www.upme.gov.co.",
};

function mensajeSincronizacion(r: ResultadoSincronizacion): string {
  const partes = [
    r.incorporados > 0 ? `${entero(r.incorporados)} ${r.incorporados === 1 ? "línea de venta anterior incorporada" : "líneas de ventas anteriores incorporadas"}` : "",
    r.calculados > 0 ? `${entero(r.calculados)} ${r.calculados === 1 ? "registro calculado" : "registros calculados"}` : "",
  ].filter(Boolean);
  return partes.length ? `Configuración guardada: ${partes.join(" y ")}.` : "Configuración guardada.";
}

/* ------------------------------------------------------------------------------ factor de la red */

function FactorRed({ factor }: { factor: { valor: number | null; anio: number | null; fuente: string | null } }) {
  const [valor, setValor] = useState(factor.valor !== null ? String(factor.valor).replace(".", ",") : "");
  const [anio, setAnio] = useState(factor.anio !== null ? String(factor.anio) : "");
  const [fuente, setFuente] = useState(factor.fuente ?? "");
  const [error, setError] = useState<string | null>(null);

  const numero = aNumeroDecimal(valor);
  const errores = {
    valor: numero !== null && numero > 0 && numero <= 5 ? null : "Escribe un valor mayor que 0 y hasta 5 (kg CO₂e por kWh)",
    anio: /^\d{4}$/.test(anio) && Number(anio) >= 2000 && Number(anio) <= 2100 ? null : "Escribe un año de 4 cifras",
    fuente: fuente.trim().length >= 5 ? null : "Documenta la fuente (mínimo 5 caracteres)",
  };
  const valido = !Object.values(errores).some(Boolean);
  const [intento, setIntento] = useState(false);

  const guardar = useMutacion(() => apiAmbiental.guardarFactor({ valor: numero!, anio: Number(anio), fuente: fuente.trim() }), {
    exito: mensajeSincronizacion,
    invalidar: INVALIDAR,
    avisarError: false,
  });

  return (
    <Card>
      <CardHeader titulo="Factor de emisión de la red eléctrica" descripcion="Cuánto CO₂ equivalente genera cada kWh de la red. Se usa para estimar las emisiones de cargar un vehículo eléctrico." />
      <div className="flex flex-col gap-4 p-5">
        {error && <Aviso tipo="error">{error}</Aviso>}
        <div className="grid gap-4 sm:grid-cols-3">
          <Input etiqueta="Valor (kg CO₂e por kWh)" required inputMode="decimal" value={valor} onChange={(e) => setValor(e.target.value)} error={intento ? (errores.valor ?? undefined) : undefined} />
          <Input etiqueta="Año del dato" required inputMode="numeric" value={anio} onChange={(e) => setAnio(e.target.value)} error={intento ? (errores.anio ?? undefined) : undefined} />
        </div>
        <Textarea etiqueta="Fuente" required rows={2} maxLength={500} value={fuente} onChange={(e) => setFuente(e.target.value)} error={intento ? (errores.fuente ?? undefined) : undefined} ayuda="Documento, entidad y fecha de donde sale el valor. Queda registrada junto a cada cálculo." />
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Button
            variante="ghost"
            tamano="sm"
            onClick={() => {
              setValor(REFERENCIA_FACTOR_RED.valor);
              setAnio(REFERENCIA_FACTOR_RED.anio);
              setFuente(REFERENCIA_FACTOR_RED.fuente);
            }}
          >
            Rellenar con el valor publicado por la UPME
          </Button>
          <Button
            cargando={guardar.isPending}
            onClick={async () => {
              setIntento(true);
              setError(null);
              if (!valido) return;
              try {
                await guardar.mutateAsync();
              } catch (e) {
                setError(mensajeDeError(e));
              }
            }}
          >
            Guardar factor
          </Button>
        </div>
        <p className="text-xs text-ink-faint">El botón solo rellena el formulario como punto de partida: revisa que el dato siga vigente antes de guardar. Cambiar el factor no altera lo ya calculado, solo las ventas nuevas y las que estaban pendientes.</p>
      </div>
    </Card>
  );
}

/* ------------------------------------------------------------------------------ categoría de vehículo */

function FormularioCategoria({ categoria, factorRed, onCerrar }: { categoria: CategoriaAmbiental; factorRed: number | null; onCerrar: () => void }) {
  const texto = (n: number | null | undefined) => (n === null || n === undefined ? "" : String(n).replace(".", ","));
  const [tipo, setTipo] = useState(categoria.tipo_vehiculo ?? "bicicleta_electrica");
  const [propulsion, setPropulsion] = useState(categoria.propulsion ?? "electrica");
  const [distancia, setDistancia] = useState(texto(categoria.distancia_anual_km));
  const [consumo, setConsumo] = useState(texto(categoria.consumo_kwh_100km));
  const [referenciaGramos, setReferenciaGramos] = useState(texto(categoria.emision_referencia_gco2_km));
  const [referenciaNombre, setReferenciaNombre] = useState(categoria.vehiculo_referencia ?? "");
  const [horizonte, setHorizonte] = useState(String(categoria.horizonte_anios || 1));
  const [fuente, setFuente] = useState(categoria.fuente ?? "");
  const [activa, setActiva] = useState(categoria.es_vehiculo ? categoria.activa : true);
  const [litros, setLitros] = useState("");
  const [intento, setIntento] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const nDistancia = aNumeroDecimal(distancia);
  const nConsumo = aNumeroDecimal(consumo);
  const nReferencia = aNumeroDecimal(referenciaGramos);
  const nHorizonte = /^\d+$/.test(horizonte) ? Number(horizonte) : null;
  const completos = nDistancia !== null && nConsumo !== null && nReferencia !== null;
  const algunoVacio = [distancia, consumo, referenciaGramos].some((x) => x.trim() === "");
  const algunoLleno = [distancia, consumo, referenciaGramos].some((x) => x.trim() !== "");

  const errores = {
    distancia: distancia.trim() !== "" && (nDistancia === null || nDistancia <= 0 || nDistancia > 200000) ? "Debe ser mayor que 0 y hasta 200 000 km" : null,
    consumo: consumo.trim() !== "" && (nConsumo === null || nConsumo > 100) ? "Debe estar entre 0 y 100 kWh/100 km" : null,
    referencia: referenciaGramos.trim() !== "" && (nReferencia === null || nReferencia > 2000) ? "Debe estar entre 0 y 2 000 g/km" : null,
    horizonte: nHorizonte !== null && nHorizonte >= 1 && nHorizonte <= 30 ? null : "Escribe un número de años entre 1 y 30",
    fuente: completos && fuente.trim().length < 5 ? "Documenta la fuente de los valores (ficha técnica, estudio o norma)" : null,
  };
  const valido = !Object.values(errores).some(Boolean);

  const vistaPrevia = co2PorUnidadKg({ distanciaAnualKm: nDistancia, horizonteAnios: nHorizonte ?? 1, consumoKwh100km: nConsumo, emisionReferenciaGco2Km: nReferencia, factorRed });
  const nLitros = aNumeroDecimal(litros);

  const guardar = useMutacion(
    () => {
      const cuerpo: CategoriaAmbientalActualizar = {
        tipo_vehiculo: tipo as CategoriaAmbientalActualizar["tipo_vehiculo"],
        propulsion: propulsion as CategoriaAmbientalActualizar["propulsion"],
        distancia_anual_km: nDistancia,
        consumo_kwh_100km: nConsumo,
        emision_referencia_gco2_km: nReferencia,
        vehiculo_referencia: referenciaNombre.trim() || null,
        horizonte_anios: nHorizonte ?? 1,
        fuente: fuente.trim() || null,
        activa,
      };
      return apiAmbiental.guardarCategoria(categoria.categoria_id, cuerpo);
    },
    { exito: mensajeSincronizacion, invalidar: INVALIDAR, avisarError: false, onExito: onCerrar },
  );

  return (
    <Modal
      abierto
      onCerrar={onCerrar}
      bloqueado={guardar.isPending}
      ancho="lg"
      titulo={`Parámetros de «${categoria.categoria_nombre}»`}
      descripcion="Las ventas de esta categoría se cuentan como vehículos vendidos. El CO₂ evitado solo se estima con los parámetros completos."
      pie={
        <>
          <Button variante="ghost" onClick={onCerrar} disabled={guardar.isPending}>
            Cancelar
          </Button>
          <Button
            cargando={guardar.isPending}
            onClick={async () => {
              setIntento(true);
              setError(null);
              if (!valido) return;
              try {
                await guardar.mutateAsync();
              } catch (e) {
                setError(mensajeDeError(e));
              }
            }}
          >
            Guardar parámetros
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <Aviso tipo="error">{error}</Aviso>}
        {algunoLleno && algunoVacio && <Aviso tipo="aviso">Faltan parámetros: mientras no estén los tres (recorrido, consumo y emisión de referencia) se cuentan los vehículos pero el CO₂ queda pendiente.</Aviso>}
        <div className="grid gap-4 sm:grid-cols-2">
          <Select etiqueta="Tipo de vehículo" required value={tipo} onChange={(e) => setTipo(e.target.value)}>
            {Object.entries(TIPO_VEHICULO).map(([k, n]) => (
              <option key={k} value={k}>
                {n}
              </option>
            ))}
          </Select>
          <Select etiqueta="Propulsión" required value={propulsion} onChange={(e) => setPropulsion(e.target.value)}>
            {Object.entries(PROPULSION).map(([k, n]) => (
              <option key={k} value={k}>
                {n}
              </option>
            ))}
          </Select>
          <Input etiqueta="Recorrido anual estimado (km)" inputMode="decimal" value={distancia} onChange={(e) => setDistancia(e.target.value)} error={errores.distancia ?? undefined} ayuda="Cuántos kilómetros recorre al año un uso típico." />
          <Input etiqueta="Años de uso considerados" required inputMode="numeric" value={horizonte} onChange={(e) => setHorizonte(e.target.value)} error={errores.horizonte ?? undefined} ayuda="1 = el primer año; más años multiplican el ahorro." />
          <Input etiqueta="Consumo eléctrico (kWh por 100 km)" inputMode="decimal" value={consumo} onChange={(e) => setConsumo(e.target.value)} error={errores.consumo ?? undefined} ayuda="De la ficha técnica del vehículo." />
          <Input etiqueta="Emisión del escenario de referencia (g CO₂/km)" inputMode="decimal" value={referenciaGramos} onChange={(e) => setReferenciaGramos(e.target.value)} error={errores.referencia ?? undefined} ayuda="Lo que emitiría el vehículo de combustión al que reemplaza." />
        </div>
        <Input etiqueta="Vehículo de combustión de referencia" maxLength={200} value={referenciaNombre} onChange={(e) => setReferenciaNombre(e.target.value)} placeholder="Ej. motocicleta de gasolina de 125 cc" />
        <Textarea etiqueta="Fuente de los valores" rows={2} maxLength={500} value={fuente} onChange={(e) => setFuente(e.target.value)} error={errores.fuente ?? undefined} ayuda="Obligatoria cuando los tres parámetros están completos: ficha técnica, estudio o norma." />

        <details className="rounded-(--radius-control) border border-line bg-surface-2/50 px-4 py-3 text-sm">
          <summary className="flex cursor-pointer items-center gap-2 font-medium text-ink-dim">
            <Calculator className="size-4" aria-hidden />
            Ayuda: calcular la emisión de referencia desde el consumo de combustible
          </summary>
          <div className="mt-3 flex flex-col gap-3">
            <p className="text-ink-dim">
              Si conoces cuántos litros de gasolina gasta el vehículo de referencia cada 100 km, la emisión es: litros ÷ 100 × {decimal(FACTOR_GASOLINA_KG_POR_LITRO, 2)} kg CO₂ por litro (8 887 g CO₂ por galón de gasolina, EPA).
            </p>
            <div className="flex flex-wrap items-end gap-3">
              <Input etiqueta="Consumo del vehículo de referencia (L por 100 km)" inputMode="decimal" value={litros} onChange={(e) => setLitros(e.target.value)} className="min-w-64" />
              <Button
                variante="secondary"
                disabled={nLitros === null || nLitros <= 0}
                onClick={() => nLitros !== null && setReferenciaGramos(String(emisionDesdeConsumoCombustible(nLitros)).replace(".", ","))}
              >
                {nLitros !== null && nLitros > 0 ? `Usar ${decimal(emisionDesdeConsumoCombustible(nLitros), 1)} g/km` : "Usar este valor"}
              </Button>
            </div>
          </div>
        </details>

        <div className="rounded-(--radius-control) border border-line bg-surface-2 px-4 py-3 text-sm" aria-live="polite">
          <p className="text-xs font-medium uppercase tracking-wide text-ink-faint">Vista previa (estimación)</p>
          {vistaPrevia !== null ? (
            <p className="mt-1 text-ink">
              Con estos parámetros y el factor de la red actual, cada unidad vendida evitaría aproximadamente <strong className="tabular text-success">{formatoCo2(vistaPrevia, decimal)}</strong> de CO₂.
            </p>
          ) : (
            <p className="mt-1 text-ink-dim">
              {factorRed === null ? "Falta definir el factor de emisión de la red (arriba) para poder estimar." : "Completa recorrido, consumo y emisión de referencia para ver la estimación."}
            </p>
          )}
        </div>
        <Casilla etiqueta="Categoría activa" descripcion="Si la desactivas, las ventas nuevas dejan de contarse; lo ya contado se conserva." checked={activa} onChange={(e) => setActiva(e.target.checked)} />
        {intento && !valido && <Aviso tipo="error">Revisa los campos marcados.</Aviso>}
      </div>
    </Modal>
  );
}

/* ------------------------------------------------------------------------------ pestaña */

export function ConfiguracionAmbientalTab() {
  const configuracion = useQuery({ queryKey: ["ambiental", "configuracion"], queryFn: apiAmbiental.configuracion });
  const [editando, setEditando] = useState<CategoriaAmbiental | null>(null);
  const sincronizar = useMutacion(() => apiAmbiental.sincronizar(), {
    exito: (r) => (r.incorporados + r.calculados > 0 ? mensajeSincronizacion(r).replace("Configuración guardada: ", "Listo: ") : "Todo estaba al día: no había ventas anteriores por incorporar."),
    invalidar: INVALIDAR,
  });

  if (configuracion.isPending) return <PanelCargando etiqueta="Cargando la configuración…" />;
  if (configuracion.isError)
    return (
      <Card>
        <EstadoError error={configuracion.error} onReintentar={() => configuracion.refetch()} />
      </Card>
    );
  const cfg = configuracion.data;
  if (!cfg.puede_configurar) return <Aviso tipo="aviso">No tienes permiso para configurar los parámetros ambientales.</Aviso>;

  return (
    <div className="flex flex-col gap-6">
      <Aviso tipo="info" titulo="Qué se configura aquí">
        Los indicadores nunca usan cifras inventadas: el número de vehículos vendidos es un dato real, y el CO₂ evitado es una <strong>estimación</strong> que solo se calcula con los parámetros que registres y documentes aquí.
      </Aviso>
      <FactorRed key={`${cfg.factor_red.valor}-${cfg.factor_red.anio}`} factor={cfg.factor_red} />
      <Card>
        <CardHeader
          titulo="Categorías que son vehículos"
          descripcion="Solo las categorías marcadas aquí cuentan en los indicadores. Define para cada una los parámetros del cálculo."
          accion={
            <Button variante="secondary" tamano="sm" cargando={sincronizar.isPending} icono={<RefreshCw className="size-4" aria-hidden />} onClick={() => sincronizar.mutate()}>
              Incorporar ventas anteriores
            </Button>
          }
        />
        <Tabla<CategoriaAmbiental>
          descripcion="Categorías y parámetros ambientales"
          idDe={(c) => c.categoria_id}
          filas={cfg.categorias}
          vacio={{ titulo: "No hay categorías", descripcion: "Crea categorías en el catálogo para poder marcarlas como vehículos." }}
          columnas={[
            { clave: "c", encabezado: "Categoría", celda: (c) => <span className="font-medium">{c.categoria_nombre}</span> },
            {
              clave: "v",
              encabezado: "Vehículo",
              celda: (c) =>
                !c.es_vehiculo ? (
                  <span className="text-ink-faint">No</span>
                ) : (
                  <div>
                    <Badge tono={c.activa ? "success" : "neutral"}>{c.activa ? "Sí" : "Inactiva"}</Badge>
                    <span className="mt-1 block text-xs text-ink-faint">{etiqueta(TIPO_VEHICULO, c.tipo_vehiculo)}</span>
                  </div>
                ),
            },
            {
              clave: "p",
              encabezado: "Parámetros",
              desde: "sm",
              celda: (c) => (!c.es_vehiculo ? <span className="text-ink-faint">—</span> : c.parametros_completos ? <Badge tono="success">Completos</Badge> : <Badge tono="warning">Pendientes</Badge>),
            },
            {
              clave: "co2",
              encabezado: "CO₂ por unidad",
              alinear: "derecha",
              desde: "md",
              celda: (c) => (c.co2_por_unidad_kg !== null && c.co2_por_unidad_kg !== undefined ? <span className="tabular">{formatoCo2(c.co2_por_unidad_kg, decimal)}</span> : <span className="text-ink-faint">—</span>),
            },
            {
              clave: "u",
              encabezado: "Vendidas",
              alinear: "derecha",
              celda: (c) => (
                <span className="tabular">
                  {entero(c.unidades_vendidas)}
                  {c.unidades_sin_parametrizar > 0 && <span className="block text-xs text-warning">{entero(c.unidades_sin_parametrizar)} sin parámetros</span>}
                </span>
              ),
            },
            {
              clave: "a",
              encabezado: "",
              alinear: "derecha",
              celda: (c) => (
                <IconButton etiqueta={c.es_vehiculo ? `Editar parámetros de ${c.categoria_nombre}` : `Marcar ${c.categoria_nombre} como vehículo`} onClick={() => setEditando(c)}>
                  <Pencil className="size-4" aria-hidden />
                </IconButton>
              ),
            },
          ]}
        />
      </Card>
      {editando && <FormularioCategoria categoria={editando} factorRed={cfg.factor_red.valor} onCerrar={() => setEditando(null)} />}
    </div>
  );
}
