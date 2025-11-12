"""Rutas adicionales para tickets de usuario"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Dict
from shared.database.session import get_db
from shared.auth.dependencies import get_current_user
from shared.database.models import Ticket, Order, OrderItem, Event


router = APIRouter()


def map_ticket_status(status: str) -> str:
    '''Mapear status del backend al formato del frontend'''
    status_map = {
        'issued': 'comprado',
        'validated': 'validado',
        'used': 'usado',
        'cancelled': 'cancelado',
        'revoked': 'cancelado'
    }
    return status_map.get(status, status)


@router.get("/user/{user_id}")
async def get_user_tickets(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    '''
    Obtener tickets de un usuario con datos del evento incluidos
    
    Compatible con: ticketsService.getUserTickets()
    Optimizado con una sola query usando JOINs
    '''
    # Verificar que el usuario solo puede ver sus propios tickets
    if current_user.get('user_id') != user_id:
        if current_user.get('role') not in ['admin', 'coordinator']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='No puedes ver tickets de otros usuarios'
            )

    # OPTIMIZACION: Una sola query con JOINs y eager loading
    stmt = (
        select(Ticket, Event)
        .join(OrderItem, Ticket.order_item_id == OrderItem.id)
        .join(Order, OrderItem.order_id == Order.id)
        .join(Event, Ticket.event_id == Event.id)
        .where(Order.user_id == user_id)
        .order_by(Ticket.created_at.desc())
    )
    
    result = await db.execute(stmt)
    rows = result.all()

    # Formatear respuesta con datos del evento
    return [
        {
            'id': str(ticket.id),
            'eventId': str(ticket.event_id),
            'id_evento': str(ticket.event_id),  # Compatibilidad
            'holder_first_name': ticket.holder_first_name,
            'holder_last_name': ticket.holder_last_name,
            'attendeeName': f'{ticket.holder_first_name} {ticket.holder_last_name}',
            'holder_document_type': ticket.holder_document_type,
            'holder_document_number': ticket.holder_document_number,
            'is_child': ticket.is_child,
            'qr_signature': ticket.qr_signature,
            'qr_code': ticket.qr_signature,  # Compatibilidad
            'status': ticket.status,
            'estado': map_ticket_status(ticket.status),  # Frontend usa 'estado'
            'issued_at': ticket.issued_at.isoformat() if ticket.issued_at else None,
            'used_at': ticket.used_at.isoformat() if ticket.used_at else None,
            'purchaseDate': ticket.issued_at.isoformat() if ticket.issued_at else None,
            # Datos del evento embebidos
            'event': {
                'id': str(event.id),
                'title': event.name,
                'nombre': event.name,  # Compatibilidad
                'location': event.location_text,
                'date': event.starts_at.isoformat() if event.starts_at else None,
                'time': event.starts_at.strftime('%H:%M') if event.starts_at else None,
                'capacity_total': event.capacity_total,
                'allow_children': event.allow_children
            }
        }
        for ticket, event in rows
    ]
