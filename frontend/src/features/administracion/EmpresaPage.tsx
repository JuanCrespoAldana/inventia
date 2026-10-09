import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { apiEmpresa } from "@/api/administracion";
import { useAuth } from "@/auth/AuthContext";
import { Aviso } from "@/components/ui/Aviso";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { EstadoError } from "@/components/ui/EstadoVacio";
import { Input } from "@/components/ui/Field";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { PanelCargando } from "@/components/ui/Skeleton";
import { useMutacion } from "@/hooks/useMutacion";
import { PARAMETROS_EMPRESA } from "@/lib/etiquetas";
import { aplicarErroresServidor, v } from "@/lib/formularios";
import type { Empresa, ParametrosEmpresa } from "@/types/api";

const esquemaDatos = z.object({
  nombre: v.texto("El nombre", 2, 150),
  identificacion: v.identificacion,
  ciudad: v.textoOpcional(100),
  direccion: v.textoOpcional(200),
  telefono: v.telefono,
  email: z.string().trim().refine((t) => t === "" || z.email().safeParse(t).success, "Escriba un correo válido"),
});
type DatosEmpresa = z.infer<typeof esquemaDatos>;

function FormularioDatos({ empresa, editable }: { empresa: Empresa; editable: boolean }) {
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setError,
    reset,
    formState: { errors, isDirty },
  } = useForm<DatosEmpresa>({
    resolver: zodResolver(esquemaDatos),
    defaultValues: {
      nombre: empresa.nombre,
      identificacion: empresa.identificacion ?? "",
      ciudad: empresa.ciudad ?? "",
      direccion: empresa.direccion ?? "",
      telefono: empresa.telefono ?? "",
      email: empresa.email ?? "",
    },
  });
  const guardar = useMutacion(
    (d: DatosEmpresa) =>
      apiEmpresa.actualizar({
        nombre: d.nombre.trim(),
        identificacion: d.identificacion.trim(),
        ciudad: d.ciudad.trim() || null,
        direccion: d.direccion.trim() || null,
        telefono: d.telefono.trim() || null,
        email: d.email.trim() || null,
      }),
    { exito: "Datos de la empresa actualizados.", invalidar: [["empresa"]], avisarError: false, onExito: (e) => reset({ nombre: e.nombre, identificacion: e.identificacion ?? "", ciudad: e.ciudad ?? "", direccion: e.direccion ?? "", telefono: e.telefono ?? "", email: e.email ?? "" }) },
  );

  return (
    <Card>
      <CardHeader titulo="Datos de la empresa" descripcion={editable ? undefined : "Solo lectura: su rol no incluye permiso para modificarlos."} />
      <form
        noValidate
        className="grid gap-4 p-5 sm:grid-cols-2"
        onSubmit={handleSubmit(async (d) => {
          setErrorGeneral(null);
          try {
            await guardar.mutateAsync(d);
          } catch (e) {
            setErrorGeneral(aplicarErroresServidor(e, setError, ["nombre", "identificacion", "ciudad", "direccion", "telefono", "email"]));
          }
        })}
      >
        {errorGeneral && <Aviso tipo="error" className="sm:col-span-2">{errorGeneral}</Aviso>}
        <Input etiqueta="Nombre" required disabled={!editable} error={errors.nombre?.message} {...register("nombre")} />
        <Input etiqueta="NIT o identificación" required disabled={!editable} error={errors.identificacion?.message} {...register("identificacion")} />
        <Input etiqueta="Ciudad" disabled={!editable} error={errors.ciudad?.message} {...register("ciudad")} />
        <Input etiqueta="Teléfono" type="tel" disabled={!editable} error={errors.telefono?.message} {...register("telefono")} />
        <Input etiqueta="Dirección" disabled={!editable} className="sm:col-span-2" error={errors.direccion?.message} {...register("direccion")} />
        <Input etiqueta="Correo de contacto" type="email" disabled={!editable} className="sm:col-span-2" error={errors.email?.message} {...register("email")} />
        {editable && (
          <div className="sm:col-span-2">
            <Button type="submit" cargando={guardar.isPending} disabled={!isDirty}>Guardar cambios</Button>
          </div>
        )}
      </form>
    </Card>
  );
}

