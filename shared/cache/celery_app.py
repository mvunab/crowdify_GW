"""
Configuración de Celery para tareas asíncronas
Optimizado para alta concurrencia (80+ usuarios simultáneos)
"""
from celery import Celery
from kombu import Queue, Exchange
import os
import logging

logger = logging.getLogger(__name__)

# Configuración de Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_MAX_CONNECTIONS = int(os.getenv("CELERY_REDIS_MAX_CONNECTIONS", "50"))

# Crear aplicación Celery
celery_app = Celery(
    "crowdify",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "services.ticket_purchase.tasks.email_tasks",
    ]
)

# Definir colas con prioridades
default_exchange = Exchange("default", type="direct")
priority_exchange = Exchange("priority", type="direct")

# Colas separadas para diferentes tipos de tareas
celery_app.conf.task_queues = (
    # Cola de alta prioridad para webhooks y confirmaciones de pago
    Queue("high_priority", priority_exchange, routing_key="high"),
    # Cola default para emails y operaciones normales
    Queue("default", default_exchange, routing_key="default"),
    # Cola de baja prioridad para reportes y operaciones batch
    Queue("low_priority", default_exchange, routing_key="low"),
)

# Routing de tareas a colas específicas
celery_app.conf.task_routes = {
    "process_order_post_payment": {"queue": "high_priority"},
    "verify_payment_status": {"queue": "high_priority"},
    "send_ticket_email": {"queue": "default"},
    "send_bulk_ticket_emails": {"queue": "default"},
    "generate_ticket_qr": {"queue": "low_priority"},
}

# Configuración optimizada para alta concurrencia
celery_app.conf.update(
    # Serialización
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Tracking
    task_track_started=True,

    # Límites de tiempo (más cortos para evitar workers colgados)
    task_time_limit=10 * 60,  # 10 minutos máximo por tarea
    task_soft_time_limit=8 * 60,  # 8 minutos soft limit

    # ========== OPTIMIZACIÓN PARA ALTA CONCURRENCIA ==========

    # Prefetch: cuántas tareas toma un worker antes de procesarlas
    # Bajo prefetch = mejor distribución de carga entre workers
    worker_prefetch_multiplier=1,  # Solo 1 tarea por worker a la vez

    # Configuración del pool de conexiones a Redis
    broker_pool_limit=REDIS_MAX_CONNECTIONS,
    redis_max_connections=REDIS_MAX_CONNECTIONS,

    # Reintentos de conexión al broker
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,

    # Heartbeat para detectar workers muertos
    broker_heartbeat=30,

    # ACK late: confirmar tarea solo cuando termina (previene pérdida de tareas)
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Resultados
    result_expires=3600,  # Resultados expiran en 1 hora
    result_extended=True,  # Guardar metadata adicional

    # Evitar que un worker monopolice tareas
    worker_concurrency=4,  # 4 tareas concurrentes por worker

    # Reiniciar worker después de N tareas (previene memory leaks)
    worker_max_tasks_per_child=1000,

    # Límite de memoria por worker (en KB)
    worker_max_memory_per_child=256000,  # 256MB

    # Default queue
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",

    # Compresión para tareas grandes
    task_compression="gzip",
    result_compression="gzip",

    # Rate limits globales por tarea (protección contra flooding)
    task_annotations={
        "send_ticket_email": {"rate_limit": "30/m"},  # 30 emails por minuto
        "send_bulk_ticket_emails": {"rate_limit": "10/m"},  # 10 bulk ops por minuto
        "generate_ticket_qr": {"rate_limit": "100/m"},  # 100 QRs por minuto
    },
)

logger.info(
    "Celery configurado - Broker: %s, Pool limit: %d, Concurrency: %d",
    REDIS_URL.split("@")[-1] if "@" in REDIS_URL else REDIS_URL,
    REDIS_MAX_CONNECTIONS,
    celery_app.conf.worker_concurrency
)

