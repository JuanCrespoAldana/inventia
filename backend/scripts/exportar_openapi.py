"""Exporta el contrato OpenAPI de la API a un archivo JSON (lo usa el generador de tipos del frontend).

    python scripts/exportar_openapi.py [salida.json]

No necesita base de datos: solo importa la aplicación. Si no hay variables de entorno, usa valores
descartables para poder ejecutarse en CI o en una máquina recién clonada.
"""

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "x" * 48)
os.environ.setdefault("ENVIRONMENT", "test")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402

destino = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
destino.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Contrato OpenAPI escrito en {destino} ({len(app.openapi()['paths'])} rutas)")
