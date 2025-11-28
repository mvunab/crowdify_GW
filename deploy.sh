#!/bin/bash

# Script de deploy para Crowdify GW
# Uso: ./deploy.sh [opciones]
#
# Opciones:
#   --server SERVER    IP o hostname del servidor (default: 209.38.78.227)
#   --user USER        Usuario SSH (default: root)
#   --key KEY          Ruta a la clave SSH privada
#   --env ENV_FILE     Ruta al archivo .env en el servidor
#   --skip-build       No reconstruir las imágenes Docker

set -e  # Salir si hay algún error

# Configuración por defecto
SERVER="${DEPLOY_SERVER:-209.38.78.227}"
USER="${DEPLOY_USER:-root}"
SSH_KEY="${DEPLOY_SSH_KEY:-}"
ENV_FILE="${DEPLOY_ENV_FILE:-/opt/crowdify/.env}"
APP_DIR="${DEPLOY_APP_DIR:-/opt/crowdify}"
SKIP_BUILD=false

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parsear argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        --server)
            SERVER="$2"
            shift 2
            ;;
        --user)
            USER="$2"
            shift 2
            ;;
        --key)
            SSH_KEY="$2"
            shift 2
            ;;
        --env)
            ENV_FILE="$2"
            shift 2
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --help)
            echo "Uso: $0 [opciones]"
            echo ""
            echo "Opciones:"
            echo "  --server SERVER    IP o hostname del servidor (default: 209.38.78.227)"
            echo "  --user USER        Usuario SSH (default: root)"
            echo "  --key KEY          Ruta a la clave SSH privada"
            echo "  --env ENV_FILE     Ruta al archivo .env en el servidor (default: /opt/crowdify/.env)"
            echo "  --skip-build       No reconstruir las imágenes Docker"
            echo ""
            echo "Variables de entorno:"
            echo "  DEPLOY_SERVER      IP del servidor"
            echo "  DEPLOY_USER        Usuario SSH"
            echo "  DEPLOY_SSH_KEY     Ruta a la clave SSH"
            echo "  DEPLOY_ENV_FILE    Ruta al archivo .env"
            echo "  DEPLOY_APP_DIR     Directorio de la aplicación en el servidor"
            exit 0
            ;;
        *)
            log_error "Opción desconocida: $1"
            exit 1
            ;;
    esac
done

# Construir comando SSH base
SSH_CMD="ssh"
if [ -n "$SSH_KEY" ]; then
    SSH_CMD="$SSH_CMD -i $SSH_KEY"
fi
SSH_CMD="$SSH_CMD $USER@$SERVER"

# Verificar conexión al servidor
log_info "Verificando conexión al servidor $SERVER..."
if ! $SSH_CMD "echo 'Conexión exitosa'" > /dev/null 2>&1; then
    log_error "No se pudo conectar al servidor $SERVER"
    exit 1
fi
log_info "Conexión establecida ✓"

# Verificar que Docker está instalado
log_info "Verificando Docker en el servidor..."
if ! $SSH_CMD "command -v docker > /dev/null 2>&1"; then
    log_error "Docker no está instalado en el servidor"
    exit 1
fi
log_info "Docker encontrado ✓"

# Verificar que Docker Compose está disponible
log_info "Verificando Docker Compose..."
if ! $SSH_CMD "docker compose version > /dev/null 2>&1"; then
    log_error "Docker Compose no está disponible en el servidor"
    exit 1
fi
log_info "Docker Compose encontrado ✓"

# Crear directorio de la aplicación si no existe
log_info "Verificando directorio de la aplicación: $APP_DIR"
$SSH_CMD "mkdir -p $APP_DIR" || true

# Sincronizar archivos del proyecto (excluyendo node_modules, .git, etc.)
log_info "Sincronizando archivos del proyecto..."
rsync_cmd="rsync -avz --delete"
if [ -n "$SSH_KEY" ]; then
    rsync_cmd="$rsync_cmd -e 'ssh -i $SSH_KEY'"
fi

# Excluir archivos innecesarios
rsync_cmd="$rsync_cmd --exclude='.git'"
rsync_cmd="$rsync_cmd --exclude='__pycache__'"
rsync_cmd="$rsync_cmd --exclude='*.pyc'"
rsync_cmd="$rsync_cmd --exclude='.env'"
rsync_cmd="$rsync_cmd --exclude='.venv'"
rsync_cmd="$rsync_cmd --exclude='node_modules'"
rsync_cmd="$rsync_cmd --exclude='.pytest_cache'"
rsync_cmd="$rsync_cmd --exclude='*.log'"

# Ejecutar rsync
eval "$rsync_cmd ./ $USER@$SERVER:$APP_DIR/"
log_info "Archivos sincronizados ✓"

# Verificar que existe el archivo .env
log_info "Verificando archivo .env..."
if ! $SSH_CMD "test -f $ENV_FILE"; then
    log_warn "El archivo .env no existe en $ENV_FILE"
    log_warn "Por favor, crea el archivo .env en el servidor antes de continuar"
    log_warn "Puedes usar el archivo .env.example como referencia"
    exit 1
fi
log_info "Archivo .env encontrado ✓"

# Construir imágenes Docker si no se omite
if [ "$SKIP_BUILD" = false ]; then
    log_info "Construyendo imágenes Docker..."
    $SSH_CMD "cd $APP_DIR && docker compose -f docker-compose.prod.yml build --no-cache"
    log_info "Imágenes construidas ✓"
else
    log_warn "Omitiendo construcción de imágenes (--skip-build)"
fi

# Migraciones ahora se manejan directamente en Supabase
# No se requieren migraciones de Alembic

# Detener servicios existentes
log_info "Deteniendo servicios existentes..."
$SSH_CMD "cd $APP_DIR && docker compose -f docker-compose.prod.yml down" || true

# Levantar servicios
log_info "Levantando servicios..."
$SSH_CMD "cd $APP_DIR && docker compose -f docker-compose.prod.yml up -d"

# Esperar a que los servicios estén listos
log_info "Esperando a que los servicios estén listos..."
sleep 10

# Verificar health de los servicios
log_info "Verificando health de los servicios..."
if $SSH_CMD "curl -f http://localhost:8000/health > /dev/null 2>&1"; then
    log_info "Backend API: ✓ Saludable"
else
    log_warn "Backend API: ⚠ No responde aún (puede estar iniciando)"
fi

if $SSH_CMD "curl -f http://localhost:9002/health > /dev/null 2>&1"; then
    log_info "PDF Service: ✓ Saludable"
else
    log_warn "PDF Service: ⚠ No responde aún (puede estar iniciando)"
fi

# Mostrar estado de los contenedores
log_info "Estado de los contenedores:"
$SSH_CMD "cd $APP_DIR && docker compose -f docker-compose.prod.yml ps"

log_info ""
log_info "${GREEN}✓ Deploy completado exitosamente${NC}"
log_info "Servidor: $SERVER"
log_info "API disponible en: http://$SERVER:8000"
log_info "PDF Service disponible en: http://$SERVER:9002"
log_info ""
log_info "Para ver los logs:"
log_info "  ssh $USER@$SERVER 'cd $APP_DIR && docker compose -f docker-compose.prod.yml logs -f'"

