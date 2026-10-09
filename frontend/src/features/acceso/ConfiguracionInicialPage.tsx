import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { apiAuth } from "@/api/auth";
import { useAuth } from "@/auth/AuthContext";
import { Aviso } from "@/components/ui/Aviso";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Field";
import { CampoPassword } from "@/components/ui/PasswordField";
import { PanelCargando } from "@/components/ui/Skeleton";
import { aplicarErroresServidor, v } from "@/lib/formularios";
import { cn } from "@/lib/cn";
import { AuthShell } from "./AuthShell";

const esquema = z
  .object({
    empresa_nombre: v.texto("El nombre de la empresa", 2, 150),
    empresa_identificacion: v.identificacion,
    empresa_ciudad: v.textoOpcional(100),
    empresa_direccion: v.textoOpcional(200),
    empresa_telefono: v.telefono,
    empresa_email: z.string().trim().refine((t) => t === "" || z.email().safeParse(t).success, "Escriba un correo válido"),
    admin_nombre: v.texto("Su nombre", 2, 150),
    admin_email: v.correo,
    admin_password: v.password,
    repetir: z.string(),
    token_configuracion: z.string().trim().max(200),
  })
  .refine((d) => d.admin_password === d.repetir, { path: ["repetir"], message: "Las contraseñas no coinciden" });
type Datos = z.infer<typeof esquema>;

const CAMPOS_PASO_1: (keyof Datos)[] = ["empresa_nombre", "empresa_identificacion", "empresa_ciudad", "empresa_direccion", "empresa_telefono", "empresa_email"];
const CAMPOS_SERVIDOR = ["empresa_nombre", "empresa_identificacion", "empresa_ciudad", "empresa_direccion", "empresa_telefono", "empresa_email", "admin_nombre", "admin_email", "admin_password", "token_configuracion"];

