import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { apiCalidad } from "@/api/sig";
import { Stat } from "@/components/ui/Card";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { Pestanas } from "@/components/ui/Tabs";
import { DialogoEntradaDetalle } from "@/features/inventario/DialogoEntradaDetalle";
import { ESTADO_GARANTIA, ESTADO_NC } from "@/lib/etiquetas";
import { entero } from "@/lib/format";
import type { ResumenCalidad } from "@/types/api";
import { Badge } from "@/components/ui/Badge";
import { Garantias } from "./Garantias";
import { GuiaCalidad } from "./GuiaCalidad";
import { NoConformidades } from "./NoConformidades";

type Pestana = "guia" | "no-conformidades" | "garantias";
const PESTANAS: Pestana[] = ["guia", "no-conformidades", "garantias"];

function Conteos({ filas, mapa }: { filas: ResumenCalidad["no_conformidades"]; mapa: Record<string, { etiqueta: string; tono: "neutral" | "accent" | "success" | "warning" | "danger" }> }) {
  const porEstado = new Map(filas.map((f) => [f.estado, f.total]));
  return (
    <div className="flex flex-wrap gap-1.5">
      {Object.entries(mapa).map(([k, e]) => (
        <Badge key={k} tono={(porEstado.get(k) ?? 0) > 0 ? e.tono : "neutral"}>
          {e.etiqueta}: {entero(porEstado.get(k) ?? 0)}
        </Badge>
      ))}
    </div>
  );
}

function Resumen() {
  const resumen = useQuery({ queryKey: ["calidad", "resumen"], queryFn: () => apiCalidad.resumen() });
  const r = resumen.data;
  if (!r) return null;
  return (
    <div className="mb-6 grid gap-4 md:grid-cols-2">
      <Stat etiqueta="No conformidades abiertas" valor={entero(r.no_conformidades_abiertas)} tono={r.no_conformidades_abiertas > 0 ? "warning" : "success"} detalle={<Conteos filas={r.no_conformidades} mapa={ESTADO_NC} />} />
      <Stat etiqueta="Garantías abiertas" valor={entero(r.garantias_abiertas)} tono={r.garantias_abiertas > 0 ? "warning" : "success"} detalle={<Conteos filas={r.garantias} mapa={ESTADO_GARANTIA} />} />
    </div>
  );
}

export default function CalidadPage() {
  const [params, setParams] = useSearchParams();
  const inicial = PESTANAS.find((p) => p === params.get("tab")) ?? "guia";
  const [pestana, setPestana] = useState<Pestana>(inicial);
  const [entradaAbierta, setEntradaAbierta] = useState<number | null>(null);
  const ncInicial = Number(params.get("nc")) || null;
  const garantiaInicial = Number(params.get("garantia")) || null;

  function cambiar(p: Pestana) {
    setParams({}, { replace: true }); // los filtros de una pestaña no deben pasar a la otra
    setPestana(p);
  }

  return (
    <>
      <EncabezadoPagina
        titulo="Calidad"
        descripcion="Gestión de no conformidades y garantías: reporta, da seguimiento, conserva evidencias y consulta el historial completo de cada caso."
      />
      <Resumen />
      <div className="mb-5">
        <Pestanas
          etiqueta="Secciones de calidad"
          activa={pestana}
          onCambiar={cambiar}
          pestanas={[
            { clave: "guia", etiqueta: "Guía" },
            { clave: "no-conformidades", etiqueta: "No conformidades" },
            { clave: "garantias", etiqueta: "Garantías" },
          ]}
        />
      </div>
      {pestana === "guia" && <GuiaCalidad irANoConformidades={() => cambiar("no-conformidades")} irAGarantias={() => cambiar("garantias")} />}
      {pestana === "no-conformidades" && <NoConformidades abrirDetalle={ncInicial} onAbrirEntrada={setEntradaAbierta} />}
      {pestana === "garantias" && <Garantias abrirDetalle={garantiaInicial} onAbrirEntrada={setEntradaAbierta} />}
      {entradaAbierta !== null && <DialogoEntradaDetalle entradaId={entradaAbierta} onCerrar={() => setEntradaAbierta(null)} />}
    </>
  );
}
