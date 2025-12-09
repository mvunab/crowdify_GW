# Copilot Instructions for Crowdify GW

## Project Overview
FastAPI-based ticket sales and validation platform for events. Uses Supabase (production) or local PostgreSQL (development) with Redis caching, Celery workers, and MercadoPago/Payku payment integrations.

## Architecture

### Service Boundaries
```
main.py                    # FastAPI entrypoint, routes all /api/v1/* endpoints
├── services/              # Domain modules with their own models/routes/services
│   ├── ticket_purchase/   # Purchase flow, payment providers (MercadoPago, Payku)
│   ├── ticket_validation/ # QR validation for scanners at events
│   ├── event_management/  # CRUD for events, ticket types, prices
│   ├── notifications/     # Email notifications via SMTP/SendGrid
│   └── admin/             # Admin-only operations
├── shared/                # Cross-cutting concerns
│   ├── database/          # SQLAlchemy models, connection, session
│   ├── auth/              # JWT/Supabase token validation, role-based deps
│   ├── cache/             # Redis client, distributed locks, Celery app
│   └── utils/             # QR generation, rate limiting
└── pdfsvc/                # Separate microservice for PDF generation + MinIO storage
```

### Data Flow Pattern
1. Routes use `Depends(get_db)` for async SQLAlchemy sessions
2. Services are instantiated per-request (lazy-loaded payment providers)
3. Redis caching with `cache_get`/`cache_set` for expensive queries (events list)
4. Celery tasks for async work (PDF generation, email sending)

## Key Conventions

### Authentication Dependencies (`shared/auth/dependencies.py`)
```python
# Use appropriate dependency based on endpoint requirements:
get_current_user       # Requires valid JWT
get_optional_user      # Returns None if no auth (anonymous purchases)
get_current_admin      # Requires role='admin'
get_current_scanner    # Requires role in ['scanner', 'admin', 'coordinator']
```

### Database Models (`shared/database/models.py`)
- All models use UUID primary keys with `uuid.uuid4` default
- Timestamps: `created_at`, `updated_at` with `server_default=func.now()`
- Main entities: `User`, `Event`, `TicketType`, `Order`, `OrderItem`, `Ticket`
- Orders can be anonymous (`user_id` is nullable)

### Service Module Structure
Each service follows this pattern:
```
services/<domain>/
├── models/      # Pydantic schemas for request/response
├── routes/      # FastAPI router with endpoints
├── services/    # Business logic classes
└── tasks/       # Celery tasks (optional)
```

### Configuration (`app/core/config.py`)
Settings loaded via `pydantic-settings` from `.env`. Key settings:
- `DATABASE_URL`: PostgreSQL connection (auto-converted to asyncpg)
- `MERCADOPAGO_ACCESS_TOKEN`: Payment provider (prefix `TEST-` for sandbox)
- `NGROK_URL`: Required for payment webhooks in development

## Development Workflow

### Quick Start
```pwsh
docker compose up -d --build
docker compose exec backend bash -lc "alembic -c app/alembic/alembic.ini upgrade head"
curl http://localhost:8000/health
```

### Useful Commands
```pwsh
make logs-backend          # Tail backend logs
make shell                 # Bash into backend container
make test                  # Run pytest
make poetry-add PKG=name   # Add dependency via Poetry
make health                # Check all services health
```

### Services & Ports
| Service | Port | Credentials |
|---------|------|-------------|
| API | 8000 | - |
| PostgreSQL | 5432 | tickets/tickets |
| Redis | 6379 | - |
| MinIO | 9000 (API), 9003 (console) | minio/minio12345 |
| Mailhog | 8025 | - |
| PDF Service | 9002 | - |

### Testing Payment Webhooks
MercadoPago/Payku webhooks require public URLs. Use ngrok:
```pwsh
ngrok http 8000
# Set NGROK_URL in .env, restart backend
```

## Code Patterns

### Adding New Endpoints
1. Create Pydantic models in `services/<domain>/models/`
2. Add route in `services/<domain>/routes/` with appropriate auth dependency
3. Implement business logic in `services/<domain>/services/`
4. Register router in `main.py` with prefix and tags

### Database Queries
```python
# Always use async SQLAlchemy patterns:
async with db.begin():
    result = await db.execute(select(Model).where(...))
    item = result.scalar_one_or_none()
```

### Caching Pattern
```python
cache_key = f"entity:{id}"
cached = await cache_get(cache_key)
if cached:
    return cached
# ... compute result
await cache_set(cache_key, result, ttl=300)
```

### Idempotency (Purchases)
Purchase requests use `idempotency_key` combining user/items/payment_method to prevent duplicates. Check Redis cache before processing.

## External Integrations

### Supabase
- Auth tokens validated via `shared/auth/supabase_validator.py`
- User roles stored in `app_metadata.role`
- Database can use Supabase PostgreSQL (set `DATABASE_URL` in `.env`)

### MercadoPago
- Sandbox requires `TEST-` prefixed tokens
- Webhook URL must be publicly accessible (ngrok for dev)
- See `docs/MERCADOPAGO_SETUP.md` for credential setup

## Important Files
- `env.template`: All environment variables with descriptions
- `Makefile`: All development commands
- `docker-compose.yml`: Local development stack
- `docs/`: Detailed documentation for specific features
