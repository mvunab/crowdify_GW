"""Conexión a la base de datos PostgreSQL"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
import os
from typing import AsyncGenerator
import logging

logger = logging.getLogger(__name__)

# Base para modelos SQLAlchemy
Base = declarative_base()

# Engine y session factory
engine = None
async_session_maker = None


async def init_db():
    """Inicializar conexión a la base de datos"""
    global engine, async_session_maker

    if engine is not None:
        logger.warning("Database engine already initialized, skipping...")
        return

    if engine is not None:
        logger.warning("Database engine already initialized, skipping...")
        return

    database_url = os.getenv("DATABASE_URL", "postgresql://crodify:crodify@localhost:5432/crodify")

    logger.info(f"Initializing database connection to: {database_url.split('@')[1] if '@' in database_url else database_url}")

    # Limpiar parámetros SSL de la URL (se configuran en connect_args)
    if "?" in database_url:
        database_url = database_url.split("?")[0]
        logger.info("Removed query parameters from DATABASE_URL (SSL configured in connect_args)")

    # Convertir a async URL
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql+psycopg://"):
        database_url = database_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)

    logger.info(f"Using async driver: {database_url.split(':')[0]}")

    # Configurar schema por defecto para Supabase
    connect_args = {}
    if "pooler.supabase.com" in database_url or "supabase.com" in database_url:
        logger.info("Detected Supabase connection, configuring search_path and SSL")
        # Para Supabase pooler, configurar search_path explícitamente
        # El pooler puede resetear el search_path, así que lo configuramos en cada conexión
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        connect_args = {
            "ssl": ssl_context,  # SSL context para Supabase
            "server_settings": {
                "search_path": "public",
                "jit": "off"  # Desactivar JIT para queries rápidas
            },
            "command_timeout": 60,  # Timeout de comandos (60s) - más permisivo para remoto
            "timeout": 60,  # Timeout de conexión (60s) - más permisivo para Supabase remoto
            "statement_cache_size": 100  # Cache de statements preparados
        }

    engine = create_async_engine(
        database_url,
        pool_size=int(os.getenv("DATABASE_POOL_SIZE", "30")),  # Aumentado a 30
        max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "20")),  # Aumentado a 20
        pool_pre_ping=True,
        pool_recycle=300,  # Reciclar conexiones cada 5 min
        pool_timeout=20,  # Timeout para obtener conexión del pool (20s)
        echo=os.getenv("APP_DEBUG", "False").lower() == "true",
        connect_args=connect_args
    )

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    logger.info("Database engine initialized successfully")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency para obtener sesión de base de datos"""
    if async_session_maker is None:
        logger.error("Database not initialized! Call init_db() first.")
        raise RuntimeError("Database not initialized. Please check application startup.")

    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def close_db():
    """Cerrar conexiones a la base de datos"""
    if engine:
        await engine.dispose()

