import httpx
import os
import hashlib
import json
from typing import Optional, Dict
from jose import jwt

SUPABASE_URL = os.getenv('SUPABASE_URL')
if not SUPABASE_URL:
    raise ValueError('SUPABASE_URL debe estar configurado en las variables de entorno')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')
CACHE_TTL_SECONDS = 600  # 10 minutos


def get_token_cache_key(token: str) -> str:
    '''Generar clave de caché para un token (usando hash para no almacenar el token completo)'''
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return f'jwt:validated:{token_hash[:16]}'


async def get_redis_client():
    '''Obtener cliente Redis (lazy loading)'''
    from shared.cache.redis_client import get_redis
    return await get_redis()


async def verify_supabase_token(token: str) -> Optional[Dict]:
    '''
    Verifica un JWT token de Supabase delegando la validación al Auth server.
    Según la documentación de Supabase, esta es la forma recomendada de validar tokens.
    
    OPTIMIZACIÓN: Cachea tokens validados en Redis por 10 minutos
    '''
    try:
        # Intentar obtener del caché primero
        redis_client = await get_redis_client()
        cache_key = get_token_cache_key(token)
        
        cached_payload = await redis_client.get(cache_key)
        if cached_payload:
            # Token encontrado en caché - FAST PATH
            return json.loads(cached_payload)
        
        # Token no en caché - validar con Supabase
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f'{SUPABASE_URL}/auth/v1/user',
                headers={
                    'apikey': SUPABASE_ANON_KEY,
                    'Authorization': f'Bearer {token}'
                }
            )
            
            if response.status_code == 200:
                user_data = response.json()
                
                # Decodificar el token SIN verificar (solo para extraer claims)
                unverified_payload = jwt.get_unverified_claims(token)
                
                # Extraer el role desde user_metadata
                user_metadata = unverified_payload.get('user_metadata', {})
                role = user_metadata.get('role', 'user')
                
                # Construir payload compatible con el sistema actual
                payload = {
                    'sub': user_data.get('id'),
                    'user_id': user_data.get('id'),
                    'email': user_data.get('email'),
                    'role': role,
                    'aud': unverified_payload.get('aud'),
                    'exp': unverified_payload.get('exp'),
                    'iat': unverified_payload.get('iat'),
                    'iss': unverified_payload.get('iss'),
                    'user_metadata': user_metadata,
                    'app_metadata': unverified_payload.get('app_metadata', {})
                }
                
                # CACHEAR el resultado en Redis
                await redis_client.setex(
                    cache_key,
                    CACHE_TTL_SECONDS,
                    json.dumps(payload)
                )
                
                return payload
            else:
                return None
                
    except Exception as e:
        print(f'Error validating token with Supabase: {e}')
        return None


def verify_token_sync(token: str) -> Optional[Dict]:
    '''
    Versión síncrona para compatibilidad con código existente
    '''
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Si ya hay un loop corriendo, crear una tarea
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, verify_supabase_token(token))
                return future.result(timeout=10)
        else:
            return loop.run_until_complete(verify_supabase_token(token))
    except Exception as e:
        print(f'Error in sync verification: {e}')
        return None
