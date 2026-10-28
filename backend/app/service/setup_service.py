"""Configuración inicial controlada: crea la empresa y su primer administrador (RF-007, RF-001).

Reemplaza al registro público anterior, donde el primer usuario en llegar se convertía en
administrador. Ahora la configuración solo es posible mientras NO exista ninguna empresa y, si se
define ``SETUP_TOKEN``, únicamente con ese token (obligatorio en producción).
"""

import secrets

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.dto.setup_dto import ConfiguracionInicial
from app.exception.excepciones import Conflicto, SinPermiso
from app.model.empresa import Empresa
from app.model.usuario import Usuario
from app.security.autenticacion import hash_password
from app.service import auditoria_service, bootstrap
from app.util.sql import bloqueo_asesor

_CLAVE_BLOQUEO_SETUP = 7_300_001


async def hay_empresa(db: AsyncSession) -> bool:
    return (await db.scalar(select(func.count()).select_from(Empresa))) > 0


async def crear_empresa_con_admin(
    db: AsyncSession,
    *,
    nombre: str,
    identificacion: str | None,
    direccion: str | None,
    ciudad: str | None,
    telefono: str | None,
    email_empresa: str | None,
    admin_nombre: str,
    admin_email: str,
    admin_password: str,
    forzar_cambio_password: bool = False,
) -> tuple[Empresa, Usuario]:
    """Crea una empresa, sus cinco roles y su administrador. Reutilizada por la API, el CLI y las pruebas."""
    if identificacion and await db.scalar(select(Empresa.id).where(Empresa.identificacion == identificacion)):
        raise Conflicto("Ya existe una empresa con esa identificación", codigo="identificacion_duplicada")
    if await db.scalar(select(Usuario.id).where(func.lower(Usuario.email) == admin_email.lower())):
        raise Conflicto("Ese correo ya está registrado", codigo="email_duplicado")

    await bootstrap.sincronizar_permisos(db)
    empresa = Empresa(
        nombre=nombre, identificacion=identificacion, direccion=direccion, ciudad=ciudad,
        telefono=telefono, email=email_empresa,
    )
    db.add(empresa)
    await db.flush()
    roles = await bootstrap.crear_roles_sistema(db, empresa.id)
    admin = Usuario(
        empresa_id=empresa.id,
        rol_id=roles["admin"].id,
        nombre=admin_nombre,
        email=admin_email.lower(),
        password_hash=hash_password(admin_password),
        debe_cambiar_password=forzar_cambio_password,
    )
    db.add(admin)
    await db.flush()
    await auditoria_service.registrar(
        db, modulo="empresa", accion="configuracion_inicial", usuario=admin, entidad="empresa",
        entidad_id=empresa.id, detalle={"empresa": nombre, "administrador": admin.email},
    )
    return empresa, admin


async def configurar(db: AsyncSession, datos: ConfiguracionInicial) -> tuple[Empresa, Usuario]:
    token = settings.setup_token
    if token and not secrets.compare_digest(datos.token_configuracion.encode(), token.encode()):
        raise SinPermiso("El token de configuración no es válido", codigo="token_configuracion_invalido")

    await bloqueo_asesor(db, _CLAVE_BLOQUEO_SETUP)  # evita dos configuraciones simultáneas
    if await hay_empresa(db):
        raise Conflicto(
            "El sistema ya fue configurado. Inicia sesión con el administrador existente.",
            codigo="ya_configurado",
        )
    empresa, admin = await crear_empresa_con_admin(
        db,
        nombre=datos.empresa_nombre,
        identificacion=datos.empresa_identificacion,
        direccion=datos.empresa_direccion,
        ciudad=datos.empresa_ciudad,
        telefono=datos.empresa_telefono,
        email_empresa=datos.empresa_email,
        admin_nombre=datos.admin_nombre,
        admin_email=datos.admin_email,
        admin_password=datos.admin_password,
    )
    await db.commit()
    # Recarga con rol y permisos (relaciones que no existían cuando se creó el objeto en memoria).
    admin = await db.scalar(
        select(Usuario).where(Usuario.id == admin.id).execution_options(populate_existing=True)
    )
    return empresa, admin
