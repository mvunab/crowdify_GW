#!/bin/bash

# Deploy rápido con configuración mínima
# Usa valores por defecto para desarrollo/pruebas

set -e

cd "$(dirname "$0")/.."

echo "============================================"
echo "Deploy Rápido - CROWDIFY GW"
echo "============================================"
echo ""

# Cargar secretos generados
source scripts/export-env.sh

# Configurar variables mínimas si no están definidas
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://tickets:tickets@db:5432/tickets}"
export MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minio12345}"
export MINIO_ROOT_PASSWORD="${MINIO_ROOT_PASSWORD:-minio12345}"
export SMTP_HOST="${SMTP_HOST:-mailhog}"
export SMTP_PORT="${SMTP_PORT:-1025}"
export SMTP_USER="${SMTP_USER:-}"
export SMTP_PASSWORD="${SMTP_PASSWORD:-}"
export SMTP_FROM="${SMTP_FROM:-noreply@crowdify.local}"
export SUPABASE_URL="${SUPABASE_URL:-}"
export SUPABASE_ANON_KEY="${SUPABASE_ANON_KEY:-}"
export CORS_ORIGINS="${CORS_ORIGINS:-*}"

echo "Variables configuradas:"
echo "  DATABASE_URL: ${DATABASE_URL:0:50}..."
echo "  JWT_SECRET: [${#JWT_SECRET} caracteres]"
echo "  QR_SECRET: [${#QR_SECRET} caracteres]"
echo "  MINIO_SECRET_KEY: [${#MINIO_SECRET_KEY} caracteres]"
echo "  SMTP_HOST: $SMTP_HOST"
echo "  CORS_ORIGINS: $CORS_ORIGINS"
echo ""

read -p "¿Continuar con el deploy? (s/N): " confirm
if [[ ! "$confirm" =~ ^[Ss]$ ]]; then
    echo "Deploy cancelado"
    exit 0
fi

echo ""
echo "Ejecutando deploy..."
./scripts/deploy-with-env.sh


