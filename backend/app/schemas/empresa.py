from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.comunes import Correo, EsquemaBase, Identificacion, Telefono, Texto, TextoOpcional


class EmpresaSalida(BaseModel):
    id: int
    nombre: str
    identificacion: str | None
    direccion: str | None
    ciudad: str | None
    telefono: str | None
    email: str | None
    activa: bool
    parametros: dict[str, int]
    created_at: datetime
    updated_at: datetime


class EmpresaActualizar(EsquemaBase):
    nombre: Texto(2, 150) | None = None
    identificacion: Identificacion | None = None
    direccion: TextoOpcional(200)
    ciudad: TextoOpcional(100)
    telefono: Telefono
    email: Correo | None = None


class ParametrosEmpresa(EsquemaBase):
    """Reglas configurables del inventario y la predicción (se documentan en docs/PREDICCION.md).

    Todos los campos son opcionales: solo se modifican los que se envían."""

    plazo_entrega_dias: int | None = Field(default=None, ge=0, le=180)
    dias_seguridad: int | None = Field(default=None, ge=0, le=90)
    dias_cobertura_objetivo: int | None = Field(default=None, ge=1, le=365)
    horizonte_dias: int | None = Field(default=None, ge=1, le=90)
    umbral_cobertura_alerta_dias: int | None = Field(default=None, ge=1, le=90)
    dias_sin_rotacion: int | None = Field(default=None, ge=7, le=730)
    dias_max_anulacion: int | None = Field(default=None, ge=0, le=365)
