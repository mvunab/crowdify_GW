#!/bin/bash

# Script para exportar variables de entorno de forma segura
# Ejecuta: source scripts/export-env.sh

# Secretos generados automáticamente
export JWT_SECRET="9c6087052627679f4ae665b7008b8f8c6ae7123402548afd6dd5625d8e9707a5"
export QR_SECRET="a9f0ab5b834f391158a1c2aadd8df9c73976f9ed6d4a775059ecfceda270a47c"

# Variables con valores por defecto (puedes sobrescribirlas)
export REDIS_URL="${REDIS_URL:-redis://redis:6379/0}"
export MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://minio:9000}"
export MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minio}"
export MINIO_SECURE="${MINIO_SECURE:-false}"
export MINIO_BUCKET_TICKETS="${MINIO_BUCKET_TICKETS:-tickets-pdf}"
export MINIO_ROOT_USER="${MINIO_ROOT_USER:-minio}"
export APP_ENV="${APP_ENV:-production}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"
export API_PORT="${API_PORT:-8000}"
export PDFSVC_PORT="${PDFSVC_PORT:-9002}"
export SMTP_PORT="${SMTP_PORT:-587}"

# Variables que DEBES configurar manualmente
# Descomenta y completa estas líneas:

# export DATABASE_URL="postgresql+psycopg://usuario:password@host:5432/database"
# export MINIO_SECRET_KEY="tu-password-minio-seguro"
# export MINIO_ROOT_PASSWORD="tu-password-minio-seguro"
# export SMTP_HOST="smtp.tu-proveedor.com"
# export SMTP_USER="tu-email@ejemplo.com"
# export SMTP_PASSWORD="tu-password-email"
# export SMTP_FROM="noreply@ejemplo.com"
# export SUPABASE_URL="https://tu-proyecto.supabase.co"
# export SUPABASE_ANON_KEY="tu-supabase-anon-key"
# export CORS_ORIGINS="https://tudominio.com,https://www.tudominio.com"

echo "✓ Variables de entorno exportadas"
echo ""
echo "Secretos generados:"
echo "  JWT_SECRET: [${#JWT_SECRET} caracteres]"
echo "  QR_SECRET: [${#QR_SECRET} caracteres]"
echo ""
echo "⚠️  IMPORTANTE: Configura las variables que están comentadas arriba"
echo "   Edita este archivo y descomenta/completa las variables necesarias"


