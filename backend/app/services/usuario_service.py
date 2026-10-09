"""Gestión de usuarios por el administrador (RF-001 a RF-004, RU-006).

Reglas: el correo es único; la empresa y la sede NUNCA vienen del navegador sin validación;
un rol de alcance «sede» exige sede; no se puede asignar un rol con más permisos que los propios;
siempre debe quedar al menos un administrador activo; los cambios de rol/sede se auditan.
"""


from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.acceso import Contexto
from app.core.exceptions import Conflicto, NoEncontrado, ReglaNegocio, SinPermiso
from app.core.security import hash_password
from app.core.tiempo import ahora_utc, asegurar_utc
from app.models.acceso import Rol
from app.models.sede import Sede
from app.models.usuario import Usuario
from app.schemas.comunes import ParametrosPagina
from app.schemas.usuario import RolResumen, SedeUsuario, UsuarioActualizar, UsuarioCrear, UsuarioSalida
from app.core.sql import bloqueo_asesor
from app.services import auditoria_service
from app.services.alcance import obtener_sede_de_empresa


def a_salida(u: Usuario, sede: Sede | None) -> UsuarioSalida:
    return UsuarioSalida(
        id=u.id, nombre=u.nombre, email=u.email, activo=u.activo, rol=RolResumen.model_validate(u.rol),
        sede=SedeUsuario.model_validate(sede) if sede else None,
        bloqueado=bool(u.bloqueado_hasta and asegurar_utc(u.bloqueado_hasta) > ahora_utc()),
        debe_cambiar_password=u.debe_cambiar_password, ultimo_acceso=u.ultimo_acceso, created_at=u.created_at,
    )


async def _sedes_por_id(db: AsyncSession, ids: set[int]) -> dict[int, Sede]:
    if not ids:
        return {}
    return {s.id: s for s in (await db.scalars(select(Sede).where(Sede.id.in_(ids)))).all()}


async def salidas(db: AsyncSession, usuarios: list[Usuario]) -> list[UsuarioSalida]:
    sedes = await _sedes_por_id(db, {u.sede_id for u in usuarios if u.sede_id})
    return [a_salida(u, sedes.get(u.sede_id)) for u in usuarios]


async def _rol_de_empresa(db: AsyncSession, ctx: Contexto, rol_id: int) -> Rol:
    rol = await db.scalar(select(Rol).where(Rol.id == rol_id, Rol.empresa_id == ctx.empresa_id))
    if rol is None:
        raise NoEncontrado("El rol no existe")
    if not rol.activo:
        raise ReglaNegocio(f"El rol «{rol.nombre}» está inhabilitado", codigo="rol_inactivo")
    exceso = rol.codigos_permisos - ctx.permisos
    if exceso:
        raise SinPermiso("No puedes asignar un rol con más permisos que los tuyos", codigo="escalada_de_privilegios")
    return rol


async def _resolver_sede(db: AsyncSession, ctx: Contexto, rol: Rol, sede_id: int | None) -> int | None:
    if rol.alcance == "sede":
        if sede_id is None:
            raise ReglaNegocio(
                f"El rol «{rol.nombre}» trabaja en una sede: debes asignar una sede", codigo="sede_requerida"
            )
        sede = await obtener_sede_de_empresa(db, ctx.empresa_id, sede_id, requerir_activa=True)
        return sede.id
    return None  # roles de alcance empresa: no se asocian a una sede


async def _email_disponible(db: AsyncSession, email: str, excluir_id: int | None = None) -> None:
    consulta = select(Usuario.id).where(func.lower(Usuario.email) == email.lower())
    if excluir_id:
        consulta = consulta.where(Usuario.id != excluir_id)
    if await db.scalar(consulta):
        raise Conflicto("Ese correo ya está registrado", codigo="email_duplicado")


async def crear(db: AsyncSession, ctx: Contexto, datos: UsuarioCrear) -> Usuario:
    await _email_disponible(db, datos.email)
    rol = await _rol_de_empresa(db, ctx, datos.rol_id)
    sede_id = await _resolver_sede(db, ctx, rol, datos.sede_id)
    usuario = Usuario(
        empresa_id=ctx.empresa_id, rol_id=rol.id, sede_id=sede_id, nombre=datos.nombre, email=datos.email.lower(),
        password_hash=hash_password(datos.password), debe_cambiar_password=datos.forzar_cambio_password,
    )
    db.add(usuario)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise Conflicto("Ese correo ya está registrado", codigo="email_duplicado") from exc
    await auditoria_service.registrar(
        db, modulo="usuarios", accion="crear", ctx=ctx, entidad="usuario", entidad_id=usuario.id, sede_id=sede_id,
        detalle={"nombre": usuario.nombre, "email": usuario.email, "rol": rol.nombre, "sede_id": sede_id},
    )
    await db.commit()
    await db.refresh(usuario)
    return usuario


async def listar(
    db: AsyncSession,
    ctx: Contexto,
    pag: ParametrosPagina,
    *,
    q: str | None = None,
    rol_id: int | None = None,
    sede_id: int | None = None,
    activo: bool | None = None,
) -> tuple[list[Usuario], int]:
    condiciones = [Usuario.empresa_id == ctx.empresa_id]
    if q:
        patron = f"%{q.strip().lower()}%"
        condiciones.append(func.lower(Usuario.nombre).like(patron) | func.lower(Usuario.email).like(patron))
    if rol_id:
        condiciones.append(Usuario.rol_id == rol_id)
    if sede_id:
        condiciones.append(Usuario.sede_id == sede_id)
    if activo is not None:
        condiciones.append(Usuario.activo.is_(activo))
    total = await db.scalar(select(func.count()).select_from(Usuario).where(*condiciones)) or 0
    filas = (
        await db.scalars(
            select(Usuario).where(*condiciones).order_by(Usuario.activo.desc(), func.lower(Usuario.nombre))
            .offset(pag.offset).limit(pag.tamano)
        )
    ).all()
    return list(filas), total


