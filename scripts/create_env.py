#!/usr/bin/env python3
"""Script para crear archivo .env con la configuración proporcionada"""
import os

# Configuración
env_content = """# Database - PostgreSQL de Supabase
DATABASE_URL=postgresql://postgres.olyicxwxyxwtiandtbcg:-->Kdc154515@aws-1-us-east-2.pooler.supabase.com:5432/postgres
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis - Local con Docker Compose
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=

# Supabase (para migración y compatibilidad)
SUPABASE_URL=https://olyicxwxyxwtiandtbcg.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9seWljeHd4eXh3dGlhbmR0YmNnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjE2NzAxMDMsImV4cCI6MjA3NzI0NjEwM30.TeteoABAf6Kf_ZGzo7PwwDXhqxXpAgFj2MPROl3aR94
SUPABASE_SERVICE_KEY=

# JWT - Clave generada automáticamente
JWT_SECRET_KEY=YOaSmGyb_jobA7QJipCIHdUXPOSoaJZClmwrIMOrFE4
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Mercado Pago - Configurar cuando necesites pagos
MERCADOPAGO_ACCESS_TOKEN=
MERCADOPAGO_WEBHOOK_SECRET=

# Email - Configurar cuando necesites emails (SendGrid)
EMAIL_PROVIDER=sendgrid
EMAIL_API_KEY=
EMAIL_FROM=noreply@crodify.com

# CORS - Orígenes permitidos
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173,https://crodify.vercel.app

# App
APP_ENV=development
APP_DEBUG=True
APP_BASE_URL=http://localhost:8000
LOG_LEVEL=INFO
"""

def main():
    import sys
    env_file = ".env"
    
    if os.path.exists(env_file):
        print(f"[AVISO] El archivo {env_file} ya existe.")
        # En modo no interactivo, sobrescribir si se pasa --force
        if '--force' not in sys.argv:
            try:
                response = input("¿Deseas sobrescribirlo? (s/n): ").lower()
                if response != 's':
                    print("[CANCELADO]")
                    return
            except EOFError:
                # Si no hay input disponible, usar --force
                print("[INFO] Modo no interactivo, sobrescribiendo...")
    
    try:
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print("=" * 60)
        print("[OK] Archivo .env creado exitosamente!")
        print("=" * 60)
        print()
        print("Configuracion incluida:")
        print("  [OK] DATABASE_URL - PostgreSQL de Supabase")
        print("  [OK] REDIS_URL - Redis local")
        print("  [OK] SUPABASE_URL y SUPABASE_ANON_KEY")
        print("  [OK] JWT_SECRET_KEY - Generada automaticamente")
        print()
        print("Variables opcionales (vacias por ahora):")
        print("  [ ] MERCADOPAGO_ACCESS_TOKEN - Para pagos")
        print("  [ ] EMAIL_API_KEY - Para emails")
        print("  [ ] SUPABASE_SERVICE_KEY - Para migracion")
        print()
        print("Proximos pasos:")
        print("  1. Inicia los servicios: docker-compose up -d")
        print("  2. Verifica: curl http://localhost:8000/health")
        print("  3. Documentacion: http://localhost:8000/docs")
        print()
        
    except Exception as e:
        print(f"[ERROR] Error creando archivo: {e}")

if __name__ == "__main__":
    main()

