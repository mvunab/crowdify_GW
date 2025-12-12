"""Conexión a la base de datos PostgreSQL"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy import event
import os
from typing import AsyncGenerator
import logging
import asyncio

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

    # Detectar si es Supabase (remoto) o local
    is_supabase = "pooler.supabase.com" in database_url or "supabase.com" in database_url
    is_local = "localhost" in database_url or "db:5432" in database_url or "127.0.0.1" in database_url

    # Configurar connect_args según el tipo de conexión
    connect_args = {}
    if is_supabase:
        logger.info("Detected Supabase connection, configuring search_path and SSL")
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        connect_args = {
            "ssl": ssl_context,
            "server_settings": {
                "search_path": "public",
                "jit": "off"
            },
            "command_timeout": 60,
            "timeout": 60,
            "statement_cache_size": 100
        }

    # Configuración del pool según el entorno
    pool_config = {
        "pool_pre_ping": True,  # Verificar conexiones antes de usar
        "pool_recycle": 180 if is_supabase else 300,  # Reciclar más seguido en Supabase
        "pool_timeout": 30,
        "pool_use_lifo": True,
    }

    if is_supabase:
        # Para Supabase remoto: pool más pequeño y conservador
        pool_config.update({
            "pool_size": int(os.getenv("DATABASE_POOL_SIZE", "3")),
            "max_overflow": int(os.getenv("DATABASE_MAX_OVERFLOW", "5")),
        })
        logger.info(f"Supabase pool config: size={pool_config['pool_size']}, overflow={pool_config['max_overflow']}")
    else:
        # Para desarrollo local: pool más grande
        pool_config.update({
            "pool_size": int(os.getenv("DATABASE_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("DATABASE_MAX_OVERFLOW", "10")),
        })
        logger.info(f"Local pool config: size={pool_config['pool_size']}, overflow={pool_config['max_overflow']}")

    engine = create_async_engine(
        database_url,
        echo=os.getenv("APP_DEBUG", "False").lower() == "true",
        connect_args=connect_args,
        **pool_config
    )

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    logger.info("Database engine initialized successfully")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency para obtener sesión de base de datos con retry para errores transitorios.

    Maneja errores de DNS y conexión transitorios con retry exponencial.
    """
    if async_session_maker is None:
        logger.error("Database not initialized! Call init_db() first.")
        raise RuntimeError("Database not initialized. Please check application startup.")

    max_retries = 3
    retry_delay = 0.5  # Segundos iniciales
    last_exception = None

    for attempt in range(max_retries):
        try:
            async with async_session_maker() as session:
                try:
                    yield session
                    return  # Exit después de yield exitoso
                finally:
                    await session.close()
        except OSError as e:
            # Captura errores de DNS y socket (socket.gaierror es subclase de OSError)
            last_exception = e
            if attempt < max_retries - 1:
                delay = retry_delay * (2 ** attempt)  # Exponential backoff
                logger.warning(
                    f"Database connection error (attempt {attempt + 1}/{max_retries}): {type(e).__name__}: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"Database connection failed after {max_retries} attempts: {e}")
        except Exception as e:
            # Para otros errores, no reintentar
            logger.error(f"Unexpected database error: {type(e).__name__}: {e}")
            raise

    # Si llegamos aquí, todos los reintentos fallaron
    raise last_exception or RuntimeError("Database connection failed")


async def get_db_with_retry(max_retries: int = 3) -> AsyncGenerator[AsyncSession, None]:
    """
    Versión alternativa de get_db con retry configurable.
    Útil para operaciones críticas que necesitan más reintentos.
    """
    if async_session_maker is None:
        logger.error("Database not initialized! Call init_db() first.")
        raise RuntimeError("Database not initialized. Please check application startup.")

    retry_delay = 0.5
    last_exception = None

    for attempt in range(max_retries):
        try:
            async with async_session_maker() as session:
                try:
                    yield session
                    return
                finally:
                    await session.close()
        except OSError as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = retry_delay * (2 ** attempt)
                logger.warning(
                    f"DB connection retry {attempt + 1}/{max_retries}: {e}. "
                    f"Next retry in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
        except Exception:
            raise

    raise last_exception or RuntimeError("Database connection failed after retries")


async def close_db():
    """Cerrar conexiones a la base de datos"""
    global engine
    if engine:
        logger.info("Closing database connections...")
        await engine.dispose()
        engine = None
        logger.info("Database connections closed")

