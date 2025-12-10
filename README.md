# Crowdify GW — FastAPI + Celery + PDF Service

Backend para venta y validación de tickets, con servicios auxiliares (PDF, MinIO, Redis y Postgres) orquestados con Docker Compose.

## Requisitos

- Docker Desktop 4.x (incluye Docker Compose V2)
- Windows, macOS o Linux
- **Poetry** 1.7+ (opcional, solo si desarrollas sin Docker)

## Estructura

- `app/` API, modelos y Alembic
- `services/` módulos de dominio (events, ticket_purchase, ticket_validation, notifications)
- `shared/` auth, db, cache, utils compartidos
- `pdfsvc/` servicio HTTP para generación/almacenamiento de PDFs
- `pyproject.toml` configuración de Poetry y dependencias
- `Dockerfile` imagen de producción de la API
- `docker-compose.yml` stack local de desarrollo
- `docs/` documentación

## Gestión de dependencias (Poetry)

Este proyecto usa **Poetry** para manejar dependencias de forma moderna y eficiente.

### Agregar una dependencia

```pwsh
# Desde tu máquina local (con Poetry instalado)
poetry add fastapi-users

# O dentro del contenedor Docker
docker compose exec backend poetry add fastapi-users
```

### Actualizar dependencias

```pwsh
poetry update

# O actualizar una específica
poetry update fastapi
```

### Instalar dependencias de desarrollo

```pwsh
poetry add --group dev black isort
```

## Variables de entorno

Archivo `.env` en la raíz (puedes partir de `.env.example`).

Claves importantes:

- `DATABASE_URL`: si la defines (por ejemplo, Supabase), la API usará esa DB. Si no, se usa la Postgres local del Compose con credenciales por defecto (`tickets`/`tickets`).
- `JWT_SECRET` y `QR_SECRET`: secretos de seguridad en la API. En desarrollo tienen default seguro, pero es mejor definirlos.

## Arranque rápido (desarrollo)

```pwsh
Copy-Item .env.example .env
docker compose up -d --build

# Migraciones de base de datos (Alembic)
docker compose exec backend bash -lc "alembic -c app/alembic/alembic.ini upgrade head"

# Comprobaciones rápidas
curl http://localhost:8000/health
curl http://localhost:9002/health
```

Servicios y puertos:

- API: http://localhost:8000
- Postgres: 5432 (usuario/clave: `tickets`/`tickets`, DB: `tickets`)
- Redis: 6379
- MinIO: 9000 (console 9003) — usuario/clave: `minio`/`minio12345`
- PDF service: http://localhost:9002

**Email**: El sistema usa Resend para envío de emails. Configura `RESEND_API_KEY` en tu `.env`.

Hot reload: el servicio `backend` monta el código (`.:/app`) y ejecuta `uvicorn --reload`.

## Usar Supabase en lugar de Postgres local

En `.env` define `DATABASE_URL` con tu cadena de Supabase, por ejemplo:

```
DATABASE_URL=postgresql://<user>:<password>@aws-1-us-east-2.pooler.supabase.com:5432/postgres
```

No necesitas cambiar nada más. El `docker-compose.yml` ya usa `DATABASE_URL` si está presente.

## Producción (Dockerfile)

Construir una imagen de producción de la API (sin Compose):

```pwsh
docker build -t crowdify-api:prod .
docker run --rm -p 8000:8000 --env-file .env crowdify-api:prod
```

Nota: ajusta variables en `.env` y usa un orquestador/infra de prod (no recomendado usar Compose en prod tal cual).

## Troubleshooting

- Si ves errores de variables no definidas en `docker compose config`, ya están cubiertas por defaults en `docker-compose.yml`. Aún así, puedes definirlas en `.env` para evitar warnings.
- Si `alembic` no encuentra el archivo, asegúrate de ejecutar el comando exactamente con `-c app/alembic/alembic.ini` dentro del contenedor `backend`.
- En Windows, PowerShell usa `curl` como alias; también puedes usar `Invoke-WebRequest`.
- **Poetry lock errors**: Si ves errores relacionados con `poetry.lock`, genera el lock file: `docker compose exec backend poetry lock`.

## Desarrollo local (sin Docker)

Si prefieres desarrollar sin Docker:

```pwsh
# Instalar Poetry (si no lo tienes)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -

# Instalar dependencias
poetry install

# Activar entorno virtual
poetry shell

# Correr la API
poetry run uvicorn main:app --reload

# Correr Celery worker
poetry run celery -A app.worker:celery_app worker -l INFO
```

## Scripts útiles

En `scripts/` tienes utilidades como `generate_env.py` (plantillas) y `generate_token.py`.

## Documentación

Documentación adicional disponible en `docs/`:
- `API_DOCUMENTATION.md` - Documentación completa de la API
- `BACKEND_README.md` - Guía detallada del backend
- `MERCADOPAGO_SETUP.md` - Configuración de Mercado Pago
- `PAYKU_FLUJO_COMPLETO.md` - Flujo completo de Payku
- `RESEND_SETUP.md` - Configuración de Resend para emails
- `WEBHOOK_CONFIGURATION.md` - Configuración de webhooks
- `EMAIL_INTEGRATION.md` - Integración de emails

## Licencia

Privado (uso interno del equipo).
