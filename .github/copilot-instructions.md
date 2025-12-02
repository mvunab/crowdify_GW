# Crowdify GW - Copilot Instructions

## Architecture Overview

FastAPI-based ticket sales platform using **service-oriented architecture**. Core services under `services/`:
- `ticket_purchase/` - Order creation, MercadoPago integration, webhook handling
- `ticket_validation/` - QR-based ticket scanning/validation
- `event_management/` - Event CRUD, ticket types, capacity management
- `admin/` - Admin dashboard, user management, stats
- `notifications/` - Email via SendGrid + Celery async tasks

Shared modules under `shared/`:
- `auth/` - JWT + Supabase Auth dual validation (`jwt_handler.py`)
- `database/` - SQLAlchemy async models (`models.py`), connection pooling
- `cache/` - Redis client + Celery workers

## Critical Patterns

### Database Models
All SQLAlchemy models live in `shared/database/models.py` (single source of truth). Pydantic schemas are per-service in `services/{service}/models/`. Example pattern:
```python
# SQLAlchemy model (shared/database/models.py)
class Event(Base):
    __tablename__ = "events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

# Pydantic schema (services/event_management/models/event.py)
class EventResponse(BaseModel):
    id: str  # UUIDs serialize to strings
    class Config:
        from_attributes = True
```

### Authentication Flow
Dual-mode JWT verification in `shared/auth/jwt_handler.py`:
1. Supabase Auth tokens (check `iss` claim for `supabase.co/auth`)
2. Backend-generated tokens (local validation)

Role-based dependencies in `shared/auth/dependencies.py`:
- `get_current_user` - Any authenticated user
- `get_current_admin` - Admin only
- `get_current_admin_or_coordinator` - Admin or coordinator
- `get_current_scanner` - Scanner/admin/coordinator
- `get_optional_user` - Optional auth (public endpoints)

### API Route Structure
All routes prefixed with `/api/v1/` (see `main.py`). Pattern:
```python
# services/{service}/routes/{resource}.py
router = APIRouter()

@router.post("", response_model=ResponseModel)
async def create_resource(
    request: RequestModel,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
```

### Async Database Sessions
Always use dependency injection:
```python
from shared.database.session import get_db
async def endpoint(db: AsyncSession = Depends(get_db)):
```

### Redis/Caching
Use `cache_get`/`cache_set` from `shared/cache/redis_client.py` for idempotency and caching.

## Development Commands

```powershell
# Start development stack
docker compose up -d --build

# Run database migrations
docker compose exec backend bash -lc "alembic -c app/alembic/alembic.ini upgrade head"

# Add new dependency
docker compose exec backend poetry add <package-name>

# Run Celery worker (handled by docker compose, but manual)
poetry run celery -A shared.cache.celery_app:celery_app worker -l INFO
```

## Key Integrations

- **MercadoPago**: Payment processing (`services/ticket_purchase/services/mercado_pago_service.py`)
- **Supabase**: Database (Postgres) + Auth - connection configured in `shared/database/connection.py`
- **Redis**: Cache + Celery broker
- **MinIO**: PDF storage for tickets (S3-compatible)

## Environment Variables

Critical variables (see `env.template`):
- `DATABASE_URL` - Postgres/Supabase connection
- `SUPABASE_URL`, `SUPABASE_ANON_KEY` - Supabase Auth
- `MERCADOPAGO_ACCESS_TOKEN` - Payment processing
- `REDIS_URL` - Cache/task queue
- `JWT_SECRET`, `QR_SECRET` - Security tokens

## Testing
```powershell
poetry run pytest
# Specific test file
poetry run pytest test_mercadopago.py
```
