"""Rutas de validación de tickets"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict
from shared.database.session import get_db
from shared.auth.dependencies import get_current_scanner
from services.ticket_validation.models.ticket import (
    TicketValidationRequest,
    TicketValidationResponse
)
from services.ticket_validation.services.ticket_service import TicketValidationService


router = APIRouter()


@router.post("/validate", response_model=TicketValidationResponse)
async def validate_ticket(
    request: TicketValidationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_scanner)
):
    """
    Validar ticket mediante QR signature
    
    Requiere autenticación de scanner/admin/coordinator
    """
    service = TicketValidationService()
    
    result = await service.validate_ticket(
        db=db,
        qr_signature=request.qr_signature,
        inspector_id=request.inspector_id,
        event_id=request.event_id
    )
    
    return TicketValidationResponse(**result)


@router.get("/{ticket_id}")
async def get_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_scanner)
):
    """
    Obtener información de un ticket por ID
    
    Compatible con: ticketsService.getTicketById()
    """
    service = TicketValidationService()
    ticket = await service.get_ticket_by_id(db, ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket no encontrado"
        )
    
    return {
        "id": str(ticket.id),
        "event_id": str(ticket.event_id),
        "holder_first_name": ticket.holder_first_name,
        "holder_last_name": ticket.holder_last_name,
        "holder_document_type": ticket.holder_document_type,
        "holder_document_number": ticket.holder_document_number,
        "is_child": ticket.is_child,
        "status": ticket.status,
        "issued_at": ticket.issued_at.isoformat() if ticket.issued_at else None,
        "used_at": ticket.used_at.isoformat() if ticket.used_at else None
    }

