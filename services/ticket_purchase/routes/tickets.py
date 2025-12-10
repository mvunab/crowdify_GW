"""Rutas adicionales para tickets de usuario"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Dict, Optional
from io import BytesIO
import uuid
import httpx
import os
from shared.database.session import get_db
from shared.auth.dependencies import get_current_user
from shared.database.models import Ticket, Order, OrderItem, Event, TicketType


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
    # Nota: user_id puede ser None ahora, pero para este endpoint siempre debe haber user_id
    stmt = (
        select(Ticket, Event)
        .join(OrderItem, Ticket.order_item_id == OrderItem.id)
        .join(Order, OrderItem.order_id == Order.id)
        .join(Event, Ticket.event_id == Event.id)
        .where(Order.user_id == uuid.UUID(user_id))
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


@router.get("/email/{email}")
async def get_tickets_by_email(
    email: str,
    db: AsyncSession = Depends(get_db)
):
    '''
    Obtener tickets por email (endpoint público - no requiere autenticación)
    
    Busca tickets donde holder_email coincida exactamente con el email proporcionado.
    Normaliza el email (lowercase, trim) antes de buscar.
    
    Compatible con: ticketsService.getTicketsByEmail()
    '''
    # Normalizar email
    normalized_email = email.lower().strip()
    
    if not normalized_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email es requerido"
        )
    
    # Validar formato básico de email
    if "@" not in normalized_email or "." not in normalized_email.split("@")[1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de email inválido"
        )
    
    # Buscar tickets por email (case-insensitive) incluyendo TicketType para obtener el precio
    stmt = (
        select(Ticket, Event, OrderItem, TicketType)
        .join(OrderItem, Ticket.order_item_id == OrderItem.id)
        .join(Event, Ticket.event_id == Event.id)
        .join(TicketType, OrderItem.ticket_type_id == TicketType.id)
        .where(func.lower(func.trim(Ticket.holder_email)) == normalized_email)
        .order_by(Ticket.created_at.desc())
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    if not rows:
        return []
    
    # Formatear respuesta con datos del evento y precio del ticket_type
    return [
        {
            'id': str(ticket.id),
            'order_item_id': str(ticket.order_item_id),
            'eventId': str(ticket.event_id),
            'id_evento': str(ticket.event_id),  # Compatibilidad
            'holder_first_name': ticket.holder_first_name,
            'holder_last_name': ticket.holder_last_name,
            'holder_email': ticket.holder_email,
            'attendeeName': f'{ticket.holder_first_name} {ticket.holder_last_name}',
            'attendeeEmail': ticket.holder_email,
            'holder_document_type': ticket.holder_document_type,
            'holder_document_number': ticket.holder_document_number,
            'is_child': ticket.is_child,
            'qr_signature': ticket.qr_signature,
            'qrCode': ticket.qr_signature,  # Compatibilidad
            'codigo_qr': ticket.qr_signature,  # Compatibilidad
            'status': ticket.status,
            'estado': map_ticket_status(ticket.status),  # Frontend usa 'estado'
            'issued_at': ticket.issued_at.isoformat() if ticket.issued_at else None,
            'validated_at': ticket.validated_at.isoformat() if ticket.validated_at else None,
            'used_at': ticket.used_at.isoformat() if ticket.used_at else None,
            'purchaseDate': ticket.issued_at.isoformat() if ticket.issued_at else None,
            'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
            'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None,
            # Datos del evento embebidos con precio del ticket_type
            'event': {
                'id': str(event.id),
                'title': event.name,
                'nombre': event.name,  # Compatibilidad
                'name': event.name,
                'location': event.location_text,
                'location_text': event.location_text,
                'lugar': event.location_text,  # Compatibilidad
                'date': event.starts_at.isoformat() if event.starts_at else None,
                'time': event.starts_at.strftime('%H:%M') if event.starts_at else None,
                'starts_at': event.starts_at.isoformat() if event.starts_at else None,
                'ends_at': event.ends_at.isoformat() if event.ends_at else None,
                'image_url': event.image_url,
            'category': event.category,
            'capacity_total': event.capacity_total,
            'allow_children': event.allow_children,
            'price': float(ticket_type.price) if ticket_type else None  # Precio del ticket_type
        }
    }
    for ticket, event, order_item, ticket_type in rows
]


@router.get("/orders/{order_id}")
async def get_tickets_by_order(
    order_id: str,
    db: AsyncSession = Depends(get_db)
):
    '''
    Obtener tickets filtrados por order_id (optimizado)
    
    Más eficiente que obtener todos los tickets por email y filtrar.
    Query directa en BD con join optimizado.
    
    Compatible con: ticketsService.getTicketsByOrderId()
    '''
    from uuid import UUID
    
    try:
        # Validar que order_id es un UUID válido
        order_uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="order_id inválido"
        )
    
    # Query optimizada: filtrar directamente en BD con join incluyendo TicketType para obtener el precio
    stmt = (
        select(Ticket, Event, OrderItem, TicketType)
        .join(OrderItem, Ticket.order_item_id == OrderItem.id)
        .join(Order, OrderItem.order_id == Order.id)
        .join(Event, Ticket.event_id == Event.id)
        .join(TicketType, OrderItem.ticket_type_id == TicketType.id)
        .where(Order.id == order_uuid)
        .where(Ticket.status == "issued")  # Solo tickets emitidos
        .order_by(Ticket.created_at.desc())  # Más recientes primero
    )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    if not rows:
        return []
    
    # Formatear respuesta con datos del evento y precio del ticket_type
    return [
        {
            'id': str(ticket.id),
            'order_item_id': str(ticket.order_item_id),
            'order_id': order_id,  # Incluir order_id explícitamente
            'eventId': str(ticket.event_id),
            'id_evento': str(ticket.event_id),  # Compatibilidad
            'holder_first_name': ticket.holder_first_name,
            'holder_last_name': ticket.holder_last_name,
            'holder_email': ticket.holder_email,
            'attendeeName': f'{ticket.holder_first_name} {ticket.holder_last_name}',
            'attendeeEmail': ticket.holder_email,
            'holder_document_type': ticket.holder_document_type,
            'holder_document_number': ticket.holder_document_number,
            'is_child': ticket.is_child,
            'qr_signature': ticket.qr_signature,
            'qrCode': ticket.qr_signature,  # Compatibilidad
            'codigo_qr': ticket.qr_signature,  # Compatibilidad
            'status': ticket.status,
            'estado': map_ticket_status(ticket.status),  # Frontend usa 'estado'
            'issued_at': ticket.issued_at.isoformat() if ticket.issued_at else None,
            'validated_at': ticket.validated_at.isoformat() if ticket.validated_at else None,
            'used_at': ticket.used_at.isoformat() if ticket.used_at else None,
            'purchaseDate': ticket.issued_at.isoformat() if ticket.issued_at else None,
            'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
            'createdAt': ticket.created_at.isoformat() if ticket.created_at else None,  # Alias para frontend
            'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None,
            # Datos del evento embebidos con precio del ticket_type
            'event': {
                'id': str(event.id),
                'title': event.name,
                'nombre': event.name,  # Compatibilidad
                'name': event.name,
                'location': event.location_text,
                'location_text': event.location_text,
                'lugar': event.location_text,  # Compatibilidad
                'date': event.starts_at.isoformat() if event.starts_at else None,
                'time': event.starts_at.strftime('%H:%M') if event.starts_at else None,
                'starts_at': event.starts_at.isoformat() if event.starts_at else None,
                'ends_at': event.ends_at.isoformat() if event.ends_at else None,
                'image_url': event.image_url,
                'category': event.category,
                'capacity_total': event.capacity_total,
                'allow_children': event.allow_children,
                'price': float(ticket_type.price) if ticket_type else None  # Precio del ticket_type
            }
        }
        for ticket, event, order_item, ticket_type in rows
    ]


@router.get("/{ticket_id}/pdf")
async def download_ticket_pdf(
    ticket_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Descarga el PDF de un ticket
    
    - Si existe pdf_object_key, descargar de MinIO (futuro)
    - Si no existe, generar PDF on-demand llamando a pdfsvc
    - Opcionalmente guardar en MinIO y actualizar pdf_object_key (futuro)
    """
    from uuid import UUID
    
    try:
        # Validar que ticket_id es un UUID válido
        ticket_uuid = UUID(ticket_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ticket_id inválido"
        )
    
    # Obtener ticket con evento de la BD
    stmt = (
        select(Ticket, Event)
        .join(Event, Ticket.event_id == Event.id)
        .where(Ticket.id == ticket_uuid)
    )
    
    result = await db.execute(stmt)
    row = result.first()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket no encontrado"
        )
    
    ticket, event = row
    
    # TODO: Si tiene pdf_object_key, descargar de MinIO
    # Por ahora, siempre generar on-demand
    
    # Preparar datos para el servicio de PDF
    pdfsvc_url = os.getenv("PDFSVC_URL", "http://pdfsvc:9002")
    
    ticket_data = {
        "ticket_id": str(ticket.id),
        "qr_signature": ticket.qr_signature,
        "holder_first_name": ticket.holder_first_name,
        "holder_last_name": ticket.holder_last_name,
        "holder_email": ticket.holder_email,
        "issued_at": ticket.issued_at.isoformat() if ticket.issued_at else None,
        "event": {
            "name": event.name,
            "title": event.name,
            "nombre": event.name,
            "starts_at": event.starts_at.isoformat() if event.starts_at else None,
            "ends_at": event.ends_at.isoformat() if event.ends_at else None,
            "date": event.starts_at.isoformat() if event.starts_at else None,
            "time": event.starts_at.strftime('%H:%M') if event.starts_at else None,
            "location_text": event.location_text,
            "location": event.location_text,
            "lugar": event.location_text,
            "image_url": event.image_url,
            "category": event.category,
        }
    }
    
    try:
        # Llamar al servicio de PDF
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{pdfsvc_url}/tickets/pdf",
                json=ticket_data
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error generando PDF"
                )
            
            # Retornar PDF como streaming response
            return StreamingResponse(
                BytesIO(response.content),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=ticket-{ticket_id}.pdf"
                }
            )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Timeout generando PDF"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando PDF: {str(e)}"
        )