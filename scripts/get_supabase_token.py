#!/usr/bin/env python3
"""Script para obtener token JWT real de Supabase Auth"""
import sys
import os
import httpx
import json

# Agregar directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://olyicxwxyxwtiandtbcg.supabase.co')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')


def get_supabase_token(email: str, password: str):
    """Obtener token JWT de Supabase Auth"""
    
    if not SUPABASE_ANON_KEY:
        print("❌ Error: SUPABASE_ANON_KEY no está configurado en .env")
        return None
    
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Content-Type": "application/json"
    }
    
    data = {
        "email": email,
        "password": password
    }
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                token = result.get("access_token")
                
                if token:
                    print("\n✅ Login exitoso!")
                    print(f"📧 Email: {email}")
                    print(f"\n🔑 Token JWT:")
                    print(token)
                    print(f"\n📋 Para usar en curl:")
                    print(f'curl -H "Authorization: Bearer {token}" http://localhost:8000/api/v1/events')
                    print(f"\n💾 Información del usuario:")
                    print(f"   User ID: {result.get('user', {}).get('id', 'N/A')}")
                    print(f"   Email: {result.get('user', {}).get('email', 'N/A')}")
                    
                    # Decodificar token para ver rol
                    try:
                        from jose import jwt
                        unverified = jwt.get_unverified_claims(token)
                        role = unverified.get('user_metadata', {}).get('role', 'user')
                        print(f"   Rol: {role}")
                    except:
                        pass
                    
                    return token
                else:
                    print("❌ Error: No se recibió token en la respuesta")
                    print(f"Respuesta: {json.dumps(result, indent=2)}")
                    return None
            else:
                print(f"❌ Error de login: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Detalle: {error_data.get('error_description', error_data.get('message', 'Error desconocido'))}")
                except:
                    print(f"Respuesta: {response.text}")
                return None
                
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Obtener token JWT de Supabase Auth")
    parser.add_argument("--email", required=True, help="Email del usuario")
    parser.add_argument("--password", required=True, help="Contraseña del usuario")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🔐 Obteniendo Token JWT de Supabase")
    print("=" * 60)
    print(f"📧 Email: {args.email}")
    print(f"🌐 Supabase URL: {SUPABASE_URL}")
    print()
    
    token = get_supabase_token(args.email, args.password)
    
    if token:
        print("\n" + "=" * 60)
        print("✅ Token obtenido exitosamente")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ No se pudo obtener el token")
        print("=" * 60)
        sys.exit(1)