async def obtener(db: AsyncSession, ctx: Contexto, usuario_id: int) -> Usuario:
    usuario = await db.scalar(select(Usuario).where(Usuario.id == usuario_id, Usuario.empresa_id == ctx.empresa_id))
    if usuario is None:
        raise NoEncontrado("El usuario no existe")
    return usuario


async def _contar_admins_activos(db: AsyncSession, empresa_id: int, excluir_id: int | None = None) -> int:
    # Serializa las decisiones «¿queda otro administrador?» de una misma empresa (evita que dos
    # administradores se inhabiliten mutuamente en paralelo y la empresa quede sin administrador).
    await bloqueo_asesor(db, 7_400_000_000 + empresa_id)
    consulta = (
        select(func.count()).select_from(Usuario).join(Rol, Rol.id == Usuario.rol_id)
        .where(Usuario.empresa_id == empresa_id, Usuario.activo.is_(True), Rol.clave == "admin")
    )
    if excluir_id:
        consulta = consulta.where(Usuario.id != excluir_id)
    return int(await db.scalar(consulta) or 0)


async def actualizar(db: AsyncSession, ctx: Contexto, usuario_id: int, datos: UsuarioActualizar) -> Usuario:
    usuario = await obtener(db, ctx, usuario_id)
    cambios = datos.model_dump(exclude_unset=True)
    antes = {"nombre": usuario.nombre, "email": usuario.email, "rol_id": usuario.rol_id, "sede_id": usuario.sede_id}

    if "email" in cambios and cambios["email"] and cambios["email"].lower() != usuario.email.lower():
        await _email_disponible(db, cambios["email"], usuario.id)
        usuario.email = cambios["email"].lower()
    if cambios.get("nombre"):
        usuario.nombre = cambios["nombre"]

    # Rol y sede se validan juntos: el rol de destino decide si la sede es obligatoria.
    rol_destino = usuario.rol
    if cambios.get("rol_id") and cambios["rol_id"] != usuario.rol_id:
        rol_destino = await _rol_de_empresa(db, ctx, cambios["rol_id"])
        if usuario.rol.clave == "admin" and rol_destino.clave != "admin" and usuario.activo:
            if await _contar_admins_activos(db, ctx.empresa_id, excluir_id=usuario.id) == 0:
                raise Conflicto("Debe quedar al menos un administrador activo", codigo="ultimo_administrador")
    sede_solicitada = None if cambios.get("quitar_sede") else cambios.get("sede_id", usuario.sede_id)
    if "rol_id" in cambios or "sede_id" in cambios or cambios.get("quitar_sede"):
        usuario.sede_id = await _resolver_sede(db, ctx, rol_destino, sede_solicitada)
        usuario.rol_id = rol_destino.id

    despues = {"nombre": usuario.nombre, "email": usuario.email, "rol_id": usuario.rol_id, "sede_id": usuario.sede_id}
    cambio_acceso = (antes["rol_id"], antes["sede_id"]) != (despues["rol_id"], despues["sede_id"])
    await auditoria_service.registrar(
        db, modulo="usuarios", accion="cambiar_rol_o_sede" if cambio_acceso else "actualizar", ctx=ctx,
        entidad="usuario", entidad_id=usuario.id, sede_id=usuario.sede_id,
        detalle={"antes": antes, "despues": despues},
    )
    await db.commit()
    await db.refresh(usuario)
    return usuario


async def cambiar_estado(db: AsyncSession, ctx: Contexto, usuario_id: int, activo: bool) -> Usuario:
    usuario = await obtener(db, ctx, usuario_id)
    if usuario.activo == activo:
        return usuario
    if not activo:
        if usuario.id == ctx.usuario_id:
            raise ReglaNegocio("No puedes inhabilitar tu propia cuenta", codigo="auto_inhabilitacion")
        if usuario.rol.clave == "admin" and await _contar_admins_activos(db, ctx.empresa_id, usuario.id) == 0:
            raise Conflicto("Debe quedar al menos un administrador activo", codigo="ultimo_administrador")
    usuario.activo = activo
    await auditoria_service.registrar(
        db, modulo="usuarios", accion="reactivar" if activo else "inhabilitar", ctx=ctx, entidad="usuario",
        entidad_id=usuario.id, sede_id=usuario.sede_id, detalle={"email": usuario.email},
    )
    await db.commit()
    await db.refresh(usuario)
    return usuario


async def restablecer_password(db: AsyncSession, ctx: Contexto, usuario_id: int, nueva_password: str) -> Usuario:
    """El administrador asigna una contraseña temporal: la persona deberá cambiarla al ingresar."""
    usuario = await obtener(db, ctx, usuario_id)
    usuario.password_hash = hash_password(nueva_password)
    usuario.password_version += 1
    usuario.debe_cambiar_password = True
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    await auditoria_service.registrar(
        db, modulo="usuarios", accion="restablecer_password", ctx=ctx, entidad="usuario", entidad_id=usuario.id,
        sede_id=usuario.sede_id, detalle={"email": usuario.email},
    )
    await db.commit()
    await db.refresh(usuario)
    return usuario


async def desbloquear(db: AsyncSession, ctx: Contexto, usuario_id: int) -> Usuario:
    usuario = await obtener(db, ctx, usuario_id)
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    await auditoria_service.registrar(
        db, modulo="usuarios", accion="desbloquear", ctx=ctx, entidad="usuario", entidad_id=usuario.id,
        detalle={"email": usuario.email},
    )
    await db.commit()
    await db.refresh(usuario)
    return usuario


