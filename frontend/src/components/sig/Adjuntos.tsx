import { useRef, useState } from "react";
import { Download, FileImage, FileText, Paperclip, Trash2, X } from "lucide-react";
import { apiAdjuntos } from "@/api/sig";
import { Aviso } from "@/components/ui/Aviso";
import { Button, IconButton } from "@/components/ui/Button";
import { useMutacion } from "@/hooks/useMutacion";
import { mensajeDeError } from "@/lib/errors";
import { fechaHora, tamanoArchivo } from "@/lib/format";
import type { AdjuntoSig, EntidadAdjunto } from "@/types/api";

/** Mismos límites que valida el servidor (que además comprueba el contenido real del archivo). */
export const ADJUNTO_MAX_BYTES = 3 * 1024 * 1024;
export const ADJUNTO_MAX_POR_REGISTRO = 5;
const TIPOS = ["image/jpeg", "image/png", "image/webp", "application/pdf"];
const ACEPTAR = ".jpg,.jpeg,.png,.webp,.pdf,image/jpeg,image/png,image/webp,application/pdf";

/** Devuelve el motivo por el que un archivo no se puede adjuntar, o `null` si es válido. */
export function validarArchivo(archivo: Pick<File, "name" | "size" | "type">, yaHay: number, max = ADJUNTO_MAX_POR_REGISTRO): string | null {
  if (yaHay >= max) return `Solo se pueden adjuntar hasta ${max} archivos.`;
  if (archivo.size === 0) return `«${archivo.name}» está vacío.`;
  if (archivo.size > ADJUNTO_MAX_BYTES) return `«${archivo.name}» pesa ${tamanoArchivo(archivo.size)}; el máximo es ${tamanoArchivo(ADJUNTO_MAX_BYTES)}.`;
  const porNombre = /\.(jpe?g|png|webp|pdf)$/i.test(archivo.name);
  if (!(TIPOS.includes(archivo.type) || (archivo.type === "" && porNombre)) || !porNombre) return `«${archivo.name}»: solo se aceptan imágenes JPG, PNG o WebP y documentos PDF.`;
  return null;
}

/** Sube los archivos elegidos al registro recién creado. Devuelve los mensajes de los que fallaron. */
export async function subirArchivos(entidad: EntidadAdjunto, entidadId: number, archivos: File[]): Promise<string[]> {
  const fallos: string[] = [];
  for (const archivo of archivos) {
    try {
      await apiAdjuntos.subir(entidad, entidadId, archivo);
    } catch (e) {
      fallos.push(`«${archivo.name}»: ${mensajeDeError(e)}`);
    }
  }
  return fallos;
}

function IconoArchivo({ tipo }: { tipo: string }) {
  const Icono = tipo === "application/pdf" ? FileText : FileImage;
  return <Icono className="size-4 shrink-0 text-ink-faint" aria-hidden />;
}

