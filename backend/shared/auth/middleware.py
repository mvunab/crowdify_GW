"""Middleware de autenticación"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from shared.auth.jwt_handler import verify_token
import re


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware para validar tokens en rutas protegidas"""
    
    # Rutas públicas que no requieren autenticación
    PUBLIC_PATHS = [
        "/health",
        "/ready",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/v1/events",  # GET para listar eventos
    ]
    
    # Rutas que requieren autenticación específica (validadas en los endpoints)
    PROTECTED_PATHS = [
        "/api/v1/tickets/validate",
        "/api/v1/purchases",
        "/api/v1/events",  # POST, PUT, DELETE
    ]
    
    async def dispatch(self, request: Request, call_next):
        """Procesar request y validar autenticación si es necesario"""
        path = request.url.path
        
        # Ignorar rutas públicas
        if any(re.match(pattern.replace("*", ".*"), path) for pattern in self.PUBLIC_PATHS):
            return await call_next(request)
        
        # Para rutas protegidas, verificar token
        if any(path.startswith(protected) for protected in self.PROTECTED_PATHS):
            auth_header = request.headers.get("Authorization")
            
            if not auth_header or not auth_header.startswith("Bearer "):
                # Permitir requests sin auth para algunos endpoints específicos
                # La validación se hace en los endpoints individuales
                pass
            else:
                token = auth_header.split(" ")[1]
                payload = verify_token(token)
                
                if payload is None:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token inválido o expirado"
                    )
                
                # Agregar usuario al request state
                request.state.user = {
                    "user_id": payload.get("sub") or payload.get("user_id"),
                    "email": payload.get("email"),
                    "role": payload.get("role", "user")
                }
        
        response = await call_next(request)
        return response

