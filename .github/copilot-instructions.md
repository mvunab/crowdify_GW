# Crowdify GW - AI Coding Agent Instructions

## Architecture Overview

**Crowdify GW** is a FastAPI-based ticket sales & validation platform with a modular service architecture. The codebase follows a **Domain-Driven Service** pattern where business logic is isolated into service modules under `services/`, with shared infrastructure in `shared/`.

### Core Architecture Principles

1. **API Gateway Pattern**: Root `main.py` aggregates all service routers under `/api/v1/` prefix
2. **Service Isolation**: Each domain (`event_management`, `ticket_purchase`, `ticket_validation`, `notifications`, `admin`) is self-contained with its own `/routes/`, `/services/`, and `/models/` subdirectories
3. **Shared Infrastructure**: Database sessions, auth, cache, and utilities centralized in `shared/`
4. **Async-First**: All I/O operations use SQLAlchemy 2.0 async, Redis async (`redis.asyncio`), and async FastAPI patterns
5. **Supabase Compatibility**: Models in `shared/database/models.py` mirror Supabase schema for migration compatibility (NULLABLE columns, Spanish field names in `ticket_child_details`)

## Critical Developer Workflows

### Starting Development Environment

```pwsh
# Always use Docker Compose for local development
docker compose up -d --build

# Run migrations (note the custom config path)
docker compose exec backend bash -lc "alembic -c app/alembic/alembic.ini upgrade head"

# View logs
docker compose logs -f backend

# Add Python dependencies via Poetry
docker compose exec backend poetry add <package-name>
```

**Service Ports** (all exposed on localhost):

- Backend API: `8000` (hot reload enabled via volume mount)
- Postgres: `5432` (user/pass/db: `tickets`/`tickets`/`tickets`)
- Redis: `6379`
- MinIO: `9000` (console: `9001`, user/pass: `minio`/`minio12345`)
- Mailhog (SMTP dev): `8025` (catches dev emails)
- PDF Service: `9002` (separate microservice in `pdfsvc/`)

### Key Development Patterns

#### 1. Database Sessions & Schema Context

**Always** use dependency injection for DB sessions:

```python
from shared.database.session import get_db

async def my_route(db: AsyncSession = Depends(get_db)):
    # Ensure Supabase Session Pooler schema context (critical!)
    await db.execute(text("SET search_path TO public"))
    # ... your queries
```

**Why**: Supabase Session Pooler can reset the schema context between requests. Explicitly set `search_path` in services that query the DB.

#### 2. Route Handler Pattern

Keep routes **thin** - delegate all business logic to service classes:

```python
# ❌ BAD: Logic in route handler
@router.post("/events")
async def create_event(data: EventCreate, db: AsyncSession = Depends(get_db)):
    event = Event(name=data.name, ...)  # ❌ Model creation in route
    db.add(event)
    await db.commit()
    return event

# ✅ GOOD: Thin route, logic in service
from services.event_management.services.event_service import EventService

@router.post("/events")
async def create_event(
    data: EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_admin)
):
    service = EventService()
    return await service.create_event(db, data.dict(), current_user['user_id'])
```

**Location**: Route handlers live in `services/*/routes/*.py`, service logic in `services/*/services/*_service.py`.

#### 3. UUID Handling

All primary keys are UUIDs. Accept `str` in route signatures, convert inside services:

```python
from uuid import UUID

# Route accepts string
@router.get("/events/{event_id}")
async def get_event(event_id: str, ...):
    event = await EventService.get_event_by_id(db, event_id)  # Pass as string

# Service converts to UUID if needed
async def get_event_by_id(db: AsyncSession, event_id: str):
    stmt = select(Event).where(Event.id == event_id)  # SQLAlchemy handles conversion
```

**Critical**: Do NOT use `UUID(event_id)` prematurely - SQLAlchemy handles string→UUID coercion automatically when column is `UUID(as_uuid=True)`.

#### 4. Distributed Locks for Critical Sections

**Always** use `DistributedLock` around operations that modify shared state (capacity, ticket generation, payment processing):

```python
from shared.cache.redis_client import DistributedLock

# Protect capacity reservation
async with DistributedLock(f"event_capacity:{event_id}", timeout=10):
    # Check and update capacity_available
    event = await db.get(Event, event_id)
    if event.capacity_available < quantity:
        raise ValueError("Not enough capacity")
    event.capacity_available -= quantity
    await db.commit()
```

**Location**: See `services/ticket_purchase/services/inventory_service.py` for reference implementation.

#### 5. Authentication & Authorization

