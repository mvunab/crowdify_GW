"""Servicio para cálculo de estadísticas del dashboard"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, Dict
from uuid import UUID
from datetime import datetime

from shared.database.models import Event, Ticket, Order, OrderItem


class StatsService:
    """Servicio para operaciones de estadísticas"""

    async def get_dashboard_stats(
        self,
        db: AsyncSession,
        organizer_id: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict:
        """
        Obtener estadísticas del dashboard para un organizador

        Args:
            db: Sesión de base de datos
            organizer_id: ID del organizador
            date_from: Fecha desde (opcional)
            date_to: Fecha hasta (opcional)

        Returns:
            Dict con estadísticas
        """
        try:
            organizer_id_uuid = UUID(organizer_id)
        except ValueError:
            raise ValueError("ID de organizador inválido")

        # Total de eventos
        stmt_total_events = select(func.count(Event.id)).where(
            Event.organizer_id == organizer_id_uuid
        )

        if date_from:
            stmt_total_events = stmt_total_events.where(Event.starts_at >= date_from)
        if date_to:
            stmt_total_events = stmt_total_events.where(Event.starts_at <= date_to)

        result_total = await db.execute(stmt_total_events)
        total_events = result_total.scalar() or 0

        # Eventos activos (starts_at >= NOW)
        stmt_active_events = select(func.count(Event.id)).where(
            and_(
                Event.organizer_id == organizer_id_uuid,
                Event.starts_at >= datetime.utcnow()
            )
        )

        if date_from:
            stmt_active_events = stmt_active_events.where(Event.starts_at >= date_from)
        if date_to:
            stmt_active_events = stmt_active_events.where(Event.starts_at <= date_to)

        result_active = await db.execute(stmt_active_events)
        active_events = result_active.scalar() or 0

        # Total de tickets vendidos
        # JOIN tickets -> order_items -> events
        stmt_tickets_sold = (
            select(func.count(Ticket.id))
            .join(OrderItem, Ticket.order_item_id == OrderItem.id)
            .join(Event, OrderItem.event_id == Event.id)
            .where(
                and_(
                    Event.organizer_id == organizer_id_uuid,
                    Ticket.status.in_(["issued", "validated", "used"])
                )
            )
        )

        if date_from:
            stmt_tickets_sold = stmt_tickets_sold.where(Event.starts_at >= date_from)
        if date_to:
            stmt_tickets_sold = stmt_tickets_sold.where(Event.starts_at <= date_to)

        result_tickets = await db.execute(stmt_tickets_sold)
        total_tickets_sold = result_tickets.scalar() or 0

        # Total de ingresos
        # JOIN orders -> order_items -> events
        stmt_revenue = (
            select(func.sum(Order.total))
            .join(OrderItem, Order.id == OrderItem.order_id)
            .join(Event, OrderItem.event_id == Event.id)
            .where(
                and_(
                    Event.organizer_id == organizer_id_uuid,
                    Order.status == "completed"
                )
            )
        )

        if date_from:
            stmt_revenue = stmt_revenue.where(Event.starts_at >= date_from)
        if date_to:
            stmt_revenue = stmt_revenue.where(Event.starts_at <= date_to)

        result_revenue = await db.execute(stmt_revenue)
        total_revenue = result_revenue.scalar() or 0.0

        return {
            "total_events": total_events,
            "active_events": active_events,
            "total_tickets_sold": total_tickets_sold,
            "total_revenue": float(total_revenue),
            "currency": "CLP",
            "period": {
                "from_date": date_from,
                "to_date": date_to
            }
        }
