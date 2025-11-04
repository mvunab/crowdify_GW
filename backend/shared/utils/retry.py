"""Utilidades para retry con backoff exponencial"""
import asyncio
from typing import Callable, Any, Type, Tuple
from functools import wraps


async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Any:
    """
    Ejecutar función con retry y backoff exponencial
    
    Args:
        func: Función a ejecutar (async o sync)
        max_retries: Número máximo de reintentos
        initial_delay: Delay inicial en segundos
        max_delay: Delay máximo en segundos
        exponential_base: Base para cálculo exponencial
        exceptions: Excepciones que deben trigger retry
    
    Returns:
        Resultado de la función
    """
    delay = initial_delay
    
    for attempt in range(max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func()
            else:
                return func()
        except exceptions as e:
            if attempt == max_retries:
                raise e
            
            await asyncio.sleep(delay)
            delay = min(delay * exponential_base, max_delay)
    
    raise Exception("Max retries exceeded")


def retry_decorator(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """Decorator para retry con backoff"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async def call_func():
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            
            return await retry_with_backoff(
                call_func,
                max_retries=max_retries,
                initial_delay=initial_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                exceptions=exceptions
            )
        return wrapper
    return decorator

