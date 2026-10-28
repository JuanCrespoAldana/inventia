"""PQRS: peticiones, quejas, reclamos y sugerencias.

* Cualquier persona autenticada con ``pqrs.crear`` envía solicitudes y ve las SUYAS.
* ``pqrs.gestionar`` (administración) ve todas, filtra, cambia el estado y responde.
* Cada cambio de estado y cada respuesta queda en un historial que no se puede alterar.
* No hay sistema de notificaciones en el proyecto (solo el correo de recuperación de contraseña), así que no
  se simulan avisos: la administración ve en la bandeja el conteo de solicitudes pendientes."""


from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dto.comunes_dto import ParametrosPagina
from app.dto.pqrs_dto import PqrsConteo, PqrsCrear, PqrsDetalle, PqrsEvento, PqrsGestionar, PqrsResumen
from app.dto.sede_dto import SedeResumen
from app.exception.excepciones import NoEncontrado, ReglaNegocio, SinPermiso
from app.model.pqrs import Pqrs, PqrsHistorial
from app.model.sede import Sede
from app.security.acceso import Contexto
from app.service import adjuntos_service, auditoria_service
from app.service.sig_util import nombres_usuarios
from app.specification.pqrs_spec import condiciones_pqrs
from app.util.sql import siguiente_secuencia
from app.util.tiempo import ahora_utc

ESTADOS = ("pendiente", "en_revision", "en_proceso", "resuelta")


async def crear(db: AsyncSession, ctx: Contexto, datos: PqrsCrear) -> Pqrs:
    pqrs = Pqrs(
        empresa_id=ctx.empresa_id, numero=await siguiente_secuencia(db, ctx.empresa_id, "pqrs"), tipo=datos.tipo,
        asunto=datos.asunto, descripcion=datos.descripcion, estado="pendiente", usuario_id=ctx.usuario_id,
        sede_id=ctx.sede_id,
    )
    db.add(pqrs)
    await db.flush()
    db.add(PqrsHistorial(pqrs_id=pqrs.id, usuario_id=ctx.usuario_id, evento="creacion", estado_nuevo="pendiente"))
    await auditoria_service.registrar(
        db, modulo="pqrs", accion="crear", ctx=ctx, entidad="pqrs", entidad_id=pqrs.id, sede_id=ctx.sede_id,
        detalle={"numero": pqrs.numero, "tipo": pqrs.tipo},
    )
    await db.commit()
    await db.refresh(pqrs)
    return pqrs


async def obtener(db: AsyncSession, ctx: Contexto, pqrs_id: int, *, bloquear: bool = False) -> Pqrs:
    consulta = select(Pqrs).where(Pqrs.id == pqrs_id, Pqrs.empresa_id == ctx.empresa_id)
    if bloquear:
        consulta = consulta.with_for_update()
    pqrs = await db.scalar(consulta)
    if pqrs is None:
        raise NoEncontrado("La solicitud no existe")
    if pqrs.usuario_id != ctx.usuario_id and not ctx.tiene("pqrs.gestionar"):
        raise SinPermiso("Solo puedes consultar tus propias solicitudes")
    return pqrs


async def resumenes(db: AsyncSession, pqrs: list[Pqrs]) -> list[PqrsResumen]:
    if not pqrs:
        return []
    nombres = await nombres_usuarios(db, {p.usuario_id for p in pqrs})
    sedes = {s.id: s for s in (await db.scalars(select(Sede).where(Sede.id.in_({p.sede_id for p in pqrs if p.sede_id})))).all()}
    adjuntos = await adjuntos_service.contar(db, "pqrs", [p.id for p in pqrs])
    return [
        PqrsResumen(
            id=p.id, numero=p.numero, tipo=p.tipo, asunto=p.asunto, estado=p.estado, usuario_id=p.usuario_id,
            usuario_nombre=nombres.get(p.usuario_id),
            sede=SedeResumen.model_validate(sedes[p.sede_id]) if p.sede_id in sedes else None,
            created_at=p.created_at, updated_at=p.updated_at, respondida=p.respuesta is not None,
            adjuntos=int(adjuntos.get(p.id, 0)),
        )
        for p in pqrs
    ]


