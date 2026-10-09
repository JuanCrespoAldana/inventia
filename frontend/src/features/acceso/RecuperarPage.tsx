import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { apiAuth } from "@/api/auth";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Field";
import { CampoPassword } from "@/components/ui/PasswordField";
import { Aviso } from "@/components/ui/Aviso";
import { v } from "@/lib/formularios";
import { mensajeDeError } from "@/lib/errors";
import { AuthShell } from "./AuthShell";

type Paso = "correo" | "codigo" | "clave" | "listo";

const esquemaCorreo = z.object({ email: v.correo });
const esquemaCodigo = z.object({ codigo: z.string().trim().regex(/^\d{6}$/, "El código tiene 6 dígitos") });
const esquemaClave = z
  .object({ nueva: v.password, repetir: z.string() })
  .refine((d) => d.nueva === d.repetir, { path: ["repetir"], message: "Las contraseñas no coinciden" });

export default function RecuperarPage() {
  const [paso, setPaso] = useState<Paso>("correo");
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const navegar = useNavigate();

  const f1 = useForm<z.infer<typeof esquemaCorreo>>({ resolver: zodResolver(esquemaCorreo), defaultValues: { email: "" } });
  const f2 = useForm<z.infer<typeof esquemaCodigo>>({ resolver: zodResolver(esquemaCodigo), defaultValues: { codigo: "" } });
  const f3 = useForm<z.infer<typeof esquemaClave>>({ resolver: zodResolver(esquemaClave), defaultValues: { nueva: "", repetir: "" } });

  async function pedirCodigo(d: z.infer<typeof esquemaCorreo>) {
    setError(null);
    try {
      await apiAuth.olvide(d.email.trim());
      setEmail(d.email.trim());
      setPaso("codigo");
    } catch (e) {
      setError(mensajeDeError(e));
    }
  }
  async function verificar(d: z.infer<typeof esquemaCodigo>) {
    setError(null);
    try {
      const r = await apiAuth.verificarCodigo(email, d.codigo);
      setToken(r.session_token);
      setPaso("clave");
    } catch (e) {
      setError(mensajeDeError(e));
    }
  }
  async function restablecer(d: z.infer<typeof esquemaClave>) {
    setError(null);
    try {
      await apiAuth.restablecer(token, d.nueva);
      setPaso("listo");
    } catch (e) {
      setError(mensajeDeError(e));
    }
  }

  const titulos: Record<Paso, [string, string]> = {
    correo: ["Recuperar contraseña", "Escriba el correo de su cuenta y le enviaremos un código de verificación."],
    codigo: ["Revise su correo", `Si ${email} corresponde a una cuenta activa, le enviamos un código de 6 dígitos. Vence en pocos minutos.`],
    clave: ["Cree una contraseña nueva", "Use una contraseña que no haya usado en otros sitios."],
    listo: ["Contraseña actualizada", "Ya puede iniciar sesión con su contraseña nueva."],
  };

  return (
    <AuthShell
      titulo={titulos[paso][0]}
      descripcion={titulos[paso][1]}
      pie={
        paso !== "listo" && (
          <Link to="/login" className="font-medium text-accent-light hover:underline">
            Volver a iniciar sesión
          </Link>
        )
      }
    >
      {error && <Aviso tipo="error" className="mb-5">{error}</Aviso>}

      {paso === "correo" && (
        <form onSubmit={f1.handleSubmit(pedirCodigo)} noValidate className="flex flex-col gap-5">
          <Input etiqueta="Correo electrónico" type="email" autoComplete="email" placeholder="nombre@empresa.com" error={f1.formState.errors.email?.message} {...f1.register("email")} />
          <Button type="submit" cargando={f1.formState.isSubmitting}>Enviar código</Button>
        </form>
      )}

      {paso === "codigo" && (
        <form onSubmit={f2.handleSubmit(verificar)} noValidate className="flex flex-col gap-5">
          <Input
            etiqueta="Código de verificación"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            placeholder="000000"
            className="[&_input]:text-center [&_input]:font-display [&_input]:text-xl [&_input]:tracking-[0.5em]"
            error={f2.formState.errors.codigo?.message}
            {...f2.register("codigo")}
          />
          <Button type="submit" cargando={f2.formState.isSubmitting}>Verificar código</Button>
          <button type="button" onClick={() => { setError(null); setPaso("correo"); }} className="text-sm text-ink-dim hover:text-ink">
            Usar otro correo
          </button>
        </form>
      )}

      {paso === "clave" && (
        <form onSubmit={f3.handleSubmit(restablecer)} noValidate className="flex flex-col gap-5">
          <CampoPassword etiqueta="Contraseña nueva" autoComplete="new-password" mostrarRequisitos valorActual={f3.watch("nueva")} error={f3.formState.errors.nueva?.message} {...f3.register("nueva")} />
          <CampoPassword etiqueta="Repita la contraseña" autoComplete="new-password" error={f3.formState.errors.repetir?.message} {...f3.register("repetir")} />
          <Button type="submit" cargando={f3.formState.isSubmitting}>Guardar contraseña</Button>
        </form>
      )}

      {paso === "listo" && (
        <div className="flex flex-col gap-5">
          <Aviso tipo="exito">Su contraseña se actualizó correctamente.</Aviso>
          <Button onClick={() => navegar("/login", { replace: true })}>Ir a iniciar sesión</Button>
        </div>
      )}
    </AuthShell>
  );
}
