"""API Gateway principal - Punto de entrada de la aplicación"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
import os
import logging
from contextlib import asynccontextmanager

from shared.database.connection import init_db, close_db
from shared.cache.redis_client import init_redis, close_redis
from shared.utils.rate_limiter import limiter, rate_limit_exceeded_handler

# Configurar logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events de la aplicación"""
    # Startup
    logger.info("Iniciando aplicación...")
    await init_db()
    await init_redis()
    logger.info("Aplicación iniciada")
    yield
    # Shutdown
    logger.info("Cerrando aplicación...")
    await close_db()
    await close_redis()
    logger.info("Aplicación cerrada")


# Crear aplicación FastAPI
app = FastAPI(
    title="Crodify API",
    description="Backend API para plataforma de venta de tickets para eventos",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS PRIMERO (antes de rate limiting)
# Por defecto, permitir los puertos comunes de desarrollo y producción
default_origins = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173,https://crodify.vercel.app"
cors_origins_str = os.getenv("CORS_ORIGINS", default_origins)

# En desarrollo, permitir todos los orígenes para facilitar testing
if os.getenv("APP_ENV", "development") == "development":
    logger.info("Modo desarrollo: CORS configurado para permitir todos los orígenes")
    allow_origins = ["*"]
    allow_credentials = False  # No se puede usar credentials con allow_origins=["*"]
else:
    # En producción, solo orígenes específicos
    cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]
    allow_origins = cors_origins
    allow_credentials = True
    logger.info(f"CORS origins configurados: {allow_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests por 1 hora
)

# Configurar rate limiting DESPUÉS de CORS
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Incluir routers de cada servicio
from services.ticket_validation.routes.validation import router as validation_router
from services.ticket_purchase.routes.purchase import router as purchase_router
from services.ticket_purchase.routes.tickets import router as tickets_router
from services.event_management.routes.events import router as events_router
from services.notifications.routes.notifications import router as notifications_router
from services.admin.routes.admin import router as admin_router

app.include_router(validation_router, prefix="/api/v1/tickets", tags=["tickets"])
app.include_router(purchase_router, prefix="/api/v1/purchases", tags=["purchases"])
app.include_router(tickets_router, prefix="/api/v1/tickets", tags=["tickets"])
app.include_router(events_router, prefix="/api/v1/events", tags=["events"])
app.include_router(notifications_router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "crodify-api"}


@app.get("/ready")
async def ready():
    """Ready check endpoint - verifica conexiones"""
    try:
        # Verificar DB
        from sqlalchemy import text
        from shared.database.connection import async_session_maker
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))

        # Verificar Redis
        from shared.cache.redis_client import get_redis
        redis = await get_redis()
        await redis.ping()

        return {"status": "ready", "database": "connected", "redis": "connected"}
    except Exception as e:
        logger.error(f"Ready check failed: {e}")
        return {"status": "not ready", "error": str(e)}, 503


@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handler para requests OPTIONS (CORS preflight)"""
    return {"message": "OK"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("APP_DEBUG", "False").lower() == "true"
    )