function FormularioParametros({ empresa, editable }: { empresa: Empresa; editable: boolean }) {
  const cliente = useQueryClient();
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);
  const [valores, setValores] = useState<Record<string, string>>(() => Object.fromEntries(PARAMETROS_EMPRESA.map((p) => [p.clave, String(empresa.parametros[p.clave] ?? "")])));
  const [errores, setErrores] = useState<Record<string, string>>({});
  const original = Object.fromEntries(PARAMETROS_EMPRESA.map((p) => [p.clave, String(empresa.parametros[p.clave] ?? "")]));
  const sucio = PARAMETROS_EMPRESA.some((p) => valores[p.clave] !== original[p.clave]);

  const guardar = useMutacion((cuerpo: ParametrosEmpresa) => apiEmpresa.parametros(cuerpo), {
    exito: "Parámetros actualizados. Se aplican en las próximas alertas, predicciones y recomendaciones.",
    avisarError: false,
    onExito: (e) => cliente.setQueryData(["empresa"], e),
  });

  async function enviar(ev: React.FormEvent) {
    ev.preventDefault();
    setErrorGeneral(null);
    const nuevos: Record<string, string> = {};
    for (const p of PARAMETROS_EMPRESA) {
      const t = valores[p.clave].trim();
      if (!/^\d+$/.test(t)) nuevos[p.clave] = "Escriba un número entero";
      else if (Number(t) < p.min || Number(t) > p.max) nuevos[p.clave] = `Debe estar entre ${p.min} y ${p.max}`;
    }
    setErrores(nuevos);
    if (Object.keys(nuevos).length) return;
    try {
      await guardar.mutateAsync(Object.fromEntries(PARAMETROS_EMPRESA.map((p) => [p.clave, Number(valores[p.clave])])) as ParametrosEmpresa);
    } catch (e) {
      const campos = Object.fromEntries(PARAMETROS_EMPRESA.map((p) => [p.clave, p.clave]));
      const mapa: Record<string, string> = {};
      const general = aplicarErroresServidor(e, (campo, err) => (mapa[campo] = err.message ?? ""), Object.keys(campos));
      setErrores(mapa);
      setErrorGeneral(general);
    }
  }

  return (
    <Card>
      <CardHeader titulo="Parámetros de inventario y predicción" descripcion="Reglas que usan las alertas, la predicción de demanda y las recomendaciones." />
      <form noValidate className="grid gap-5 p-5 sm:grid-cols-2" onSubmit={enviar}>
        {errorGeneral && <Aviso tipo="error" className="sm:col-span-2">{errorGeneral}</Aviso>}
        {PARAMETROS_EMPRESA.map((p) => (
          <Input
            key={p.clave}
            etiqueta={p.etiqueta}
            inputMode="numeric"
            value={valores[p.clave]}
            disabled={!editable}
            ayuda={p.ayuda}
            error={errores[p.clave]}
            onChange={(e) => setValores((s) => ({ ...s, [p.clave]: e.target.value.replace(/\D/g, "") }))}
          />
        ))}
        {editable && (
          <div className="sm:col-span-2">
            <Button type="submit" cargando={guardar.isPending} disabled={!sucio}>Guardar parámetros</Button>
          </div>
        )}
      </form>
    </Card>
  );
}

export default function EmpresaPage() {
  const { tiene } = useAuth();
  const consulta = useQuery({ queryKey: ["empresa"], queryFn: apiEmpresa.obtener });
  const editable = tiene("empresa.editar");

  return (
    <>
      <EncabezadoPagina titulo="Empresa" descripcion="Datos generales y reglas de operación de su empresa." />
      {consulta.isPending && <PanelCargando etiqueta="Cargando los datos de la empresa…" />}
      {consulta.isError && <Card><EstadoError error={consulta.error} onReintentar={() => consulta.refetch()} /></Card>}
      {consulta.data && (
        <div className="grid items-start gap-6 xl:grid-cols-2">
          <FormularioDatos key={`d-${consulta.data.updated_at}`} empresa={consulta.data} editable={editable} />
          <FormularioParametros key={`p-${consulta.data.updated_at}`} empresa={consulta.data} editable={editable} />
        </div>
      )}
    </>
  );
}
