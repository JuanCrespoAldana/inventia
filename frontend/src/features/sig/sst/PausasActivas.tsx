import { useCallback, useEffect, useRef, useState } from "react";
import { useIsMutating, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiSst } from "@/api/sig";
import { useAuth } from "@/auth/AuthContext";
import { hayBloqueos } from "@/lib/bloqueoPausas";
import { mensajeDeError } from "@/lib/errors";
import type { PausaMostrada } from "@/types/api";
import { ModalPausa } from "./ModalPausa";
import { calcularProximaPausa, ESPERA_ESCRITURA_MS, puedeMostrarPausa, REINTENTO_MS, REVISION_MS } from "./programacion";

const CANAL = "inventia-sst-pausas";
type Mensaje = { tipo: "abierta" | "cerrada"; pausaId: number; pestana: string };

/**
 * Programador global de pausas activas. Se monta una sola vez en el diseño de la aplicación.
 * - Solo actúa para quien el servidor indica que le aplican (las personas administradoras quedan excluidas).
 * - Pide la pausa al servidor cuando toca y NO hay nada crítico en curso (formularios abiertos, guardados
 *   en marcha); mientras tanto espera. El servidor además impide repetirlas antes de tiempo.
 * - Con varias pestañas abiertas solo una muestra la pausa (BroadcastChannel); si coinciden gana una de forma determinista.
 */
