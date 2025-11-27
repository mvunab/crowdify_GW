# Guía de Deploy - Crowdify GW

Esta guía explica cómo desplegar `crowdify_GW` en el servidor de producción.

## Requisitos Previos

### En el servidor (209.38.78.227)

1. **Docker y Docker Compose** instalados
   ```bash
   # Verificar instalación
   docker --version
   docker compose version
   ```

2. **Acceso SSH** configurado
   - Clave SSH configurada
   - Usuario con permisos para ejecutar Docker

3. **Puertos disponibles**
   - 8000: API Backend
   - 9000: MinIO
   - 9001: MinIO Console
   - 9002: PDF Service
   - 6379: Redis

### En tu máquina local

1. **rsync** instalado (generalmente viene preinstalado en macOS/Linux)
2. **SSH** configurado con acceso al servidor
3. **Archivo .env** preparado con las variables de producción

## Configuración Inicial

### 1. Preparar archivo .env en el servidor

Crea un archivo `.env` en el servidor con las variables de entorno necesarias. Puedes usar como referencia el siguiente template:

```bash
# Database
DATABASE_URL=postgresql+psycopg://user:password@host:5432/database

# Redis
REDIS_URL=redis://redis:6379/0

# MinIO Object Storage
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=minio
MINIO_SECRET_KEY=tu-password-seguro-aqui
MINIO_SECURE=false
MINIO_BUCKET_TICKETS=tickets-pdf
MINIO_ROOT_USER=minio
MINIO_ROOT_PASSWORD=tu-password-seguro-aqui

# Security
JWT_SECRET=tu-jwt-secret-super-seguro-aqui
QR_SECRET=tu-qr-secret-super-seguro-aqui

# SMTP Configuration
SMTP_HOST=smtp.tu-proveedor.com
SMTP_PORT=587
SMTP_USER=tu-email@ejemplo.com
SMTP_PASSWORD=tu-password-email
SMTP_FROM=noreply@ejemplo.com

# Supabase (opcional)
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_ANON_KEY=tu-supabase-anon-key

# CORS
CORS_ORIGINS=https://tudominio.com,https://www.tudominio.com

# Application
APP_ENV=production
LOG_LEVEL=INFO

# Ports
API_PORT=8000
PDFSVC_PORT=9002
```

**Importante:** 
- Cambia todos los valores por defecto por valores seguros
- No compartas este archivo públicamente
- El archivo `.env` debe estar en `/opt/crowdify/.env` en el servidor (o ajusta la ruta en el script)

### 2. Configurar acceso SSH

Asegúrate de poder conectarte al servidor sin contraseña:

```bash
# Copiar tu clave SSH al servidor (si no lo has hecho)
ssh-copy-id usuario@209.38.78.227

# O usar una clave específica
ssh -i ~/.ssh/id_rsa usuario@209.38.78.227
```

## Deploy

### Opción 1: Usar el script de deploy (Recomendado)

El script `deploy.sh` automatiza todo el proceso:

```bash
# Hacer el script ejecutable
chmod +x deploy.sh

# Deploy básico (usa valores por defecto)
./deploy.sh

# Deploy con opciones personalizadas
./deploy.sh --server 209.38.78.227 --user root --key ~/.ssh/id_rsa

# Deploy sin reconstruir imágenes (más rápido)
./deploy.sh --skip-build

# Deploy sin ejecutar migraciones
./deploy.sh --skip-migrate
```

**Opciones del script:**
- `--server SERVER`: IP o hostname del servidor (default: 209.38.78.227)
- `--user USER`: Usuario SSH (default: root)
- `--key KEY`: Ruta a la clave SSH privada
- `--env ENV_FILE`: Ruta al archivo .env en el servidor (default: /opt/crowdify/.env)
- `--skip-build`: No reconstruir las imágenes Docker
- `--skip-migrate`: No ejecutar migraciones de base de datos

**Variables de entorno:**
También puedes configurar estas variables de entorno antes de ejecutar el script:
```bash
export DEPLOY_SERVER=209.38.78.227
export DEPLOY_USER=root
export DEPLOY_SSH_KEY=~/.ssh/id_rsa
export DEPLOY_ENV_FILE=/opt/crowdify/.env
export DEPLOY_APP_DIR=/opt/crowdify
```

### Opción 2: Deploy manual

Si prefieres hacer el deploy manualmente:

