"""Lo que recibe cada respuesta del asistente: quién pregunta, qué entendió el motor y a qué datos puede llegar."""

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.empresa import Empresa
from app.security.acceso import Contexto
from app.service.asistente.bloques import Resp, lista_natural
from app.service.asistente.entidades import Directorio, Entidades
from app.util import lenguaje as L

_ES_MES = re.compile(r"^[a-zñ]+ de \d{4}$")
_ES_ANIO = re.compile(r"^el año \d{4}$")
_ES_DIA = re.compile(r"^el (lunes|martes|miércoles|jueves|viernes|sábado|domingo|fin de semana)( pasado)?$")
HISTORIAL = "todo el historial"  # etiqueta de un periodo sin límites
LIMITE_POR_DEFECTO = 10
LIMITE_MAXIMO = 25


@dataclass
class Peticion:
    db: AsyncSession
    ctx: Contexto
    d: Directorio
    e: Entidades
    hoy: date
    frase: str
    clave: str
    sede_ids: list[int] | None  # alcance efectivo: ``None`` = toda la empresa
    sedes_nombradas: bool  # la persona nombró sedes (o vienen de la conversación)
    producto_ids: list[int] = field(default_factory=list)
    categoria_ids: list[int] = field(default_factory=list)
    periodo: L.Periodo | None = None
    avisos: list[str] = field(default_factory=list)
    _parametros: dict[str, int] | None = None

    # ------------------------------------------------------------------------------------------------- permisos
    def tiene(self, *permisos: str) -> bool:
        return self.ctx.tiene_alguno(*permisos)

    # -------------------------------------------------------------------------------------------------- alcance
    @property
    def limitado(self) -> bool:
        return self.ctx.limitado_a_sede

    def nombres_sedes(self, ids: list[int] | None = None) -> list[str]:
        ids = self.sede_ids if ids is None else ids
        if ids is None:
            return []
        return [s.nombre for s in self.d.sedes if s.id in ids]

    @property
    def alcance(self) -> str:
        if self.sede_ids is None:
            return "Toda la empresa"
        nombres = self.nombres_sedes()
        return lista_natural(nombres) if nombres else "Sin sede asignada"

    @property
    def en_alcance(self) -> str:
        """«en toda la empresa», «en Sede Norte», «en Sede Norte y Sede Sur»."""
        return "en toda la empresa" if self.sede_ids is None else f"en {self.alcance}"

    @property
    def una_sola_sede(self) -> bool:
        return self.sede_ids is not None and len(self.sede_ids) == 1

    @property
    def sin_acceso_a_sede(self) -> bool:
        return self.sede_ids is not None and not self.sede_ids

    # ------------------------------------------------------------------------------------------------- filtros
    @property
    def hay_producto(self) -> bool:
        return bool(self.producto_ids)

    @property
    def hay_categoria(self) -> bool:
        return bool(self.categoria_ids)

    def descripcion_filtro(self) -> str:
        """«de BAT-002», «de la categoría Motos eléctricas», «de 3 productos»…"""
        if self.producto_ids:
            productos = [p for p in self.d.productos if p.id in self.producto_ids]
            if len(productos) == 1:
                return f"de {productos[0].nombre} ({productos[0].codigo})"
            if len(productos) <= 3:
                return "de " + lista_natural([f"{p.nombre} ({p.codigo})" for p in productos])
            return f"de {len(productos)} productos que coinciden con tu búsqueda"
        if self.categoria_ids:
            nombres = [c.nombre for c in self.d.categorias if c.id in self.categoria_ids]
            return ("de la categoría " if len(nombres) == 1 else "de las categorías ") + lista_natural(nombres)
        return ""

    def con_filtro(self, base: str) -> str:
        filtro = self.descripcion_filtro()
        return f"{base} {filtro}" if filtro else base

    # -------------------------------------------------------------------------------------------------- límites
    def limite(self, defecto: int = LIMITE_POR_DEFECTO) -> int:
        return max(1, min(self.e.limite or defecto, LIMITE_MAXIMO))

    # --------------------------------------------------------------------------------------------------- periodos
    def periodo_o(self, desde: date, hasta: date, etiqueta: str) -> L.Periodo:
        return self.periodo or L.Periodo(desde, hasta, etiqueta)

    def ultimos_dias(self, dias: int) -> L.Periodo:
        if self.periodo:
            return self.periodo
        from datetime import timedelta

        return L.Periodo(self.hoy - timedelta(days=dias - 1), self.hoy, f"los últimos {dias} días")

    def este_mes(self) -> L.Periodo:
        return self.periodo or L.Periodo(self.hoy.replace(day=1), self.hoy, "este mes")

    def hoy_periodo(self) -> L.Periodo:
        return self.periodo or L.Periodo(self.hoy, self.hoy, "hoy")

    def periodo_texto(self, p: L.Periodo) -> str:
        """Texto corto para mostrar el periodo consultado: «este mes (del 1 al 5 de noviembre de 2026)»."""
        rango = L.describir_rango(p.desde, p.hasta)
        etiqueta = p.etiqueta.strip()
        if etiqueta in (HISTORIAL, rango) or not etiqueta or _ES_MES.match(etiqueta) or _ES_ANIO.match(etiqueta) or etiqueta.startswith("desde "):
            return etiqueta or rango
        return f"{etiqueta} ({rango})"

    def en_periodo(self, p: L.Periodo) -> str:
        """El periodo como complemento de una frase, con su preposición cuando la lleva:
        «ayer», «el 5 de noviembre de 2026», «del 1 al 15 de octubre de 2026», «en este mes (del 1 al 5 de noviembre de 2026)»."""
        etiqueta = p.etiqueta.strip()
        rango = L.describir_rango(p.desde, p.hasta)
        if etiqueta == "hoy":
            return "hoy"
        if etiqueta == HISTORIAL:
            return f"en {HISTORIAL}"
        if etiqueta in ("ayer", "anteayer") or _ES_DIA.match(etiqueta):
            return f"{etiqueta} ({rango})"
        if not etiqueta or etiqueta == rango:
            return f"el {rango}" if p.desde == p.hasta else rango
        if etiqueta.startswith("desde "):
            return etiqueta
        if _ES_MES.match(etiqueta):
            return f"en {etiqueta}" + (" (hasta hoy)" if p.hasta == self.hoy else "")
        if _ES_ANIO.match(etiqueta):
            return f"en {etiqueta}"
        return f"en {etiqueta} ({rango})"

    def periodo_inicio(self, p: L.Periodo) -> str:
        """Igual que ``en_periodo`` pero para abrir una oración: «Ayer…», «En este mes…», «Del 1 al 15 de octubre…»."""
        texto = self.en_periodo(p)
        return texto[:1].upper() + texto[1:]

    # ------------------------------------------------------------------------------------------------ parámetros
    async def parametros(self) -> dict[str, int]:
        if self._parametros is None:
            empresa = await self.db.scalar(select(Empresa).where(Empresa.id == self.ctx.empresa_id))
            self._parametros = empresa.parametros() if empresa else {}
        return self._parametros

    async def nombre_empresa(self) -> str:
        return await self.db.scalar(select(Empresa.nombre).where(Empresa.id == self.ctx.empresa_id)) or "tu empresa"


Manejador = Callable[[Peticion], Awaitable[Resp]]
MANEJADORES: dict[str, Manejador] = {}


def manejador(*claves: str) -> Callable[[Manejador], Manejador]:
    """Registra una función como la respuesta de una o varias intenciones."""

    def registrar(funcion: Manejador) -> Manejador:
        for clave in claves:
            MANEJADORES[clave] = funcion
        return funcion

    return registrar


def cuenta(consulta) -> "select":  # type: ignore[valid-type]
    """``SELECT count(*)`` sobre una consulta ya armada."""
    return select(func.count()).select_from(consulta.subquery())
