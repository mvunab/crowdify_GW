"""Servicio de validación de tickets"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from shared.database.models import Ticket, Event
from shared.cache.redis_client import cache_get, cache_set, cache_delete
import json


class TicketValidationService:
    """Servicio para validar tickets mediante QR"""
    
    @staticmethod
    async def validate_ticket(
        db: AsyncSession,
        qr_signature: str,
        inspector_id: str,
        event_id: Optional[str] = None
    ) -> dict:
        """
        Validar ticket por QR signature
        
        Returns:
            dict con valid, ticket_id, event_id, attendee_name, message
        """
        # Verificar cache primero
        cache_key = f"ticket:validation:{qr_signature}"
        cached = await cache_get(cache_key)
        if cached:
            return cached
        
        # Buscar ticket por QR signature
        stmt = select(Ticket).where(Ticket.qr_signature == qr_signature)
        result = await db.execute(stmt)
        ticket = result.scalar_one_or_none()
        
        if not ticket:
            response = {
                "valid": False,
                "message": "Ticket no encontrado"
            }
            await cache_set(cache_key, response, expire=300)  # Cache por 5 min
            return response
        
        # Verificar que el ticket no esté usado
        if ticket.status == "used":
            response = {
                "valid": False,
                "ticket_id": str(ticket.id),
                "event_id": str(ticket.event_id),
                "message": "Ticket ya utilizado"
            }
            await cache_set(cache_key, response, expire=300)
            return response
        
        # Verificar que el ticket esté en estado issued
        if ticket.status != "issued":
            response = {
                "valid": False,
                "ticket_id": str(ticket.id),
                "event_id": str(ticket.event_id),
                "message": f"Ticket en estado inválido: {ticket.status}"
            }
            await cache_set(cache_key, response, expire=300)
            return response
        
        # Verificar evento si se proporciona
        if event_id and str(ticket.event_id) != event_id:
            response = {
                "valid": False,
                "ticket_id": str(ticket.id),
                "event_id": str(ticket.event_id),
                "message": "Ticket no corresponde a este evento"
            }
            await cache_set(cache_key, response, expire=300)
            return response
        
        # Verificar que el evento existe y esté activo
        stmt_event = select(Event).where(Event.id == ticket.event_id)
        result_event = await db.execute(stmt_event)
        event = result_event.scalar_one_or_none()
        
        if not event:
            response = {
                "valid": False,
                "ticket_id": str(ticket.id),
                "event_id": str(ticket.event_id),
                "message": "Evento no encontrado"
            }
            await cache_set(cache_key, response, expire=300)
            return response
        
        # Ticket válido
        attendee_name = f"{ticket.holder_first_name} {ticket.holder_last_name}"
        
        response = {
            "valid": True,
            "ticket_id": str(ticket.id),
            "event_id": str(ticket.event_id),
            "attendee_name": attendee_name
        }
        
        # Cache solo por 1 min para tickets válidos (para permitir re-validación)
        await cache_set(cache_key, response, expire=60)
        
        return response
    
    @staticmethod
    async def mark_ticket_as_used(
        db: AsyncSession,
        ticket_id: str
    ) -> bool:
        """Marcar ticket como usado"""
        from datetime import datetime
        
        stmt = select(Ticket).where(Ticket.id == ticket_id)
        result = await db.execute(stmt)
        ticket = result.scalar_one_or_none()
        
        if not ticket:
            return False
        
        ticket.status = "used"
        ticket.used_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(ticket)
        
        # Invalidar cache
        if ticket.qr_signature:
            cache_key = f"ticket:validation:{ticket.qr_signature}"
            await cache_delete(cache_key)
        
        return True
    
    @staticmethod
    async def get_ticket_by_id(
        db: AsyncSession,
        ticket_id: str
    ) -> Optional[Ticket]:
        """Obtener ticket por ID"""
        stmt = select(Ticket).where(Ticket.id == ticket_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

