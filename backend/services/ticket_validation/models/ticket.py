"""Modelos Pydantic para validación de tickets"""
from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class TicketValidationRequest(BaseModel):
    qr_signature: str
    inspector_id: str
    event_id: Optional[str] = None


class TicketValidationResponse(BaseModel):
    valid: bool
    ticket_id: Optional[str] = None
    event_id: Optional[str] = None
    attendee_name: Optional[str] = None
    message: Optional[str] = None

