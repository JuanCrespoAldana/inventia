import { Navigate, Outlet, useLocation } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import { Link } from "react-router-dom";
import { EstadoVacio } from "@/components/ui/EstadoVacio";
import { PanelCargando } from "@/components/ui/Skeleton";
import { useAuth } from "./AuthContext";

/** Exige sesión iniciada. Si la persona debe cambiar su contraseña, la lleva primero a esa pantalla. */
export function RutaProtegida() {
  const { estado, sesion } = useAuth();
  const ubicacion = useLocation();

  if (estado === "cargando") return <div className="mx-auto max-w-md p-10"><PanelCargando etiqueta="Verificando la sesión…" /></div>;
  if (estado === "anonimo" || !sesion) return <Navigate to="/login" replace state={{ desde: ubicacion.pathname + ubicacion.search }} />;
  if (sesion.debe_cambiar_password && ubicacion.pathname !== "/cambiar-password") return <Navigate to="/cambiar-password" replace />;
  return <Outlet />;
}

/** Rutas públicas (inicio de sesión, recuperación): si ya hay sesión se redirige al panel. */
export function RutaPublica() {
  const { estado } = useAuth();
  if (estado === "cargando") return <div className="mx-auto max-w-md p-10"><PanelCargando etiqueta="Cargando…" /></div>;
  if (estado === "autenticado") return <Navigate to="/" replace />;
  return <Outlet />;
}

/** Protege una pantalla por permiso: si falta, muestra «sin acceso» en lugar de una pantalla vacía o rota. */
export function RequierePermiso({ alguno, children }: { alguno: string[]; children: React.ReactNode }) {
  const { tieneAlguno } = useAuth();
  if (!tieneAlguno(...alguno)) {
    return (
      <EstadoVacio
        comoPagina
        icono={<ShieldAlert className="size-5" aria-hidden />}
        titulo="No tiene acceso a esta sección"
        descripcion="Su rol no incluye el permiso necesario. Si cree que es un error, solicite el acceso a un administrador de su empresa."
        accion={
          <Link to="/" className="text-sm font-semibold text-accent-light hover:underline">
            Volver al panel de control
          </Link>
        }
      />
    );
  }
  return <>{children}</>;
}
