"""Asistente de consultas de Inventia: responde preguntas en lenguaje natural con los datos reales de la empresa.

Es de solo lectura y respeta el rol y la sede de quien pregunta. Funciona con reglas (sin servicios externos ni costo
por consulta): ver ``app/service/asistente`` para el reconocimiento de la pregunta y las respuestas.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.dto.asistente_dto import AyudaAsistente, PreguntaAsistente, RespuestaAsistente
from app.security.acceso import Contexto
from app.service.asistente import motor
from app.service.asistente.respuestas_general import construir_ayuda


async def preguntar(db: AsyncSession, ctx: Contexto, datos: PreguntaAsistente) -> RespuestaAsistente:
    return await motor.responder(db, ctx, datos.mensaje, datos.contexto)


def ayuda(ctx: Contexto) -> AyudaAsistente:
    return construir_ayuda(ctx)
