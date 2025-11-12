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
- PDF Service: `localhost:9002`

### Database Migrations (Alembic)

**IMPORTANT**: Alembic config is in `app/alembic/alembic.ini`, NOT the root.

```pwsh
# Generate migration (inside container)
docker compose exec backend bash -lc "alembic -c app/alembic/alembic.ini revision --autogenerate -m 'description'"

# Apply migrations
docker compose exec backend bash -lc "alembic -c app/alembic/alembic.ini upgrade head"

# Rollback
docker compose exec backend bash -lc "alembic -c app/alembic/alembic.ini downgrade -1"
```

**Models Location**: All SQLAlchemy models are in `shared/database/models.py` (single file, ~500 lines). Update this file for schema changes.

### Poetry Dependency Management

**This project uses Poetry**, not pip directly. The `pyproject.toml` defines dependencies.

```pwsh
# Add a dependency
docker compose exec backend poetry add httpx

# Add dev dependency
docker compose exec backend poetry add --group dev pytest-cov

# Update dependencies
docker compose exec backend poetry update

# Lock file issues
docker compose exec backend poetry lock --no-update
```

**Never** manually edit `requirements.txt` - it's generated from Poetry.

## Service Architecture Patterns

### Standard Service Structure

Each service follows this pattern (example: `ticket_purchase`):

```
ticket_purchase/
  ├── routes/           # FastAPI endpoints (thin controllers)
  │   └── purchase.py   # Delegates to services
  ├── services/         # Business logic (thick services)
  │   ├── purchase_service.py       # Main orchestration
  │   ├── inventory_service.py      # Capacity management
  │   └── mercado_pago_service.py   # Payment provider
  └── models/           # Pydantic request/response models
      └── purchase.py
```

**Key Pattern**: Routes are thin and delegate to service classes. Services contain ALL business logic, database queries, and external integrations.

### Route Registration in main.py

All service routers are imported and registered in `main.py`:

```python
from services.ticket_purchase.routes.purchase import router as purchase_router
app.include_router(purchase_router, prefix="/api/v1/purchases", tags=["purchases"])
```

**Convention**: Always use versioned API prefix `/api/v1/` and descriptive tags for OpenAPI docs.

## Authentication & Authorization

### JWT Token Pattern

**Token Verification**: `shared/auth/jwt_handler.py` handles token encoding/decoding using `python-jose`.

**Dependency Injection**: Use FastAPI dependencies from `shared/auth/dependencies.py`:

```python
from shared.auth.dependencies import get_current_user, get_current_admin, get_current_scanner, get_optional_user

@router.post("/events")
async def create_event(
    current_user: Dict = Depends(get_current_admin)  # Requires admin role
):
    pass

@router.get("/events")
async def list_events(
    current_user: Optional[Dict] = Depends(get_optional_user)  # Public endpoint
):
    pass
```

**Roles**: `user`, `admin`, `scanner`, `coordinator` (defined in JWT payload as `"role"` claim).

**Important**: Token payload MUST contain `sub` or `user_id` (for user ID), `email`, and `role`.

## Database Patterns

### Async Session Management

**Always** get sessions via dependency injection:

```python
from shared.database.session import get_db

@router.get("/events")
async def list_events(db: AsyncSession = Depends(get_db)):
    # db is auto-committed/rolled back by FastAPI
    stmt = select(Event).where(Event.name.like(f"%{search}%"))
    result = await db.execute(stmt)
    events = result.scalars().all()
```

**Never** create sessions manually. The `get_db()` dependency handles lifecycle.

### UUID Primary Keys

All IDs are `UUID(as_uuid=True)` in SQLAlchemy. When accepting IDs in routes, use `str` type and cast inside services:

```python
from uuid import UUID

event_id_uuid = UUID(event_id)  # Converts string to UUID
```

### Model Relationships

Models use SQLAlchemy relationships for eager/lazy loading:

```python
class Order(Base):
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
```

**Cascade Deletes**: Most parent-child relationships use `cascade="all, delete-orphan"` to auto-delete children.

## Cache & Distributed Locks

### Redis Usage

Import from `shared/cache/redis_client.py`:

```python
from shared.cache.redis_client import cache_get, cache_set, cache_delete, DistributedLock

# Simple cache
await cache_set("event:123", event_data, expire=3600)
data = await cache_get("event:123")

# Distributed lock (for inventory/capacity operations)
async with DistributedLock("event:123:capacity"):
    # Critical section - only one worker can execute this
    event.capacity_available -= quantity
    await db.commit()
```

**Use locks** for any operation that modifies shared resources (event capacity, ticket generation, payment processing).

## External Integrations

### Mercado Pago (Payment Gateway)

Service: `services/ticket_purchase/services/mercado_pago_service.py`

**Pattern**: Create payment preference, redirect user to `payment_link`, handle webhook callback:

