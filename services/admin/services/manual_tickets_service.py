"""Servicio para crear tickets manualmente (admin)"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Optional
from datetime import datetime
import uuid

from shared.database.models import (
    Order, OrderItem, Ticket, Event, TicketType, EventService,
    OrderServiceItem, OrderCommission
)
from services.ticket_purchase.services.inventory_service import InventoryService
from shared.utils.qr_generator import generate_qr_signature


class ManualTicketsService:
    """Servicio para crear tickets manualmente desde el admin"""

    def __init__(self):
        self.inventory_service = InventoryService()

    async def create_manual_tickets(
        self,
        db: AsyncSession,
        event_id: str,
        buyer: Dict,
        quantity: int,
        services: Optional[list] = None,
        notes: Optional[str] = None
    ) -> Dict:
        """
        Crear tickets manualmente para pagos realizados fuera del sistema
        
        Args:
            db: Sesión de base de datos
            event_id: ID del evento
            buyer: Diccionario con datos del comprador (first_name, last_name, email, document_type, document_number)
            quantity: Cantidad de tickets a crear
            services: Lista opcional de servicios adicionales [{"service_id": str, "quantity": int}]
            notes: Notas opcionales sobre el pago
        
        Returns:
            Dict con order_id y tickets_created
        """
        # Verificar que el evento existe
        stmt_event = select(Event).where(Event.id == event_id)
        result_event = await db.execute(stmt_event)
        event = result_event.scalar_one_or_none()

        if not event:
            raise ValueError("Evento no encontrado")

        # Verificar capacidad disponible
        available, message = await self.inventory_service.check_capacity(
            db, event_id, quantity
        )
        if not available:
            raise ValueError(message)

        # Obtener tipo de ticket (ticket general para adultos)
        stmt_ticket_type = select(TicketType).where(
            TicketType.event_id == event_id,
            TicketType.is_child == False
        ).limit(1)
        result_ticket_type = await db.execute(stmt_ticket_type)
        ticket_type = result_ticket_type.scalar_one_or_none()

        if not ticket_type:
            raise ValueError("No se encontró tipo de ticket para el evento")

        # Calcular precios
        tickets_subtotal = float(ticket_type.price) * quantity

        # Calcular precios de servicios adicionales
        services_subtotal = 0.0
        if services:
            service_ids = [uuid.UUID(s["service_id"]) for s in services if s.get("quantity", 0) > 0]
            
            if service_ids:
                stmt_services = select(EventService).where(
                    EventService.event_id == event_id,
                    EventService.id.in_(service_ids)
                )
                result_services = await db.execute(stmt_services)
                event_services = result_services.scalars().all()

                for service in event_services:
                    service_request = next((s for s in services if str(service.id) == s["service_id"]), None)
                    if service_request:
                        service_quantity = service_request.get("quantity", 0)
                        if service_quantity > 0:
                            services_subtotal += float(service.price) * service_quantity

        # Calcular comisiones (1500 CLP por ticket)
        COMMISSION_PER_TICKET = 1500.0
        commission_total = quantity * COMMISSION_PER_TICKET

        discount_total = 0.0
        total = tickets_subtotal + services_subtotal + commission_total - discount_total

        # Crear orden con estado "completed" (ya pagada)
        order = Order(
            id=uuid.uuid4(),
            user_id=None,  # Puede ser None para pagos manuales
            subtotal=tickets_subtotal + services_subtotal,
            discount_total=discount_total,
            total=total,
            commission_total=commission_total,
            currency="CLP",
            status="completed",  # Ya está pagada
            payment_provider="manual",  # Indicar que es manual
            receipt_url=None,
            paid_at=datetime.utcnow(),  # Marcar como pagada ahora
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(order)
        await db.flush()

        # Reservar capacidad
        reserved = await self.inventory_service.reserve_capacity(
            db, event_id, quantity, f"manual_order_{order.id}"
        )

        if not reserved:
            await db.rollback()
            raise ValueError("No se pudo reservar capacidad")

        try:
            # Crear order item para tickets
            order_item = OrderItem(
                id=uuid.uuid4(),
                order_id=order.id,
                event_id=event_id,
                ticket_type_id=ticket_type.id,
                quantity=quantity,
                unit_price=ticket_type.price,
                final_price=tickets_subtotal
            )
            db.add(order_item)
            await db.flush()

            # Crear order service items para servicios adicionales
            if services:
                for service_request in services:
                    if service_request.get("quantity", 0) > 0:
                        service_id = uuid.UUID(service_request["service_id"])
                        
                        # Obtener el servicio
                        stmt_service = select(EventService).where(EventService.id == service_id)
                        result_service = await db.execute(stmt_service)
                        service = result_service.scalar_one_or_none()
                        
                        if service:
                            service_quantity = service_request["quantity"]
                            service_item = OrderServiceItem(
                                id=uuid.uuid4(),
                                order_id=order.id,
                                event_id=event_id,
                                service_id=service.id,
                                quantity=service_quantity,
                                unit_price=service.price,
                                final_price=float(service.price) * service_quantity
                            )
                            db.add(service_item)

            await db.flush()

            # Crear tickets con estado "issued"
            tickets_created = []
            for i in range(quantity):
                ticket_id = uuid.uuid4()
                qr_signature = generate_qr_signature(str(ticket_id))

                ticket = Ticket(
                    id=ticket_id,
                    order_item_id=order_item.id,
                    event_id=event_id,
                    holder_first_name=buyer["first_name"],
                    holder_last_name=buyer.get("last_name", ""),
                    holder_email=buyer.get("email", "").lower().strip() if buyer.get("email") else None,
                    holder_document_type=buyer.get("document_type") or "RUT",  # Por defecto RUT
                    holder_document_number=buyer.get("document_number") or None,
                    is_child=False,  # Por ahora solo adultos
                    qr_signature=qr_signature,
                    status="issued",  # Ya emitidos
                    issued_at=datetime.utcnow()
                )
                db.add(ticket)
                await db.flush()

                # Crear registro de comisión
                commission = OrderCommission(
                    id=uuid.uuid4(),
                    order_id=order.id,
                    ticket_id=ticket.id,
                    ticket_type="adult",
                    commission_amount=COMMISSION_PER_TICKET
                )
                db.add(commission)

                tickets_created.append(ticket)

            await db.commit()
            await db.refresh(order)

            return {
                "order_id": str(order.id),
                "tickets_created": len(tickets_created)
            }

        except Exception as e:
            # Si algo falla, liberar capacidad y hacer rollback
            await self.inventory_service.release_capacity(
                db, event_id, quantity, "manual_ticket_creation_failed"
            )
            await db.rollback()
            raise ValueError(f"Error al crear tickets: {str(e)}")

