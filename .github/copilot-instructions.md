# Crowdify GW - AI Coding Agent Instructions

## Architecture Overview

**Crowdify GW** is a FastAPI-based ticket sales & validation platform with a modular service architecture. The codebase follows a **Domain-Driven Service** pattern where business logic is isolated into service modules under `services/`, with shared infrastructure in `shared/`.

### Core Architecture Principles

1. **API Gateway Pattern**: `main.py` is the single entry point that aggregates all service routers
2. **Service Isolation**: Each domain (`event_management`, `ticket_purchase`, `ticket_validation`, `notifications`) is self-contained with its own routes, services, and models
3. **Shared Infrastructure**: Database, auth, cache, and utilities are centralized in `shared/`
4. **Async-First**: All I/O operations use SQLAlchemy 2.0 async, Redis async, and async FastAPI patterns
5. **Supabase Compatibility**: Models in `shared/database/models.py` mirror Supabase schema for migration compatibility

## Project Structure

```
services/               # Business domain modules (4 services)
  ├── event_management/   # Event CRUD, capacity management
  ├── ticket_purchase/    # Order creation, Mercado Pago integration, ticket generation
  ├── ticket_validation/  # QR validation, scanner auth
  └── notifications/      # Email sending via SendGrid/Mailhog
shared/                 # Cross-cutting concerns
  ├── auth/              # JWT handling, role-based dependencies
  ├── database/          # SQLAlchemy models, async session factory
  ├── cache/             # Redis client, distributed locks
  └── utils/             # Circuit breaker, rate limiting, QR generation
app/                   # Legacy structure (migrations, worker)
pdfsvc/                # Separate PDF generation microservice (port 9002)
```

## Critical Developer Workflows

### Starting Development Environment

```pwsh
# Always use Docker Compose for local development
docker compose up -d --build

# Run migrations (required after schema changes)
docker compose exec backend bash -lc "alembic -c app/alembic/alembic.ini upgrade head"

# View logs
docker compose logs -f backend
```

**Service Ports**:

- Backend API: `localhost:8000` (hot reload enabled)
- Postgres: `localhost:5432` (user/pass/db: `tickets`/`tickets`/`tickets`)
- Redis: `localhost:6379`
- MinIO: `localhost:9000` (console: `9001`, user/pass: `minio`/`minio12345`)
- Mailhog: `localhost:8025` (catches dev emails)
## Copilot / AI Agent Quick Instructions — Crowdify GW

Short, actionable guidance for AI coding agents working on this FastAPI-based ticketing gateway.

- Big picture: root `main.py` aggregates routers; domain services live under `services/` and reuse shared infra in `shared/` (auth, db, cache, utils). PDF generation runs in `pdfsvc/` and Celery tasks are in `app/worker.py`.

- Key files to inspect before edits: `main.py`, `app/worker.py`, `shared/database/models.py`, `shared/auth/dependencies.py`, `shared/cache/redis_client.py`, `services/*/services/*_service.py` and `services/*/routes/*.py`.

- Dev commands (use in PowerShell):
    - Start everything: `docker compose up -d --build`
    - Run alembic (note config path): `docker compose exec backend bash -lc "alembic -c app/alembic/alembic.ini upgrade head"`
    - Run tests in container: `docker compose exec backend pytest`

- Conventions & patterns to follow:
    - All API routers use prefix `/api/v1/` (see `main.py`). Keep route handlers thin; move logic to service classes in `services/*/services/`.
    - DB sessions: always use `Depends(get_db)` from `shared/database/session.py` (async SQLAlchemy). Do not instantiate sessions manually.
    - IDs are UUIDs (SQLAlchemy UUID(as_uuid=True)). Accept `str` in routes and convert with `UUID(id_str)` inside services.
    - Distributed safety: use `DistributedLock` from `shared/cache/redis_client.py` around capacity/ticket generation and payment-critical sections.
    - Auth: JWT handled in `shared/auth/jwt_handler.py`; use DI helpers in `shared/auth/dependencies.py`. Required claims: `sub`/`user_id`, `email`, `role` (roles: `user`, `admin`, `scanner`, `coordinator`).

- External integrations:
    - MercadoPago logic: `services/ticket_purchase/services/mercado_pago_service.py`; webhook endpoint at `/api/v1/purchases/webhook`.
    - Emails: `services/notifications/services/email_service.py` (Mailhog local, SendGrid in prod).
    - PDF generation: `pdfsvc/` microservice (port 9002) called by Celery tasks.

- Environment & infra notes:
    - Alembic config lives at `app/alembic/alembic.ini`.
    - Use Poetry inside container for deps (do not edit `requirements.txt` directly).
    - Common local ports: backend 8000, Postgres 5432, Redis 6379, MinIO 9000, Mailhog 8025, pdfsvc 9002.

- Quick examples (imports you will commonly edit/add):
    - `from shared.database.session import get_db`
    - `from shared.cache.redis_client import DistributedLock`
    - `from shared.auth.dependencies import get_current_admin`

If any section should include more examples or a short checklist for code reviews (tests/linters), tell me which part to expand and I will iterate.
