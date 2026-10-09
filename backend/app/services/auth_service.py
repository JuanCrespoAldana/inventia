"""Inicio de sesión, cierre de sesión, cambio y recuperación de contraseña (RF-005, RF-006).

Seguridad aplicada (RNF-022, RNF-023, RNF-025, RNF-026):
 - Argon2id; contraseña nunca en logs ni auditoría.
 - Bloqueo temporal de la cuenta tras N intentos fallidos consecutivos + límite por IP en la API.
 - El mensaje de credenciales es el mismo exista o no el correo (sin enumeración de usuarios).
 - Códigos de recuperación de 6 dígitos: hash en base de datos, vencen, un solo uso y máximo 5 intentos.
"""

import logging
import secrets
from datetime import timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.acceso import Contexto
from app.core.config import settings
from app.core.email import enviar_codigo_recuperacion
from app.core.exceptions import (
    CodigoInvalido,
    CredencialesInvalidas,
    CuentaBloqueada,
    ReglaNegocio,
    SinPermiso,
    TokenRecuperacionInvalido,
)
from app.core.security import (
    comparar_seguro,
    create_access_token,
    generar_codigo_numerico,
    hash_password,
    hash_token,
    necesita_rehash,
    verificar_contra_relleno,
    verify_password,
)
from app.core.tiempo import ahora_utc, asegurar_utc
from app.models.empresa import Empresa
from app.models.password_reset_token import PasswordResetToken
from app.models.usuario import Usuario
from app.services import auditoria_service
from app.services.sesion import construir_sesion

logger = logging.getLogger("inventia.auth")

MAX_INTENTOS_CODIGO = 5


async def _buscar_por_correo(db: AsyncSession, email: str) -> Usuario | None:
    return await db.scalar(select(Usuario).where(func.lower(Usuario.email) == email.lower()))


async def iniciar_sesion(db: AsyncSession, email: str, password: str) -> tuple[str, Usuario]:
    ahora = ahora_utc()
    usuario = await _buscar_por_correo(db, email)

    if usuario is None:
        verificar_contra_relleno(password)  # mismo costo de tiempo que un usuario real
        await auditoria_service.registrar(
            db, modulo="auth", accion="inicio_sesion", resultado="fallido",
            detalle={"email": email.lower(), "motivo": "credenciales_invalidas"},
        )
        await db.commit()
        raise CredencialesInvalidas("Correo o contraseña incorrectos")

    # Bloqueo vigente: no se evalúa la contraseña ni se revela nada más.
    if usuario.bloqueado_hasta is not None:
        if asegurar_utc(usuario.bloqueado_hasta) > ahora:
            minutos = max(1, int((asegurar_utc(usuario.bloqueado_hasta) - ahora).total_seconds() // 60) + 1)
            await auditoria_service.registrar(
                db, modulo="auth", accion="inicio_sesion", resultado="fallido", usuario=usuario,
                detalle={"motivo": "cuenta_bloqueada"},
            )
            await db.commit()
            raise CuentaBloqueada(
                f"Demasiados intentos fallidos. Tu cuenta está bloqueada temporalmente; inténtalo de nuevo en {minutos} min."
            )
        usuario.bloqueado_hasta = None  # el bloqueo venció
        usuario.intentos_fallidos = 0

    if not verify_password(password, usuario.password_hash):
        usuario.intentos_fallidos += 1
        detalle = {"motivo": "credenciales_invalidas", "intentos": usuario.intentos_fallidos}
        if usuario.intentos_fallidos >= settings.login_max_attempts:
            usuario.bloqueado_hasta = ahora + timedelta(minutes=settings.login_lock_minutes)
            detalle["bloqueada_hasta"] = usuario.bloqueado_hasta.isoformat()
        await auditoria_service.registrar(
            db, modulo="auth", accion="inicio_sesion", resultado="fallido", usuario=usuario, detalle=detalle
        )
        await db.commit()
        raise CredencialesInvalidas("Correo o contraseña incorrectos")

    # Credenciales correctas: ahora sí se puede informar el estado de la cuenta.
    empresa = await db.get(Empresa, usuario.empresa_id)
    if not usuario.activo or empresa is None or not empresa.activa:
        await auditoria_service.registrar(
            db, modulo="auth", accion="inicio_sesion", resultado="fallido", usuario=usuario,
            detalle={"motivo": "cuenta_inhabilitada"},
        )
        await db.commit()
        raise SinPermiso(
            "Tu cuenta está inhabilitada. Comunícate con el administrador de tu empresa.", codigo="cuenta_inhabilitada"
        )

    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    usuario.ultimo_acceso = ahora
    if necesita_rehash(usuario.password_hash):
        usuario.password_hash = hash_password(password)
    await auditoria_service.registrar(db, modulo="auth", accion="inicio_sesion", usuario=usuario, sede_id=usuario.sede_id)
    await db.commit()
    return create_access_token(usuario.id, usuario.password_version), usuario


async def cerrar_sesion(db: AsyncSession, ctx: Contexto) -> None:
    await auditoria_service.registrar(db, modulo="auth", accion="cierre_sesion", ctx=ctx, sede_id=ctx.sede_id)
    await db.commit()


async def cambiar_password(db: AsyncSession, ctx: Contexto, password_actual: str, nueva: str) -> str:
    usuario = ctx.usuario
    if not verify_password(password_actual, usuario.password_hash):
        await auditoria_service.registrar(
            db, modulo="auth", accion="cambio_password", ctx=ctx, resultado="fallido",
            detalle={"motivo": "password_actual_incorrecta"},
        )
        await db.commit()
        raise CredencialesInvalidas("La contraseña actual no es correcta", codigo="password_actual_incorrecta")
    if verify_password(nueva, usuario.password_hash):
        raise ReglaNegocio("La nueva contraseña debe ser diferente a la actual", codigo="password_repetida")
    usuario.password_hash = hash_password(nueva)
    usuario.password_version += 1
    usuario.debe_cambiar_password = False
    await auditoria_service.registrar(db, modulo="auth", accion="cambio_password", ctx=ctx)
    await db.commit()
    return create_access_token(usuario.id, usuario.password_version)


# ---------------------------------------------------------------- recuperación (RF-006)
async def solicitar_recuperacion(db: AsyncSession, email: str) -> None:
    """Genera y envía el código. No revela si el correo existe: siempre termina sin error."""
    usuario = await _buscar_por_correo(db, email)
    if usuario is None or not usuario.activo:
        return

    # Un código nuevo invalida los anteriores pendientes.
    await db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.usuario_id == usuario.id, PasswordResetToken.used.is_(False))
        .values(used=True)
    )
    codigo = generar_codigo_numerico(6)
    db.add(
        PasswordResetToken(
            usuario_id=usuario.id,
            codigo_hash=hash_token(codigo),
            expires_at=ahora_utc() + timedelta(minutes=settings.reset_token_expire_minutes),
        )
    )
    await auditoria_service.registrar(db, modulo="auth", accion="solicitud_recuperacion", usuario=usuario)
    await db.commit()

    try:
        await enviar_codigo_recuperacion(usuario.email, usuario.nombre, codigo)
    except Exception:  # noqa: BLE001 - el fallo del proveedor no debe cambiar la respuesta ni revelar nada
        logger.exception("No se pudo enviar el código de recuperación a un usuario")


