import os
from celery import Celery

celery_app = Celery(
    __name__,
    broker=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://redis:6379/0")
)

@celery_app.task
def generate_and_store_ticket_pdf(ticket_id: str):
    # TODO: call pdfsvc to generate PDF, then upload to MinIO
    return {"ticket_id": ticket_id, "status": "queued"}
