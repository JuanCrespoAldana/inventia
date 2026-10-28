from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.dto.comunes_dto import EsquemaBase, Texto, TextoOpcional


class PermisoSalida(BaseModel):
    codigo: str
    modulo: str
    descripcion: str

    model_config = {"from_attributes": True}


class RolSalida(BaseModel):
    id: int
    clave: str | None
    nombre: str
    descripcion: str | None
    alcance: str
    es_sistema: bool
    activo: bool
    permisos: list[str]
    total_usuarios: int
    created_at: datetime
    updated_at: datetime


class RolCrear(EsquemaBase):
    nombre: Texto(3, 80)
    descripcion: TextoOpcional(300)
    alcance: Literal["empresa", "sede"] = "sede"
    permisos: list[str] = Field(default_factory=list, max_length=200)


class RolActualizar(EsquemaBase):
    nombre: Texto(3, 80) | None = None
    descripcion: TextoOpcional(300)
    alcance: Literal["empresa", "sede"] | None = None
    activo: bool | None = None


class RolPermisosEntrada(EsquemaBase):
    permisos: list[str] = Field(max_length=200)
