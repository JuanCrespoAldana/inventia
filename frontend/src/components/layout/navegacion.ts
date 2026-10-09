import {
  Activity,
  BarChart3,
  Bell,
  Boxes,
  Building2,
  ClipboardList,
  FileBarChart,
  KeyRound,
  Layers,
  LayoutDashboard,
  MapPin,
  PackageSearch,
  Receipt,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Tags,
  Truck,
  Users,
  type LucideIcon,
} from "lucide-react";
import type { Sesion } from "@/types/api";
import { tieneAlguno, tienePermiso } from "@/lib/permisos";

export interface ItemNavegacion {
  ruta: string;
  etiqueta: string;
  icono: LucideIcon;
  visible: (s: Sesion) => boolean;
  fin?: boolean;
}

export interface GrupoNavegacion {
  titulo: string | null;
  items: ItemNavegacion[];
}

const alguno = (...c: string[]) => (s: Sesion) => tieneAlguno(s, ...c);

export const NAVEGACION: GrupoNavegacion[] = [
  { titulo: null, items: [{ ruta: "/", etiqueta: "Panel de control", icono: LayoutDashboard, visible: () => true, fin: true }] },
  {
    titulo: "Inventario",
    items: [
      { ruta: "/inventario", etiqueta: "Existencias", icono: Boxes, visible: alguno("inventario.ver"), fin: true },
      { ruta: "/inventario/consolidado", etiqueta: "Consolidado", icono: Layers, visible: alguno("inventario.consolidado") },
      { ruta: "/movimientos", etiqueta: "Movimientos", icono: Activity, visible: alguno("movimientos.ver") },
      { ruta: "/productos", etiqueta: "Productos", icono: PackageSearch, visible: alguno("productos.ver") },
      { ruta: "/categorias", etiqueta: "Categorías", icono: Tags, visible: alguno("categorias.ver") },
    ],
  },
  {
    titulo: "Operación",
    items: [
      { ruta: "/ventas", etiqueta: "Ventas", icono: Receipt, visible: alguno("ventas.ver", "ventas.registrar") },
      { ruta: "/traslados", etiqueta: "Traslados", icono: Truck, visible: alguno("traslados.ver", "traslados.solicitar") },
      { ruta: "/alertas", etiqueta: "Alertas", icono: Bell, visible: alguno("alertas.ver") },
    ],
  },
  {
    titulo: "Inteligencia",
    items: [
      { ruta: "/predicciones", etiqueta: "Predicción de demanda", icono: BarChart3, visible: alguno("prediccion.ver") },
      { ruta: "/recomendaciones", etiqueta: "Recomendaciones", icono: Sparkles, visible: alguno("recomendaciones.ver") },
      {
        ruta: "/reportes",
        etiqueta: "Reportes",
        icono: FileBarChart,
        visible: alguno("reportes.inventario", "reportes.ventas", "reportes.movimientos", "reportes.traslados", "reportes.alertas", "reportes.predicciones", "reportes.recomendaciones"),
      },
    ],
  },
  {
    titulo: "Administración",
    items: [
      { ruta: "/empresa", etiqueta: "Empresa", icono: Building2, visible: alguno("empresa.ver") },
      { ruta: "/sedes", etiqueta: "Sedes", icono: MapPin, visible: (s) => tienePermiso(s, "sedes.ver") && (s.rol.alcance === "empresa" || tieneAlguno(s, "sedes.editar", "sedes.crear")) },
      { ruta: "/usuarios", etiqueta: "Usuarios", icono: Users, visible: alguno("usuarios.ver") },
      { ruta: "/roles", etiqueta: "Roles y permisos", icono: ShieldCheck, visible: (s) => tienePermiso(s, "roles.ver", "usuarios.ver") },
      { ruta: "/auditoria", etiqueta: "Auditoría", icono: ScrollText, visible: alguno("auditoria.ver", "auditoria.operaciones") },
      { ruta: "/integraciones", etiqueta: "Agentes de IA", icono: KeyRound, visible: alguno("agentes.gestionar") },
    ],
  },
];

export function gruposVisibles(sesion: Sesion): GrupoNavegacion[] {
  return NAVEGACION.map((g) => ({ ...g, items: g.items.filter((i) => i.visible(sesion)) })).filter((g) => g.items.length > 0);
}

export const ICONO_PERFIL = ClipboardList;
