"""Hashing de contraseñas (Argon2id) y tokens de acceso (JWT)."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from jwt import PyJWTError

from app.core.config import settings

# Argon2id es el algoritmo recomendado por OWASP (RNF-023). En pruebas se reducen los
# parámetros de coste para que la suite sea rápida; en cualquier otro entorno se usan los
# valores por defecto de argon2-cffi.
_ph = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1) if settings.es_prueba else PasswordHasher()

# Hash de relleno para igualar el tiempo de respuesta cuando el correo no existe
# (evita enumerar usuarios midiendo la latencia del login).
_HASH_RELLENO = _ph.hash("contraseña-de-relleno-no-valida")


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return _ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def verificar_contra_relleno(plain_password: str) -> None:
    verify_password(plain_password, _HASH_RELLENO)


def necesita_rehash(hashed_password: str) -> bool:
    try:
        return _ph.check_needs_rehash(hashed_password)
    except InvalidHashError:
        return False


def create_access_token(usuario_id: int, password_version: int, minutos: int | None = None) -> str:
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario_id),
        "pv": password_version,  # al cambiar la contraseña, los tokens anteriores dejan de valer
        "iat": ahora,
        "exp": ahora + timedelta(minutes=minutos or settings.access_token_expire_minutes),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"require": ["exp", "sub"]},
        )
    except PyJWTError:
        return None


def hash_token(valor: str) -> str:
    """SHA-256 para valores aleatorios de alta entropía (llaves de API, tokens de sesión)."""
    return hashlib.sha256(valor.encode()).hexdigest()


def generar_codigo_numerico(digitos: int = 6) -> str:
    return f"{secrets.randbelow(10**digitos):0{digitos}d}"


def comparar_seguro(a: str, b: str) -> bool:
    return secrets.compare_digest(a, b)
