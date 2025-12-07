"""Servicio para gestión de órdenes pendientes (admin)"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from shared.database.models import (
    Order, OrderItem, Ticket, User, Event
)


class AdminOrdersService:
    """Servicio para operaciones de órdenes pendientes para admin"""

    async def get_pending_orders(
        self,
        db: AsyncSession
    ) -> List[Dict]:
        """
        Obtener todas las órdenes pendientes con método de pago bank_transfer

        Returns:
            Lista de órdenes con información del usuario y conteo de tickets
        """
        # Query: órdenes pendientes de transferencia bancaria
        stmt = (
            select(Order)
            .options(selectinload(Order.user))
            .where(
                and_(
                    Order.status == "pending",
                    Order.payment_provider.in_(["bank_transfer", "stripe"])
                )
            )
            .order_by(Order.created_at.desc())
        )

        result = await db.execute(stmt)
        orders = result.scalars().all()

        # Para cada orden, obtener conteo de tickets
        orders_data = []
        for order in orders:
            # Obtener order_items de esta orden
            order_items_stmt = select(OrderItem.id).where(OrderItem.order_id == order.id)
            order_items_result = await db.execute(order_items_stmt)
            order_item_ids = [item_id for (item_id,) in order_items_result.all()]

            # Contar tickets
            tickets_count = 0
            if order_item_ids:
                tickets_stmt = (
                    select(func.count(Ticket.id))
                    .where(Ticket.order_item_id.in_(order_item_ids))
                )
                tickets_result = await db.execute(tickets_stmt)
                tickets_count = tickets_result.scalar() or 0

            # Información del usuario
            user_email = None
            user_name = None
            if order.user:
                user_email = order.user.email
                first_name = order.user.first_name or ""
                last_name = order.user.last_name or ""
                user_name = f"{first_name} {last_name}".strip() if first_name or last_name else user_email

            orders_data.append({
                "id": str(order.id),
                "user_id": str(order.user_id) if order.user_id else None,
                "user_email": user_email,
                "user_name": user_name,
                "subtotal": float(order.subtotal),
                "discount_total": float(order.discount_total),
                "total": float(order.total),
                "commission_total": float(order.commission_total) if order.commission_total else 0.0,
                "currency": order.currency or "CLP",
                "status": order.status,
                "payment_provider": order.payment_provider,
                "payment_reference": order.payment_reference,
                "receipt_url": order.receipt_url,
                "created_at": order.created_at,
                "updated_at": order.updated_at,
                "paid_at": order.paid_at,
                "tickets_count": tickets_count
            })

        return orders_data

    async def get_order_detail(
        self,
        db: AsyncSession,
        order_id: str
    ) -> Optional[Dict]:
        """
        Obtener detalle completo de una orden con todos sus tickets

        Returns:
            Orden con información del usuario y lista de tickets
        """
        try:
            order_uuid = UUID(order_id)
        except ValueError:
            return None

        # Obtener orden con usuario
        stmt = (
            select(Order)
            .options(selectinload(Order.user))
            .where(Order.id == order_uuid)
        )

        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            return None

        # Obtener order_items
        order_items_stmt = (
            select(OrderItem)
            .where(OrderItem.order_id == order.id)
        )
        order_items_result = await db.execute(order_items_stmt)
        order_items = order_items_result.scalars().all()
        order_item_ids = [item.id for item in order_items]

        # Obtener tickets con eventos
        tickets_data = []
        if order_item_ids:
            tickets_stmt = (
                select(Ticket, Event)
                .join(Event, Ticket.event_id == Event.id)
                .where(Ticket.order_item_id.in_(order_item_ids))
                .order_by(Ticket.created_at.asc())
            )
            tickets_result = await db.execute(tickets_stmt)
            tickets_rows = tickets_result.all()

            for ticket, event in tickets_rows:
                tickets_data.append({
                    "id": str(ticket.id),
                    "holder_first_name": ticket.holder_first_name or "",  # Asegurar que no sea None
                    "holder_last_name": ticket.holder_last_name or "",  # Asegurar que no sea None
                    "holder_email": ticket.holder_email,
                    "status": ticket.status,
                    "event_id": str(ticket.event_id),
                    "event_name": event.name if event else None
                })

        # Información del usuario
        user_email = None
        user_name = None
        if order.user:
            user_email = order.user.email
            first_name = order.user.first_name or ""
            last_name = order.user.last_name or ""
            user_name = f"{first_name} {last_name}".strip() if first_name or last_name else user_email

        return {
            "id": str(order.id),
            "user_id": str(order.user_id) if order.user_id else None,
            "user_email": user_email,
            "user_name": user_name,
            "subtotal": float(order.subtotal),
            "discount_total": float(order.discount_total),
            "total": float(order.total),
            "commission_total": float(order.commission_total) if order.commission_total else 0.0,
            "currency": order.currency or "CLP",
            "status": order.status,
            "payment_provider": order.payment_provider,
            "payment_reference": order.payment_reference,
            "receipt_url": order.receipt_url,
            "created_at": order.created_at,
            "updated_at": order.updated_at or order.created_at,  # Fallback a created_at si updated_at es None
            "paid_at": order.paid_at,
            "tickets_count": len(tickets_data),
            "tickets": tickets_data
        }

    async def confirm_order(
        self,
        db: AsyncSession,
        order_id: str
    ) -> Optional[Dict]:
        """
        Confirmar una orden pendiente usando stored procedure

        Returns:
            Orden actualizada o None si falla
        """
        try:
            order_uuid = UUID(order_id)
        except ValueError:
            return None

        # Verificar que la orden existe y está pendiente
        stmt = select(Order).where(
            and_(
                Order.id == order_uuid,
                Order.status == "pending"
            )
        )
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            return None

        # Llamar a la función stored procedure para confirmar la orden
        # Esto garantiza transacciones atómicas
        try:
            # Ejecutar la función stored procedure
            # La función retorna JSON y maneja la transacción internamente
            # Usar CAST en lugar de :: para evitar problemas de sintaxis con parámetros
            proc_result = await db.execute(
                text("SELECT confirm_pending_order(CAST(:order_uuid AS uuid))"),
                {"order_uuid": str(order_uuid)}
            )
            result_data = proc_result.scalar()
            
            # La función retorna un dict de Python directamente desde PostgreSQL
            # Verificar que la función retornó éxito
            if isinstance(result_data, dict):
                if not result_data.get('success', False):
                    raise ValueError(f"La función stored procedure no retornó éxito: {result_data}")
            elif isinstance(result_data, str):
                # Si viene como string JSON, parsearlo
                import json
                result_data = json.loads(result_data)
                if not result_data.get('success', False):
                    raise ValueError(f"La función stored procedure no retornó éxito: {result_data}")

            # Commit de la transacción (la función ya hizo los cambios, solo confirmamos)
            await db.commit()

            # Retornar los datos actualizados (hacer nueva query para obtener datos frescos)
            order_detail = await self.get_order_detail(db, order_id)
            
            if not order_detail:
                raise ValueError("No se pudieron obtener los detalles de la orden actualizada")
                
            return order_detail

        except Exception as e:
            await db.rollback()
            error_msg = str(e)
            # Log del error para debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error confirming order {order_id}: {error_msg}", exc_info=True)
            raise ValueError(f"Error al confirmar orden: {error_msg}")

