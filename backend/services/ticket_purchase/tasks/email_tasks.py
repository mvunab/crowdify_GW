"""Tareas asíncronas para envío de emails"""
from typing import Dict
from shared.cache.celery_app import celery_app
from services.notifications.services.email_service import EmailService


@celery_app.task(name="send_ticket_email")
def send_ticket_email_task(order_id: str, ticket_data: Dict):
    """Tarea Celery para enviar email con tickets"""
    service = EmailService()
    
    # TODO: Implementar lógica de envío
    # Por ahora solo log
    print(f"Enviando email para orden {order_id}")
    return {"status": "queued", "order_id": order_id}

