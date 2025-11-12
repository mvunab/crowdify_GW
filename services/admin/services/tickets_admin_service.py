"""Servicio para gestión de tickets (admin)"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict
from uuid import UUID

from shared.database.models import (
    Ticket, Event, OrderItem, Order, User,
    TicketChildDetail, TicketChildMedication
)


class TicketsAdminService:
    """Servicio para operaciones de tickets para admin"""

    async def get_event_tickets(
        self,
        db: AsyncSession,
        event_id: str,
        status: Optional[str] = None,
        is_child: Optional[bool] = None,
        include_child_details: bool = True,
        search: Optional[str] = None
    ) -> Dict:
        """
        Obtener todos los tickets de un evento con detalles completos

        Args:
            db: Sesión de base de datos
            event_id: ID del evento
            status: Filtrar por estado (opcional)
            is_child: Filtrar por tipo (opcional)
            include_child_details: Incluir detalles de niños
            search: Buscar por nombre o documento

        Returns:
            Dict con event, tickets y summary
        """
        try:
            event_id_uuid = UUID(event_id)
        except ValueError:
            raise ValueError("ID de evento inválido")

        # Obtener evento
        stmt_event = select(Event).where(Event.id == event_id_uuid)
        result_event = await db.execute(stmt_event)
        event = result_event.scalar_one_or_none()

        if not event:
            raise ValueError("Evento no encontrado")

        # Query base con joins
        stmt = (
            select(Ticket)
            .options(
                selectinload(Ticket.order_item).selectinload(OrderItem.order).selectinload(Order.user),
                selectinload(Ticket.child_details).selectinload(TicketChildDetail.medications)
            )
            .where(Ticket.event_id == event_id_uuid)
        )

        # Aplicar filtros
        if status:
            stmt = stmt.where(Ticket.status == status)

        if is_child is not None:
            stmt = stmt.where(Ticket.is_child == is_child)

        # Búsqueda por nombre o documento
        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Ticket.holder_first_name.ilike(search_term),
                    Ticket.holder_last_name.ilike(search_term),
                    Ticket.holder_document_number.ilike(search_term)
                )
            )

        # Ordenar por fecha de emisión
        stmt = stmt.order_by(Ticket.issued_at.desc())

        result = await db.execute(stmt)
        tickets = result.scalars().all()

        # Calcular summary
        stmt_summary_total = select(func.count(Ticket.id)).where(
            Ticket.event_id == event_id_uuid
        )
        result_summary_total = await db.execute(stmt_summary_total)
        total = result_summary_total.scalar() or 0

        stmt_summary_adults = select(func.count(Ticket.id)).where(
            and_(
                Ticket.event_id == event_id_uuid,
                Ticket.is_child == False
            )
        )
        result_summary_adults = await db.execute(stmt_summary_adults)
        adults = result_summary_adults.scalar() or 0

        stmt_summary_children = select(func.count(Ticket.id)).where(
            and_(
                Ticket.event_id == event_id_uuid,
                Ticket.is_child == True
            )
        )
        result_summary_children = await db.execute(stmt_summary_children)
        children = result_summary_children.scalar() or 0

        # Count by status
        by_status = {}
        for ticket_status in ["issued", "validated", "used", "cancelled"]:
            stmt_status = select(func.count(Ticket.id)).where(
                and_(
                    Ticket.event_id == event_id_uuid,
                    Ticket.status == ticket_status
                )
            )
            result_status = await db.execute(stmt_status)
            by_status[ticket_status] = result_status.scalar() or 0

        return {
            "event": event,
            "tickets": tickets,
            "summary": {
                "total": total,
                "adults": adults,
                "children": children,
                "by_status": by_status
            }
        }

    async def export_children_tickets(
        self,
        db: AsyncSession,
        event_id: str
    ) -> Dict:
        """
        Exportar datos de niños de un evento

        Args:
            db: Sesión de base de datos
            event_id: ID del evento

        Returns:
            Dict con event y children data
        """
        try:
            event_id_uuid = UUID(event_id)
        except ValueError:
            raise ValueError("ID de evento inválido")

        # Obtener evento
        stmt_event = select(Event).where(Event.id == event_id_uuid)
        result_event = await db.execute(stmt_event)
        event = result_event.scalar_one_or_none()

        if not event:
            raise ValueError("Evento no encontrado")

        # Obtener tickets de niños con todos los detalles
        stmt = (
            select(Ticket)
            .options(
                selectinload(Ticket.child_details).selectinload(TicketChildDetail.medications),
                selectinload(Ticket.order_item).selectinload(OrderItem.order).selectinload(Order.user)
            )
            .where(
                and_(
                    Ticket.event_id == event_id_uuid,
                    Ticket.is_child == True
                )
            )
            .order_by(Ticket.issued_at.asc())
        )

        result = await db.execute(stmt)
        tickets = result.scalars().all()

        return {
            "event": event,
            "tickets": tickets
        }
