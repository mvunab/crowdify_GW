#!/usr/bin/env python3
"""Script interactivo para generar archivo .env"""
import os
import secrets
import sys

def generate_secret_key():
    """Generar clave secreta aleatoria"""
    return secrets.token_urlsafe(32)

def main():
    print("=" * 60)
    print("Generador de archivo .env para Crodify Backend")
    print("=" * 60)
    print()
    
    env_vars = {}
    
    # Database
    print("📊 CONFIGURACIÓN DE BASE DE DATOS")
    print("-" * 60)
    db_option = input("¿Usar PostgreSQL de Supabase? (s/n): ").lower()
    
    if db_option == 's':
        print("\nPara obtener la connection string:")
        print("1. Ve a Supabase Dashboard → Settings → Database")
        print("2. Busca 'Connection string' → 'URI'")
        print("3. Formato: postgresql://postgres:[PASSWORD]@db.xxx.supabase.co:5432/postgres")
        print()
        db_url = input("Pega aquí la DATABASE_URL: ").strip()
        if db_url:
            env_vars["DATABASE_URL"] = db_url
    else:
        print("Usando PostgreSQL local (Docker Compose)")
        env_vars["DATABASE_URL"] = "postgresql://crodify:crodify@postgres:5432/crodify"
    
    env_vars["DATABASE_POOL_SIZE"] = "20"
    env_vars["DATABASE_MAX_OVERFLOW"] = "10"
    print()
    
    # Redis
    print("💾 CONFIGURACIÓN DE REDIS")
    print("-" * 60)
    redis_option = input("¿Usar Redis local? (s/n): ").lower()
    if redis_option == 's':
        env_vars["REDIS_URL"] = "redis://redis:6379/0"
        env_vars["REDIS_PASSWORD"] = ""
    else:
        redis_url = input("Pega aquí la REDIS_URL: ").strip()
        if redis_url:
            env_vars["REDIS_URL"] = redis_url
            env_vars["REDIS_PASSWORD"] = input("Redis password (opcional, Enter para omitir): ").strip()
    print()
    
    # Supabase
    print("🔐 CONFIGURACIÓN DE SUPABASE")
    print("-" * 60)
    supabase_url = input("SUPABASE_URL (ya lo tienes): ").strip()
    if supabase_url:
        env_vars["SUPABASE_URL"] = supabase_url
    
    supabase_anon = input("SUPABASE_ANON_KEY (ya lo tienes): ").strip()
    if supabase_anon:
        env_vars["SUPABASE_ANON_KEY"] = supabase_anon
    
    print("\nPara obtener SUPABASE_SERVICE_KEY:")
    print("1. Ve a Supabase Dashboard → Settings → API")
    print("2. Busca 'service_role key' (NO la anon key)")
    print()
    supabase_service = input("SUPABASE_SERVICE_KEY (opcional, Enter para omitir): ").strip()
    if supabase_service:
        env_vars["SUPABASE_SERVICE_KEY"] = supabase_service
    print()
    
    # JWT
    print("🔑 CONFIGURACIÓN JWT")
    print("-" * 60)
    generate_jwt = input("¿Generar JWT_SECRET_KEY automáticamente? (s/n): ").lower()
    if generate_jwt == 's':
        jwt_secret = generate_secret_key()
        print(f"✅ Clave generada: {jwt_secret[:20]}...")
        env_vars["JWT_SECRET_KEY"] = jwt_secret
    else:
        jwt_secret = input("JWT_SECRET_KEY (o Enter para generar): ").strip()
        env_vars["JWT_SECRET_KEY"] = jwt_secret or generate_secret_key()
    
    env_vars["JWT_ALGORITHM"] = "HS256"
    env_vars["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
    env_vars["JWT_REFRESH_TOKEN_EXPIRE_DAYS"] = "7"
    print()
    
    # Mercado Pago
    print("💳 CONFIGURACIÓN DE MERCADO PAGO")
    print("-" * 60)
    print("Opcional - Puedes omitir esto para desarrollo")
    print("Para obtener: https://www.mercadopago.com.ar/developers/panel")
    print()
    mp_token = input("MERCADOPAGO_ACCESS_TOKEN (Enter para omitir): ").strip()
    if mp_token:
        env_vars["MERCADOPAGO_ACCESS_TOKEN"] = mp_token
        env_vars["MERCADOPAGO_WEBHOOK_SECRET"] = input("MERCADOPAGO_WEBHOOK_SECRET (opcional): ").strip()
    print()
    
    # Email (Resend)
    print("📧 CONFIGURACIÓN DE EMAIL (Resend)")
    print("-" * 60)
    print("Opcional - Puedes omitir esto para desarrollo")
    print("El sistema usa Resend para envío de emails.")
    print("Obtén tu API key en: https://resend.com/api-keys")
    print()
    resend_key = input("RESEND_API_KEY (Enter para omitir): ").strip()
    if resend_key:
        env_vars["RESEND_API_KEY"] = resend_key
        env_vars["RESEND_FROM_EMAIL"] = input("RESEND_FROM_EMAIL (default: onboarding@resend.dev): ").strip() or "onboarding@resend.dev"
    print()
    
    # CORS
    print("🌐 CONFIGURACIÓN CORS")
    print("-" * 60)
    cors_origins = input("CORS_ORIGINS (default: http://localhost:5173): ").strip()
    env_vars["CORS_ORIGINS"] = cors_origins or "http://localhost:5173"
    print()
    
    # App
    print("⚙️ CONFIGURACIÓN DE APP")
    print("-" * 60)
    env_vars["APP_ENV"] = "development"
    env_vars["APP_DEBUG"] = "True"
    env_vars["APP_BASE_URL"] = "http://localhost:8000"
    env_vars["LOG_LEVEL"] = "INFO"
    print()
    
    # Generar archivo
    env_file = ".env"
    if os.path.exists(env_file):
        overwrite = input(f"⚠️  {env_file} ya existe. ¿Sobrescribir? (s/n): ").lower()
        if overwrite != 's':
            print("❌ Cancelado")
            return
    
    with open(env_file, 'w') as f:
        f.write("# Crodify Backend - Variables de Entorno\n")
        f.write("# Generado automáticamente\n\n")
        
        sections = {
            "Database": ["DATABASE_URL", "DATABASE_POOL_SIZE", "DATABASE_MAX_OVERFLOW"],
            "Redis": ["REDIS_URL", "REDIS_PASSWORD"],
            "Supabase": ["SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_KEY"],
            "JWT": ["JWT_SECRET_KEY", "JWT_ALGORITHM", "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "JWT_REFRESH_TOKEN_EXPIRE_DAYS"],
            "Mercado Pago": ["MERCADOPAGO_ACCESS_TOKEN", "MERCADOPAGO_WEBHOOK_SECRET"],
            "Email": ["EMAIL_PROVIDER", "EMAIL_API_KEY", "EMAIL_FROM"],
            "CORS": ["CORS_ORIGINS"],
            "App": ["APP_ENV", "APP_DEBUG", "APP_BASE_URL", "LOG_LEVEL"]
        }
        
        for section, keys in sections.items():
            f.write(f"\n# {section}\n")
            for key in keys:
                if key in env_vars and env_vars[key]:
                    f.write(f"{key}={env_vars[key]}\n")
            f.write("\n")
    
    print()
    print("=" * 60)
    print("✅ Archivo .env creado exitosamente!")
    print("=" * 60)
    print()
    print("📝 Próximos pasos:")
    print("1. Revisa el archivo .env y completa las variables opcionales")
    print("2. Inicia los servicios: docker-compose up -d")
    print("3. Verifica: curl http://localhost:8000/health")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelado por el usuario")
        sys.exit(1)

