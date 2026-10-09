"""Sincronización del catálogo de permisos y creación de los roles del sistema de una empresa."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permisos import CODIGOS_PERMISOS, PERMISOS, ROLES_SISTEMA
from app.models.acceso import Permiso, Rol, RolPermiso


async def sincronizar_permisos(db: AsyncSession) -> None:
    """Deja la tabla ``permisos`` igual al catálogo definido en código.

    - Inserta los permisos nuevos y actualiza la descripción de los existentes.
    - Elimina los obsoletos (sus asignaciones caen por ON DELETE CASCADE).
    - Los permisos nuevos se añaden automáticamente a los roles «Administrador» de cada empresa.
    """
    existentes = {p.codigo: p for p in (await db.scalars(select(Permiso))).all()}
    nuevos: list[str] = []
    for definicion in PERMISOS:
        actual = existentes.get(definicion.codigo)
        if actual is None:
            db.add(Permiso(codigo=definicion.codigo, modulo=definicion.modulo, descripcion=definicion.descripcion))
            nuevos.append(definicion.codigo)
        elif (actual.modulo, actual.descripcion) != (definicion.modulo, definicion.descripcion):
            actual.modulo, actual.descripcion = definicion.modulo, definicion.descripcion
    obsoletos = set(existentes) - CODIGOS_PERMISOS
    if obsoletos:
        await db.execute(delete(RolPermiso).where(RolPermiso.permiso_codigo.in_(obsoletos)))
        await db.execute(delete(Permiso).where(Permiso.codigo.in_(obsoletos)))
    await db.flush()

    if nuevos:
        admins = (await db.scalars(select(Rol).where(Rol.clave == "admin"))).all()
        for rol in admins:
            for codigo in nuevos:
                db.add(RolPermiso(rol_id=rol.id, permiso_codigo=codigo))
        await db.flush()


async def crear_roles_sistema(db: AsyncSession, empresa_id: int) -> dict[str, Rol]:
    """Crea los cinco roles de la empresa (Tabla 6 del documento) con sus permisos por defecto."""
    roles: dict[str, Rol] = {}
    for definicion in ROLES_SISTEMA:
        rol = Rol(
            empresa_id=empresa_id,
            clave=definicion.clave,
            nombre=definicion.nombre,
            descripcion=definicion.descripcion,
            alcance=definicion.alcance,
            es_sistema=True,
            permisos=[RolPermiso(permiso_codigo=c) for c in sorted(definicion.permisos)],
        )
        db.add(rol)
        roles[definicion.clave] = rol
    await db.flush()
    return roles
