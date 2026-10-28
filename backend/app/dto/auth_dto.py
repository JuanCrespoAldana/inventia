from pydantic import BaseModel, Field

from app.dto.comunes_dto import Correo, EsquemaBase, Password
from app.dto.usuario_dto import UsuarioSesion


class LoginEntrada(EsquemaBase):
    email: Correo
    password: str = Field(min_length=1, max_length=128)


class TokenSalida(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expira_en_minutos: int
    usuario: UsuarioSesion


class SolicitudRecuperacion(EsquemaBase):
    email: Correo


class VerificarCodigoEntrada(EsquemaBase):
    email: Correo
    codigo: str = Field(pattern=r"^\d{6}$")


class VerificarCodigoSalida(BaseModel):
    session_token: str


class RestablecerPasswordEntrada(EsquemaBase):
    session_token: str = Field(min_length=10, max_length=200)
    nueva_password: Password


class CambiarPasswordEntrada(EsquemaBase):
    password_actual: str = Field(min_length=1, max_length=128)
    nueva_password: Password
