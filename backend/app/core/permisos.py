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
)

CODIGOS_PERMISOS: frozenset[str] = frozenset(p.codigo for p in PERMISOS)

_LECTURA_BASICA = {"sedes.ver", "categorias.ver", "productos.ver", "inventario.ver", "movimientos.ver",
                   "ventas.ver", "traslados.ver", "alertas.ver", "reportes.movimientos"}

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
            | {
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
        permisos=frozenset(_LECTURA_BASICA | _OPERACION_DE_SEDE | {"reportes.alertas"}),
    ),
    DefRol(
        clave="analista_compras",
        nombre="Analista de compras",
        descripcion="Consulta históricos y predicciones, y revisa las recomendaciones de reabastecimiento.",
        alcance="empresa",
        permisos=frozenset(
            _LECTURA_BASICA
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
