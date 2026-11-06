"""Esquemas del asistente de consultas: pregunta, respuesta (texto + bloques de datos) y ayuda."""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.dto.comunes_dto import EsquemaBase, Texto

Tono = Literal["neutral", "accent", "success", "warning", "danger"]
Celda = str | int | float | bool | None


class ContextoConversacion(EsquemaBase):
    """Lo que el asistente recuerda de la última respuesta para entender preguntas de seguimiento («¿y en la Sede Sur?»).
    Solo contiene identificadores: cada uno se vuelve a validar contra la empresa y el alcance de quien pregunta."""

    intencion: str | None = None
    sede_ids: list[int] = Field(default_factory=list, max_length=20)
    categoria_ids: list[int] = Field(default_factory=list, max_length=20)
    producto_ids: list[int] = Field(default_factory=list, max_length=60)
    desde: date | None = None
    hasta: date | None = None


class PreguntaAsistente(EsquemaBase):
    mensaje: Texto(1, 500)
    contexto: ContextoConversacion | None = None


class Metrica(BaseModel):
    etiqueta: str
    valor: str
    detalle: str | None = None
    tono: Tono = "neutral"


class Columna(BaseModel):
    clave: str
    etiqueta: str
    formato: Literal["texto", "entero", "decimal", "moneda", "porcentaje", "fecha", "fecha_hora"] = "texto"
    alinear: Literal["izq", "der"] = "izq"


class Fila(BaseModel):
    celdas: dict[str, Celda]
    tonos: dict[str, Tono] = Field(default_factory=dict)  # columnas que se muestran como etiqueta de color
    ruta: str | None = None  # pantalla de detalle (la primera celda se vuelve enlace)


class Barra(BaseModel):
    etiqueta: str
    valor: float
    texto: str


class BloqueMetricas(BaseModel):
    tipo: Literal["metricas"] = "metricas"
    titulo: str | None = None
    metricas: list[Metrica]


class BloqueTabla(BaseModel):
    tipo: Literal["tabla"] = "tabla"
    titulo: str | None = None
    columnas: list[Columna]
    filas: list[Fila]
    total: int  # filas que cumplen la consulta (puede ser más que las mostradas)
    nota: str | None = None


class BloqueBarras(BaseModel):
    tipo: Literal["barras"] = "barras"
    titulo: str | None = None
    barras: list[Barra]


class BloqueLista(BaseModel):
    tipo: Literal["lista"] = "lista"
    titulo: str | None = None
    elementos: list[str]


Bloque = Annotated[BloqueMetricas | BloqueTabla | BloqueBarras | BloqueLista, Field(discriminator="tipo")]


class Enlace(BaseModel):
    etiqueta: str
    ruta: str


class RespuestaAsistente(BaseModel):
    intencion: str
    entendida: bool
    texto: str
    bloques: list[Bloque] = Field(default_factory=list)
    enlaces: list[Enlace] = Field(default_factory=list)
    sugerencias: list[str] = Field(default_factory=list)
    avisos: list[str] = Field(default_factory=list)
    alcance: str | None = None  # a qué sedes se refiere la respuesta
    periodo: str | None = None
    contexto: ContextoConversacion


class GrupoAyuda(BaseModel):
    titulo: str
    ejemplos: list[str]


class AyudaAsistente(BaseModel):
    saludo: str
    iniciales: list[str]
    grupos: list[GrupoAyuda]
