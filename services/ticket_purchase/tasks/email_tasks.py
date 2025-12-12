"""Tareas asíncronas para envío de emails y generación de tickets"""
from typing import Dict, List, Optional
import logging
import asyncio
from shared.cache.celery_app import celery_app

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper para ejecutar coroutines en contexto síncrono de Celery"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    name="send_ticket_email",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 3},
)
def send_ticket_email_task(self, email: str, attendee_name: str, event_name: str,
                           event_date: str, event_location: str, ticket_id: str,
                           qr_signature: Optional[str] = None):
    """
    Tarea Celery para enviar email con ticket individual

    Incluye retry automático con backoff exponencial
    """
    from services.notifications.services.email_service import EmailService

    try:
        logger.info(f"[CELERY] Enviando email de ticket a {email} para evento {event_name}")

        service = EmailService()

        # EmailService.send_ticket_email es async, lo ejecutamos con run_async
        async def send_email():
            return await service.send_ticket_email(
                to_email=email,
                attendee_name=attendee_name,
                event_name=event_name,
                event_date=event_date,
                event_location=event_location,
                ticket_id=ticket_id,
                qr_signature=qr_signature
            )

        success = run_async(send_email())

        if success:
            logger.info(f"[CELERY] Email enviado exitosamente a {email}")
            return {"status": "sent", "email": email, "ticket_id": ticket_id}
        else:
            logger.error(f"[CELERY] Error enviando email a {email}")
            raise Exception(f"Error enviando email a {email}")

    except Exception as e:
        logger.error(f"[CELERY] Error en send_ticket_email_task: {e}", exc_info=True)
        raise


@celery_app.task(
    name="send_bulk_ticket_emails",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def send_bulk_ticket_emails_task(self, order_id: str, tickets_data: List[Dict]):
    """
    Tarea Celery para enviar múltiples emails de tickets de una orden

    Args:
        order_id: ID de la orden
        tickets_data: Lista de dicts con datos de cada ticket:
            - email: str
            - attendee_name: str
            - event_name: str
            - event_date: str
            - event_location: str
            - ticket_id: str
            - qr_signature: str
    """
    logger.info(f"[CELERY] Procesando {len(tickets_data)} emails para orden {order_id}")

    results = []
    for ticket in tickets_data:
        try:
            # Encolar cada email como subtarea
            result = send_ticket_email_task.delay(
                email=ticket["email"],
                attendee_name=ticket["attendee_name"],
                event_name=ticket["event_name"],
                event_date=ticket["event_date"],
                event_location=ticket["event_location"],
                ticket_id=ticket["ticket_id"],
                qr_signature=ticket.get("qr_signature")
            )
            results.append({"ticket_id": ticket["ticket_id"], "task_id": result.id})
        except Exception as e:
            logger.error(f"[CELERY] Error encolando email para ticket {ticket.get('ticket_id')}: {e}")
            results.append({"ticket_id": ticket.get("ticket_id"), "error": str(e)})

    return {"order_id": order_id, "emails_queued": len(results), "results": results}


@celery_app.task(
    name="generate_tickets_background",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def generate_tickets_background_task(self, order_id: str, attendees_data: List[Dict]):
    """
    Tarea Celery para generar tickets en background después del pago

    Esta tarea:
    1. Obtiene la orden de la DB
    2. Genera los tickets
    3. Envía los emails
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from shared.database.models import Order
    from sqlalchemy import select
    import os

    logger.info(f"[CELERY] Generando tickets en background para orden {order_id}")

    async def generate():
        # Crear conexión a DB
        database_url = os.getenv("DATABASE_URL", "postgresql://crodify:crodify@localhost:5432/crodify")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif database_url.startswith("postgresql+psycopg://"):
            database_url = database_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)

        engine = create_async_engine(database_url, pool_size=2, max_overflow=2)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        try:
            async with async_session() as db:
                # Obtener orden
                stmt = select(Order).where(Order.id == order_id)
                result = await db.execute(stmt)
                order = result.scalar_one_or_none()

                if not order:
                    raise Exception(f"Orden {order_id} no encontrada")

                # Importar PurchaseService para generar tickets
                from services.ticket_purchase.services.purchase_service import PurchaseService
                service = PurchaseService()

                tickets = await service._generate_tickets(db, order, attendees_data, ticket_status="issued")

                logger.info(f"[CELERY] {len(tickets)} tickets generados para orden {order_id}")
                return {"order_id": order_id, "tickets_generated": len(tickets)}

        finally:
            await engine.dispose()

    return run_async(generate())

