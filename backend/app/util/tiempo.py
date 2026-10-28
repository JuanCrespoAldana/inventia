"""Utilidades de fecha y hora.

Todo se guarda en UTC (``timestamptz``). Las agrupaciones por "día" (ventas,
series de tiempo para la predicción) usan la zona horaria de la empresa
(``APP_TIMEZONE``) para que un día calendario coincida con la realidad del negocio.
"""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.config.settings import settings

ZONA = ZoneInfo(settings.app_timezone)


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


def asegurar_utc(momento: datetime) -> datetime:
    """Algunos drivers (p. ej. SQLite en pruebas) devuelven fechas sin zona: se asumen UTC."""
    if momento.tzinfo is None:
        return momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(timezone.utc)


def a_fecha_local(momento: datetime) -> date:
    return asegurar_utc(momento).astimezone(ZONA).date()


def hoy_local() -> date:
    return a_fecha_local(ahora_utc())


def inicio_de_dia_utc(dia: date) -> datetime:
    return datetime.combine(dia, time.min, tzinfo=ZONA).astimezone(timezone.utc)


def fin_de_dia_utc(dia: date) -> datetime:
    """Límite superior EXCLUSIVO: inicio del día siguiente."""
    return inicio_de_dia_utc(dia + timedelta(days=1))
