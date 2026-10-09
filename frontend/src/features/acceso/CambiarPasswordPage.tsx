import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { apiAuth } from "@/api/auth";
import { useAuth, useSesion } from "@/auth/AuthContext";
import { Aviso } from "@/components/ui/Aviso";
import { Button } from "@/components/ui/Button";
import { CampoPassword } from "@/components/ui/PasswordField";
import { useToast } from "@/components/ui/Toast";
import { aplicarErroresServidor, v } from "@/lib/formularios";
import { AuthShell } from "./AuthShell";

const esquema = z
  .object({ actual: z.string().min(1, "Escriba su contraseña actual"), nueva: v.password, repetir: z.string() })
  .refine((d) => d.nueva === d.repetir, { path: ["repetir"], message: "Las contraseñas no coinciden" })
  .refine((d) => d.nueva !== d.actual, { path: ["nueva"], message: "La contraseña nueva debe ser distinta de la actual" });
type Datos = z.infer<typeof esquema>;

export function useCambiarPassword(alTerminar: () => void) {
  const { aplicarToken } = useAuth();
  const toast = useToast();
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const form = useForm<Datos>({ resolver: zodResolver(esquema), defaultValues: { actual: "", nueva: "", repetir: "" } });

  const enviar = form.handleSubmit(async (d) => {
    setErrorGeneral(null);
    try {
      const token = await apiAuth.cambiarPassword(d.actual, d.nueva);
      aplicarToken(token, false);
      toast.exito("Contraseña actualizada.");
      form.reset();
      alTerminar();
    } catch (e) {
      const general = aplicarErroresServidor(e, form.setError, ["nueva_password", "password_actual"]);
      setErrorGeneral(general);
    }
  });
  return { form, enviar, errorGeneral };
}

export function FormularioCambiarPassword({ alTerminar }: { alTerminar: () => void }) {
  const { form, enviar, errorGeneral } = useCambiarPassword(alTerminar);
  const { register, formState, watch } = form;
  return (
    <form onSubmit={enviar} noValidate className="flex flex-col gap-5">
      {errorGeneral && <Aviso tipo="error">{errorGeneral}</Aviso>}
      <CampoPassword etiqueta="Contraseña actual" autoComplete="current-password" error={formState.errors.actual?.message} {...register("actual")} />
      <CampoPassword etiqueta="Contraseña nueva" autoComplete="new-password" mostrarRequisitos valorActual={watch("nueva")} error={formState.errors.nueva?.message} {...register("nueva")} />
      <CampoPassword etiqueta="Repita la contraseña nueva" autoComplete="new-password" error={formState.errors.repetir?.message} {...register("repetir")} />
      <Button type="submit" cargando={formState.isSubmitting} className="self-start">
        Cambiar contraseña
      </Button>
    </form>
  );
}

/** Pantalla obligatoria cuando un administrador asignó una contraseña temporal. */
export default function CambiarPasswordPage() {
  const sesion = useSesion();
  const navegar = useNavigate();
  const { cerrarSesion } = useAuth();
  return (
    <AuthShell
      titulo="Cree su contraseña personal"
      descripcion={`${sesion.nombre}, la contraseña actual es temporal. Defina una nueva para continuar.`}
      pie={
        <button
          type="button"
          className="font-medium text-ink-dim hover:text-ink"
          onClick={async () => {
            await cerrarSesion();
            navegar("/login", { replace: true });
          }}
        >
          Cerrar sesión
        </button>
      }
    >
      <FormularioCambiarPassword alTerminar={() => navegar("/", { replace: true })} />
    </AuthShell>
  );
}
