"""Manejo de JWT tokens"""
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
import os


JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key-change-in-production')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRE_DAYS', '7'))


def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    '''Crear token de acceso JWT'''
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({'exp': expire, 'type': 'access'})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict) -> str:
    '''Crear token de refresh JWT'''
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({'exp': expire, 'type': 'refresh'})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict]:
    '''Decodificar y validar token JWT'''
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


async def verify_token(token: str) -> Optional[Dict]:
    '''
    Verificar token delegando a Supabase Auth (ASYNC).
    Para tokens de Supabase, usa el validador de Supabase.
    Para tokens propios del backend, usa la validación local.
    '''
    # Primero intentar decodificar sin verificar para ver el issuer
    try:
        unverified = jwt.get_unverified_claims(token)
        issuer = unverified.get('iss', '')
        
        # Si es un token de Supabase Auth, validar con Supabase
        if 'supabase.co/auth' in issuer:
            from shared.auth.supabase_validator import verify_supabase_token
            return await verify_supabase_token(token)
        else:
            # Token propio del backend, validar localmente
            return decode_token(token)
    except Exception as e:
        print(f'Error verifying token: {e}')
        # Si falla la detección, intentar validación local
        return decode_token(token)
