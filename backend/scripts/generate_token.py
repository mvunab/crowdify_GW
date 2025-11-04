#!/usr/bin/env python3
"""Script para generar tokens JWT de prueba"""
import sys
import os
from datetime import datetime, timedelta
from jose import jwt

# Agregar directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.auth.jwt_handler import JWT_SECRET_KEY, JWT_ALGORITHM


def generate_token(user_id: str, email: str = None, role: str = "user"):
    """Generar token JWT"""
    data = {
        "sub": user_id,
        "user_id": user_id,
        "email": email or f"{user_id}@example.com",
        "role": role,
        "iat": datetime.utcnow(),
    }
    
    token = jwt.encode(data, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generar token JWT de prueba")
    parser.add_argument("--user-id", required=True, help="ID del usuario")
    parser.add_argument("--email", help="Email del usuario")
    parser.add_argument("--role", default="user", choices=["user", "admin", "scanner", "coordinator"], help="Rol del usuario")
    
    args = parser.parse_args()
    
    token = generate_token(args.user_id, args.email, args.role)
    print(f"\nToken generado:")
    print(token)
    print(f"\nPara usar en curl:")
    print(f'curl -H "Authorization: Bearer {token}" http://localhost:8000/api/v1/events')
    print()

