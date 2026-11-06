import { useCallback, useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Bot, ChevronDown, RotateCcw, SendHorizontal } from "lucide-react";
import { Aviso } from "@/components/ui/Aviso";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { apiAsistente } from "@/api/asistente";
import { cn } from "@/lib/cn";
import { mensajeDeError } from "@/lib/errors";
import type { AyudaAsistente, ContextoAsistente, RespuestaAsistente } from "@/types/api";
import { BloqueVista, Enlaces, TextoAsistente } from "./Bloques";

const MAX_CARACTERES = 500;

type Mensaje =
  | { id: number; rol: "usuario"; texto: string }
  | { id: number; rol: "asistente"; respuesta: RespuestaAsistente }
  | { id: number; rol: "error"; texto: string; pregunta: string };

function Chips({ preguntas, onElegir, deshabilitado, etiqueta }: { preguntas: string[]; onElegir: (p: string) => void; deshabilitado?: boolean; etiqueta: string }) {
  if (preguntas.length === 0) return null;
  return (
    <ul aria-label={etiqueta} className="flex flex-wrap gap-2">
      {preguntas.map((p) => (
        <li key={p}>
          <button
            type="button"
            disabled={deshabilitado}
            onClick={() => onElegir(p)}
            className="rounded-full border border-line-strong bg-surface-2 px-3 py-1.5 text-left text-[13px] text-ink-dim transition hover:border-accent/50 hover:bg-accent-dim hover:text-ink disabled:cursor-not-allowed disabled:opacity-50"
          >
            {p}
          </button>
        </li>
      ))}
    </ul>
  );
}

function Avatar() {
  return (
    <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-accent-dim text-accent-light ring-1 ring-accent/30" aria-hidden>
      <Bot className="size-4" />
    </span>
  );
}

function RespuestaVista({ respuesta, esUltima, ocupado, onPreguntar }: { respuesta: RespuestaAsistente; esUltima: boolean; ocupado: boolean; onPreguntar: (p: string) => void }) {
  const contexto = [respuesta.alcance, respuesta.periodo].filter(Boolean).join(" · ");
  return (
    <div className="flex gap-3">
      <Avatar />
      <div className="flex min-w-0 max-w-full flex-1 flex-col gap-3">
        <div className="rounded-2xl rounded-tl-md border border-line bg-surface-2 px-4 py-3">
          <span className="sr-only">Asistente: </span>
          <TextoAsistente texto={respuesta.texto} />
        </div>
        {respuesta.bloques?.map((b, i) => <BloqueVista key={i} bloque={b} />)}
        {respuesta.avisos && respuesta.avisos.length > 0 && (
          <ul className="flex flex-col gap-1.5">
            {respuesta.avisos.map((a) => (
              <li key={a}>
                <Aviso tipo="aviso" className="px-3 py-2 text-[13px]">
                  {a}
                </Aviso>
              </li>
            ))}
          </ul>
        )}
        {respuesta.enlaces && <Enlaces enlaces={respuesta.enlaces} />}
        {contexto && <p className="text-xs text-ink-faint">{contexto}</p>}
        {esUltima && respuesta.sugerencias && respuesta.sugerencias.length > 0 && (
          <div className="flex flex-col gap-1.5">
            <p className="text-xs font-medium text-ink-faint">Puedes preguntar también</p>
            <Chips preguntas={respuesta.sugerencias} onElegir={onPreguntar} deshabilitado={ocupado} etiqueta="Preguntas sugeridas" />
          </div>
        )}
      </div>
    </div>
  );
}

