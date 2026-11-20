"""Modelos de Inventia. Importar este paquete registra todas las tablas en ``Base.metadata``."""

from app.model.acceso import Permiso, Rol, RolPermiso
from app.model.auditoria import Auditoria
from app.model.base import Base
from app.model.catalogo import Categoria, Producto
from app.model.empresa import CONFIGURACION_POR_DEFECTO, Empresa
from app.model.inventario import Alerta, EntradaInventario, InventarioSede, Movimiento, Secuencia
from app.model.operaciones import Traslado, TrasladoItem, Venta, VentaItem
from app.model.password_reset_token import PasswordResetToken
from app.model.prediccion import EjecucionPrediccion, Prediccion, Recomendacion
from app.model.sede import Sede
from app.model.usuario import Usuario

__all__ = [
    "Alerta",
    "Auditoria",
    "Base",
    "CONFIGURACION_POR_DEFECTO",
    "Categoria",
    "EjecucionPrediccion",
    "Empresa",
    "EntradaInventario",
    "InventarioSede",
    "Movimiento",
    "PasswordResetToken",
    "Permiso",
    "Prediccion",
    "Producto",
    "Recomendacion",
    "Rol",
    "RolPermiso",
    "Secuencia",
    "Sede",
    "Traslado",
    "TrasladoItem",
    "Usuario",
    "Venta",
    "VentaItem",
]
