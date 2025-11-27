# 🚀 Guía de Inicio Rápido - Crowdify Backend

## Opción 1: Inicio con Docker Compose (Recomendado)

### Paso 1: Verificar requisitos
```bash
# Verificar que Docker está instalado
docker --version
docker compose version
```

### Paso 2: Configurar variables de entorno (Opcional)
El proyecto tiene valores por defecto, pero puedes crear un `.env` si necesitas personalizar:

**Opción A: Generar .env automáticamente**
```bash
python3 scripts/generate_env.py
```

**Opción B: Crear .env manualmente**
```bash
# Crear archivo .env (opcional, los valores por defecto funcionan)
touch .env
```

Variables importantes (opcionales):
- `DATABASE_URL`: Si quieres usar Supabase en lugar de PostgreSQL local
- `JWT_SECRET`: Clave secreta para JWT (por defecto: "dev-secret")
- `QR_SECRET`: Clave para QR codes (por defecto: "dev-qr")
- `SUPABASE_URL` y `SUPABASE_ANON_KEY`: Si usas Supabase Auth

### Paso 3: Iniciar servicios
```bash
# Construir e iniciar todos los servicios
docker compose up -d --build

# O usando Makefile
make up
```

Esto iniciará:
- ✅ PostgreSQL (puerto 5432)
- ✅ Redis (puerto 6379)
- ✅ MinIO (puertos 9000, 9001)
- ✅ Mailhog (puerto 8025)
- ✅ Backend API (puerto 8000)
- ✅ Celery Worker
- ✅ PDF Service (puerto 9002)

### Paso 4: Ejecutar migraciones de base de datos
```bash
# Aplicar migraciones con Alembic
docker compose exec backend poetry run alembic -c app/alembic/alembic.ini upgrade head

# O usando Makefile
make migrate
```

### Paso 5: Verificar que todo funciona
```bash
# Verificar health check
curl http://localhost:8000/health

# Verificar ready check (conexiones a DB y Redis)
curl http://localhost:8000/ready

# O usando Makefile
make health
```

### Paso 6: Ver logs (opcional)
```bash
# Ver todos los logs
docker compose logs -f

# Ver solo backend
docker compose logs -f backend

# O usando Makefile
make logs
make logs-backend
```

---

## Opción 2: Desarrollo Local (sin Docker)

### Paso 1: Instalar Poetry
```bash
# macOS/Linux
curl -sSL https://install.python-poetry.org | python3 -

# O con pip
pip install poetry
```

### Paso 2: Instalar dependencias
```bash
poetry install
```

### Paso 3: Activar entorno virtual
```bash
poetry shell
```

### Paso 4: Configurar variables de entorno
```bash
# Crear .env con las variables necesarias
cp .env.example .env  # Si existe
# O editar .env manualmente
```

Variables mínimas necesarias:
```env
DATABASE_URL=postgresql+psycopg://tickets:tickets@localhost:5432/tickets
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=dev-secret
QR_SECRET=dev-qr
```

### Paso 5: Iniciar servicios externos
Necesitas tener corriendo:
- PostgreSQL en puerto 5432
- Redis en puerto 6379

O usar Docker solo para estos servicios:
```bash
docker compose up -d db redis minio mailhog
```

### Paso 6: Ejecutar migraciones
```bash
poetry run alembic -c app/alembic/alembic.ini upgrade head
```

### Paso 7: Iniciar servidor
```bash
# Backend API
poetry run uvicorn main:app --reload --port 8000

# En otra terminal: Celery Worker
poetry run celery -A app.worker:celery_app worker -l INFO
```

---

## Comandos Útiles (Makefile)

```bash
make help          # Ver todos los comandos disponibles
make up            # Levantar servicios
make down          # Detener servicios
make build         # Reconstruir imágenes
make logs          # Ver logs
make shell         # Abrir shell en backend
make migrate       # Aplicar migraciones
make health        # Verificar health checks
make ps            # Ver estado de servicios
make restart       # Reiniciar servicios
```

---

## Verificar que todo funciona

### 1. Health Check
```bash
curl http://localhost:8000/health
# Debe responder: {"status":"ok","service":"crodify-api"}
```

### 2. Ready Check
```bash
curl http://localhost:8000/ready
# Debe responder: {"status":"ready","database":"connected","redis":"connected"}
```

### 3. Documentación API
Abre en el navegador:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 4. Servicios auxiliares
- Mailhog UI: http://localhost:8025
- MinIO Console: http://localhost:9001 (usuario: minio, password: minio12345)
- PDF Service: http://localhost:9002/health

---

## Solución de Problemas

### Error: Puerto ya en uso
```bash
# Ver qué está usando el puerto
lsof -i :8000

# Cambiar puerto en docker-compose.yml o detener el proceso
```

### Error: No se puede conectar a la base de datos
```bash
# Verificar que PostgreSQL está corriendo
docker compose ps

# Ver logs de la base de datos
docker compose logs db

# Reiniciar servicios
docker compose restart db backend
```

### Error: Migraciones fallan
```bash
# Verificar que la base de datos existe
docker compose exec db psql -U tickets -d tickets -c "\dt"

# Recrear base de datos (CUIDADO: borra datos)
docker compose down -v
docker compose up -d db
# Esperar 5 segundos
docker compose exec backend poetry run alembic -c app/alembic/alembic.ini upgrade head
```

### Error: Poetry lock desactualizado
```bash
make poetry-lock
```

---

## Próximos Pasos

1. ✅ Backend corriendo en http://localhost:8000
2. 📖 Revisar documentación API en http://localhost:8000/docs
3. 🔐 Configurar autenticación (Supabase o JWT)
4. 💳 Configurar Mercado Pago (opcional para desarrollo)
5. 📧 Configurar email service (opcional, Mailhog funciona para desarrollo)

---

## Estructura de Puertos

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| Backend API | 8000 | API principal |
| PostgreSQL | 5432 | Base de datos |
| Redis | 6379 | Cache y broker |
| MinIO | 9000 | Almacenamiento |
| MinIO Console | 9001 | Interfaz web |
| Mailhog | 8025 | SMTP de desarrollo |
| PDF Service | 9002 | Servicio de PDFs |

