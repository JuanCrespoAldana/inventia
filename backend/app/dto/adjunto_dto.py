"""Esquemas de archivos adjuntos (evidencias)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

EntidadAdjuntoT = Literal["pqrs", "no_conformidad", "garantia"]


class AdjuntoSalida(BaseModel):
    id: int
    nombre: str
    tipo_mime: str
    tamano: int
    created_at: datetime
    subido_por: int
    subido_por_nombre: str | None = None
    puede_eliminar: bool = False
