import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field

from app.dto.comunes_dto import Dinero, EsquemaBase, Texto, TextoOpcional

UnidadMedida = Literal[
    "unidad", "caja", "paquete", "docena", "par", "bolsa", "rollo", "frasco", "kg", "g", "lb", "litro", "ml", "metro"
]
UNIDADES: tuple[str, ...] = UnidadMedida.__args__  # type: ignore[attr-defined]


def _codigo(valor: str) -> str:
    codigo = re.sub(r"\s+", "", valor).upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9._\-/]{0,59}", codigo):
        raise ValueError("El código solo admite letras, números, punto, guion, barra y guion bajo (máx. 60)")
    return codigo


CodigoProducto = Annotated[str, Field(min_length=1, max_length=80), AfterValidator(_codigo)]


# ---------------- Categorías ----------------
class CategoriaCrear(EsquemaBase):
    nombre: Texto(2, 100)
    descripcion: TextoOpcional(300)


class CategoriaActualizar(EsquemaBase):
    nombre: Texto(2, 100) | None = None
    descripcion: TextoOpcional(300)


class CategoriaEstado(EsquemaBase):
    activa: bool


class CategoriaSalida(BaseModel):
    id: int
    nombre: str
    descripcion: str | None
    activa: bool
    total_productos: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CategoriaResumen(BaseModel):
    id: int
    nombre: str

    model_config = {"from_attributes": True}


# ---------------- Productos ----------------
class ProductoCrear(EsquemaBase):
    codigo: CodigoProducto
    nombre: Texto(2, 200)
    descripcion: TextoOpcional(1000)
    categoria_id: int = Field(gt=0)
    unidad_medida: UnidadMedida = "unidad"
    costo: Dinero | None = None
    precio_venta: Dinero | None = None


class ProductoActualizar(EsquemaBase):
    """El código no se puede modificar: identifica al producto en todo su historial."""

    nombre: Texto(2, 200) | None = None
    descripcion: TextoOpcional(1000)
    categoria_id: int | None = Field(default=None, gt=0)
    unidad_medida: UnidadMedida | None = None
    costo: Dinero | None = None
    precio_venta: Dinero | None = None


class ProductoEstado(EsquemaBase):
    activo: bool


class ProductoSalida(BaseModel):
    id: int
    codigo: str
    nombre: str
    descripcion: str | None
    categoria: CategoriaResumen
    unidad_medida: str
    costo: Dinero | None
    precio_venta: Dinero | None
    activo: bool
    existencias_total: int = 0
    created_at: datetime
    updated_at: datetime


class ProductoResumen(BaseModel):
    id: int
    codigo: str
    nombre: str
    unidad_medida: str

    model_config = {"from_attributes": True}