function Bienvenida({ ayuda, cargando, onPreguntar }: { ayuda?: AyudaAsistente; cargando: boolean; onPreguntar: (p: string) => void }) {
  return (
    <div className="flex gap-3">
      <Avatar />
      <div className="flex min-w-0 flex-1 flex-col gap-4">
        <div className="rounded-2xl rounded-tl-md border border-line bg-surface-2 px-4 py-3">
          <TextoAsistente texto={ayuda?.saludo ?? "Hola, soy el asistente de Inventia. Pregúntame por tu inventario, ventas, traslados, alertas o lo que necesites consultar."} />
          <p className="mt-2 text-[13px] text-ink-dim">
            Escribe con tus palabras, con o sin tildes. Solo consulto datos: no registro ni modifico nada, y respondo según tu rol y tu sede.
          </p>
        </div>
        {cargando ? (
          <div className="flex flex-wrap gap-2" aria-hidden>
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-8 w-40" />
            <Skeleton className="h-8 w-56" />
          </div>
        ) : (
          ayuda && (
            <>
              <Chips preguntas={ayuda.iniciales} onElegir={onPreguntar} etiqueta="Preguntas para empezar" />
              {ayuda.grupos.length > 0 && (
                <div className="flex flex-col gap-2">
                  <p className="text-xs font-medium text-ink-faint">Qué puedes preguntar</p>
                  {ayuda.grupos.map((g) => (
                    <details key={g.titulo} className="group rounded-(--radius-control) border border-line bg-surface">
                      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-3 py-2 text-[13px] font-medium text-ink-dim hover:text-ink [&::-webkit-details-marker]:hidden">
                        {g.titulo}
                        <ChevronDown className="size-4 transition group-open:rotate-180" aria-hidden />
                      </summary>
                      <div className="border-t border-line px-3 py-3">
                        <Chips preguntas={g.ejemplos} onElegir={onPreguntar} etiqueta={`Ejemplos de ${g.titulo}`} />
                      </div>
                    </details>
                  ))}
                </div>
              )}
            </>
          )
        )}
      </div>
    </div>
  );
}

function Escribiendo() {
  return (
    <div className="flex gap-3" role="status">
      <Avatar />
      <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-md border border-line bg-surface-2 px-4 py-3.5" aria-label="El asistente está consultando">
        <span className="sr-only">Consultando…</span>
        {[0, 1, 2].map((i) => (
          <span key={i} aria-hidden className="size-1.5 animate-pulse rounded-full bg-ink-faint motion-reduce:animate-none" style={{ animationDelay: `${i * 160}ms` }} />
        ))}
      </div>
    </div>
  );
}

