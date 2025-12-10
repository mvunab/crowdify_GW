# ============================================================================
# Stage 1: Builder - Instalar dependencias
# ============================================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Instalar dependencias del sistema necesarias para compilar paquetes Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar Poetry
ENV POETRY_VERSION=1.7.1
ENV POETRY_HOME=/opt/poetry
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=false
ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_CACHE_DIR=/opt/poetry-cache
ENV PATH="$POETRY_HOME/bin:$PATH"

# Instalar Poetry usando cache mount para acelerar builds
RUN --mount=type=cache,target=/root/.cache/pip \
    curl -sSL https://install.python-poetry.org | python3 - && \
    poetry --version

# Copiar archivos de dependencias primero (mejor caching)
COPY pyproject.toml poetry.lock* ./

# Instalar dependencias usando cache mount de Poetry
# Si poetry.lock está desincronizado, actualizarlo primero
# Exportar a requirements.txt para uso en runtime
RUN --mount=type=cache,target=/opt/poetry-cache \
    (poetry install --no-root --only main || \
     (poetry lock --no-update && poetry install --no-root --only main)) && \
    poetry export -f requirements.txt --output requirements.txt --without-hashes

# ============================================================================
# Stage 2: Runtime - Imagen final mínima
# ============================================================================
FROM python:3.11-slim AS runtime

WORKDIR /app

# Instalar solo dependencias de runtime necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root para seguridad
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copiar Poetry desde builder (solo el binario, necesario para desarrollo)
COPY --from=builder /opt/poetry /opt/poetry
ENV PATH="/opt/poetry/bin:$PATH"

# Copiar requirements.txt desde builder
COPY --from=builder /app/requirements.txt /tmp/requirements.txt

# Instalar dependencias Python usando pip (instalar como root, luego cambiar ownership)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Copiar código de la aplicación
COPY . .

# Cambiar ownership de archivos al usuario no-root
RUN chown -R appuser:appuser /app

# Cambiar a usuario no-root
USER appuser

# PATH ya incluye /usr/local/bin donde pip instaló las dependencias

# Exponer puerto
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Comando por defecto (usar python -m para asegurar que encuentre uvicorn)
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
