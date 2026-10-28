"""Modelos de Inventia. Importar este paquete registra todas las tablas en ``Base.metadata``."""

from app.model.acceso import Permiso, Rol, RolPermiso
from app.model.adjunto import Adjunto
from app.model.ambiental import AmbCategoria, AmbConfiguracion, AmbRegistro
from app.model.auditoria import ApiKey, Auditoria
from app.model.base import Base
from app.model.calidad import Garantia, GarantiaHistorial, NoConformidad, NoConformidadHistorial
from app.model.catalogo import Categoria, Producto
from app.model.empresa import CONFIGURACION_POR_DEFECTO, Empresa
from app.model.inventario import Alerta, EntradaInventario, EntradaObservacion, InventarioSede, Movimiento, Secuencia
from app.model.operaciones import Traslado, TrasladoItem, Venta, VentaItem
from app.model.password_reset_token import PasswordResetToken
from app.model.pqrs import Pqrs, PqrsHistorial
from app.model.prediccion import EjecucionPrediccion, Prediccion, Recomendacion
from app.model.sede import Sede
from app.model.sst import SstActividad, SstConfiguracion, SstPausa
from app.model.usuario import Usuario

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
