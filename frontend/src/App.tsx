import { lazy, type ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { RequierePermiso, RutaProtegida, RutaPublica } from "@/auth/Rutas";
import { AppShell } from "@/components/layout/AppShell";

const LoginPage = lazy(() => import("@/features/acceso/LoginPage"));
const RecuperarPage = lazy(() => import("@/features/acceso/RecuperarPage"));
const ConfiguracionInicialPage = lazy(() => import("@/features/acceso/ConfiguracionInicialPage"));
const CambiarPasswordPage = lazy(() => import("@/features/acceso/CambiarPasswordPage"));
const PerfilPage = lazy(() => import("@/features/acceso/PerfilPage"));
const PanelPage = lazy(() => import("@/features/panel/PanelPage"));

const ExistenciasPage = lazy(() => import("@/features/inventario/ExistenciasPage"));
const ConsolidadoPage = lazy(() => import("@/features/inventario/ConsolidadoPage"));
const MovimientosPage = lazy(() => import("@/features/inventario/MovimientosPage"));
const ProductosPage = lazy(() => import("@/features/catalogo/ProductosPage"));
const CategoriasPage = lazy(() => import("@/features/catalogo/CategoriasPage"));

const VentasPage = lazy(() => import("@/features/ventas/VentasPage"));
const NuevaVentaPage = lazy(() => import("@/features/ventas/NuevaVentaPage"));
const VentaDetallePage = lazy(() => import("@/features/ventas/VentaDetallePage"));
const TrasladosPage = lazy(() => import("@/features/traslados/TrasladosPage"));
const NuevoTrasladoPage = lazy(() => import("@/features/traslados/NuevoTrasladoPage"));
const TrasladoDetallePage = lazy(() => import("@/features/traslados/TrasladoDetallePage"));
const AlertasPage = lazy(() => import("@/features/alertas/AlertasPage"));

const PrediccionesPage = lazy(() => import("@/features/prediccion/PrediccionesPage"));
const RecomendacionesPage = lazy(() => import("@/features/recomendaciones/RecomendacionesPage"));
const ReportesPage = lazy(() => import("@/features/reportes/ReportesPage"));

const EmpresaPage = lazy(() => import("@/features/administracion/EmpresaPage"));
const SedesPage = lazy(() => import("@/features/administracion/SedesPage"));
const UsuariosPage = lazy(() => import("@/features/administracion/UsuariosPage"));
const RolesPage = lazy(() => import("@/features/administracion/RolesPage"));
const AuditoriaPage = lazy(() => import("@/features/auditoria/AuditoriaPage"));
const IntegracionesPage = lazy(() => import("@/features/administracion/IntegracionesPage"));

const PqrsPage = lazy(() => import("@/features/sig/pqrs/PqrsPage"));
const SstPage = lazy(() => import("@/features/sig/sst/SstPage"));
const CalidadPage = lazy(() => import("@/features/sig/calidad/CalidadPage"));
const AmbientalPage = lazy(() => import("@/features/sig/ambiental/AmbientalPage"));

const PERMISOS_REPORTES = [
  "reportes.inventario",
  "reportes.ventas",
  "reportes.movimientos",
  "reportes.traslados",
  "reportes.alertas",
  "reportes.predicciones",
  "reportes.recomendaciones",
];

/** Cada pantalla se protege por permiso; el backend vuelve a validarlo en cada solicitud. */
function Con({ permisos, children }: { permisos: string[]; children: ReactNode }) {
  return <RequierePermiso alguno={permisos}>{children}</RequierePermiso>;
}

export default function App() {
  return (
    <Routes>
      <Route element={<RutaPublica />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/recuperar" element={<RecuperarPage />} />
        <Route path="/configuracion-inicial" element={<ConfiguracionInicialPage />} />
      </Route>

      <Route element={<RutaProtegida />}>
        <Route path="/cambiar-password" element={<CambiarPasswordPage />} />
        <Route element={<AppShell />}>
          <Route index element={<PanelPage />} />
          <Route path="/perfil" element={<PerfilPage />} />

          <Route path="/inventario" element={<Con permisos={["inventario.ver"]}><ExistenciasPage /></Con>} />
          <Route path="/inventario/consolidado" element={<Con permisos={["inventario.consolidado"]}><ConsolidadoPage /></Con>} />
          <Route path="/movimientos" element={<Con permisos={["movimientos.ver"]}><MovimientosPage /></Con>} />
          <Route path="/productos" element={<Con permisos={["productos.ver"]}><ProductosPage /></Con>} />
          <Route path="/categorias" element={<Con permisos={["categorias.ver"]}><CategoriasPage /></Con>} />

          <Route path="/ventas" element={<Con permisos={["ventas.ver", "ventas.registrar"]}><VentasPage /></Con>} />
          <Route path="/ventas/nueva" element={<Con permisos={["ventas.registrar"]}><NuevaVentaPage /></Con>} />
          <Route path="/ventas/:id" element={<Con permisos={["ventas.ver", "ventas.registrar"]}><VentaDetallePage /></Con>} />
          <Route path="/traslados" element={<Con permisos={["traslados.ver", "traslados.solicitar"]}><TrasladosPage /></Con>} />
          <Route path="/traslados/nuevo" element={<Con permisos={["traslados.solicitar"]}><NuevoTrasladoPage /></Con>} />
          <Route path="/traslados/:id" element={<Con permisos={["traslados.ver", "traslados.solicitar"]}><TrasladoDetallePage /></Con>} />
          <Route path="/alertas" element={<Con permisos={["alertas.ver"]}><AlertasPage /></Con>} />

          <Route path="/predicciones" element={<Con permisos={["prediccion.ver"]}><PrediccionesPage /></Con>} />
          <Route path="/recomendaciones" element={<Con permisos={["recomendaciones.ver"]}><RecomendacionesPage /></Con>} />
          <Route path="/reportes" element={<Con permisos={PERMISOS_REPORTES}><ReportesPage /></Con>} />

          <Route path="/sig/pqrs" element={<Con permisos={["pqrs.crear", "pqrs.gestionar"]}><PqrsPage /></Con>} />
          <Route path="/sig/sst" element={<Con permisos={["sst.ver", "sst.gestionar"]}><SstPage /></Con>} />
          <Route path="/sig/calidad" element={<Con permisos={["calidad.ver", "calidad.reportar", "calidad.gestionar"]}><CalidadPage /></Con>} />
          <Route path="/sig/ambiental" element={<Con permisos={["ambiental.ver", "ambiental.configurar"]}><AmbientalPage /></Con>} />

          <Route path="/empresa" element={<Con permisos={["empresa.ver"]}><EmpresaPage /></Con>} />
          <Route path="/sedes" element={<Con permisos={["sedes.ver"]}><SedesPage /></Con>} />
          <Route path="/usuarios" element={<Con permisos={["usuarios.ver"]}><UsuariosPage /></Con>} />
          <Route path="/roles" element={<Con permisos={["roles.ver"]}><RolesPage /></Con>} />
          <Route path="/auditoria" element={<Con permisos={["auditoria.ver", "auditoria.operaciones"]}><AuditoriaPage /></Con>} />
          <Route path="/integraciones" element={<Con permisos={["agentes.gestionar"]}><IntegracionesPage /></Con>} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Route>
    </Routes>
  );
}
