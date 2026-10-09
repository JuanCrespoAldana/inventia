# syntax=docker/dockerfile:1.7
# Etapa 1: compilar la aplicación (React + Vite + TypeScript).
FROM node:22-alpine AS compilacion
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
# Vite incrusta las variables VITE_* al compilar. Con la configuración por defecto la aplicación llama a /api
# en su mismo origen (nginx lo reenvía al backend), así que normalmente no hace falta ninguna.
ARG VITE_API_URL=""
ARG VITE_LOCALE="es-CO"
ARG VITE_MONEDA="COP"
ENV VITE_API_URL=$VITE_API_URL VITE_LOCALE=$VITE_LOCALE VITE_MONEDA=$VITE_MONEDA
RUN npm run build

# Etapa 2: nginx sin privilegios sirviendo los archivos estáticos.
FROM nginxinc/nginx-unprivileged:1.27-alpine AS final
COPY --from=compilacion /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/nginx-health || exit 1