export default function ConfiguracionInicialPage() {
  const { aplicarToken } = useAuth();
  const navegar = useNavigate();
  const [paso, setPaso] = useState<1 | 2>(1);
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const estado = useQuery({ queryKey: ["setup", "estado"], queryFn: apiAuth.estadoInstalacion, retry: 1 });

  const {
    register,
    handleSubmit,
    trigger,
    setError,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<Datos>({
    resolver: zodResolver(esquema),
    defaultValues: {
      empresa_nombre: "", empresa_identificacion: "", empresa_ciudad: "", empresa_direccion: "", empresa_telefono: "", empresa_email: "",
      admin_nombre: "", admin_email: "", admin_password: "", repetir: "", token_configuracion: "",
    },
  });

  if (estado.isPending) return <div className="mx-auto max-w-md p-10"><PanelCargando etiqueta="Verificando la instalación…" /></div>;
  if (estado.data?.configurado) return <Navigate to="/login" replace />;

  async function siguiente() {
    if (await trigger(CAMPOS_PASO_1)) setPaso(2);
  }

  async function enviar(d: Datos) {
    setErrorGeneral(null);
    try {
      const token = await apiAuth.configurar({
        empresa_nombre: d.empresa_nombre.trim(),
        empresa_identificacion: d.empresa_identificacion.trim(),
        empresa_ciudad: d.empresa_ciudad.trim() || null,
        empresa_direccion: d.empresa_direccion.trim() || null,
        empresa_telefono: d.empresa_telefono.trim() || null,
        empresa_email: d.empresa_email.trim() || null,
        admin_nombre: d.admin_nombre.trim(),
        admin_email: d.admin_email.trim(),
        admin_password: d.admin_password,
        token_configuracion: d.token_configuracion.trim(),
      });
      aplicarToken(token, false);
      navegar("/", { replace: true });
    } catch (e) {
      const general = aplicarErroresServidor(e, setError, CAMPOS_SERVIDOR);
      setErrorGeneral(general);
      const empresaConError = CAMPOS_PASO_1.some((c) => (errors as Record<string, unknown>)[c]);
      if (empresaConError) setPaso(1);
    }
  }

  const requiereToken = estado.data?.requiere_token ?? false;

  return (
    <AuthShell
      titulo="Configuración inicial"
      descripcion="Registre su empresa y cree la cuenta del primer administrador. Este paso solo se realiza una vez."
      pie={<Link to="/login" className="font-medium text-accent-light hover:underline">Ya tengo una cuenta</Link>}
    >
      <ol className="mb-7 flex items-center gap-3 text-[13px] font-semibold" aria-label="Pasos">
        {[
          [1, "Empresa"],
          [2, "Administrador"],
        ].map(([n, nombre]) => (
          <li key={n} className="flex flex-1 items-center gap-2.5" aria-current={paso === n ? "step" : undefined}>
            <span className={cn("flex size-6 items-center justify-center rounded-full text-xs", paso >= (n as number) ? "bg-accent text-white" : "bg-surface-3 text-ink-faint")}>{n}</span>
            <span className={paso === n ? "text-ink" : "text-ink-faint"}>{nombre}</span>
            <span className="h-px flex-1 bg-line last:hidden" />
          </li>
        ))}
      </ol>

      <form onSubmit={handleSubmit(enviar)} noValidate className="flex flex-col gap-5">
        {errorGeneral && <Aviso tipo="error">{errorGeneral}</Aviso>}

        <div className={cn("flex flex-col gap-5", paso !== 1 && "hidden")}>
          <Input etiqueta="Nombre de la empresa" required autoComplete="organization" error={errors.empresa_nombre?.message} {...register("empresa_nombre")} />
          <Input etiqueta="NIT o identificación tributaria" required placeholder="900123456-7" error={errors.empresa_identificacion?.message} {...register("empresa_identificacion")} />
          <div className="grid gap-5 sm:grid-cols-2">
            <Input etiqueta="Ciudad" autoComplete="address-level2" error={errors.empresa_ciudad?.message} {...register("empresa_ciudad")} />
            <Input etiqueta="Teléfono" type="tel" autoComplete="tel" error={errors.empresa_telefono?.message} {...register("empresa_telefono")} />
          </div>
          <Input etiqueta="Dirección" autoComplete="street-address" error={errors.empresa_direccion?.message} {...register("empresa_direccion")} />
          <Input etiqueta="Correo de la empresa" type="email" placeholder="contacto@empresa.com" error={errors.empresa_email?.message} {...register("empresa_email")} />
          <Button onClick={siguiente}>
            Continuar <ArrowRight className="size-4" aria-hidden />
          </Button>
        </div>

        <div className={cn("flex flex-col gap-5", paso !== 2 && "hidden")}>
          <Input etiqueta="Nombre completo" required autoComplete="name" error={errors.admin_nombre?.message} {...register("admin_nombre")} />
          <Input etiqueta="Correo electrónico" required type="email" autoComplete="username" error={errors.admin_email?.message} {...register("admin_email")} />
          <CampoPassword etiqueta="Contraseña" required autoComplete="new-password" mostrarRequisitos valorActual={watch("admin_password")} error={errors.admin_password?.message} {...register("admin_password")} />
          <CampoPassword etiqueta="Repita la contraseña" required autoComplete="new-password" error={errors.repetir?.message} {...register("repetir")} />
          {requiereToken && (
            <Input
              etiqueta="Código de configuración"
              required
              autoComplete="off"
              ayuda="Lo define quien instaló el sistema (variable SETUP_TOKEN del servidor)."
              error={errors.token_configuracion?.message}
              {...register("token_configuracion")}
            />
          )}
          <div className="flex gap-3">
            <Button variante="secondary" onClick={() => setPaso(1)} icono={<ArrowLeft className="size-4" aria-hidden />}>
              Atrás
            </Button>
            <Button type="submit" cargando={isSubmitting} className="flex-1">
              Crear empresa y administrador
            </Button>
          </div>
        </div>
      </form>
    </AuthShell>
  );
}
