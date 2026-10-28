"""Entradas de mercancía: consulta de recepciones y observaciones acumulativas.

La cabecera (``EntradaInventario``) la crea ``inventario_service.registrar_entrada`` junto con los movimientos.
Aquí se consulta y se agregan observaciones: cada observación es una fila nueva con fecha y autor, de modo que
añadir una no reemplaza ni oculta las anteriores, y no toca existencias ni datos del producto."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dto.catalogo_dto import ProductoResumen
from app.dto.comunes_dto import ParametrosPagina
from app.dto.inventario_dto import (
    EntradaDetalle,
    EntradaLinea,
    EntradaObservacionCrear,
    EntradaObservacionSalida,
    EntradaResumen,
    NoConformidadVinculo,
)
from app.dto.sede_dto import SedeResumen
from app.exception.excepciones import NoEncontrado, ReglaNegocio
from app.model.calidad import NoConformidad
from app.model.catalogo import Producto
from app.model.inventario import EntradaInventario, EntradaObservacion, Movimiento
from app.model.sede import Sede
from app.model.usuario import Usuario
from app.security.acceso import Contexto
from app.service import auditoria_service
from app.service.alcance import obtener_sede_autorizada, resolver_filtro_sede
from app.util.tiempo import fin_de_dia_utc, inicio_de_dia_utc


async def obtener_entrada(db: AsyncSession, ctx: Contexto, entrada_id: int) -> EntradaInventario:
    entrada = await db.scalar(
        select(EntradaInventario).where(EntradaInventario.id == entrada_id, EntradaInventario.empresa_id == ctx.empresa_id)
    )
    if entrada is None:
        raise NoEncontrado("La entrada no existe")
    await obtener_sede_autorizada(db, ctx, entrada.sede_id)  # 403 si es de otra sede y el usuario está limitado
    return entrada


async def _nombres(db: AsyncSession, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return {i: n for i, n in (await db.execute(select(Usuario.id, Usuario.nombre).where(Usuario.id.in_(ids)))).all()}


async def resumenes(db: AsyncSession, entradas: list[EntradaInventario]) -> list[EntradaResumen]:
    if not entradas:
        return []
    ids = [e.id for e in entradas]
    movs = {
        eid: (int(unidades or 0), int(lineas))
        for eid, unidades, lineas in (
            await db.execute(
                select(Movimiento.entrada_id, func.sum(Movimiento.delta), func.count())
                .where(Movimiento.entrada_id.in_(ids)).group_by(Movimiento.entrada_id)
            )
        ).all()
    }
    obs = dict(
        (await db.execute(
            select(EntradaObservacion.entrada_id, func.count()).where(EntradaObservacion.entrada_id.in_(ids))
            .group_by(EntradaObservacion.entrada_id)
        )).all()
    )
    ncs = dict(
        (await db.execute(
            select(NoConformidad.entrada_id, func.count()).where(NoConformidad.entrada_id.in_(ids))
            .group_by(NoConformidad.entrada_id)
        )).all()
    )
    sedes = {s.id: s for s in (await db.scalars(select(Sede).where(Sede.id.in_({e.sede_id for e in entradas})))).all()}
    nombres = await _nombres(db, {e.usuario_id for e in entradas})
    return [
        EntradaResumen(
            id=e.id, numero=e.numero, fecha=e.fecha, motivo=e.motivo, sede=SedeResumen.model_validate(sedes[e.sede_id]),
            usuario_id=e.usuario_id, usuario_nombre=nombres.get(e.usuario_id),
            unidades=movs.get(e.id, (0, 0))[0], lineas=movs.get(e.id, (0, 0))[1],
            observaciones=int(obs.get(e.id, 0)), no_conformidades=int(ncs.get(e.id, 0)),
        )
        for e in entradas
    ]


async def listar_entradas(
    db: AsyncSession, ctx: Contexto, pag: ParametrosPagina, *, sede_id: int | None, desde: date | None,
    hasta: date | None, numero: int | None,
) -> tuple[list[EntradaResumen], int]:
    sede_ids = resolver_filtro_sede(ctx, sede_id)
    condiciones = [EntradaInventario.empresa_id == ctx.empresa_id]
    if sede_ids is not None:
        condiciones.append(EntradaInventario.sede_id.in_(sede_ids))
    if desde:
        condiciones.append(EntradaInventario.fecha >= inicio_de_dia_utc(desde))
    if hasta:
        condiciones.append(EntradaInventario.fecha < fin_de_dia_utc(hasta))
    if numero:
        condiciones.append(EntradaInventario.numero == numero)
    total = await db.scalar(select(func.count()).select_from(EntradaInventario).where(*condiciones)) or 0
    filas = (
        await db.scalars(
            select(EntradaInventario).where(*condiciones)
            .order_by(EntradaInventario.fecha.desc(), EntradaInventario.id.desc()).offset(pag.offset).limit(pag.tamano)
        )
    ).all()
    return await resumenes(db, list(filas)), total


async def detalle(db: AsyncSession, ctx: Contexto, entrada: EntradaInventario) -> EntradaDetalle:
    base = (await resumenes(db, [entrada]))[0]
    lineas = (
        await db.execute(
            select(Producto, Movimiento.delta, Movimiento.saldo_posterior)
            .join(Movimiento, Movimiento.producto_id == Producto.id)
            .where(Movimiento.entrada_id == entrada.id).order_by(Movimiento.id)
        )
    ).all()
    observaciones = (
        await db.scalars(
            select(EntradaObservacion).where(EntradaObservacion.entrada_id == entrada.id)
            .order_by(EntradaObservacion.id)
        )
    ).all()
    ncs = (
        await db.execute(
            select(NoConformidad.id, NoConformidad.numero, NoConformidad.estado, NoConformidad.entrada_observacion_id)
            .where(NoConformidad.entrada_id == entrada.id).order_by(NoConformidad.numero)
        )
    ).all()
    por_observacion: dict[int, list[NoConformidadVinculo]] = {}
    for nc_id, numero, estado, obs_id in ncs:
        if obs_id:
            por_observacion.setdefault(obs_id, []).append(NoConformidadVinculo(id=nc_id, numero=numero, estado=estado))
    nombres = await _nombres(db, {o.usuario_id for o in observaciones})
    productos = {p.id: p for p in (await db.scalars(
        select(Producto).where(Producto.id.in_({o.producto_id for o in observaciones if o.producto_id}))
    )).all()} if any(o.producto_id for o in observaciones) else {}
    return EntradaDetalle(
        **base.model_dump(),
        detalle_lineas=[
            EntradaLinea(producto=ProductoResumen.model_validate(p), cantidad=delta, saldo_posterior=saldo)
            for p, delta, saldo in lineas
        ],
        historial_observaciones=[
            EntradaObservacionSalida(
                id=o.id, fecha=o.fecha, usuario_id=o.usuario_id, usuario_nombre=nombres.get(o.usuario_id),
                contenido=o.contenido,
                producto=ProductoResumen.model_validate(productos[o.producto_id]) if o.producto_id else None,
                no_conformidades=por_observacion.get(o.id, []),
            )
            for o in observaciones
        ],
        no_conformidades_vinculadas=[NoConformidadVinculo(id=i, numero=n, estado=e) for i, n, e, _ in ncs],
        puede_observar=ctx.tiene("inventario.entrada"),
        puede_reportar_calidad=ctx.tiene("calidad.reportar"),
    )


async def agregar_observacion(
    db: AsyncSession, ctx: Contexto, entrada_id: int, datos: EntradaObservacionCrear
) -> EntradaDetalle:
    """Añade una observación a la entrada. Nunca modifica las anteriores ni las existencias."""
    entrada = await obtener_entrada(db, ctx, entrada_id)
    if datos.producto_id is not None:
        en_entrada = await db.scalar(
            select(func.count()).select_from(Movimiento)
            .where(Movimiento.entrada_id == entrada.id, Movimiento.producto_id == datos.producto_id)
        )
        if not en_entrada:
            raise ReglaNegocio("El producto no hace parte de esta entrada", codigo="producto_fuera_de_entrada")
    observacion = EntradaObservacion(
        entrada_id=entrada.id, producto_id=datos.producto_id, usuario_id=ctx.usuario_id, contenido=datos.contenido,
    )
    db.add(observacion)
    await db.flush()
    await auditoria_service.registrar(
        db, modulo="inventario", accion="observar_entrada", ctx=ctx, entidad="entrada", entidad_id=entrada.id,
        sede_id=entrada.sede_id, detalle={"numero": entrada.numero, "observacion_id": observacion.id},
    )
    await db.commit()
    return await detalle(db, ctx, entrada)
