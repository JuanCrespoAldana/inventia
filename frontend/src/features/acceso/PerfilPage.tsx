import { Building2, Mail, MapPin, ShieldCheck } from "lucide-react";
import { useSesion } from "@/auth/AuthContext";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { FormularioCambiarPassword } from "./CambiarPasswordPage";

function Dato({ icono, etiqueta, children }: { icono: React.ReactNode; etiqueta: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-(--radius-control) bg-surface-2 text-ink-faint" aria-hidden>{icono}</span>
      <div className="min-w-0">
        <dt className="text-xs text-ink-faint">{etiqueta}</dt>
        <dd className="mt-0.5 break-words text-sm font-medium text-ink">{children}</dd>
      </div>
    </div>
  );
}

export default function PerfilPage() {
  const sesion = useSesion();
  return (
    <>
      <EncabezadoPagina titulo="Mi perfil" descripcion="Sus datos de acceso y la seguridad de su cuenta." />
      <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader titulo="Información de la cuenta" descripcion="Si necesita corregir estos datos, solicítelo a un administrador." />
          <dl className="grid grid-cols-1 gap-5 p-5 sm:grid-cols-2">
            <Dato icono={<Mail className="size-4" />} etiqueta="Nombre y correo">
              {sesion.nombre}
              <span className="block text-xs font-normal text-ink-dim">{sesion.email}</span>
            </Dato>
            <Dato icono={<Building2 className="size-4" />} etiqueta="Empresa">{sesion.empresa_nombre}</Dato>
            <Dato icono={<ShieldCheck className="size-4" />} etiqueta="Rol">
              {sesion.rol.nombre}
              <span className="mt-1 block">
                <Badge tono="accent">{sesion.rol.alcance === "empresa" ? "Ve todas las sedes" : "Opera en una sede"}</Badge>
              </span>
            </Dato>
            <Dato icono={<MapPin className="size-4" />} etiqueta="Sede">{sesion.sede ? sesion.sede.nombre : "Todas las sedes"}</Dato>
          </dl>
          <p className="border-t border-line px-5 py-3 text-xs text-ink-faint">
            <span className="tabular">{sesion.permisos.length}</span> permisos activos según su rol.
          </p>
        </Card>
        <Card>
          <CardHeader titulo="Cambiar contraseña" descripcion="Al cambiarla se cierran las demás sesiones abiertas de su cuenta." />
          <div className="p-5">
            <FormularioCambiarPassword alTerminar={() => undefined} />
          </div>
        </Card>
      </div>
    </>
  );
}
