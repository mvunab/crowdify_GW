# Crodify Backend API

Backend FastAPI para la plataforma de venta de tickets para eventos con validación QR.

## Estructura del Proyecto

```
backend/
├── services/              # Servicios modulares
│   ├── ticket_validation/   # Validación de tickets QR
│   ├── ticket_purchase/      # Compra de tickets y pagos
│   ├── event_management/     # Gestión de eventos
│   └── notifications/       # Envío de emails y notificaciones
├── shared/                # Componentes compartidos
│   ├── database/            # Modelos y conexión DB
│   ├── auth/                # Autenticación JWT
│   ├── cache/               # Redis y cache
│   └── utils/               # Utilidades (rate limiting, circuit breaker, retry)
├── main.py                 # API Gateway principal
├── requirements.txt        # Dependencias Python
├── Dockerfile             # Imagen Docker
├── docker-compose.yml     # Orquestación de servicios
└── .env.example           # Variables de entorno de ejemplo
```

## Requisitos Previos

- Python 3.11+
- Docker y Docker Compose
- PostgreSQL 15+
- Redis 7+

## Instalación y Configuración

### 1. Clonar y configurar entorno

```bash
cd backend

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus credenciales
```

Variables importantes:
- `DATABASE_URL`: URL de conexión a PostgreSQL
- `REDIS_URL`: URL de conexión a Redis
- `JWT_SECRET_KEY`: Clave secreta para JWT (cambiar en producción)
- `MERCADOPAGO_ACCESS_TOKEN`: Token de acceso de Mercado Pago
- `EMAIL_API_KEY`: API key de SendGrid

### 3. Iniciar con Docker Compose

```bash
docker-compose up -d --build
```

Esto iniciará:
- PostgreSQL en puerto 5432
- Redis en puerto 6379
- RabbitMQ en puertos 5672 y 15672
- Backend API en puerto 8000
- Celery worker para tareas asíncronas

### 4. Ejecutar migraciones (si usas Alembic)

```bash
docker-compose exec backend alembic upgrade head
```

### 5. Iniciar servidor (desarrollo local)

```bash
uvicorn main:app --reload --port 8000
```

## Endpoints Principales

### Health Checks
- `GET /health` - Health check básico
- `GET /ready` - Verifica conexiones a DB y Redis

### Eventos
- `GET /api/v1/events` - Listar eventos (público)
- `GET /api/v1/events/{event_id}` - Obtener evento por ID (público)
- `POST /api/v1/events` - Crear evento (requiere admin)
- `PUT /api/v1/events/{event_id}` - Actualizar evento (requiere admin)
- `DELETE /api/v1/events/{event_id}` - Eliminar evento (requiere admin)

### Tickets
- `GET /api/v1/tickets/user/{user_id}` - Obtener tickets de usuario
- `GET /api/v1/tickets/{ticket_id}` - Obtener ticket por ID
- `POST /api/v1/tickets/validate` - Validar ticket QR (requiere scanner)

### Compras
- `POST /api/v1/purchases` - Crear orden de compra
- `POST /api/v1/purchases/webhook` - Webhook de Mercado Pago
- `GET /api/v1/purchases/{order_id}/status` - Estado de orden

### Notificaciones
- `POST /api/v1/notifications/test-email` - Probar envío de email (requiere admin)

## Autenticación

La API usa JWT tokens. Para obtener un token:

1. El frontend debe autenticarse con Supabase Auth (durante migración)
2. Usar el token JWT en el header: `Authorization: Bearer <token>`

Roles disponibles:
- `user`: Usuario normal
- `admin`: Administrador
- `scanner`: Validador de tickets
- `coordinator`: Coordinador de eventos

## Desarrollo

### Estructura de Servicios

Cada servicio sigue esta estructura:
```
service_name/
├── __init__.py
├── main.py              # Entry point del servicio (opcional)
├── routes/              # Endpoints FastAPI
│   ├── __init__.py
│   └── routes.py
├── services/            # Lógica de negocio
│   ├── __init__.py
│   └── service.py
└── models/             # Modelos Pydantic
    ├── __init__.py
    └── models.py
```

### Base de Datos

Los modelos están en `shared/database/models.py` usando SQLAlchemy 2.0 con async.

Para crear nuevas migraciones:
```bash
alembic revision --autogenerate -m "descripción"
alembic upgrade head
```

### Cache y Locks Distribuidos

Redis se usa para:
- Cache de validaciones de tickets
- Locks distribuidos para reserva de capacidad
- Cache general de la aplicación

Ejemplo de uso:
```python
from shared.cache.redis_client import cache_get, cache_set, DistributedLock

# Cache
await cache_set("key", {"data": "value"}, expire=3600)
data = await cache_get("key")

# Lock distribuido
async with DistributedLock("resource:123"):
    # Operación crítica
    pass
```

## Testing

```bash
pytest
```

## Producción

### Variables de Entorno Importantes

- `APP_ENV=production`
- `APP_DEBUG=False`
- `LOG_LEVEL=INFO`
- `JWT_SECRET_KEY`: Debe ser una clave segura y aleatoria
- `DATABASE_POOL_SIZE`: Ajustar según carga
- `CORS_ORIGINS`: Solo dominios permitidos

### Deploy

1. Construir imagen:
```bash
docker build -t crodify-backend .
```

2. Ejecutar con docker-compose o Kubernetes

3. Configurar reverse proxy (nginx/traefik) para HTTPS

## Migración desde Supabase

El backend está diseñado para convivir con Supabase durante la migración:

1. **Fase 1**: Frontend sigue usando Supabase, backend lee/escribe a Supabase
2. **Fase 2**: Backend migra datos a PostgreSQL propio
3. **Fase 3**: Frontend migra endpoints gradualmente

Usar variables de entorno para alternar:
- `USE_SUPABASE=true` (temporal)
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`

## Documentación API

La documentación interactiva está disponible en:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Troubleshooting

### Error de conexión a DB
- Verificar que PostgreSQL esté corriendo
- Verificar `DATABASE_URL` en `.env`
- Verificar que el usuario tenga permisos

### Error de conexión a Redis
- Verificar que Redis esté corriendo
- Verificar `REDIS_URL` en `.env`

### Error de autenticación
- Verificar `JWT_SECRET_KEY` en `.env`
- Verificar que el token sea válido y no haya expirado

## Licencia

Propietario - Crodify

