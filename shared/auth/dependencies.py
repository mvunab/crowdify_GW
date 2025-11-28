"""Dependencies de autenticación para FastAPI"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict
from shared.auth.jwt_handler import verify_token


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict:
    '''Obtener usuario actual desde token JWT'''
    token = credentials.credentials
    payload = await verify_token(token)  # AHORA ES ASYNC

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token inválido o expirado',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    user_id = payload.get('sub') or payload.get('user_id')
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token inválido: falta user_id',
        )

    return {
        'user_id': user_id,
        'email': payload.get('email'),
        'role': payload.get('app_metadata', {}).get('role', 'user')
    }


async def OptionalUser(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[Dict]:
    '''Obtener usuario actual si está autenticado, None si no lo está (para endpoints públicos)'''
    if credentials is None:
        return None
    
    try:
        token = credentials.credentials
        payload = await verify_token(token)
        
        if payload is None:
            return None
        
        user_id = payload.get('sub') or payload.get('user_id')
        if not user_id:
            return None
        
        return {
            'user_id': user_id,
            'email': payload.get('email'),
            'role': payload.get('app_metadata', {}).get('role', 'user')
        }
    except Exception:
        return None


async def get_current_admin(
    current_user: Dict = Depends(get_current_user)
) -> Dict:
    '''Verificar que el usuario sea admin'''
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Se requieren permisos de administrador'
        )
    return current_user


async def get_current_admin_or_coordinator(
    current_user: Dict = Depends(get_current_user)
) -> Dict:
    '''Verificar que el usuario sea admin O coordinator'''
    role = current_user.get('role')
    if role not in ['admin', 'coordinator']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acceso denegado. Requiere rol de admin o coordinator, tu rol es: {role}"
        )
    return current_user


async def get_current_scanner(
    current_user: Dict = Depends(get_current_user)
) -> Dict:
    '''Verificar que el usuario sea scanner o admin'''
    role = current_user.get('role')
    if role not in ['scanner', 'admin', 'coordinator']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Se requieren permisos de scanner'
        )
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[Dict]:
    '''Obtener usuario opcional (para endpoints públicos)'''
    if not credentials:
        return None

    token = credentials.credentials
    payload = await verify_token(token)  # AHORA ES ASYNC

    if payload is None:
        return None

    return {
        'user_id': payload.get('sub') or payload.get('user_id'),
        'email': payload.get('email'),
        'role': payload.get('app_metadata', {}).get('role', 'user')
    }
