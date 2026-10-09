from datetime import datetime

from pydantic import BaseModel

from app.schemas.comunes import EsquemaBase, Texto, TextoOpcional


class SedeCrear(EsquemaBase):
    nombre: Texto(2, 150)
    direccion: TextoOpcional(200)
    ciudad: Texto(2, 150)


class SedeActualizar(EsquemaBase):
    nombre: Texto(2, 150) | None = None
    direccion: TextoOpcional(200)
    ciudad: Texto(2, 150) | None = None


class SedeSalida(BaseModel):
    id: int
    nombre: str
    direccion: str | None
    ciudad: str | None
    activa: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SedeDetalle(SedeSalida):
    total_usuarios: int = 0
    unidades_en_existencia: int = 0


class SedeEstado(EsquemaBase):
    activa: bool


class SedeResumen(BaseModel):
    id: int
    nombre: str
    ciudad: str | None = None

    model_config = {"from_attributes": True}
