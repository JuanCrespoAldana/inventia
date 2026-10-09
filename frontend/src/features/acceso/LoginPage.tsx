import { useState } from "react";
import { Link, useLocation, useNavigate, Navigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { apiAuth } from "@/api/auth";
import { useAuth } from "@/auth/AuthContext";
import { Button } from "@/components/ui/Button";
import { Casilla, Input } from "@/components/ui/Field";
import { CampoPassword } from "@/components/ui/PasswordField";
import { Aviso } from "@/components/ui/Aviso";
import { mensajeDeError } from "@/lib/errors";
import { AuthShell } from "./AuthShell";

const esquema = z.object({
  email: z.string().trim().min(1, "Escriba su correo electrónico").email("Escriba un correo válido"),
  password: z.string().min(1, "Escriba su contraseña"),
  recordar: z.boolean(),
});
type Datos = z.infer<typeof esquema>;

export default function LoginPage() {
  const { iniciarSesion, sesionExpirada } = useAuth();
  const navegar = useNavigate();
  const ubicacion = useLocation();
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const instalacion = useQuery({ queryKey: ["setup", "estado"], queryFn: apiAuth.estadoInstalacion, retry: 1, staleTime: 60_000 });

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Datos>({ resolver: zodResolver(esquema), defaultValues: { email: "", password: "", recordar: false } });

  if (instalacion.data && !instalacion.data.configurado) return <Navigate to="/configuracion-inicial" replace />;

  const destino = (ubicacion.state as { desde?: string } | null)?.desde ?? "/";

  async function enviar(d: Datos) {
    setErrorGeneral(null);
    try {
      await iniciarSesion(d.email.trim(), d.password, d.recordar);
      navegar(destino, { replace: true });
    } catch (e) {
      setErrorGeneral(mensajeDeError(e));
    }
  }

  return (
    <AuthShell titulo="Iniciar sesión" descripcion="Ingrese con la cuenta que le asignó el administrador de su empresa.">
      <form onSubmit={handleSubmit(enviar)} noValidate className="flex flex-col gap-5">
        {sesionExpirada && !errorGeneral && <Aviso tipo="aviso" titulo="Su sesión terminó">Por seguridad debe iniciar sesión de nuevo.</Aviso>}
        {errorGeneral && <Aviso tipo="error">{errorGeneral}</Aviso>}
        <Input etiqueta="Correo electrónico" type="email" autoComplete="username" placeholder="nombre@empresa.com" error={errors.email?.message} {...register("email")} />
        <div>
          <CampoPassword etiqueta="Contraseña" autoComplete="current-password" placeholder="Su contraseña" error={errors.password?.message} {...register("password")} />
          <div className="mt-2 text-right">
            <Link to="/recuperar" className="text-[13px] font-medium text-accent-light hover:underline">
              ¿Olvidó su contraseña?
            </Link>
          </div>
        </div>
        <Casilla etiqueta="Mantener la sesión iniciada en este equipo" descripcion="Úselo solo en equipos de confianza." {...register("recordar")} />
        <Button type="submit" cargando={isSubmitting} className="w-full">
          Ingresar
        </Button>
      </form>
    </AuthShell>
  );
}