```bash
# 1. Conectarse al servidor
ssh usuario@209.38.78.227

# 2. Crear directorio de la aplicación
mkdir -p /opt/crowdify
cd /opt/crowdify

# 3. Clonar o copiar el código (si es la primera vez)
# git clone <repo-url> .
# O usar rsync desde tu máquina local:
# rsync -avz --exclude='.git' --exclude='__pycache__' ./ usuario@209.38.78.227:/opt/crowdify/

# 4. Crear archivo .env (si no existe)
nano .env
# Pegar las variables de entorno necesarias

# 5. Construir imágenes
docker compose -f docker-compose.prod.yml build

# 6. Ejecutar migraciones
docker compose -f docker-compose.prod.yml run --rm backend \
  poetry run alembic -c app/alembic/alembic.ini upgrade head

# 7. Levantar servicios
docker compose -f docker-compose.prod.yml up -d

# 8. Verificar que todo está funcionando
docker compose -f docker-compose.prod.yml ps
curl http://localhost:8000/health
```

## Verificación Post-Deploy

### 1. Verificar servicios

```bash
# En el servidor
ssh usuario@209.38.78.227
cd /opt/crowdify
docker compose -f docker-compose.prod.yml ps
```

Todos los servicios deben estar en estado "Up".

### 2. Verificar health endpoints

```bash
# Backend API
curl http://209.38.78.227:8000/health
# Debe responder: {"status":"ok","service":"crodify-api"}

# Ready check (verifica DB y Redis)
curl http://209.38.78.227:8000/ready
# Debe responder: {"status":"ready","database":"connected","redis":"connected"}

# PDF Service
curl http://209.38.78.227:9002/health
```

### 3. Ver logs

```bash
# Todos los servicios
docker compose -f docker-compose.prod.yml logs -f

# Solo backend
docker compose -f docker-compose.prod.yml logs -f backend

# Solo worker
docker compose -f docker-compose.prod.yml logs -f worker
```

## Actualizaciones

Para actualizar la aplicación después del primer deploy:

```bash
# Opción 1: Con el script (recomendado)
./deploy.sh

# Opción 2: Manual
ssh usuario@209.38.78.227
cd /opt/crowdify
# Actualizar código (git pull o rsync)
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml run --rm backend \
  poetry run alembic -c app/alembic/alembic.ini upgrade head
docker compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Los servicios no inician

1. Verificar logs:
   ```bash
   docker compose -f docker-compose.prod.yml logs
   ```

2. Verificar que el archivo .env existe y tiene todas las variables:
   ```bash
   cat /opt/crowdify/.env
   ```

3. Verificar que los puertos no están en uso:
   ```bash
   netstat -tulpn | grep -E '8000|9000|9001|9002|6379'
   ```

### Error de conexión a la base de datos

- Verificar que `DATABASE_URL` en `.env` es correcta
- Verificar que la base de datos está accesible desde el servidor
- Verificar firewall/security groups

### Error de migraciones

```bash
# Ver logs de migración
docker compose -f docker-compose.prod.yml run --rm backend \
  poetry run alembic -c app/alembic/alembic.ini upgrade head

# Si hay errores, puedes revisar el estado actual
docker compose -f docker-compose.prod.yml run --rm backend \
  poetry run alembic -c app/alembic/alembic.ini current
```

### Reiniciar un servicio específico

```bash
docker compose -f docker-compose.prod.yml restart backend
docker compose -f docker-compose.prod.yml restart worker
```

### Detener todos los servicios

```bash
docker compose -f docker-compose.prod.yml down
```

### Limpiar y empezar de nuevo

```bash
# CUIDADO: Esto elimina todos los datos
docker compose -f docker-compose.prod.yml down -v
docker system prune -a -f
```

## Seguridad

1. **Nunca** commitees el archivo `.env` al repositorio
2. Usa contraseñas seguras y únicas para producción
3. Configura un firewall para limitar acceso a los puertos
4. Considera usar HTTPS con un reverse proxy (nginx, traefik)
5. Mantén Docker y las imágenes actualizadas

## Monitoreo

Considera configurar:
- Health checks automáticos
- Logging centralizado
- Alertas para servicios caídos
- Monitoreo de recursos (CPU, memoria, disco)

## Soporte

Para problemas o preguntas sobre el deploy, contacta al equipo de desarrollo.


