"""Envío de correos por SMTP (Gmail u otro proveedor). Configuración en variables ``SMTP_*``."""

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

from app.core.config import settings

logger = logging.getLogger("inventia.correo")


def _enviar_smtp(destinatario: str, nombre: str, codigo: str) -> None:
    minutos = settings.reset_token_expire_minutes
    app = settings.app_nombre
    nombre_seguro = escape(nombre)

    mensaje = MIMEMultipart("alternative")
    mensaje["Subject"] = f"{app}: tu código para restablecer la contraseña"
    mensaje["From"] = settings.email_from
    mensaje["To"] = destinatario

    texto = (
        f"Hola {nombre},\n\n"
        f"Tu código para restablecer la contraseña de {app} es: {codigo}\n\n"
        f"Es válido por {minutos} minutos y solo puede usarse una vez. "
        f"Si no lo solicitaste, ignora este correo: tu contraseña no cambiará."
    )
    html = f"""
    <div style="font-family: Arial, sans-serif; background:#0A0A0F; color:#F5F6FA; padding:32px; text-align:center;">
      <h2 style="color:#ffffff; margin-bottom: 8px;">Tu código de verificación</h2>
      <p style="color:#9497A6;">Hola {nombre_seguro}, usa este código en {escape(app)} para continuar.</p>
      <div style="margin:28px 0; font-size:36px; font-weight:700; letter-spacing:10px;
                  color:#8AA3FF; font-family: monospace;">{codigo}</div>
      <p style="color:#9497A6; font-size:13px;">
        Válido por {minutos} minutos y de un solo uso. Si no lo solicitaste, ignora este correo.
      </p>
    </div>
    """
    mensaje.attach(MIMEText(texto, "plain", "utf-8"))
    mensaje.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as servidor:
        servidor.starttls()
        servidor.login(settings.smtp_user, settings.smtp_password)
        servidor.send_message(mensaje)


async def enviar_codigo_recuperacion(destinatario: str, nombre: str, codigo: str) -> None:
    if not settings.smtp_configurado:
        if settings.environment == "development":
            # Solo en desarrollo y sin SMTP: permite probar el flujo sin servidor de correo.
            logger.warning("SMTP no configurado (modo desarrollo). Código de %s: %s", destinatario, codigo)
        else:
            logger.error("SMTP no configurado: no se pudo enviar el código de recuperación.")
        return
    # smtplib es bloqueante: se ejecuta en un hilo para no congelar el event loop.
    await asyncio.to_thread(_enviar_smtp, destinatario, nombre, codigo)
