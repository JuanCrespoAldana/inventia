import logging
import sys

from app.core.config import settings
from app.core.contexto import request_id_actual


class _FiltroRequestId(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_actual() or "-"
        return True


def configurar_logging() -> None:
    manejador = logging.StreamHandler(sys.stdout)
    manejador.addFilter(_FiltroRequestId())
    manejador.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s")
    )
    raiz = logging.getLogger()
    raiz.handlers[:] = [manejador]
    raiz.setLevel(settings.log_level.upper())
    # El log de SQL y de acceso de uvicorn es ruidoso y no debe incluir datos sensibles.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
