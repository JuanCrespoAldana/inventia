import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { Pestanas } from "@/components/ui/Tabs";
import { ConfiguracionAmbientalTab } from "./ConfiguracionAmbiental";
import { HistorialAmbiental } from "./HistorialAmbiental";
import { Metodologia } from "./Metodologia";
import { PanelAmbiental } from "./PanelAmbiental";

type Pestana = "panel" | "historial" | "metodologia" | "configuracion";

export default function AmbientalPage() {
  const { tiene } = useAuth();
  const puedeConfigurar = tiene("ambiental.configurar");
  const [params, setParams] = useSearchParams();
  const permitidas: Pestana[] = puedeConfigurar ? ["panel", "historial", "metodologia", "configuracion"] : ["panel", "historial", "metodologia"];
  const [pestana, setPestana] = useState<Pestana>(permitidas.find((p) => p === params.get("tab")) ?? "panel");

  function cambiar(p: Pestana) {
    setParams({}, { replace: true }); // los filtros del historial no deben pasar a otra pestaña
    setPestana(p);
  }

  return (
    <>
      <EncabezadoPagina
        titulo="Gestión ambiental"
        descripcion="Vehículos eléctricos vendidos y estimación del CO₂ que ayudan a evitar. Las ventas confirmadas se contabilizan solas; no hay que registrar nada a mano."
      />
      <div className="mb-5">
        <Pestanas
          etiqueta="Secciones de gestión ambiental"
          activa={pestana}
          onCambiar={cambiar}
          pestanas={[
            { clave: "panel", etiqueta: "Panel" },
            { clave: "historial", etiqueta: "Historial" },
            { clave: "metodologia", etiqueta: "Metodología" },
            ...(puedeConfigurar ? [{ clave: "configuracion" as const, etiqueta: "Configuración" }] : []),
          ]}
        />
      </div>
      {pestana === "panel" && <PanelAmbiental puedeConfigurar={puedeConfigurar} irAConfiguracion={() => cambiar("configuracion")} />}
      {pestana === "historial" && <HistorialAmbiental />}
      {pestana === "metodologia" && <Metodologia />}
      {pestana === "configuracion" && puedeConfigurar && <ConfiguracionAmbientalTab />}
    </>
  );
}
