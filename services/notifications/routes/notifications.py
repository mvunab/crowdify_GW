"""Rutas de notificaciones"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict
from shared.database.session import get_db
from shared.auth.dependencies import get_current_admin
from services.notifications.services.email_service import EmailService


router = APIRouter()


@router.post("/test-email")
async def test_email(
    to_email: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_admin)
):
    """
    Endpoint de prueba para enviar emails
    
    Requiere: admin role
    """
    service = EmailService()
    
    success = await service.send_email(
        to_email=to_email,
        subject="Test Email from Crodify",
        html_content="<p>Este es un email de prueba.</p>"
    )
    
    if success:
        return {"status": "sent", "message": f"Email enviado a {to_email}"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error enviando email"
        )

