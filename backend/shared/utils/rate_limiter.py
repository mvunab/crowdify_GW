"""Rate limiting usando slowapi"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request


limiter = Limiter(key_func=get_remote_address)


def get_rate_limiter():
    """Obtener instancia de rate limiter"""
    return limiter