/** Selector de evidencias para formularios de creación (se suben cuando el registro ya existe). */
export function SelectorArchivos({ archivos, onChange, max = ADJUNTO_MAX_POR_REGISTRO }: { archivos: File[]; onChange: (a: File[]) => void; max?: number }) {
  const entrada = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  function agregar(lista: FileList | null) {
    if (!lista) return;
    const siguientes = [...archivos];
    let problema: string | null = null;
    for (const f of Array.from(lista)) {
      const motivo = validarArchivo(f, siguientes.length, max);
      if (motivo) problema ??= motivo;
      else siguientes.push(f);
    }
    setError(problema);
    onChange(siguientes);
    if (entrada.current) entrada.current.value = "";
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-3">
        <Button variante="secondary" tamano="sm" icono={<Paperclip className="size-4" aria-hidden />} onClick={() => entrada.current?.click()} disabled={archivos.length >= max}>
          Adjuntar evidencias
        </Button>
        <span className="text-xs text-ink-faint">Opcional · imágenes JPG, PNG, WebP o PDF · máx. {tamanoArchivo(ADJUNTO_MAX_BYTES)} cada una · hasta {max}</span>
        <input ref={entrada} type="file" multiple accept={ACEPTAR} className="sr-only" tabIndex={-1} aria-label="Elegir archivos de evidencia" onChange={(e) => agregar(e.target.files)} />
      </div>
      {error && <Aviso tipo="aviso">{error}</Aviso>}
      {archivos.length > 0 && (
        <ul className="flex flex-col gap-1.5" aria-label="Archivos por adjuntar">
          {archivos.map((f, i) => (
            <li key={`${f.name}-${i}`} className="flex items-center gap-3 rounded-(--radius-control) border border-line bg-surface-2 px-3 py-1.5 text-sm">
              <IconoArchivo tipo={f.type} />
              <span className="min-w-0 flex-1 truncate">{f.name}</span>
              <span className="tabular shrink-0 text-xs text-ink-faint">{tamanoArchivo(f.size)}</span>
              <IconButton etiqueta={`Quitar ${f.name}`} className="size-7" onClick={() => onChange(archivos.filter((_, j) => j !== i))}>
                <X className="size-4" aria-hidden />
              </IconButton>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Evidencias de un registro existente: listar, descargar, agregar y eliminar (según los permisos que informa el servidor). */
export function PanelAdjuntos({
  entidad,
  entidadId,
  archivos,
  puedeAdjuntar,
  invalidar,
}: {
  entidad: EntidadAdjunto;
  entidadId: number;
  archivos: AdjuntoSig[];
  puedeAdjuntar: boolean;
  invalidar: string[][];
}) {
  const entrada = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  const subir = useMutacion((f: File) => apiAdjuntos.subir(entidad, entidadId, f), {
    exito: "Archivo adjuntado.",
    invalidar,
    avisarError: false,
  });
  const quitar = useMutacion((id: number) => apiAdjuntos.eliminar(id), { exito: "Archivo eliminado.", invalidar });
  const descargar = useMutacion((a: AdjuntoSig) => apiAdjuntos.descargar(a));

  async function elegir(lista: FileList | null) {
    setError(null);
    const f = lista?.[0];
    if (entrada.current) entrada.current.value = "";
    if (!f) return;
    const motivo = validarArchivo(f, archivos.length);
    if (motivo) return setError(motivo);
    try {
      await subir.mutateAsync(f);
    } catch (e) {
      setError(mensajeDeError(e));
    }
  }

  return (
    <section aria-label="Evidencias" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-[13px] font-semibold uppercase tracking-wide text-ink-faint">Evidencias ({archivos.length})</h3>
        {puedeAdjuntar && archivos.length < ADJUNTO_MAX_POR_REGISTRO && (
          <>
            <Button variante="secondary" tamano="sm" icono={<Paperclip className="size-4" aria-hidden />} cargando={subir.isPending} onClick={() => entrada.current?.click()}>
              Adjuntar archivo
            </Button>
            <input ref={entrada} type="file" accept={ACEPTAR} className="sr-only" tabIndex={-1} aria-label="Elegir archivo de evidencia" onChange={(e) => void elegir(e.target.files)} />
          </>
        )}
      </div>
      {error && <Aviso tipo="error">{error}</Aviso>}
      {archivos.length === 0 ? (
        <p className="text-sm text-ink-faint">No hay evidencias adjuntas.</p>
      ) : (
        <ul className="flex flex-col gap-1.5">
          {archivos.map((a) => (
            <li key={a.id} className="flex items-center gap-3 rounded-(--radius-control) border border-line bg-surface-2 px-3 py-2 text-sm">
              <IconoArchivo tipo={a.tipo_mime} />
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">{a.nombre}</p>
                <p className="text-xs text-ink-faint">
                  {tamanoArchivo(a.tamano)} · {a.subido_por_nombre ?? "—"} · {fechaHora(a.created_at)}
                </p>
              </div>
              <IconButton etiqueta={`Descargar ${a.nombre}`} onClick={() => descargar.mutate(a)} disabled={descargar.isPending}>
                <Download className="size-4" aria-hidden />
              </IconButton>
              {a.puede_eliminar && (
                <IconButton etiqueta={`Eliminar ${a.nombre}`} onClick={() => quitar.mutate(a.id)} disabled={quitar.isPending} className="hover:text-danger">
                  <Trash2 className="size-4" aria-hidden />
                </IconButton>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