async def listar(db: AsyncSession, ctx: Contexto, pag: ParametrosPagina, **filtros) -> tuple[list[PqrsResumen], int]:
    condiciones = condiciones_pqrs(ctx, **filtros)
    total = await db.scalar(select(func.count()).select_from(Pqrs).where(*condiciones)) or 0
    filas = (
        await db.scalars(
            select(Pqrs).where(*condiciones).order_by(Pqrs.created_at.desc(), Pqrs.id.desc())
            .offset(pag.offset).limit(pag.tamano)
        )
    ).all()
    return await resumenes(db, list(filas)), total


async def conteo(db: AsyncSession, ctx: Contexto) -> PqrsConteo:
    ctx.exigir("pqrs.gestionar")
    por_estado = dict(
        (await db.execute(select(Pqrs.estado, func.count()).where(Pqrs.empresa_id == ctx.empresa_id).group_by(Pqrs.estado))).all()
    )
    valores = {e: int(por_estado.get(e, 0)) for e in ESTADOS}
    return PqrsConteo(total=sum(valores.values()), **valores)


async def detalle(db: AsyncSession, ctx: Contexto, pqrs: Pqrs) -> PqrsDetalle:
    base = (await resumenes(db, [pqrs]))[0]
    eventos = (
        await db.scalars(select(PqrsHistorial).where(PqrsHistorial.pqrs_id == pqrs.id).order_by(PqrsHistorial.id))
    ).all()
    nombres = await nombres_usuarios(db, {e.usuario_id for e in eventos} | {pqrs.respondida_por})
    gestor = ctx.tiene("pqrs.gestionar")
    return PqrsDetalle(
        **base.model_dump(),
        descripcion=pqrs.descripcion, respuesta=pqrs.respuesta,
        respondida_por_nombre=nombres.get(pqrs.respondida_por) if pqrs.respondida_por else None,
        respondida_en=pqrs.respondida_en,
        historial=[
            PqrsEvento(
                id=e.id, fecha=e.fecha, usuario_id=e.usuario_id, usuario_nombre=nombres.get(e.usuario_id), evento=e.evento,
                estado_anterior=e.estado_anterior, estado_nuevo=e.estado_nuevo, comentario=e.comentario,
            )
            for e in eventos
        ],
        archivos=await adjuntos_service.listar(db, "pqrs", pqrs.id, ver_usuario_id=ctx.usuario_id, es_gestor=gestor),
        puede_gestionar=gestor,
        puede_adjuntar=gestor or (pqrs.usuario_id == ctx.usuario_id and pqrs.estado != "resuelta"),
    )


async def gestionar(db: AsyncSession, ctx: Contexto, pqrs_id: int, datos: PqrsGestionar) -> Pqrs:
    ctx.exigir("pqrs.gestionar")
    pqrs = await obtener(db, ctx, pqrs_id, bloquear=True)
    nuevo_estado = datos.estado or pqrs.estado
    cambia_estado = nuevo_estado != pqrs.estado
    if not cambia_estado and not datos.respuesta:
        raise ReglaNegocio("La solicitud ya está en ese estado: escribe una respuesta o elige otro estado", codigo="sin_cambios")
    if nuevo_estado == "resuelta" and not (datos.respuesta or pqrs.respuesta):
        raise ReglaNegocio("Para marcarla como resuelta escribe la respuesta para quien la envió", codigo="respuesta_requerida")

    anterior = pqrs.estado
    ahora = ahora_utc()
    if datos.respuesta:
        pqrs.respuesta, pqrs.respondida_por, pqrs.respondida_en = datos.respuesta, ctx.usuario_id, ahora
    pqrs.estado = nuevo_estado
    db.add(
        PqrsHistorial(
            pqrs_id=pqrs.id, usuario_id=ctx.usuario_id, evento="estado" if cambia_estado else "respuesta",
            estado_anterior=anterior if cambia_estado else None, estado_nuevo=nuevo_estado if cambia_estado else None,
            comentario=datos.respuesta,
        )
    )
    await auditoria_service.registrar(
        db, modulo="pqrs", accion="gestionar", ctx=ctx, entidad="pqrs", entidad_id=pqrs.id, sede_id=pqrs.sede_id,
        detalle={"numero": pqrs.numero, "antes": anterior, "despues": nuevo_estado, "con_respuesta": bool(datos.respuesta)},
    )
    await db.commit()
    await db.refresh(pqrs)
    return pqrs
