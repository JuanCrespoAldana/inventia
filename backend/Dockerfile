# syntax=docker/dockerfile:1.7
# Imagen de la API de Inventia. Dos etapas: en la primera se instalan las dependencias (con compilador por si
# alguna rueda binaria no existe para la plataforma); la imagen final no lleva compiladores y corre sin root.

FROM python:3.13-slim AS dependencias
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM python:3.13-slim AS final
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    ENVIRONMENT=production
RUN groupadd --system --gid 10001 inventia \
    && useradd --system --uid 10001 --gid inventia --home-dir /app --shell /usr/sbin/nologin inventia
COPY --from=dependencias /opt/venv /opt/venv
WORKDIR /app
COPY --chown=inventia:inventia app ./app
COPY --chown=inventia:inventia alembic ./alembic
COPY --chown=inventia:inventia alembic.ini ./
COPY --chown=inventia:inventia scripts ./scripts
COPY --chown=inventia:inventia docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 0555 /usr/local/bin/docker-entrypoint.sh
USER inventia
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health/ready', timeout=4)" || exit 1
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
