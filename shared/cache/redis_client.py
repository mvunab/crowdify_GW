"""Cliente Redis para cache y locks distribuidos"""
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
import os
import json
from typing import Optional, Any
from functools import wraps
import asyncio
import logging

logger = logging.getLogger(__name__)

redis_client: Optional[redis.Redis] = None
redis_pool: Optional[ConnectionPool] = None


async def init_redis():
    """Inicializar conexión a Redis con pool de conexiones"""
    global redis_client, redis_pool

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_password = os.getenv("REDIS_PASSWORD")

    # Configuración del pool para alta concurrencia
    max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "20"))

    # Crear pool de conexiones
    redis_pool = ConnectionPool.from_url(
        redis_url,
        password=redis_password,
        max_connections=max_connections,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_keepalive=True,
        retry_on_timeout=True,
        health_check_interval=30,  # Health check cada 30s
    )

    redis_client = redis.Redis(connection_pool=redis_pool)

    # Test connection
    try:
        await redis_client.ping()
        logger.info(f"Redis conectado exitosamente (pool max_connections={max_connections})")
    except Exception as e:
        logger.error(f"Error conectando a Redis: {e}")


async def get_redis() -> redis.Redis:
    """Obtener cliente Redis"""
    if redis_client is None:
        await init_redis()
    return redis_client


async def close_redis():
    """Cerrar conexión a Redis y pool"""
    global redis_client, redis_pool
    if redis_client:
        await redis_client.close()
        redis_client = None
    if redis_pool:
        await redis_pool.disconnect()
        redis_pool = None
    logger.info("Redis desconectado")


class DistributedLock:
    """Lock distribuido usando Redis"""

    def __init__(self, key: str, timeout: int = 10, expire: int = 30):
        self.key = f"lock:{key}"
        self.timeout = timeout
        self.expire = expire
        self.identifier = None

    async def acquire(self) -> bool:
        """Adquirir lock"""
        redis_conn = await get_redis()
        import uuid
        self.identifier = str(uuid.uuid4())

        end_time = asyncio.get_event_loop().time() + self.timeout
        while asyncio.get_event_loop().time() < end_time:
            if await redis_conn.set(self.key, self.identifier, nx=True, ex=self.expire):
                return True
            await asyncio.sleep(0.1)

        return False

    async def release(self):
        """Liberar lock"""
        if not self.identifier:
            return

        redis_conn = await get_redis()
        # Lua script para asegurar que solo el owner puede liberar
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        await redis_conn.eval(lua_script, 1, self.key, self.identifier)

    async def __aenter__(self):
        if not await self.acquire():
            raise Exception(f"No se pudo adquirir lock: {self.key}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()


async def cache_get(key: str) -> Optional[Any]:
    """Obtener valor del cache"""
    redis_conn = await get_redis()
    value = await redis_conn.get(key)
    if value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return None


async def cache_set(key: str, value: Any, expire: int = 3600):
    """Guardar valor en cache"""
    redis_conn = await get_redis()
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
    await redis_conn.setex(key, expire, value)


async def cache_delete(key: str):
    """Eliminar del cache"""
    redis_conn = await get_redis()
    await redis_conn.delete(key)

