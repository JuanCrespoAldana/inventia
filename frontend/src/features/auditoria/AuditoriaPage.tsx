import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronRight } from "lucide-react";
import { apiAuditoria } from "@/api/analitica";
import { useAuth } from "@/auth/AuthContext";
import { Aviso } from "@/components/ui/Aviso";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Tabla } from "@/components/ui/DataTable";
import { FiltroFecha, FiltroSelect } from "@/components/ui/Field";
import { BarraFiltros } from "@/components/ui/FiltrosBarra";
import { EncabezadoPagina } from "@/components/ui/PageHeader";
import { Paginacion } from "@/components/ui/Pagination";
import { Busqueda } from "@/components/ui/SearchInput";
import { useFiltros } from "@/hooks/useFiltros";
import { estado, RESULTADO_AUDITORIA } from "@/lib/etiquetas";
import { fechaHora } from "@/lib/format";
import type { RegistroAuditoria } from "@/types/api";

function legible(codigo: string): string {
  const t = codigo.replaceAll("_", " ");
  return t.charAt(0).toUpperCase() + t.slice(1);
}

function valorDetalle(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

function Detalle({ r, verIp }: { r: RegistroAuditoria; verIp: boolean }) {
  const entradas = Object.entries(r.detalle ?? {});
  return (
    <div className="grid gap-4 text-sm lg:grid-cols-2">
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5">
        <dt className="text-ink-faint">Entidad</dt>
        <dd>{r.entidad ? `${legible(r.entidad)}${r.entidad_id ? ` #${r.entidad_id}` : ""}` : "—"}</dd>
        {verIp && (
          <>
            <dt className="text-ink-faint">Dirección IP</dt>
            <dd className="font-mono text-[13px]">{r.ip ?? "—"}</dd>
          </>
        )}
        <dt className="text-ink-faint">Registro</dt>
        <dd className="tabular">#{r.id}</dd>
      </dl>
      <div>
        <p className="mb-1.5 text-ink-faint">Detalle</p>
        {entradas.length === 0 ? (
          <p className="text-ink-dim">Sin datos adicionales.</p>
        ) : (
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5">
            {entradas.map(([k, v]) => (
              <div key={k} className="contents">
                <dt className="text-ink-faint">{legible(k)}</dt>
                <dd className="break-words font-mono text-[13px] text-ink-dim">{valorDetalle(v)}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>
    </div>
  );
}

export default function AuditoriaPage() {
  const { tiene } = useAuth();
  const completa = tiene("auditoria.ver");
  const opciones = useQuery({ queryKey: ["auditoria", "opciones"], queryFn: apiAuditoria.opciones, staleTime: 300_000 });
  const { filtros, pagina, tamano, cambiar, irAPagina, limpiar, hayFiltros } = useFiltros({ q: "", modulo: "", accion: "", resultado: "", desde: "", hasta: "" }, 25);
  const [abierta, setAbierta] = useState<Set<number>>(new Set());

  const lista = useQuery({
    queryKey: ["auditoria", filtros, pagina],
    queryFn: () => apiAuditoria.listar({ q: filtros.q, modulo: filtros.modulo, accion: filtros.accion, resultado: filtros.resultado, desde: filtros.desde, hasta: filtros.hasta, pagina, tamano }),
    placeholderData: keepPreviousData,
  });

  function alternar(r: RegistroAuditoria) {
    setAbierta((prev) => {
      const s = new Set(prev);
      if (!s.delete(r.id)) s.add(r.id);
      return s;
    });
  }

  return (
    <>
      <EncabezadoPagina
        titulo={completa ? "Auditoría" : "Historial de operaciones"}
        descripcion={completa ? "Registro de la actividad de los usuarios: accesos, cambios y operaciones. Los registros no se pueden modificar ni eliminar." : "Operaciones de negocio registradas en su empresa o sede. Los registros no se pueden modificar ni eliminar."}
      />
      {!completa && <Aviso tipo="info" className="mb-5">Su rol permite consultar las operaciones, pero no los accesos al sistema ni las direcciones IP.</Aviso>}
      <Card>
        <BarraFiltros hayFiltros={hayFiltros} onLimpiar={limpiar}>
          <Busqueda valor={filtros.q} onCambiar={(q) => cambiar({ q })} placeholder="Buscar por usuario, acción o entidad…" className="sm:max-w-sm" />
          <FiltroSelect etiqueta="Módulo" value={filtros.modulo} onChange={(e) => cambiar({ modulo: e.target.value })}>
            <option value="">Todos los módulos</option>
            {opciones.data?.modulos.map((m) => (
              <option key={m} value={m}>{legible(m)}</option>
            ))}
          </FiltroSelect>
          <FiltroSelect etiqueta="Acción" value={filtros.accion} onChange={(e) => cambiar({ accion: e.target.value })}>
            <option value="">Todas las acciones</option>
            {opciones.data?.acciones.map((a) => (
              <option key={a} value={a}>{legible(a)}</option>
            ))}
          </FiltroSelect>
          <FiltroSelect etiqueta="Resultado" value={filtros.resultado} onChange={(e) => cambiar({ resultado: e.target.value })}>
            <option value="">Todos los resultados</option>
            <option value="exitoso">Exitosos</option>
            <option value="fallido">Fallidos</option>
          </FiltroSelect>
          <FiltroFecha etiqueta="Desde" value={filtros.desde} max={filtros.hasta || undefined} onChange={(e) => cambiar({ desde: e.target.value })} />
          <FiltroFecha etiqueta="Hasta" value={filtros.hasta} min={filtros.desde || undefined} onChange={(e) => cambiar({ hasta: e.target.value })} />
        </BarraFiltros>
        <Tabla
          descripcion="Registros de auditoría"
          idDe={(r) => r.id}
          filas={lista.data?.items}
          cargando={lista.isFetching}
          error={lista.error}
          onReintentar={() => lista.refetch()}
          onFila={alternar}
          abierta={(r) => abierta.has(r.id)}
          detalle={(r) => <Detalle r={r} verIp={completa} />}
          vacio={{ titulo: hayFiltros ? "Sin resultados" : "Aún no hay registros", descripcion: hayFiltros ? "Pruebe con otros filtros o con otro rango de fechas." : undefined }}
          columnas={[
            {
              clave: "fecha",
              encabezado: "Fecha",
              celda: (r) => (
                <span className="flex items-center gap-2 whitespace-nowrap text-ink-dim">
                  {abierta.has(r.id) ? <ChevronDown className="size-4 text-ink-faint" aria-hidden /> : <ChevronRight className="size-4 text-ink-faint" aria-hidden />}
                  {fechaHora(r.fecha)}
                </span>
              ),
            },
            { clave: "usuario", encabezado: "Usuario", celda: (r) => <span>{r.usuario_email ?? <span className="text-ink-faint">Sistema</span>}</span> },
            { clave: "modulo", encabezado: "Módulo", desde: "md", celda: (r) => <span className="text-ink-dim">{legible(r.modulo)}</span> },
            { clave: "accion", encabezado: "Acción", celda: (r) => <span className="font-medium">{legible(r.accion)}</span> },
            { clave: "entidad", encabezado: "Entidad", desde: "lg", celda: (r) => <span className="text-ink-dim">{r.entidad ? `${legible(r.entidad)}${r.entidad_id ? ` #${r.entidad_id}` : ""}` : "—"}</span> },
            { clave: "resultado", encabezado: "Resultado", celda: (r) => { const e = estado(RESULTADO_AUDITORIA, r.resultado); return <Badge tono={e.tono}>{e.etiqueta}</Badge>; } },
          ]}
        />
        {lista.data && <Paginacion pagina={lista.data.pagina} paginas={lista.data.paginas} total={lista.data.total} tamano={lista.data.tamano} onCambiar={irAPagina} />}
      </Card>
    </>
  );
}
