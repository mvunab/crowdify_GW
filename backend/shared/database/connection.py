"""Conexión a la base de datos PostgreSQL"""
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
import os
from typing import AsyncGenerator

# Base para modelos SQLAlchemy
Base = declarative_base()

# Engine y session factory
engine = None
async_session_maker = None


async def init_db():
    """Inicializar conexión a la base de datos"""
    global engine, async_session_maker
    
    database_url = os.getenv("DATABASE_URL", "postgresql://crodify:crodify@localhost:5432/crodify")
    # Convertir a async URL
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql+psycopg://"):
        database_url = database_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
    
    # Configurar schema por defecto para Supabase
    connect_args = {}
    if "pooler.supabase.com" in database_url or "supabase.com" in database_url:
        # Para Supabase pooler, configurar search_path explícitamente
        # El pooler puede resetear el search_path, así que lo configuramos en cada conexión
        connect_args = {
            "server_settings": {
                "search_path": "public"
            },
            "command_timeout": 60
        }
    
    engine = create_async_engine(
        database_url,
        pool_size=int(os.getenv("DATABASE_POOL_SIZE", "20")),
        max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "10")),
        pool_pre_ping=True,
        echo=os.getenv("APP_DEBUG", "False").lower() == "true",
        connect_args=connect_args
    )
    
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency para obtener sesión de base de datos"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def close_db():
    """Cerrar conexiones a la base de datos"""
    if engine:
        await engine.dispose()

