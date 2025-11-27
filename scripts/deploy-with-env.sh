#!/bin/bash

# Script de deploy que usa variables de entorno exportadas
# Más seguro que usar archivos .env

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Configuración
SERVER="${DEPLOY_SERVER:-209.38.78.227}"
USER="${DEPLOY_USER:-root}"
SSH_KEY="${DEPLOY_SSH_KEY:-}"
APP_DIR="${DEPLOY_APP_DIR:-/opt/crowdify}"

# Construir comando SSH
SSH_CMD="ssh"
if [ -n "$SSH_KEY" ]; then
    SSH_CMD="$SSH_CMD -i $SSH_KEY"
fi
SSH_CMD="$SSH_CMD $USER@$SERVER"

# Verificar que las variables esenciales estén definidas
log_info "Verificando variables de entorno..."

REQUIRED_VARS=(
    "DATABASE_URL"
    "JWT_SECRET"
    "QR_SECRET"
    "MINIO_ACCESS_KEY"
    "MINIO_SECRET_KEY"
    "MINIO_ROOT_PASSWORD"
    "SMTP_HOST"
    "SMTP_FROM"
)

# Variables opcionales con valores por defecto
OPTIONAL_VARS=(
    "SMTP_USER"
    "SMTP_PASSWORD"
    "SUPABASE_URL"
    "SUPABASE_ANON_KEY"
    "CORS_ORIGINS"
)

MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    log_error "Faltan las siguientes variables de entorno requeridas:"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    echo ""
    log_info "Ejecuta primero: source scripts/setup-env.sh"
    exit 1
fi

# Establecer valores por defecto para variables opcionales
export SMTP_USER="${SMTP_USER:-}"
export SMTP_PASSWORD="${SMTP_PASSWORD:-}"
export SUPABASE_URL="${SUPABASE_URL:-}"
export SUPABASE_ANON_KEY="${SUPABASE_ANON_KEY:-}"
export CORS_ORIGINS="${CORS_ORIGINS:-*}"

log_info "Todas las variables requeridas están definidas ✓"

# Sincronizar archivos
log_info "Sincronizando archivos..."
rsync_cmd="rsync -avz --delete"
if [ -n "$SSH_KEY" ]; then
    rsync_cmd="$rsync_cmd -e 'ssh -i $SSH_KEY'"
fi

rsync_cmd="$rsync_cmd --exclude='.git'"
rsync_cmd="$rsync_cmd --exclude='__pycache__'"
rsync_cmd="$rsync_cmd --exclude='*.pyc'"
rsync_cmd="$rsync_cmd --exclude='.env'"
rsync_cmd="$rsync_cmd --exclude='.venv'"
rsync_cmd="$rsync_cmd --exclude='node_modules'"

eval "$rsync_cmd ./ $USER@$SERVER:$APP_DIR/"
log_info "Archivos sincronizados ✓"

# Construir comando para pasar variables de entorno a Docker Compose
log_info "Preparando deploy con variables de entorno..."

# Crear un script temporal en el servidor que exporte las variables
ENV_SCRIPT=$(cat <<EOF
#!/bin/bash
export DATABASE_URL="$DATABASE_URL"
export REDIS_URL="${REDIS_URL:-redis://redis:6379/0}"
export MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://minio:9000}"
export MINIO_ACCESS_KEY="$MINIO_ACCESS_KEY"
export MINIO_SECRET_KEY="$MINIO_SECRET_KEY"
export MINIO_SECURE="${MINIO_SECURE:-false}"
export MINIO_BUCKET_TICKETS="${MINIO_BUCKET_TICKETS:-tickets-pdf}"
export MINIO_ROOT_USER="${MINIO_ROOT_USER:-minio}"
export MINIO_ROOT_PASSWORD="$MINIO_ROOT_PASSWORD"
export JWT_SECRET="$JWT_SECRET"
export QR_SECRET="$QR_SECRET"
export SMTP_HOST="$SMTP_HOST"
export SMTP_PORT="${SMTP_PORT:-587}"
export SMTP_USER="$SMTP_USER"
export SMTP_PASSWORD="$SMTP_PASSWORD"
export SMTP_FROM="$SMTP_FROM"
export SUPABASE_URL="${SUPABASE_URL:-}"
export SUPABASE_ANON_KEY="${SUPABASE_ANON_KEY:-}"
export CORS_ORIGINS="${CORS_ORIGINS:-}"
export APP_ENV="${APP_ENV:-production}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"
export API_PORT="${API_PORT:-8000}"
export PDFSVC_PORT="${PDFSVC_PORT:-9002}"
export PYTHONUNBUFFERED="1"
export PYTHONPATH="/app"
export POETRY_VIRTUALENVS_CREATE="false"
EOF
)

# Enviar el script al servidor y ejecutarlo
log_info "Configurando variables en el servidor..."
$SSH_CMD "cat > $APP_DIR/.env.export <<'ENVEOF'
$ENV_SCRIPT
ENVEOF
chmod +x $APP_DIR/.env.export"

# Construir imágenes si es necesario
if [ "${SKIP_BUILD:-false}" != "true" ]; then
    log_info "Construyendo imágenes Docker..."
    $SSH_CMD "cd $APP_DIR && source .env.export && docker compose -f docker-compose.prod.yml build --no-cache"
    log_info "Imágenes construidas ✓"
fi

# Ejecutar migraciones
if [ "${SKIP_MIGRATE:-false}" != "true" ]; then
    log_info "Ejecutando migraciones..."
    $SSH_CMD "cd $APP_DIR && source .env.export && docker compose -f docker-compose.prod.yml run --rm backend poetry run alembic -c app/alembic/alembic.ini upgrade head" || log_warn "Error en migraciones, continuando..."
fi

# Detener servicios existentes
log_info "Deteniendo servicios existentes..."
$SSH_CMD "cd $APP_DIR && source .env.export && docker compose -f docker-compose.prod.yml down" || true

# Levantar servicios
log_info "Levantando servicios..."
$SSH_CMD "cd $APP_DIR && source .env.export && docker compose -f docker-compose.prod.yml up -d"

# Esperar y verificar
sleep 10
log_info "Verificando servicios..."

if $SSH_CMD "curl -f http://localhost:8000/health > /dev/null 2>&1"; then
    log_info "Backend API: ✓ Saludable"
else
    log_warn "Backend API: ⚠ No responde aún"
fi

log_info ""
log_info "${GREEN}✓ Deploy completado${NC}"
log_info "Servidor: $SERVER"
log_info "API: http://$SERVER:8000"

