"""
Rate limiting usando slowapi + Redis para alta concurrencia
Optimizado para manejar 80+ usuarios simultáneos
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request, Response
from starlette.responses import JSONResponse
import os
import logging
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Configuración de Redis para rate limiting distribuido
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def get_real_client_ip(request: Request) -> str:
    """
    Obtener IP real del cliente considerando proxies/load balancers.
    Importante para rate limiting correcto detrás de nginx/cloudflare.
    """
    # Headers comunes de proxy (en orden de prioridad)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For puede tener múltiples IPs: client, proxy1, proxy2
        # La primera es la IP real del cliente
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    cf_connecting_ip = request.headers.get("CF-Connecting-IP")
    if cf_connecting_ip:
        return cf_connecting_ip

    # Fallback a IP directa
    return get_remote_address(request)


def get_user_identifier(request: Request) -> str:
    """
    Generar identificador único para rate limiting.
    Combina IP + user_id si está autenticado para mayor precisión.
    """
    ip = get_real_client_ip(request)

    # Si hay token de autenticación, usarlo como parte del identificador
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        # Usar hash del token para no exponer el token completo
        import hashlib
        token_hash = hashlib.md5(auth_header.encode()).hexdigest()[:8]
        return f"{ip}:{token_hash}"

    return ip


# Crear limiter con Redis storage para rate limiting distribuido
# Esto permite que múltiples instancias de la API compartan el rate limiting
try:
    limiter = Limiter(
        key_func=get_user_identifier,
        storage_uri=REDIS_URL,
        strategy="fixed-window",  # fixed-window o moving-window
        headers_enabled=False,  # Deshabilitado para compatibilidad con response_model de FastAPI
    )
    logger.info(f"Rate limiter inicializado con Redis: {REDIS_URL.split('@')[-1] if '@' in REDIS_URL else 'localhost'}")
except Exception as e:
    # Fallback a memoria si Redis no está disponible
    logger.warning(f"Redis no disponible para rate limiting, usando memoria local: {e}")
    limiter = Limiter(
        key_func=get_user_identifier,
        strategy="fixed-window",
        headers_enabled=False,  # Deshabilitado para compatibilidad con response_model de FastAPI
    )


def get_rate_limiter():
    """Obtener instancia de rate limiter"""
    return limiter


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Handler personalizado para rate limit exceeded.
    Retorna JSON con información útil para el cliente.
    """
    retry_after = exc.detail.split(" ")[-1] if exc.detail else "60"

    logger.warning(
        f"Rate limit exceeded - IP: {get_real_client_ip(request)}, "
        f"Path: {request.url.path}, "
        f"Retry-After: {retry_after}"
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "detail": "Demasiadas solicitudes. Por favor espera antes de intentar nuevamente.",
            "retry_after_seconds": int(retry_after) if retry_after.isdigit() else 60,
        },
        headers={
            "Retry-After": str(retry_after),
            "X-RateLimit-Reset": str(retry_after),
        }
    )


# ============ RATE LIMITS PRE-DEFINIDOS ============

# Límites específicos para diferentes tipos de operaciones
RATE_LIMITS = {
    # Compras: más restrictivo para prevenir abuse y proteger payments
    "purchase": "10/minute",  # 10 intentos de compra por minuto por IP

    # Webhooks: más permisivo porque vienen de payment providers
    "webhook": "100/minute",  # Payment providers pueden hacer muchas llamadas

    # Validación de tickets: moderado
    "validation": "60/minute",  # Scanners validando tickets

    # APIs públicas: más permisivo
    "public": "60/minute",  # Consultas de eventos, tickets por email

    # Admin: más permisivo para operaciones de gestión
    "admin": "120/minute",  # Operaciones administrativas

    # Default: fallback
    "default": "30/minute",
}

