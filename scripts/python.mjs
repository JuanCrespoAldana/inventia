// Uso: node scripts/python.mjs <argumentos de python>   (p. ej. -m pytest, -m alembic upgrade head)
import { ejecutar } from "./lib/python.mjs";

ejecutar(process.argv.slice(2));
