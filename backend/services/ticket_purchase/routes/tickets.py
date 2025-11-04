"""Rutas adicionales para tickets de usuario"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict
from shared.database.session import get_db
from shared.auth.dependencies import get_current_user
from shared.database.models import Ticket, Order, OrderItem


router = APIRouter()


@router.get("/user/{user_id}")
async def get_user_tickets(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """
    Obtener tickets de un usuario
    
    Compatible con: ticketsService.getUserTickets()
    """
    # Verificar que el usuario solo puede ver sus propios tickets
    if current_user.get("user_id") != user_id:
        if current_user.get("role") not in ["admin", "coordinator"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes ver tickets de otros usuarios"
            )
    
    # Buscar órdenes del usuario
    stmt_orders = select(Order).where(Order.user_id == user_id)
    result_orders = await db.execute(stmt_orders)
    orders = result_orders.scalars().all()
    
    order_ids = [order.id for order in orders]
    
    if not order_ids:
        return []
    
    # Buscar order items de las órdenes
    stmt_items = select(OrderItem).where(OrderItem.order_id.in_(order_ids))
    result_items = await db.execute(stmt_items)
    items = result_items.scalars().all()
    
    item_ids = [item.id for item in items]
    
    if not item_ids:
        return []
    
    # Buscar tickets de los order items
    stmt_tickets = select(Ticket).where(Ticket.order_item_id.in_(item_ids))
    result_tickets = await db.execute(stmt_tickets)
    tickets = result_tickets.scalars().all()
    
    # Formatear respuesta
    return [
        {
            "id": str(ticket.id),
            "event_id": str(ticket.event_id),
            "holder_first_name": ticket.holder_first_name,
            "holder_last_name": ticket.holder_last_name,
            "holder_document_type": ticket.holder_document_type,
            "holder_document_number": ticket.holder_document_number,
            "is_child": ticket.is_child,
            "qr_signature": ticket.qr_signature,
            "status": ticket.status,
            "issued_at": ticket.issued_at.isoformat() if ticket.issued_at else None,
            "used_at": ticket.used_at.isoformat() if ticket.used_at else None
        }
        for ticket in tickets
    ]

