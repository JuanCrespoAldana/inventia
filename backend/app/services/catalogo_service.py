"""Categorías y productos (RF-011 a RF-014). Todo se filtra por la empresa del usuario."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.acceso import Contexto
from app.core.exceptions import Conflicto, NoEncontrado
from app.models.catalogo import Categoria, Producto
from app.models.inventario import InventarioSede
from app.models.operaciones import Traslado, TrasladoItem
from app.schemas.catalogo import (
    CategoriaActualizar,
    CategoriaCrear,
    CategoriaResumen,
    CategoriaSalida,
    ProductoActualizar,
    ProductoCrear,
    ProductoSalida,
)
from app.schemas.comunes import ParametrosPagina
from app.services import auditoria_service

# ----------------------------------------------------------------------------- categorías


async def _nombre_categoria_libre(db: AsyncSession, empresa_id: int, nombre: str, excluir: int | None = None) -> None:
    consulta = select(Categoria.id).where(Categoria.empresa_id == empresa_id, func.lower(Categoria.nombre) == nombre.lower())
    if excluir:
        consulta = consulta.where(Categoria.id != excluir)
    if await db.scalar(consulta):
        raise Conflicto(f"Ya existe una categoría llamada «{nombre}»", codigo="categoria_duplicada")


async def crear_categoria(db: AsyncSession, ctx: Contexto, datos: CategoriaCrear) -> Categoria:
    await _nombre_categoria_libre(db, ctx.empresa_id, datos.nombre)
    categoria = Categoria(empresa_id=ctx.empresa_id, nombre=datos.nombre, descripcion=datos.descripcion)
    db.add(categoria)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise Conflicto(f"Ya existe una categoría llamada «{datos.nombre}»", codigo="categoria_duplicada") from exc
    await auditoria_service.registrar(
        db, modulo="categorias", accion="crear", ctx=ctx, entidad="categoria", entidad_id=categoria.id,
        detalle={"nombre": categoria.nombre},
    )
    await db.commit()
    await db.refresh(categoria)
    return categoria


async def obtener_categoria(db: AsyncSession, ctx: Contexto, categoria_id: int) -> Categoria:
    categoria = await db.scalar(
        select(Categoria).where(Categoria.id == categoria_id, Categoria.empresa_id == ctx.empresa_id)
    )
    if categoria is None:
        raise NoEncontrado("La categoría no existe")
    return categoria


async def _totales_productos(db: AsyncSession, categoria_ids: list[int]) -> dict[int, int]:
    if not categoria_ids:
        return {}
    filas = await db.execute(
        select(Producto.categoria_id, func.count()).where(Producto.categoria_id.in_(categoria_ids)).group_by(Producto.categoria_id)
    )
    return {c: n for c, n in filas.all()}


async def salidas_categorias(db: AsyncSession, categorias: list[Categoria]) -> list[CategoriaSalida]:
    totales = await _totales_productos(db, [c.id for c in categorias])
    return [
        CategoriaSalida.model_validate(c).model_copy(update={"total_productos": totales.get(c.id, 0)}) for c in categorias
    ]


async def listar_categorias(
    db: AsyncSession, ctx: Contexto, pag: ParametrosPagina, *, q: str | None, activa: bool | None
) -> tuple[list[Categoria], int]:
    condiciones = [Categoria.empresa_id == ctx.empresa_id]
    if q:
        condiciones.append(func.lower(Categoria.nombre).like(f"%{q.strip().lower()}%"))
    if activa is not None:
        condiciones.append(Categoria.activa.is_(activa))
    total = await db.scalar(select(func.count()).select_from(Categoria).where(*condiciones)) or 0
    filas = (
        await db.scalars(
            select(Categoria).where(*condiciones).order_by(Categoria.activa.desc(), func.lower(Categoria.nombre))
            .offset(pag.offset).limit(pag.tamano)
        )
    ).all()
    return list(filas), total


async def actualizar_categoria(db: AsyncSession, ctx: Contexto, categoria_id: int, datos: CategoriaActualizar) -> Categoria:
    categoria = await obtener_categoria(db, ctx, categoria_id)
    cambios = datos.model_dump(exclude_unset=True)
    antes = {"nombre": categoria.nombre, "descripcion": categoria.descripcion}
    if cambios.get("nombre"):
        await _nombre_categoria_libre(db, ctx.empresa_id, cambios["nombre"], categoria.id)
        categoria.nombre = cambios["nombre"]
    if "descripcion" in cambios:
        categoria.descripcion = cambios["descripcion"]
    await auditoria_service.registrar(
        db, modulo="categorias", accion="actualizar", ctx=ctx, entidad="categoria", entidad_id=categoria.id,
        detalle={"antes": antes, "despues": {"nombre": categoria.nombre, "descripcion": categoria.descripcion}},
    )
    await db.commit()
    await db.refresh(categoria)
    return categoria


async def cambiar_estado_categoria(db: AsyncSession, ctx: Contexto, categoria_id: int, activa: bool) -> Categoria:
    categoria = await obtener_categoria(db, ctx, categoria_id)
    if categoria.activa == activa:
        return categoria
    if not activa:
        activos = await db.scalar(
            select(func.count()).select_from(Producto).where(Producto.categoria_id == categoria.id, Producto.activo.is_(True))
        )
        if activos:
            raise Conflicto(
                f"La categoría tiene {activos} producto(s) activo(s). Muévelos a otra categoría antes de inhabilitarla.",
                codigo="categoria_con_productos",
            )
    categoria.activa = activa
    await auditoria_service.registrar(
        db, modulo="categorias", accion="reactivar" if activa else "inhabilitar", ctx=ctx, entidad="categoria",
        entidad_id=categoria.id, detalle={"nombre": categoria.nombre},
    )
    await db.commit()
    await db.refresh(categoria)
    return categoria


# ----------------------------------------------------------------------------- productos


async def _categoria_utilizable(db: AsyncSession, ctx: Contexto, categoria_id: int) -> Categoria:
    categoria = await obtener_categoria(db, ctx, categoria_id)
    if not categoria.activa:
        raise Conflicto(f"La categoría «{categoria.nombre}» está inhabilitada", codigo="categoria_inactiva")
    return categoria


async def crear_producto(db: AsyncSession, ctx: Contexto, datos: ProductoCrear) -> Producto:
    categoria = await _categoria_utilizable(db, ctx, datos.categoria_id)
    if await db.scalar(select(Producto.id).where(Producto.empresa_id == ctx.empresa_id, Producto.codigo == datos.codigo)):
        raise Conflicto(f"Ya existe un producto con el código «{datos.codigo}»", codigo="codigo_duplicado")
    producto = Producto(
        empresa_id=ctx.empresa_id, categoria_id=categoria.id, codigo=datos.codigo, nombre=datos.nombre,
        descripcion=datos.descripcion, unidad_medida=datos.unidad_medida, costo=datos.costo,
        precio_venta=datos.precio_venta,
    )
    db.add(producto)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise Conflicto(f"Ya existe un producto con el código «{datos.codigo}»", codigo="codigo_duplicado") from exc
    await auditoria_service.registrar(
        db, modulo="productos", accion="crear", ctx=ctx, entidad="producto", entidad_id=producto.id,
        detalle={"codigo": producto.codigo, "nombre": producto.nombre, "categoria": categoria.nombre,
                 "costo": producto.costo, "precio_venta": producto.precio_venta},
    )
    await db.commit()
    await db.refresh(producto)
    return producto


async def obtener_producto(db: AsyncSession, ctx: Contexto, producto_id: int) -> Producto:
    producto = await db.scalar(select(Producto).where(Producto.id == producto_id, Producto.empresa_id == ctx.empresa_id))
    if producto is None:
        raise NoEncontrado("El producto no existe")
    return producto


async def listar_productos(
    db: AsyncSession,
    ctx: Contexto,
    pag: ParametrosPagina,
    *,
    q: str | None,
    categoria_id: int | None,
    activo: bool | None,
) -> tuple[list[Producto], int]:
    condiciones = [Producto.empresa_id == ctx.empresa_id]
    if q:
        patron = f"%{q.strip().lower()}%"
        condiciones.append(func.lower(Producto.nombre).like(patron) | func.lower(Producto.codigo).like(patron))
    if categoria_id:
        condiciones.append(Producto.categoria_id == categoria_id)
    if activo is not None:
        condiciones.append(Producto.activo.is_(activo))
    total = await db.scalar(select(func.count()).select_from(Producto).where(*condiciones)) or 0
    filas = (
        await db.scalars(
            select(Producto).where(*condiciones).order_by(Producto.activo.desc(), func.lower(Producto.nombre))
            .offset(pag.offset).limit(pag.tamano)
        )
    ).all()
    return list(filas), total


async def salidas_productos(db: AsyncSession, ctx: Contexto, productos: list[Producto]) -> list[ProductoSalida]:
    if not productos:
        return []
    ids = [p.id for p in productos]
    categorias = {
        c.id: c
        for c in (await db.scalars(select(Categoria).where(Categoria.id.in_({p.categoria_id for p in productos})))).all()
    }
    consulta = (
        select(InventarioSede.producto_id, func.sum(InventarioSede.cantidad))
        .where(InventarioSede.producto_id.in_(ids), InventarioSede.empresa_id == ctx.empresa_id)
        .group_by(InventarioSede.producto_id)
    )
    autorizadas = ctx.sedes_autorizadas()
    if autorizadas is not None:
        consulta = consulta.where(InventarioSede.sede_id.in_(autorizadas))
    existencias = {pid: int(total or 0) for pid, total in (await db.execute(consulta)).all()}
    return [
        ProductoSalida(
            id=p.id, codigo=p.codigo, nombre=p.nombre, descripcion=p.descripcion,
            categoria=CategoriaResumen.model_validate(categorias[p.categoria_id]),
            unidad_medida=p.unidad_medida, costo=p.costo, precio_venta=p.precio_venta, activo=p.activo,
            existencias_total=existencias.get(p.id, 0),
            created_at=p.created_at, updated_at=p.updated_at,
        )
        for p in productos
    ]


async def actualizar_producto(db: AsyncSession, ctx: Contexto, producto_id: int, datos: ProductoActualizar) -> Producto:
    producto = await obtener_producto(db, ctx, producto_id)
    cambios = datos.model_dump(exclude_unset=True)
    campos = ("nombre", "descripcion", "categoria_id", "unidad_medida", "costo", "precio_venta")
    antes = {c: getattr(producto, c) for c in campos}
    if cambios.get("categoria_id") and cambios["categoria_id"] != producto.categoria_id:
        await _categoria_utilizable(db, ctx, cambios["categoria_id"])
    for campo in campos:
        if campo in cambios and not (cambios[campo] is None and campo in ("nombre", "categoria_id", "unidad_medida")):
            setattr(producto, campo, cambios[campo])
    despues = {c: getattr(producto, c) for c in campos}
    await auditoria_service.registrar(
        db, modulo="productos", accion="actualizar", ctx=ctx, entidad="producto", entidad_id=producto.id,
        detalle={"codigo": producto.codigo, "antes": antes, "despues": despues},
    )
    await db.commit()
    await db.refresh(producto)
    return producto


async def cambiar_estado_producto(db: AsyncSession, ctx: Contexto, producto_id: int, activo: bool) -> Producto:
    producto = await obtener_producto(db, ctx, producto_id)
    if producto.activo == activo:
        return producto
    if not activo:
        pendientes = await db.scalar(
            select(func.count(func.distinct(Traslado.id)))
            .select_from(Traslado)
            .join(TrasladoItem, TrasladoItem.traslado_id == Traslado.id)
            .where(Traslado.empresa_id == ctx.empresa_id, TrasladoItem.producto_id == producto.id,
                   Traslado.estado.in_(("solicitado", "aprobado")))
        )
        if pendientes:
            raise Conflicto(
                f"El producto está en {pendientes} traslado(s) pendiente(s). Ciérralos antes de inhabilitarlo.",
                codigo="producto_en_traslados",
            )
    producto.activo = activo
    await auditoria_service.registrar(
        db, modulo="productos", accion="reactivar" if activo else "inhabilitar", ctx=ctx, entidad="producto",
        entidad_id=producto.id, detalle={"codigo": producto.codigo, "nombre": producto.nombre},
    )
    await db.commit()
    await db.refresh(producto)
    return producto