export default function AsistentePage() {
  const ayuda = useQuery({ queryKey: ["asistente", "ayuda"], queryFn: apiAsistente.ayuda, staleTime: 5 * 60_000 });
  const [mensajes, setMensajes] = useState<Mensaje[]>([]);
  const [borrador, setBorrador] = useState("");
  const idCampo = useId();
  const campo = useRef<HTMLTextAreaElement>(null);
  const fin = useRef<HTMLDivElement>(null);
  const contexto = useRef<ContextoAsistente | null>(null);
  const siguiente = useRef(1);
  const generacion = useRef(0); // «Nueva conversación» invalida las respuestas que aún no llegaron

  const consulta = useMutation({
    mutationFn: ({ pregunta }: { pregunta: string; generacion: number }) => apiAsistente.preguntar(pregunta, contexto.current),
    onSuccess: (respuesta, { generacion: g }) => {
      if (g !== generacion.current) return;
      contexto.current = respuesta.contexto;
      setMensajes((m) => [...m, { id: siguiente.current++, rol: "asistente", respuesta }]);
    },
    onError: (error, { pregunta, generacion: g }) => {
      if (g !== generacion.current) return;
      setMensajes((m) => [...m, { id: siguiente.current++, rol: "error", texto: mensajeDeError(error), pregunta }]);
    },
  });
  const ocupado = consulta.isPending;

  const preguntar = useCallback(
    (texto: string) => {
      const pregunta = texto.trim().slice(0, MAX_CARACTERES);
      if (!pregunta || consulta.isPending) return;
      setMensajes((m) => [...m, { id: siguiente.current++, rol: "usuario", texto: pregunta }]);
      setBorrador("");
      consulta.mutate({ pregunta, generacion: generacion.current });
      campo.current?.focus();
    },
    [consulta],
  );

  const reiniciar = () => {
    generacion.current += 1;
    contexto.current = null;
    setMensajes([]);
    setBorrador("");
    consulta.reset();
    campo.current?.focus();
  };

  // Al llegar un mensaje nuevo, la conversación se desplaza hasta el final (sin animar si la persona prefiere menos movimiento).
  useEffect(() => {
    if (mensajes.length === 0 && !ocupado) return;
    const reducido = typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    fin.current?.scrollIntoView?.({ block: "end", behavior: reducido ? "auto" : "smooth" });
  }, [mensajes.length, ocupado]);

  const alTeclear = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      preguntar(borrador);
    }
  };

  const ultimaRespuesta = [...mensajes].reverse().find((m) => m.rol === "asistente")?.id;
  const restantes = MAX_CARACTERES - borrador.length;

  return (
    <>
      <EncabezadoPagina
        titulo="Asistente"
        descripcion="Pregunta en lenguaje natural por tu inventario, ventas, traslados, alertas, predicción y más, o pide que te explique un término o cómo se hace una tarea. Puedes hacer hasta tres preguntas en un mensaje. Responde con los datos reales de tu empresa, según tu rol y tu sede."
        acciones={
          <Button variante="secondary" tamano="sm" icono={<RotateCcw className="size-4" aria-hidden />} onClick={reiniciar} disabled={mensajes.length === 0 && !ocupado}>
            Nueva conversación
          </Button>
        }
      />

      <div className="flex flex-col gap-4">
        <Card>
          <div role="log" aria-live="polite" aria-relevant="additions" aria-label="Conversación con el asistente" className="flex min-h-[45dvh] flex-col gap-5 p-4 sm:p-6">
            {mensajes.length === 0 && <Bienvenida ayuda={ayuda.data} cargando={ayuda.isLoading} onPreguntar={preguntar} />}
            {mensajes.map((m) => {
              if (m.rol === "usuario") {
                return (
                  <div key={m.id} className="flex justify-end">
                    <p className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-br-md bg-accent px-4 py-2.5 text-sm text-white">
                      <span className="sr-only">Tú: </span>
                      {m.texto}
                    </p>
                  </div>
                );
              }
              if (m.rol === "error") {
                return (
                  <div key={m.id} className="flex gap-3">
                    <Avatar />
                    <Aviso tipo="error" titulo="No pude responder" className="flex-1">
                      <p>{m.texto}</p>
                      <Button variante="secondary" tamano="sm" className="mt-2" onClick={() => preguntar(m.pregunta)} disabled={ocupado}>
                        Reintentar
                      </Button>
                    </Aviso>
                  </div>
                );
              }
              return <RespuestaVista key={m.id} respuesta={m.respuesta} esUltima={m.id === ultimaRespuesta && !ocupado} ocupado={ocupado} onPreguntar={preguntar} />;
            })}
            {ocupado && <Escribiendo />}
            <div ref={fin} aria-hidden className="scroll-mb-44" />
          </div>
        </Card>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            preguntar(borrador);
          }}
          className="sticky bottom-3 z-10 rounded-(--radius-panel) border border-line-strong bg-surface p-3 shadow-(--shadow-pop)"
        >
          <label htmlFor={idCampo} className="sr-only">
            Escribe tu pregunta
          </label>
          <div className="flex items-end gap-2">
            <textarea
              id={idCampo}
              ref={campo}
              value={borrador}
              onChange={(e) => setBorrador(e.target.value)}
              onKeyDown={alTeclear}
              maxLength={MAX_CARACTERES}
              rows={1}
              placeholder="Escribe tu pregunta…"
              className="max-h-40 min-h-11 w-full resize-none rounded-(--radius-control) border border-line-strong bg-surface-2 px-3.5 py-2.5 text-sm text-ink [field-sizing:content] placeholder:text-ink-faint focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
            />
            <Button type="submit" className="h-11" cargando={ocupado} disabled={!borrador.trim()} icono={<SendHorizontal className="size-4" aria-hidden />}>
              Enviar
            </Button>
          </div>
          <p className={cn("mt-1.5 flex justify-between gap-3 text-xs", restantes <= 50 ? "text-warning" : "text-ink-faint")}>
            <span>Enter para enviar · Mayús + Enter para una línea nueva</span>
            {restantes <= 100 && <span aria-live="polite">{restantes} caracteres disponibles</span>}
          </p>
        </form>
      </div>
    </>
  );
}