```python
# 1. Create preference
preference = mercado_pago_service.create_preference(
    order_id=str(order.id),
    title="Tickets",
    total_amount=total,
    currency="CLP"
)

# 2. User pays, Mercado Pago sends webhook to /api/v1/purchases/webhook
# 3. Webhook handler verifies payment and generates tickets
```

**Webhook**: `/api/v1/purchases/webhook` receives payment notifications. Uses `payment_reference` to find order.

### Email Sending

Service: `services/notifications/services/email_service.py`

**Local Dev**: Emails are sent to Mailhog (no real delivery), view at `http://localhost:8025`.

**Production**: Uses SendGrid API (configured via `EMAIL_API_KEY`).

### PDF Generation

**Separate microservice** at `pdfsvc/` (port 9002). Called by Celery worker to generate ticket PDFs, stores in MinIO.

## Celery Background Tasks

Worker: `app/worker.py`

**Pattern**: Celery tasks are defined in services (e.g., `services/ticket_purchase/tasks/email_tasks.py`).

```python
from app.worker import celery_app

@celery_app.task
def send_ticket_email(ticket_id: str):
    # Async work
    pass

# Enqueue from route/service
send_ticket_email.delay(ticket_id)
```

**Running**: Worker runs in separate container (`docker compose` service `worker`).

## Frontend API Compatibility

### Supabase Migration Context

This backend is designed to **replace Supabase** incrementally. Current state:

- **Auth**: Still using Supabase Auth (JWT tokens are Supabase-issued)
- **Database**: Backend uses Supabase Postgres OR local Postgres (configured via `DATABASE_URL`)
- **Models**: Mirror Supabase schema exactly (see `shared/database/models.py`)

**Field Naming**: Some models use Spanish field names (e.g., `TicketChildDetail` has `nombre`, `rut`, `fecha_nacimiento`) to match Supabase schema.

### Response Model Conventions

Always define Pydantic response models in `services/{service}/models/`:

```python
from pydantic import BaseModel

class EventResponse(BaseModel):
    id: str  # UUID as string
    name: str
    starts_at: datetime
    # ... fields match frontend expectations
```

**UUID Serialization**: Convert UUID to `str` in response models: `id=str(event.id)`.

## Rate Limiting & Circuit Breakers

### Rate Limiting (SlowAPI)

Applied globally in `main.py`:

```python
from slowapi import Limiter
from shared.utils.rate_limiter import limiter

app.state.limiter = limiter
```

**Per-route limits**: Add decorator if needed (see SlowAPI docs).

### Circuit Breaker Pattern

For external services (payments, emails), use `shared/utils/circuit_breaker.py`:

```python
from shared.utils.circuit_breaker import CircuitBreaker

breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

result = await breaker.call(mercado_pago_api.create_preference, data)
```

## Environment Variables

**Required vars** (see `.env.example`):

- `DATABASE_URL`: PostgreSQL connection string (default: local Docker Postgres)
- `REDIS_URL`: Redis connection (default: `redis://redis:6379/0`)
- `JWT_SECRET`: Signing key for tokens (change in production!)
- `QR_SECRET`: QR code signing secret
- `MERCADOPAGO_ACCESS_TOKEN`: Payment gateway token
- `MINIO_*`: Object storage config for PDFs
- `SMTP_*`: Email config (Mailhog for dev, SendGrid for prod)

**Optional vars**:

- `CORS_ORIGINS`: Comma-separated allowed origins (default includes `localhost:3000`, `localhost:5173`)
- `LOG_LEVEL`: `INFO` (default), `DEBUG`, `WARNING`

## Common Pitfalls

1. **Alembic Path**: Always use `-c app/alembic/alembic.ini` when running alembic commands
2. **UUID Conversion**: Routes receive string IDs, convert to UUID inside services
3. **Async Context**: Never use sync DB operations; always `await` queries
4. **Redis Connection**: Call `await get_redis()` to get client, don't access `redis_client` directly
5. **Poetry vs Pip**: Always use `poetry add`, never manually edit `requirements.txt`
6. **Child Ticket Details**: Field names are in Spanish (`nombre`, `rut`, `fecha_nacimiento`) - don't change them
7. **Capacity Locks**: Use `DistributedLock` when modifying `capacity_available` to prevent race conditions

## Testing

Run tests inside container:

```pwsh
docker compose exec backend pytest
```

**Test Structure**: Tests should be in `tests/` (not yet fully implemented in this codebase).

## Debugging

- **API Docs**: `http://localhost:8000/docs` (Swagger UI)
- **Health Check**: `http://localhost:8000/health` and `http://localhost:8000/ready`
- **Logs**: `docker compose logs -f backend` or `docker compose logs -f worker`
- **Redis CLI**: `docker compose exec redis redis-cli`
- **DB CLI**: `docker compose exec db psql -U tickets -d tickets`

## API Documentation

For complete API endpoint documentation including request/response examples, see:

- **Full API Docs**: `docs/API_DOCUMENTATION.md`
- **Interactive Swagger**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