export function PausasActivas() {
  const { sesion } = useAuth();
  const cliente = useQueryClient();
  const mutaciones = useIsMutating();
  const [idPestana] = useState(() => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`);
  const canal = useRef<BroadcastChannel | null>(null);
  const ocupadas = useRef(new Set<number>());

  const [pausa, setPausa] = useState<PausaMostrada | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pausaRef = useRef<PausaMostrada | null>(null);
  useEffect(() => {
    pausaRef.current = pausa;
  }, [pausa]);

  const estado = useQuery({
    queryKey: ["sst", "estado", sesion?.id],
    queryFn: apiSst.estado,
    enabled: Boolean(sesion),
    staleTime: 5 * 60_000,
    refetchInterval: 10 * 60_000, // recoge cambios de configuración hechos por la administración
  });

  /* Reloj del servidor: evita depender de que el reloj del equipo esté bien. */
  const desfase = useRef(0);
  const baseInicial = useRef<number | null>(null);
  const proxima = useRef<number | null>(null);
  const iniciando = useRef(false);
  const mutacionesRef = useRef(0);
  useEffect(() => {
    mutacionesRef.current = mutaciones;
  }, [mutaciones]);

  const ahoraServidor = useCallback(() => Date.now() + desfase.current, []);

  /* Última vez que se tecleó en un campo: no se interrumpe a quien está escribiendo. */
  const ultimaEscritura = useRef(0);
  useEffect(() => {
    const alTeclear = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable)) ultimaEscritura.current = Date.now();
    };
    document.addEventListener("keydown", alTeclear, true);
    return () => document.removeEventListener("keydown", alTeclear, true);
  }, []);

  useEffect(() => {
    const e = estado.data;
    if (!e) return;
    desfase.current = new Date(e.ahora).getTime() - Date.now();
    if (!e.aplica || !e.activo) {
      proxima.current = null;
      return;
    }
    baseInicial.current ??= new Date(e.ahora).getTime();
    const ahora = ahoraServidor();
    if (e.pendiente && !ocupadas.current.has(e.pendiente.id)) {
      proxima.current = ahora; // quedó una pausa abierta (por ejemplo, al recargar): se retoma cuando se pueda
      return;
    }
    proxima.current = calcularProximaPausa({
      ahora,
      ultimaPausa: e.ultima_pausa_en ? new Date(e.ultima_pausa_en).getTime() : baseInicial.current,
      intervaloMin: e.intervalo_minutos,
    });
  }, [estado.data, ahoraServidor]);

  const avisarOtrasPestanas = useCallback((m: Omit<Mensaje, "pestana">) => {
    canal.current?.postMessage({ ...m, pestana: idPestana } satisfies Mensaje);
  }, [idPestana]);

  const intentar = useCallback(async () => {
    const e = estado.data;
    if (!e || !e.aplica || !e.activo || proxima.current === null || iniciando.current) return;
    if (
      !puedeMostrarPausa({
        ahora: ahoraServidor(),
        proxima: proxima.current,
        hayBloqueos: hayBloqueos(),
        mutacionesEnCurso: mutacionesRef.current,
        pestanaVisible: typeof document === "undefined" || document.visibilityState === "visible",
        pausaAbierta: pausaRef.current !== null,
        escribiendo: Date.now() - ultimaEscritura.current < ESPERA_ESCRITURA_MS,
      })
    )
      return;
    iniciando.current = true;
    try {
      const r = await apiSst.iniciar();
      if (r.mostrar && r.pausa) {
        if (!r.pausa.actividad) {
          // La actividad se eliminó mientras tanto: no hay nada que mostrar, la pausa se cierra como omitida.
          await apiSst.cerrar(r.pausa.id, "omitida");
          proxima.current = ahoraServidor() + 60_000;
        } else if (ocupadas.current.has(r.pausa.id)) {
          proxima.current = ahoraServidor() + 30_000; // otra pestaña ya la está mostrando
        } else if (!hayBloqueos() && mutacionesRef.current === 0) {
          setError(null);
          setPausa(r.pausa);
          avisarOtrasPestanas({ tipo: "abierta", pausaId: r.pausa.id });
        } else {
          proxima.current = ahoraServidor() + 5_000; // apareció algo crítico mientras se pedía: se reintenta enseguida
        }
      } else if (r.proxima_en) {
        proxima.current = new Date(r.proxima_en).getTime();
      } else {
        proxima.current = ahoraServidor() + REINTENTO_MS;
        void cliente.invalidateQueries({ queryKey: ["sst", "estado"] });
      }
    } catch {
      proxima.current = ahoraServidor() + 60_000; // sin conexión o error temporal: se reintenta más tarde
    } finally {
      iniciando.current = false;
    }
  }, [estado.data, avisarOtrasPestanas, cliente, ahoraServidor]);

  useEffect(() => {
    const id = window.setInterval(() => void intentar(), REVISION_MS);
    const alVolver = () => document.visibilityState === "visible" && void intentar();
    document.addEventListener("visibilitychange", alVolver);
    const primero = window.setTimeout(() => void intentar(), 1500);
    return () => {
      window.clearInterval(id);
      window.clearTimeout(primero);
      document.removeEventListener("visibilitychange", alVolver);
    };
  }, [intentar]);

  /* Coordinación entre pestañas. */
  useEffect(() => {
    if (typeof BroadcastChannel === "undefined") return;
    const c = new BroadcastChannel(CANAL);
    canal.current = c;
    c.onmessage = (ev: MessageEvent<Mensaje>) => {
      const m = ev.data;
      if (!m || m.pestana === idPestana) return;
      if (m.tipo === "abierta") {
        ocupadas.current.add(m.pausaId);
        // Si las dos pestañas la abrieron a la vez, se queda la de identificador menor.
        if (pausaRef.current?.id === m.pausaId && m.pestana < idPestana) setPausa(null);
      } else {
        ocupadas.current.delete(m.pausaId);
        void cliente.invalidateQueries({ queryKey: ["sst", "estado"] });
      }
    };
    return () => {
      c.close();
      canal.current = null;
    };
  }, [cliente, idPestana]);

  const actividad = pausa?.actividad ?? null;

  async function resolver(resultado: "realizada" | "omitida", segundos: number) {
    if (!pausa) return;
    setGuardando(true);
    setError(null);
    try {
      await apiSst.cerrar(pausa.id, resultado, segundos);
      avisarOtrasPestanas({ tipo: "cerrada", pausaId: pausa.id });
      setPausa(null);
      await cliente.invalidateQueries({ queryKey: ["sst"] });
    } catch (e) {
      setError(mensajeDeError(e));
    } finally {
      setGuardando(false);
    }
  }

  if (!actividad || !pausa) return null;
  return (
    <ModalPausa
      key={pausa.id}
      actividad={actividad}
      guardando={guardando}
      error={error}
      onRealizada={(s) => void resolver("realizada", s)}
      onOmitida={(s) => void resolver("omitida", s)}
    />
  );
}
