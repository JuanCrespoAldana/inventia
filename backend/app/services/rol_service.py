"""Roles personalizados y asignación de permisos (RU-003, RF-038)."""

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.acceso import Contexto
from app.core.exceptions import Conflicto, NoEncontrado, ReglaNegocio, SinPermiso
from app.core.permisos import CODIGOS_PERMISOS
from app.models.acceso import Permiso, Rol, RolPermiso
from app.models.usuario import Usuario
from app.schemas.rol import RolActualizar, RolCrear, RolSalida
from app.services import auditoria_service


async def _conteo_usuarios(db: AsyncSession, rol_ids: list[int]) -> dict[int, int]:
    if not rol_ids:
        return {}
    filas = await db.execute(select(Usuario.rol_id, func.count()).where(Usuario.rol_id.in_(rol_ids)).group_by(Usuario.rol_id))
    return {r: n for r, n in filas.all()}


def a_salida(rol: Rol, total_usuarios: int) -> RolSalida:
    return RolSalida(
        id=rol.id, clave=rol.clave, nombre=rol.nombre, descripcion=rol.descripcion, alcance=rol.alcance,
        es_sistema=rol.es_sistema, activo=rol.activo, permisos=sorted(rol.codigos_permisos),
        total_usuarios=total_usuarios, created_at=rol.created_at, updated_at=rol.updated_at,
    )


async def salidas(db: AsyncSession, roles: list[Rol]) -> list[RolSalida]:
    conteos = await _conteo_usuarios(db, [r.id for r in roles])
    return [a_salida(r, conteos.get(r.id, 0)) for r in roles]


async def listar_permisos(db: AsyncSession) -> list[Permiso]:
    return list((await db.scalars(select(Permiso).order_by(Permiso.modulo, Permiso.codigo))).all())


async def listar(db: AsyncSession, ctx: Contexto) -> list[Rol]:
    return list(
        (await db.scalars(select(Rol).where(Rol.empresa_id == ctx.empresa_id).order_by(Rol.es_sistema.desc(), Rol.nombre))).all()
    )


async def obtener(db: AsyncSession, ctx: Contexto, rol_id: int) -> Rol:
    rol = await db.scalar(select(Rol).where(Rol.id == rol_id, Rol.empresa_id == ctx.empresa_id))
    if rol is None:
        raise NoEncontrado("El rol no existe")
    return rol


def _validar_permisos(ctx: Contexto, permisos: list[str]) -> set[str]:
    solicitados = set(permisos)
    desconocidos = solicitados - CODIGOS_PERMISOS
    if desconocidos:
        raise ReglaNegocio(f"Permisos desconocidos: {', '.join(sorted(desconocidos))}", codigo="permiso_desconocido")
    exceso = solicitados - ctx.permisos
    if exceso:
        raise SinPermiso("No puedes conceder permisos que tú no tienes", codigo="escalada_de_privilegios")
    return solicitados


async def _nombre_libre(db: AsyncSession, empresa_id: int, nombre: str, excluir_id: int | None = None) -> None:
    consulta = select(Rol.id).where(Rol.empresa_id == empresa_id, func.lower(Rol.nombre) == nombre.lower())
    if excluir_id:
        consulta = consulta.where(Rol.id != excluir_id)
    if await db.scalar(consulta):
        raise Conflicto(f"Ya existe un rol llamado «{nombre}»", codigo="rol_duplicado")


async def crear(db: AsyncSession, ctx: Contexto, datos: RolCrear) -> Rol:
    await _nombre_libre(db, ctx.empresa_id, datos.nombre)
    permisos = _validar_permisos(ctx, datos.permisos)
    rol = Rol(
        empresa_id=ctx.empresa_id, nombre=datos.nombre, descripcion=datos.descripcion, alcance=datos.alcance,
        es_sistema=False, permisos=[RolPermiso(permiso_codigo=c) for c in sorted(permisos)],
    )
    db.add(rol)
    await db.flush()
    await auditoria_service.registrar(
        db, modulo="roles", accion="crear", ctx=ctx, entidad="rol", entidad_id=rol.id,
        detalle={"nombre": rol.nombre, "alcance": rol.alcance, "permisos": sorted(permisos)},
    )
    await db.commit()
    await db.refresh(rol)
    return rol


