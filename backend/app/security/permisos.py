"""Catálogo de permisos y roles del sistema.

Fuente de verdad: la matriz de casos de uso (Tabla 19) del documento de grado. Los permisos
se definen aquí y se sincronizan con la base de datos al iniciar (``sincronizar_permisos``);
los roles del sistema se crean para cada empresa con los permisos por defecto indicados.

Decisiones respecto al documento (registradas en docs/DECISIONES.md):
 - D-03  El Administrador recibe TODOS los permisos (también los de «generar predicción»,
         que la matriz atribuye al analista) para que nunca quede un proceso sin responsable.
 - D-04  Sedes, categorías y productos son de lectura para todo rol que consulta inventario:
         sin ellos las pantallas no podrían mostrar nombres ni filtros.
 - D-05  La anulación de ventas, la configuración de niveles mínimos/máximos y el
         recálculo de alertas no figuran en la matriz; se asignan al encargado y al administrador.
 - D-28  El Sistema Integrado de Gestión (PQRS, SST, calidad y gestión ambiental) se añadió después de la
         matriz: todos los roles envían PQRS, consultan SST/calidad/ambiental; quienes operan inventario
         reportan no conformidades y garantías; solo el administrador gestiona (ver docs/DECISIONES.md).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DefPermiso:
    codigo: str
    modulo: str
    descripcion: str


@dataclass(frozen=True)
class DefRol:
    clave: str
    nombre: str
    descripcion: str
    alcance: str  # "empresa" | "sede"
    permisos: frozenset[str]


_P = DefPermiso

PERMISOS: tuple[DefPermiso, ...] = (
    _P("empresa.ver", "Empresa", "Consultar los datos de la empresa"),
    _P("empresa.editar", "Empresa", "Modificar los datos y parámetros de la empresa"),
    _P("sedes.ver", "Sedes", "Consultar sedes"),
    _P("sedes.crear", "Sedes", "Crear sedes"),
    _P("sedes.editar", "Sedes", "Modificar sedes"),
    _P("sedes.inhabilitar", "Sedes", "Inhabilitar o reactivar sedes"),
    _P("usuarios.ver", "Usuarios", "Consultar usuarios"),
    _P("usuarios.crear", "Usuarios", "Crear usuarios"),
    _P("usuarios.editar", "Usuarios", "Modificar usuarios, su rol y su sede"),
    _P("usuarios.inhabilitar", "Usuarios", "Inhabilitar o reactivar usuarios"),
    _P("roles.ver", "Roles y permisos", "Consultar roles y permisos"),
    _P("roles.crear", "Roles y permisos", "Crear roles"),
    _P("roles.editar", "Roles y permisos", "Modificar roles"),
    _P("roles.asignar_permisos", "Roles y permisos", "Asignar permisos a los roles"),
    _P("categorias.ver", "Categorías", "Consultar categorías"),
    _P("categorias.crear", "Categorías", "Crear categorías"),
    _P("categorias.editar", "Categorías", "Modificar categorías"),
    _P("productos.ver", "Productos", "Consultar productos"),
    _P("productos.crear", "Productos", "Crear productos"),
    _P("productos.editar", "Productos", "Modificar productos"),
    _P("productos.inhabilitar", "Productos", "Inhabilitar o reactivar productos"),
    _P("inventario.ver", "Inventario", "Consultar el inventario por sede"),
    _P("inventario.consolidado", "Inventario", "Consultar el inventario consolidado de la empresa"),
    _P("inventario.entrada", "Inventario", "Registrar entradas de productos"),
    _P("inventario.salida", "Inventario", "Registrar salidas de productos"),
    _P("inventario.ajustar", "Inventario", "Ajustar existencias"),
    _P("inventario.niveles", "Inventario", "Configurar stock mínimo y máximo"),
    _P("movimientos.ver", "Inventario", "Consultar el historial de movimientos"),
    _P("ventas.registrar", "Ventas", "Registrar ventas"),
    _P("ventas.ver", "Ventas", "Consultar ventas"),
    _P("ventas.anular", "Ventas", "Anular ventas"),
    _P("traslados.solicitar", "Traslados", "Solicitar traslados entre sedes"),
    _P("traslados.ver", "Traslados", "Consultar traslados"),
    _P("traslados.aprobar", "Traslados", "Aprobar o rechazar traslados"),
    _P("traslados.confirmar", "Traslados", "Confirmar traslados"),
    _P("alertas.ver", "Alertas", "Consultar alertas de inventario"),
    _P("alertas.recalcular", "Alertas", "Recalcular las alertas de inventario"),
    _P("prediccion.ver", "Predicción", "Consultar predicciones de demanda"),
    _P("prediccion.ejecutar", "Predicción", "Generar predicciones de demanda"),
    _P("recomendaciones.ver", "Recomendaciones", "Consultar recomendaciones"),
    _P("recomendaciones.generar", "Recomendaciones", "Generar recomendaciones"),
    _P("recomendaciones.aprobar", "Recomendaciones", "Aprobar o rechazar recomendaciones"),
    _P("reportes.inventario", "Reportes", "Generar reportes de inventario"),
    _P("reportes.ventas", "Reportes", "Generar reportes de ventas"),
    _P("reportes.movimientos", "Reportes", "Generar reportes de movimientos"),
    _P("reportes.traslados", "Reportes", "Generar reportes de traslados"),
    _P("reportes.alertas", "Reportes", "Generar reportes de alertas"),
    _P("reportes.predicciones", "Reportes", "Generar reportes de predicciones"),
    _P("reportes.recomendaciones", "Reportes", "Generar reportes de recomendaciones"),
    _P("auditoria.ver", "Auditoría", "Consultar la actividad completa de los usuarios"),
    _P("auditoria.operaciones", "Auditoría", "Consultar el historial de operaciones"),
    _P("agentes.gestionar", "Agentes de IA", "Administrar las llaves de acceso de agentes de IA"),
    # --- Sistema Integrado de Gestión (SIG) ---
    _P("pqrs.crear", "SIG · PQRS", "Enviar peticiones, quejas, reclamos y sugerencias y consultar las propias"),
    _P("pqrs.gestionar", "SIG · PQRS", "Ver todas las PQRS, cambiar su estado y responderlas"),
    _P("sst.ver", "SIG · SST", "Consultar las pausas activas y las recomendaciones de salud en el trabajo"),
    _P("sst.gestionar", "SIG · SST", "Configurar las pausas activas (frecuencia, ejercicios) y ver su cumplimiento"),
    _P("calidad.ver", "SIG · Calidad", "Consultar la guía, las no conformidades y las garantías"),
    _P("calidad.reportar", "SIG · Calidad", "Registrar no conformidades y garantías y agregar observaciones"),
    _P("calidad.gestionar", "SIG · Calidad", "Cambiar el estado, asignar responsables y cerrar no conformidades y garantías"),
    _P("ambiental.ver", "SIG · Ambiental", "Consultar los indicadores de gestión ambiental"),
    _P("ambiental.configurar", "SIG · Ambiental", "Configurar los parámetros de cálculo ambiental"),
)

CODIGOS_PERMISOS: frozenset[str] = frozenset(p.codigo for p in PERMISOS)

_LECTURA_BASICA = {"sedes.ver", "categorias.ver", "productos.ver", "inventario.ver", "movimientos.ver",
                   "ventas.ver", "traslados.ver", "alertas.ver", "reportes.movimientos"}

# SIG: todos los roles pueden enviar PQRS y consultar el material informativo; quien opera inventario también
# reporta no conformidades y garantías (puede detectarlas al recibir o vender mercancía).
_SIG_BASICO = {"pqrs.crear", "sst.ver", "calidad.ver", "ambiental.ver"}

_OPERACION_DE_SEDE = {"inventario.entrada", "inventario.salida", "inventario.ajustar", "ventas.registrar",
                      "traslados.solicitar", "traslados.confirmar"}

ROLES_SISTEMA: tuple[DefRol, ...] = (
    DefRol(
        clave="admin",
        nombre="Administrador",
        descripcion="Gestiona la empresa, las sedes, los usuarios, los roles, los productos y la configuración general.",
        alcance="empresa",
        permisos=CODIGOS_PERMISOS,
    ),
    DefRol(
        clave="gerente",
        nombre="Gerente",
        descripcion="Consulta reportes consolidados e indicadores para apoyar la toma de decisiones.",
        alcance="empresa",
        permisos=frozenset(
            _LECTURA_BASICA
            | _SIG_BASICO
            | {
                "empresa.ver",
                "inventario.consolidado",
                "prediccion.ver",
                "recomendaciones.ver",
                "recomendaciones.aprobar",
                "reportes.inventario",
                "reportes.ventas",
                "reportes.traslados",
                "reportes.alertas",
                "reportes.predicciones",
                "reportes.recomendaciones",
                "auditoria.operaciones",
            }
        ),
    ),
    DefRol(
        clave="encargado_sede",
        nombre="Encargado de sede",
        descripcion="Administra el inventario, las ventas y los movimientos de su sede.",
        alcance="sede",
        permisos=frozenset(
            _LECTURA_BASICA
            | _OPERACION_DE_SEDE
            | _SIG_BASICO
            | {
                "calidad.reportar",
                "roles.ver",
                "inventario.niveles",
                "ventas.anular",
                "traslados.aprobar",
                "alertas.recalcular",
                "prediccion.ver",
                "recomendaciones.ver",
                "recomendaciones.aprobar",
                "reportes.inventario",
                "reportes.ventas",
                "reportes.traslados",
                "reportes.alertas",
                "reportes.recomendaciones",
                "auditoria.operaciones",
            }
        ),
    ),
    DefRol(
        clave="usuario_inventario",
        nombre="Usuario de inventario",
        descripcion="Registra y consulta entradas, salidas, ventas, existencias y traslados de su sede.",
        alcance="sede",
        permisos=frozenset(_LECTURA_BASICA | _OPERACION_DE_SEDE | _SIG_BASICO | {"reportes.alertas", "calidad.reportar"}),
    ),
    DefRol(
        clave="analista_compras",
        nombre="Analista de compras",
        descripcion="Consulta históricos y predicciones, y revisa las recomendaciones de reabastecimiento.",
        alcance="empresa",
        permisos=frozenset(
            _LECTURA_BASICA
            | _SIG_BASICO
            | {
                "inventario.consolidado",
                "prediccion.ver",
                "prediccion.ejecutar",
                "recomendaciones.ver",
                "recomendaciones.generar",
                "recomendaciones.aprobar",
                "reportes.inventario",
                "reportes.ventas",
                "reportes.alertas",
                "reportes.predicciones",
                "reportes.recomendaciones",
            }
        ),
    ),
)

ROLES_POR_CLAVE: dict[str, DefRol] = {r.clave: r for r in ROLES_SISTEMA}

# Cada permiso por defecto de un rol debe existir en el catálogo (se verifica en las pruebas).
