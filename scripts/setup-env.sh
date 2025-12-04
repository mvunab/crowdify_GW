#!/bin/bash

# Script para configurar variables de entorno de forma segura
# Este script permite configurar las variables sin guardarlas en archivos de texto plano

set -e

echo "============================================"
echo "Configuración de Variables de Entorno"
echo "CROWDIFY GW - Producción"
echo "============================================"
echo ""

# Generar secretos automáticamente
echo "Generando secretos seguros..."
JWT_SECRET=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
QR_SECRET=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")

echo "✓ Secretos generados"
echo ""

# Función para leer input de forma segura (sin mostrar en pantalla)
read_secret() {
    local prompt="$1"
    local var_name="$2"
    local value
    
    read -sp "$prompt: " value
    echo ""
    export "$var_name=$value"
}

# Función para leer input normal
read_input() {
    local prompt="$1"
    local var_name="$2"
    local default="$3"
    local value
    
    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " value
        value=${value:-$default}
    else
        read -p "$prompt: " value
    fi
    
    export "$var_name=$value"
}

echo "=== BASE DE DATOS ==="
read_input "DATABASE_URL" "DATABASE_URL" "postgresql+psycopg://usuario:password@host:5432/database"
echo ""

echo "=== MINIO ==="
read_input "MINIO_ACCESS_KEY" "MINIO_ACCESS_KEY" "minio"
read_secret "MINIO_SECRET_KEY" "MINIO_SECRET_KEY"
read_input "MINIO_ROOT_USER" "MINIO_ROOT_USER" "minio"
read_secret "MINIO_ROOT_PASSWORD" "MINIO_ROOT_PASSWORD"
echo ""

echo "=== SMTP / EMAIL ==="
read_input "SMTP_HOST" "SMTP_HOST" "smtp.example.com"
read_input "SMTP_PORT" "SMTP_PORT" "587"
read_input "SMTP_USER" "SMTP_USER" "your-email@example.com"
read_secret "SMTP_PASSWORD" "SMTP_PASSWORD"
read_input "SMTP_FROM" "SMTP_FROM" "noreply@example.com"
echo ""

echo "=== SUPABASE (Opcional) ==="
read_input "SUPABASE_URL" "SUPABASE_URL" ""
read_secret "SUPABASE_ANON_KEY" "SUPABASE_ANON_KEY"
echo ""

echo "=== CORS ==="
read_input "CORS_ORIGINS" "CORS_ORIGINS" "https://yourdomain.com,https://www.yourdomain.com"
echo ""

# Variables con valores generados
export JWT_SECRET="$JWT_SECRET"
export QR_SECRET="$QR_SECRET"

# Variables con valores por defecto
export REDIS_URL="${REDIS_URL:-redis://redis:6379/0}"
export MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://minio:9000}"
export MINIO_SECURE="${MINIO_SECURE:-false}"
export MINIO_BUCKET_TICKETS="${MINIO_BUCKET_TICKETS:-tickets-pdf}"
export APP_ENV="${APP_ENV:-production}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"
export API_PORT="${API_PORT:-8000}"
export PDFSVC_PORT="${PDFSVC_PORT:-9002}"

echo ""
echo "============================================"
echo "Variables configuradas ✓"
echo "============================================"
echo ""
echo "Opciones:"
echo "1. Exportar variables al shell actual (temporal)"
echo "2. Guardar en archivo .env (menos seguro)"
echo "3. Ver resumen de variables (sin valores sensibles)"
echo ""
read -p "Selecciona una opción (1/2/3): " option

