"""Figura: arquitectura de componentes de Inventia (capas y módulos)."""
from pathlib import Path
from dibujo import *

fig, ax = lienzo(11.5, 8.6, (0, 16.2), (-0.4, 12.0))

grupo(ax, 0.3, 9.6, 7.9, 2.2, "Cliente (navegador)")
spa = caja(ax, 0.8, 9.8, 6.9, 1.35, "Aplicación web (SPA)", "React 19 · TypeScript · Vite · Tailwind v4\nTanStack Query · React Hook Form + zod")

grupo(ax, 0.3, 1.9, 11.9, 7.1, "Servidor")
nginx = caja(ax, 0.8, 7.05, 6.9, 1.2, "nginx", "archivos estáticos · proxy /api · cabeceras de seguridad (CSP)", "gris")

grupo(ax, 0.8, 2.3, 11.0, 4.5, "API FastAPI · Python 3.13", color=AZUL, texto=AZUL_OSC, estilo="--")
rutas = caja(ax, 1.2, 5.0, 4.4, 1.15, "Controladores (controller/)", "validan la entrada (dto/) · exigen permiso")
serv = caja(ax, 1.2, 3.75, 4.4, 1.0, "Servicios (service/)", "reglas de negocio · transacciones · auditoría")
mod = caja(ax, 1.2, 2.5, 4.4, 0.95, "Modelos (model/)", "SQLAlchemy 2 asíncrono · Alembic")
nuc = caja(ax, 7.1, 5.0, 4.4, 1.15, "Seguridad (security/)", "JWT · Argon2 · RBAC (61 permisos)\ncontexto de petición · excepciones (exception/)", "gris")
ml = caja(ax, 7.1, 2.75, 4.4, 1.9, "Módulo de predicción (ml/)", "6 modelos · validación temporal\nnumpy · pandas · statsmodels · scikit-learn\ncálculo puro: recibe series, devuelve pronósticos", "naranja")

db = caja(ax, 1.2, 0.0, 4.4, 1.3, "PostgreSQL 16", "37 tablas · restricciones\ndisparadores de solo inserción", "verde")
smtp = caja(ax, 13.0, 5.0, 3.0, 1.15, "Servidor SMTP", "códigos de recuperación", "amarillo")
ag = caja(ax, 13.0, 2.9, 3.0, 1.15, "Agente de IA externo", "solo lectura", "amarillo")

flecha(ax, centro(spa, "s"), centro(nginx, "n"), "HTTPS · JWT", desplaza=(1.05, 0))
flecha(ax, (4.25, 7.05), (4.25, 6.15), "/api", desplaza=(0.45, 0))
flecha(ax, centro(rutas, "s"), centro(serv, "n"))
flecha(ax, centro(serv, "s"), centro(mod, "n"))
flecha(ax, centro(mod, "s"), centro(db, "n"), "SQL asíncrono", desplaza=(1.2, 0))
flecha(ax, (5.6, 4.1), (7.1, 4.1), "series", desplaza=(0, 0.28), ambos=True)
flecha(ax, (5.6, 5.57), (7.1, 5.57), "permisos", estilo="--", desplaza=(0, 0.28))
flecha(ax, (11.8, 5.57), (13.0, 5.57), "correo", desplaza=(0, 0.28))
flecha(ax, (13.0, 3.47), (11.8, 3.47), "X-API-Key", desplaza=(0, 0.28))
ax.text(14.5, 2.8, "/api/agentes", ha="center", va="top", fontsize=7.2, color=GRIS)

guardar(fig, Path(__file__).with_name("arquitectura.png"))
