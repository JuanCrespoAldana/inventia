"""Modelos de Inventia. Importar este paquete registra todas las tablas en ``Base.metadata``."""

from app.models.acceso import Permiso, Rol, RolPermiso
from app.models.auditoria import ApiKey, Auditoria
from app.models.base import Base
from app.models.catalogo import Categoria, Producto
from app.models.empresa import CONFIGURACION_POR_DEFECTO, Empresa
from app.models.inventario import Alerta, InventarioSede, Movimiento, Secuencia
from app.models.operaciones import Traslado, TrasladoItem, Venta, VentaItem
from app.models.password_reset_token import PasswordResetToken
from app.models.prediccion import EjecucionPrediccion, Prediccion, Recomendacion
from app.models.sede import Sede
from app.models.usuario import Usuario

__all__ = [
    "Alerta",
    "ApiKey",
    "Auditoria",
    "Base",
    "CONFIGURACION_POR_DEFECTO",
    "Categoria",
    "EjecucionPrediccion",
    "Empresa",
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
