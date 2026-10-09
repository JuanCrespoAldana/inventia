"""Modelos de Inventia. Importar este paquete registra todas las tablas en ``Base.metadata``."""

from app.models.acceso import Permiso, Rol, RolPermiso
from app.models.adjunto import Adjunto
from app.models.ambiental import AmbCategoria, AmbConfiguracion, AmbRegistro
from app.models.auditoria import ApiKey, Auditoria
from app.models.base import Base
from app.models.calidad import Garantia, GarantiaHistorial, NoConformidad, NoConformidadHistorial
from app.models.catalogo import Categoria, Producto
from app.models.empresa import CONFIGURACION_POR_DEFECTO, Empresa
from app.models.inventario import Alerta, EntradaInventario, EntradaObservacion, InventarioSede, Movimiento, Secuencia
from app.models.operaciones import Traslado, TrasladoItem, Venta, VentaItem
from app.models.password_reset_token import PasswordResetToken
from app.models.pqrs import Pqrs, PqrsHistorial
from app.models.prediccion import EjecucionPrediccion, Prediccion, Recomendacion
from app.models.sede import Sede
from app.models.sst import SstActividad, SstConfiguracion, SstPausa
from app.models.usuario import Usuario

__all__ = [
    "Adjunto",
    "Alerta",
    "AmbCategoria",
    "AmbConfiguracion",
    "AmbRegistro",
    "ApiKey",
    "Auditoria",
    "Base",
    "CONFIGURACION_POR_DEFECTO",
    "Categoria",
    "EjecucionPrediccion",
    "Empresa",
    "EntradaInventario",
    "EntradaObservacion",
    "Garantia",
    "GarantiaHistorial",
    "InventarioSede",
    "Movimiento",
    "NoConformidad",
    "NoConformidadHistorial",
    "PasswordResetToken",
    "Permiso",
    "Pqrs",
    "PqrsHistorial",
    "Prediccion",
    "Producto",
    "Recomendacion",
    "Rol",
    "RolPermiso",
    "Secuencia",
    "Sede",
    "SstActividad",
    "SstConfiguracion",
    "SstPausa",
    "Traslado",
    "TrasladoItem",
    "Usuario",
    "Venta",
    "VentaItem",
]