async def verificar_codigo(db: AsyncSession, email: str, codigo: str) -> str:
    usuario = await _buscar_por_correo(db, email)
    if usuario is None:
        raise CodigoInvalido()

    registro = await db.scalar(
        select(PasswordResetToken)
        .where(
            PasswordResetToken.usuario_id == usuario.id,
            PasswordResetToken.used.is_(False),
            PasswordResetToken.verificado.is_(False),
        )
        .order_by(PasswordResetToken.created_at.desc(), PasswordResetToken.id.desc())
    )
    if registro is None or registro.intentos >= MAX_INTENTOS_CODIGO or asegurar_utc(registro.expires_at) < ahora_utc():
        raise CodigoInvalido()

    if not comparar_seguro(hash_token(codigo), registro.codigo_hash):
        registro.intentos += 1
        await db.commit()
        raise CodigoInvalido(intentos_restantes=MAX_INTENTOS_CODIGO - registro.intentos)

    sesion = secrets.token_urlsafe(32)
    registro.session_token_hash = hash_token(sesion)
    registro.verificado = True
    await db.commit()
    return sesion


async def restablecer_password(db: AsyncSession, session_token: str, nueva_password: str) -> None:
    registro = await db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.session_token_hash == hash_token(session_token))
    )
    if (
        registro is None
        or not registro.verificado
        or registro.used
        or asegurar_utc(registro.expires_at) < ahora_utc()
    ):
        raise TokenRecuperacionInvalido()

    usuario = await db.get(Usuario, registro.usuario_id)
    if usuario is None or not usuario.activo:
        raise TokenRecuperacionInvalido()
    usuario.password_hash = hash_password(nueva_password)
    usuario.password_version += 1  # cierra las sesiones abiertas con la contraseña anterior
    usuario.debe_cambiar_password = False
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    registro.used = True
    await auditoria_service.registrar(db, modulo="auth", accion="restablecer_password", usuario=usuario)
    await db.commit()


async def sesion_de_usuario(db: AsyncSession, ctx: Contexto):
    return await construir_sesion(db, ctx)
