from datetime import datetime

from pydantic import BaseModel, Field

from app.dto.comunes_dto import Correo, EsquemaBase, Password, Texto


class RolResumen(BaseModel):
    id: int
    clave: str | None
    nombre: str
    alcance: str

    model_config = {"from_attributes": True}


class SedeUsuario(BaseModel):
    id: int
    nombre: str

    model_config = {"from_attributes": True}


class UsuarioSesion(BaseModel):
    """Lo que necesita la interfaz tras iniciar sesión: identidad, rol, sede y permisos efectivos."""

    id: int
    nombre: str
    email: str
    empresa_id: int
    empresa_nombre: str
    rol: RolResumen
    sede: SedeUsuario | None
    permisos: list[str]
    debe_cambiar_password: bool


class UsuarioSalida(BaseModel):
    id: int
    nombre: str
    email: str
    activo: bool
    rol: RolResumen
    sede: SedeUsuario | None
    bloqueado: bool
    debe_cambiar_password: bool
    ultimo_acceso: datetime | None
    created_at: datetime


class UsuarioCrear(EsquemaBase):
    nombre: Texto(2, 150)
    email: Correo
    password: Password
    rol_id: int = Field(gt=0)
    sede_id: int | None = Field(default=None, gt=0)
    forzar_cambio_password: bool = True


class UsuarioActualizar(EsquemaBase):
    nombre: Texto(2, 150) | None = None
    email: Correo | None = None
    rol_id: int | None = Field(default=None, gt=0)
    sede_id: int | None = Field(default=None, gt=0)
    quitar_sede: bool = False


class UsuarioEstado(EsquemaBase):
    activo: bool


class UsuarioRestablecerPassword(EsquemaBase):
    nueva_password: Password
