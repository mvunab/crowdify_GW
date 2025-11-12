"""Servicio para gestión de eventos con estadísticas (admin)"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict
from uuid import UUID
from datetime import datetime

from shared.database.models import (
    Event, Ticket, Order, OrderItem, Organizer,
    TicketType, EventService, OrderServiceItem
)


class AdminEventsService:
    """Servicio para operaciones de eventos con estadísticas para admin"""

    async def get_events_with_stats(
        self,
        db: AsyncSession,
        organizer_id: str,
        status: str = "all",
        sort: str = "starts_at_desc"
    ) -> List[Dict]:
        """
        Obtener eventos del organizador con estadísticas

        Args:
            db: Sesión de base de datos
            organizer_id: ID del organizador
            status: Filtro de estado (upcoming, ongoing, past, all)
            sort: Ordenamiento (starts_at_asc, starts_at_desc, revenue_desc)

        Returns:
            Lista de eventos con estadísticas
        """
        try:
            organizer_id_uuid = UUID(organizer_id)
        except ValueError:
            raise ValueError("ID de organizador inválido")

        # Query base: eventos con ticket_types y organizer
        stmt = (
            select(Event)
            .options(
                selectinload(Event.ticket_types),
                selectinload(Event.organizer),
                selectinload(Event.event_services)
            )
            .where(Event.organizer_id == organizer_id_uuid)
        )

        # Filtrar por estado
        now = datetime.utcnow()
        if status == "upcoming":
            stmt = stmt.where(Event.starts_at > now)
        elif status == "ongoing":
            stmt = stmt.where(
                and_(
                    Event.starts_at <= now,
                    Event.ends_at >= now
                )
            )
        elif status == "past":
            stmt = stmt.where(Event.ends_at < now)

        # Ordenamiento
        if sort == "starts_at_asc":
            stmt = stmt.order_by(Event.starts_at.asc())
        elif sort == "starts_at_desc":
            stmt = stmt.order_by(Event.starts_at.desc())
        # revenue_desc requiere calcular revenue primero, se ordena después

        result = await db.execute(stmt)
        events = result.scalars().all()

        # Para cada evento, calcular estadísticas
        events_with_stats = []
        for event in events:
            # Calcular tickets vendidos
            stmt_tickets = (
                select(func.count(Ticket.id))
                .where(
                    and_(
                        Ticket.event_id == event.id,
                        Ticket.status.in_(["issued", "validated", "used"])
                    )
                )
            )
            result_tickets = await db.execute(stmt_tickets)
            tickets_sold = result_tickets.scalar() or 0

            # Calcular revenue (suma de unit_price * quantity de order_items completados)
            stmt_revenue = (
                select(func.sum(OrderItem.unit_price * OrderItem.quantity))
                .join(Order, OrderItem.order_id == Order.id)
                .where(
                    and_(
                        OrderItem.event_id == event.id,
                        Order.status == "completed"
                    )
                )
            )
            result_revenue = await db.execute(stmt_revenue)
            revenue = result_revenue.scalar() or 0.0
            # Calcular stats de servicios
            services_stats = []
            for service in event.event_services:
                # Calcular vendidos
                stmt_sold = (
                    select(func.sum(OrderServiceItem.quantity))
                    .join(Order, OrderServiceItem.order_id == Order.id)
                    .where(
                        and_(
                            OrderServiceItem.service_id == service.id,
                            Order.status == "completed"
                        )
                    )
                )
                result_sold = await db.execute(stmt_sold)
                sold = result_sold.scalar() or 0

                services_stats.append({
                    "id": str(service.id),
                    "name": service.name,
                    "service_type": service.service_type,
                    "stock": service.stock,
                    "sold": sold,
                    "remaining": service.stock - sold
                })

            # Calcular porcentaje de ventas
            sales_percentage = 0
            if event.capacity_total > 0:
                sales_percentage = (tickets_sold / event.capacity_total) * 100

            events_with_stats.append({
                "event": event,
                "stats": {
                    "tickets_sold": tickets_sold,
                    "tickets_remaining": event.capacity_available,
                    "revenue": float(revenue),
                    "sales_percentage": round(sales_percentage, 2),
                    "services_stats": services_stats
                }
            })

        # Ordenar por revenue si se especificó
        if sort == "revenue_desc":
            events_with_stats.sort(
                key=lambda x: x["stats"]["revenue"],
                reverse=True
            )

        return events_with_stats
