# Crowdify GW - AI Coding Instructions

## Architecture Overview

**Crowdify GW** is a FastAPI ticket sales backend with domain-driven service organization:

```
main.py              → FastAPI app entry, router registration, lifespan events
services/            → Domain modules (ticket_purchase, ticket_validation, admin, notifications, event_management)
shared/              → Cross-cutting: auth/, cache/, database/, utils/
pdfsvc/              → Separate microservice for PDF generation (port 9002)
```

### Service Pattern
Each service in `services/` follows: `routes/` → `services/` → `models/`

Example: `services/ticket_purchase/services/purchase_service.py` handles purchase logic, called from `services/ticket_purchase/routes/purchase.py`.

## API Endpoints Reference

### Route Prefixes
- `/api/v1/events` - Event listing/management
- `/api/v1/purchases` - Purchase creation, webhooks
- `/api/v1/tickets` - Ticket queries, validation
- `/api/v1/admin` - Admin operations (orders, reports)
- `/api/v1/notifications` - Email notifications

### Key Endpoints
| Endpoint | Auth | Description |
|----------|------|-------------|
| `POST /api/v1/purchases` | Optional | Create order with attendees, payment_method (payku/bank_transfer/mercadopago) |
| `POST /api/v1/purchases/webhook` | None | MercadoPago webhook |
| `POST /api/v1/purchases/payku-webhook` | None | Payku webhook |
| `POST /api/v1/tickets/validate` | Scanner/Admin | Validate ticket QR |
| `GET /api/v1/tickets/email/{email}` | None | Public ticket search by email |
| `PUT /api/v1/admin/orders/{id}/approve` | Admin | Approve bank transfer |

### Purchase Flow
1. Frontend calls `POST /api/v1/purchases` with `event_id`, `attendees[]`, `payment_method`
2. Backend returns `order_id` + `payment_link` (Payku) or `preference_id` (MercadoPago)
3. User pays externally → webhook received → tickets generated → email sent

## Key Patterns

### Database Access
```python
from shared.database.session import get_db
from shared.database.models import Order, Ticket, Event

async def my_route(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.id == order_id))
```

### Authentication
```python
from shared.auth.dependencies import get_current_user, get_current_admin, get_current_admin_or_coordinator

@router.get("/protected")
async def protected(current_user: Dict = Depends(get_current_user)): ...

@router.post("/admin-only")
async def admin_only(admin: Dict = Depends(get_current_admin)): ...
```
Roles: `user`, `admin`, `scanner`, `coordinator`

### Caching & Idempotency
```python
from shared.cache.redis_client import cache_get, cache_set, DistributedLock

# Idempotency pattern for purchases
cache_key = f"purchase:idempotency:{idempotency_key}"
cached = await cache_get(cache_key)
if cached:
    return cached
```

### Error Handling Convention
- Services raise `ValueError` for business logic errors
- Routes catch and convert to `HTTPException(status_code=400, detail=str(e))`
- Use 409 for conflicts (duplicate idempotency key, ticket already scanned)

## Development Workflow

### Local Development (Docker)
```pwsh
docker compose up -d --build
docker compose exec backend bash -lc "alembic -c app/alembic/alembic.ini upgrade head"
```

### Without Docker
```pwsh
poetry install
poetry run uvicorn main:app --reload
poetry run celery -A app.worker:celery_app worker -l INFO
```

### Key Ports
API: 8000 | Postgres: 5432 | Redis: 6379 | MinIO: 9000/9003 | PDF: 9002

## Configuration

Environment via `app/core/config.py` (pydantic-settings):
- `DATABASE_URL` - PostgreSQL connection (supports Supabase)
- `REDIS_URL` - Redis for cache/celery
- `RESEND_API_KEY` - Email service
- `MERCADOPAGO_ACCESS_TOKEN`, `PAYKU_TOKEN_PUBLICO/PRIVADO` - Payment providers
- `FRONTEND_URL`, `NGROK_URL` - Webhook return URLs

## Important Files

- `shared/database/models.py` - SQLAlchemy models (User, Event, Order, Ticket, TicketType, etc.)
- `shared/auth/dependencies.py` - Auth decorators
- `services/ticket_purchase/services/purchase_service.py` - Core purchase logic
- `services/notifications/services/email_service.py` - Resend email + QR generation
- `main.py` - App initialization, CORS, rate limiting
