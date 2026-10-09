from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONType, MarcaTiempo

# Parámetros de inventario y predicción configurables por empresa (se editan desde la interfaz).
# Son las «reglas configurables y documentadas» para las recomendaciones: no se inventan plazos.
CONFIGURACION_POR_DEFECTO: dict[str, int] = {
    "plazo_entrega_dias": 7,  # días entre pedir y recibir mercancía
    "dias_seguridad": 3,  # colchón adicional sobre el plazo de entrega
    "dias_cobertura_objetivo": 21,  # días de demanda que se quiere cubrir al reabastecer
    "horizonte_dias": 14,  # horizonte por defecto de la predicción
    "umbral_cobertura_alerta_dias": 5,  # alerta de riesgo si el stock cubre menos días
    "dias_sin_rotacion": 60,  # sin ventas en estos días con existencias => revisar
    "dias_max_anulacion": 30,  # una venta solo puede anularse dentro de estos días
}


class Empresa(MarcaTiempo, Base):
    __tablename__ = "empresas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    identificacion: Mapped[str | None] = mapped_column(String(40), nullable=True, unique=True)  # NIT u otra
    direccion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ciudad: Mapped[str | None] = mapped_column(String(100), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    configuracion: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict, server_default=text("'{}'"))

    def parametros(self) -> dict[str, int]:
        """Configuración efectiva: valores guardados sobre los valores por defecto."""
        efectivos = dict(CONFIGURACION_POR_DEFECTO)
        efectivos.update({k: v for k, v in (self.configuracion or {}).items() if k in CONFIGURACION_POR_DEFECTO})
        return efectivos
