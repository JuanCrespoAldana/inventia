"""
Configuración central de Inventia.

Todos los valores salen de variables de entorno (o del archivo ``.env`` en
desarrollo). Los nombres de las variables que ya existían en el proyecto
(DATABASE_URL, SECRET_KEY, SMTP_*, FRONTEND_URL...) se conservan para que un
``.env`` anterior siga funcionando; las variables nuevas son opcionales y
tienen valores por defecto seguros.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_CLAVES_DE_EJEMPLO = {"cambia-esto", "changeme", "secret", "secreto", "clave-secreta"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # --- Aplicación ---
    app_nombre: str = "Inventia"
    environment: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"
    app_timezone: str = "America/Bogota"
    trust_proxy_headers: bool = False  # true solo detrás de un proxy de confianza (nginx, balanceador)
    docs_api_activa: bool = True  # false oculta /api/docs y /api/openapi.json (recomendado en producción pública)

    # --- Base de datos ---
    database_url: str
    database_ssl: Literal["auto", "true", "false"] = "auto"
    db_pool_size: int = Field(10, ge=1, le=100)
    db_max_overflow: int = Field(10, ge=0, le=100)

    # --- Seguridad / JWT ---
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(60, ge=5, le=1440)
    reset_token_expire_minutes: int = Field(15, ge=5, le=120)
    login_max_attempts: int = Field(5, ge=3, le=20)
    login_lock_minutes: int = Field(15, ge=1, le=240)
    setup_token: str = ""  # protege la configuración inicial; obligatorio en producción

    # --- CORS / frontend ---
    frontend_url: str = "http://localhost:5173"
    cors_origins: str = ""  # orígenes adicionales separados por coma

    # --- Correo (recuperación de contraseña) ---
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = ""

    # --- Predicción de demanda ---
    ml_max_series_por_ejecucion: int = Field(5000, ge=1)
    ml_tiempo_maximo_segundos: int = Field(900, ge=30, le=7200)  # tope de cálculo por ejecución
    ml_historia_maxima_dias: int = Field(365, ge=60, le=1460)  # ventana de historia que se usa

    @field_validator("secret_key")
    @classmethod
    def _clave_robusta(cls, v: str) -> str:
        if len(v) < 32 or v.lower() in _CLAVES_DE_EJEMPLO:
            raise ValueError(
                "SECRET_KEY debe tener al menos 32 caracteres. Genera una con: "
                'python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )
        return v

    @model_validator(mode="after")
    def _reglas_de_produccion(self) -> "Settings":
        if self.environment == "production":
            if not self.setup_token or len(self.setup_token) < 16:
                raise ValueError(
                    "En producción SETUP_TOKEN es obligatorio (mínimo 16 caracteres) "
                    "para proteger la configuración inicial."
                )
        return self

    # ---- Derivados ----
    @property
    def es_produccion(self) -> bool:
        return self.environment == "production"

    @property
    def es_prueba(self) -> bool:
        return self.environment == "test"

    @property
    def origenes_permitidos(self) -> list[str]:
        extra = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        base = [self.frontend_url.rstrip("/")]
        return list(dict.fromkeys(base + [o.rstrip("/") for o in extra]))

    @property
    def smtp_configurado(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password and self.email_from)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
