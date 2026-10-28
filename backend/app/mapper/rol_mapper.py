"""Mapper de roles: convierte la entidad Rol (con su conteo de usuarios) en su DTO de salida."""

from app.dto.rol_dto import RolSalida
from app.model.acceso import Rol


def a_rol_salida(rol: Rol, total_usuarios: int) -> RolSalida:
    return RolSalida(
        id=rol.id, clave=rol.clave, nombre=rol.nombre, descripcion=rol.descripcion, alcance=rol.alcance,
        es_sistema=rol.es_sistema, activo=rol.activo, permisos=sorted(rol.codigos_permisos),
        total_usuarios=total_usuarios, created_at=rol.created_at, updated_at=rol.updated_at,
    )
