"""Cliente Redis para cache y locks distribuidos"""
import redis.asyncio as redis
import os
import json
from typing import Optional, Any
from functools import wraps
import asyncio


redis_client: Optional[redis.Redis] = None


async def init_redis():
    """Inicializar conexión a Redis"""
    global redis_client
    
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_password = os.getenv("REDIS_PASSWORD")
    
    redis_client = redis.from_url(
        redis_url,
        password=redis_password,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_keepalive=True
    )
    
    # Test connection
    try:
        await redis_client.ping()
    except Exception as e:
        print(f"Error conectando a Redis: {e}")


async def get_redis() -> redis.Redis:
    """Obtener cliente Redis"""
    if redis_client is None:
        await init_redis()
    return redis_client


async def close_redis():
    """Cerrar conexión a Redis"""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


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

