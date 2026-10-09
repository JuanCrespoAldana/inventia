"""Sincronización del catálogo de permisos y creación de los roles del sistema de una empresa."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permisos import CODIGOS_PERMISOS, PERMISOS, ROLES_POR_CLAVE, ROLES_SISTEMA
from app.models.acceso import Permiso, Rol, RolPermiso


async def sincronizar_permisos(db: AsyncSession) -> None:
    """Deja la tabla ``permisos`` igual al catálogo definido en código.

    - Inserta los permisos nuevos y actualiza la descripción de los existentes.
    - Elimina los obsoletos (sus asignaciones caen por ON DELETE CASCADE).
    - Los permisos nuevos se añaden automáticamente a los roles «Administrador» de cada empresa y a los demás
      roles del SISTEMA cuyo conjunto por defecto los incluya (p. ej. «pqrs.crear» a todos). Los roles creados
      por la empresa no se tocan: su administrador decide. Solo se actúa sobre permisos NUEVOS, así que si una
      empresa le quitó un permiso a un rol, no se le vuelve a poner.
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
        roles = (await db.scalars(select(Rol).where(Rol.es_sistema.is_(True)))).all()
        for rol in roles:
            definicion = ROLES_POR_CLAVE.get(rol.clave)
            if definicion is None:
                continue
            for codigo in nuevos:
                if codigo in definicion.permisos:
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