case $option in
    1)
        echo ""
        echo "✓ Variables exportadas al shell actual"
        echo "Para usar: source este script o ejecuta los exports manualmente"
        echo ""
        echo "Para aplicar a Docker Compose, ejecuta:"
        echo "  docker compose -f docker-compose.prod.yml --env-file <(env | grep -E '^(DATABASE_URL|REDIS_URL|MINIO|JWT|QR|SMTP|SUPABASE|CORS|APP_|LOG_|API_PORT|PDFSVC_PORT)=') up -d"
        ;;
    2)
        echo ""
        read -p "¿Guardar en archivo .env? (s/N): " save
        if [[ "$save" =~ ^[Ss]$ ]]; then
            ENV_FILE="${1:-.env}"
            {
                echo "# Variables de entorno generadas el $(date)"
                echo "DATABASE_URL=$DATABASE_URL"
                echo "REDIS_URL=$REDIS_URL"
                echo "MINIO_ENDPOINT=$MINIO_ENDPOINT"
                echo "MINIO_ACCESS_KEY=$MINIO_ACCESS_KEY"
                echo "MINIO_SECRET_KEY=$MINIO_SECRET_KEY"
                echo "MINIO_SECURE=$MINIO_SECURE"
                echo "MINIO_BUCKET_TICKETS=$MINIO_BUCKET_TICKETS"
                echo "MINIO_ROOT_USER=$MINIO_ROOT_USER"
                echo "MINIO_ROOT_PASSWORD=$MINIO_ROOT_PASSWORD"
                echo "JWT_SECRET=$JWT_SECRET"
                echo "QR_SECRET=$QR_SECRET"
                echo "SMTP_HOST=$SMTP_HOST"
                echo "SMTP_PORT=$SMTP_PORT"
                echo "SMTP_USER=$SMTP_USER"
                echo "SMTP_PASSWORD=$SMTP_PASSWORD"
                echo "SMTP_FROM=$SMTP_FROM"
                echo "SUPABASE_URL=$SUPABASE_URL"
                echo "SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY"
                echo "CORS_ORIGINS=$CORS_ORIGINS"
                echo "APP_ENV=$APP_ENV"
                echo "LOG_LEVEL=$LOG_LEVEL"
                echo "API_PORT=$API_PORT"
                echo "PDFSVC_PORT=$PDFSVC_PORT"
            } > "$ENV_FILE"
            chmod 600 "$ENV_FILE"
            echo "✓ Archivo $ENV_FILE creado con permisos 600 (solo lectura para el propietario)"
        fi
        ;;
    3)
        echo ""
        echo "=== Resumen de Variables ==="
        echo "DATABASE_URL: ${DATABASE_URL:0:30}..."
        echo "REDIS_URL: $REDIS_URL"
        echo "MINIO_ENDPOINT: $MINIO_ENDPOINT"
        echo "MINIO_ACCESS_KEY: $MINIO_ACCESS_KEY"
        echo "MINIO_SECRET_KEY: [OCULTO]"
        echo "MINIO_ROOT_USER: $MINIO_ROOT_USER"
        echo "MINIO_ROOT_PASSWORD: [OCULTO]"
        echo "JWT_SECRET: [OCULTO - ${#JWT_SECRET} caracteres]"
        echo "QR_SECRET: [OCULTO - ${#QR_SECRET} caracteres]"
        echo "SMTP_HOST: $SMTP_HOST"
        echo "SMTP_PORT: $SMTP_PORT"
        echo "SMTP_USER: $SMTP_USER"
        echo "SMTP_PASSWORD: [OCULTO]"
        echo "SMTP_FROM: $SMTP_FROM"
        echo "SUPABASE_URL: ${SUPABASE_URL:0:30}..."
        echo "SUPABASE_ANON_KEY: [OCULTO]"
        echo "CORS_ORIGINS: $CORS_ORIGINS"
        echo "APP_ENV: $APP_ENV"
        echo "LOG_LEVEL: $LOG_LEVEL"
        echo "API_PORT: $API_PORT"
        echo "PDFSVC_PORT: $PDFSVC_PORT"
        ;;
    *)
        echo "Opción no válida"
        exit 1
        ;;
esac

echo ""
echo "============================================"


