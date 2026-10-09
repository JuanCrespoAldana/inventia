from sqlalchemy.ext.asyncio import AsyncSession

from app.core.acceso import Contexto
from app.models.empresa import Empresa
from app.models.sede import Sede
from app.schemas.usuario import RolResumen, SedeUsuario, UsuarioSesion


async def construir_sesion(db: AsyncSession, ctx: Contexto) -> UsuarioSesion:
    empresa = await db.get(Empresa, ctx.empresa_id)
    sede = await db.get(Sede, ctx.usuario.sede_id) if ctx.usuario.sede_id else None
    return UsuarioSesion(
        id=ctx.usuario.id,
        nombre=ctx.usuario.nombre,
        email=ctx.usuario.email,
        empresa_id=ctx.empresa_id,
        empresa_nombre=empresa.nombre if empresa else "",
        rol=RolResumen.model_validate(ctx.rol),
        sede=SedeUsuario.model_validate(sede) if sede else None,
        permisos=sorted(ctx.permisos),
        debe_cambiar_password=ctx.usuario.debe_cambiar_password,
    )
