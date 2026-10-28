"""Mapper de usuarios: convierte la entidad Usuario (con su sede) en su DTO de salida."""

from app.dto.usuario_dto import RolResumen, SedeUsuario, UsuarioSalida
from app.model.sede import Sede
from app.model.usuario import Usuario
from app.util.tiempo import ahora_utc, asegurar_utc


def a_usuario_salida(u: Usuario, sede: Sede | None) -> UsuarioSalida:
    return UsuarioSalida(
        id=u.id, nombre=u.nombre, email=u.email, activo=u.activo, rol=RolResumen.model_validate(u.rol),
        sede=SedeUsuario.model_validate(sede) if sede else None,
        bloqueado=bool(u.bloqueado_hasta and asegurar_utc(u.bloqueado_hasta) > ahora_utc()),
        debe_cambiar_password=u.debe_cambiar_password, ultimo_acceso=u.ultimo_acceso, created_at=u.created_at,
    )