async def actualizar(db: AsyncSession, ctx: Contexto, rol_id: int, datos: RolActualizar) -> Rol:
    rol = await obtener(db, ctx, rol_id)
    cambios = datos.model_dump(exclude_unset=True)
    if rol.clave == "admin":
        raise ReglaNegocio("El rol Administrador no se puede modificar", codigo="rol_protegido")
    usuarios = (await _conteo_usuarios(db, [rol.id])).get(rol.id, 0)
    if cambios.get("nombre") and cambios["nombre"].lower() != rol.nombre.lower():
        if rol.es_sistema:
            raise ReglaNegocio("Los roles del sistema no se pueden renombrar", codigo="rol_protegido")
        await _nombre_libre(db, ctx.empresa_id, cambios["nombre"], rol.id)
    if cambios.get("alcance") and cambios["alcance"] != rol.alcance:
        if rol.es_sistema or usuarios:
            raise ReglaNegocio(
                "No se puede cambiar el alcance de un rol del sistema o con usuarios asignados", codigo="alcance_inmutable"
            )
    if cambios.get("activo") is False and usuarios:
        raise Conflicto("No se puede inhabilitar un rol con usuarios asignados", codigo="rol_en_uso")
    antes = {k: getattr(rol, k) for k in cambios}
    for campo, valor in cambios.items():
        if campo in ("nombre", "alcance", "activo") and valor is None:
            continue
        setattr(rol, campo, valor)
    await auditoria_service.registrar(
        db, modulo="roles", accion="actualizar", ctx=ctx, entidad="rol", entidad_id=rol.id,
        detalle={"antes": antes, "despues": cambios},
    )
    await db.commit()
    await db.refresh(rol)
    return rol


async def asignar_permisos(db: AsyncSession, ctx: Contexto, rol_id: int, permisos: list[str]) -> Rol:
    rol = await obtener(db, ctx, rol_id)
    if rol.clave == "admin":
        raise ReglaNegocio("El rol Administrador siempre conserva todos los permisos", codigo="rol_protegido")
    nuevos = _validar_permisos(ctx, permisos)
    actuales = rol.codigos_permisos
    # Un rol puede perder permisos que quien lo edita no posee solo si no los toca: se conservan.
    conservados = {p for p in actuales if p not in ctx.permisos}
    finales = nuevos | conservados
    for existente in list(rol.permisos):
        if existente.permiso_codigo not in finales:
            rol.permisos.remove(existente)
    for codigo in sorted(finales - actuales):
        rol.permisos.append(RolPermiso(rol_id=rol.id, permiso_codigo=codigo))
    await db.flush()
    await auditoria_service.registrar(
        db, modulo="roles", accion="asignar_permisos", ctx=ctx, entidad="rol", entidad_id=rol.id,
        detalle={"agregados": sorted(finales - actuales), "quitados": sorted(actuales - finales)},
    )
    await db.commit()
    return rol


async def eliminar(db: AsyncSession, ctx: Contexto, rol_id: int) -> None:
    rol = await obtener(db, ctx, rol_id)
    if rol.es_sistema:
        raise ReglaNegocio("Los roles del sistema no se pueden eliminar", codigo="rol_protegido")
    if (await _conteo_usuarios(db, [rol.id])).get(rol.id, 0):
        raise Conflicto("No se puede eliminar un rol con usuarios asignados", codigo="rol_en_uso")
    nombre = rol.nombre
    await db.delete(rol)
    await auditoria_service.registrar(
        db, modulo="roles", accion="eliminar", ctx=ctx, entidad="rol", entidad_id=rol_id, detalle={"nombre": nombre}
    )
    await db.commit()
