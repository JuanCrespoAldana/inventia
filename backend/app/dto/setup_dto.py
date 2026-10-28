from pydantic import BaseModel, Field

from app.dto.comunes_dto import Correo, EsquemaBase, Identificacion, Password, Telefono, Texto, TextoOpcional


class EstadoInstalacion(BaseModel):
    configurado: bool
    requiere_token: bool
    nombre_aplicacion: str


class ConfiguracionInicial(EsquemaBase):
    """Alta controlada de la empresa y de su primer administrador (RF-007, RF-001)."""

    empresa_nombre: Texto(2, 150)
    empresa_identificacion: Identificacion
    empresa_direccion: TextoOpcional(200)
    empresa_ciudad: TextoOpcional(100)
    empresa_telefono: Telefono
    empresa_email: Correo | None = None
    admin_nombre: Texto(2, 150)
    admin_email: Correo
    admin_password: Password
    token_configuracion: str = Field(default="", max_length=200)