JWT tokens contain: `sub` (user_id), `email`, `app_metadata.role`. Use dependency injection for auth:

```python
from shared.auth.dependencies import (
    get_current_user,        # Any authenticated user
    get_current_admin,       # Admin only
    get_current_scanner,     # Scanner, Admin, or Coordinator
    get_current_admin_or_coordinator,  # Admin or Coordinator
    get_optional_user        # Public endpoint with optional auth
)

# Example: Admin-only endpoint
@router.post("/admin/events")
async def create_event(
    data: EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_admin)  # 403 if not admin
):
    return await service.create_event(db, data.dict(), current_user['user_id'])
```

**Roles**: `user`, `admin`, `scanner`, `coordinator` (stored in JWT `app_metadata.role`).

#### 6. Eager Loading to Avoid N+1 Queries

Use `selectinload()` for relationships:

```python
from sqlalchemy.orm import selectinload

stmt = select(Event).options(
    selectinload(Event.organizer),
    selectinload(Event.ticket_types),
    selectinload(Event.event_services)  # Avoids N+1 on related tables
).where(Event.id == event_id)
```

**Location**: See `services/event_management/services/event_service.py` for pattern.

## External Integrations

### MercadoPago Payment Flow

1. **Create Preference**: `services/ticket_purchase/services/mercado_pago_service.py` → `create_preference()`
2. **Webhook Handler**: `/api/v1/purchases/webhook` (no auth - MP validates signature)
3. **Process Payment**: `PurchaseService.process_payment_webhook()` updates order status, generates tickets

**Key Details**:

- Preferences expire after 24 hours (`expiration_date_to`)
- `external_reference` field stores `order_id` (UUID)
- Webhook retries handled by returning 200 even on internal errors (log and continue)

### Email Notifications

- **Dev**: Mailhog (SMTP on `mailhog:1025`, view at `localhost:8025`)
- **Prod**: SendGrid (configured via `EMAIL_API_KEY` in `.env`)
- Service: `services/notifications/services/email_service.py`

### PDF Generation (Separate Microservice)

- **Service**: `pdfsvc/` (Python service on port 9002)
- **Caller**: Celery tasks in `app/worker.py` call pdfsvc, upload result to MinIO
- **Storage**: MinIO bucket `tickets-pdf` (object key stored in `tickets.pdf_object_key`)

## Environment Configuration

**Critical ENV vars** (see `.env.example`):

- `DATABASE_URL`: If set, overrides local Postgres (used for Supabase)
- `JWT_SECRET` / `QR_SECRET`: MUST change in production
- `MERCADOPAGO_ACCESS_TOKEN`: Required for payments
- `APP_ENV`: `development` allows all CORS origins (`allow_origins=["*"]`)

**Alembic Path**: Migrations config at `app/alembic/alembic.ini` (NOT in project root).

## Dependency Management

**Poetry** is the source of truth (do NOT edit `requirements.txt` directly):

```pwsh
# Add dependency
docker compose exec backend poetry add httpx

# Update lockfile
docker compose exec backend poetry lock

# Install after adding to pyproject.toml
docker compose exec backend poetry install
```

## Common Imports & Patterns

```python
# Database session
from shared.database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

# Auth dependencies
from shared.auth.dependencies import get_current_user, get_current_admin

# Distributed locking
from shared.cache.redis_client import DistributedLock, cache_get, cache_set

# Models (centralized)
from shared.database.models import Event, Order, Ticket, User

# SQLAlchemy queries
from sqlalchemy import select, and_, or_, text
from sqlalchemy.orm import selectinload
```

## Testing & Debugging

```pwsh
# Run tests in container
docker compose exec backend pytest

# Check DB connection
docker compose exec backend poetry run python -c "from shared.database.connection import init_db; import asyncio; asyncio.run(init_db())"

# View Celery worker logs
docker compose logs -f worker

# Check Redis connectivity
docker compose exec redis redis-cli ping
```

## Known Gotchas

1. **Supabase Session Pooler**: Always `SET search_path TO public` in services (pooler resets schema)
2. **Alembic Path**: Must use `-c app/alembic/alembic.ini` (config not in root)
3. **CORS in Dev**: `APP_ENV=development` allows all origins; production requires explicit `CORS_ORIGINS`
4. **UUID Coercion**: Don't manually convert `str` to `UUID` in queries - SQLAlchemy handles it
5. **Webhook Retries**: Always return 200 from `/webhook` endpoints to prevent infinite retries
6. **Lock Timeouts**: Default `DistributedLock` timeout is 10s; adjust for long-running operations
