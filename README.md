# Ticketing Monorepo (React soon) — FastAPI + PDF Service + Compose

## Arranque rápido
```bash
cp .env.example .env
docker compose up -d --build
# Aplicar migraciones
docker compose exec backend bash -lc "alembic -c app/alembic/alembic.ini upgrade head"
# Probar
curl http://localhost:8000/health
curl http://localhost:9002/health
```
