"""Servicio principal de compra de tickets"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Optional
from datetime import datetime, date
import uuid
import hashlib
from shared.database.models import (
    Order, OrderItem, Ticket, Event, TicketType, EventService,
    TicketChildDetail, TicketChildMedication, OrderCommission
)
from shared.utils.qr_generator import generate_qr_signature
from services.ticket_purchase.models.purchase import PurchaseRequest, AttendeeData
from services.ticket_purchase.services.inventory_service import InventoryService
from services.ticket_purchase.services.mercado_pago_service import MercadoPagoService
from shared.cache.redis_client import cache_get, cache_set


class PurchaseService:
    """Servicio para procesar compras de tickets"""
    
    def __init__(self):
        self.inventory_service = InventoryService()
        self.mercado_pago_service = MercadoPagoService()
    
    async def create_purchase(
        self,
        db: AsyncSession,
        request: PurchaseRequest
    ) -> Dict:
        """
        Crear orden de compra y generar link de pago
        
        Returns:
            dict con order_id, payment_link, status
        """
        # Verificar idempotencia
        if request.idempotency_key:
            cache_key = f"purchase:idempotency:{request.idempotency_key}"
            cached = await cache_get(cache_key)
            if cached:
                return cached
        
        # Verificar que el evento existe
        stmt_event = select(Event).where(Event.id == request.event_id)
        result_event = await db.execute(stmt_event)
        event = result_event.scalar_one_or_none()
        
        if not event:
            raise ValueError("Evento no encontrado")
        
        # Calcular totales
        total_quantity = len(request.attendees)
        
        # Verificar capacidad
        available, message = await self.inventory_service.check_capacity(
            db, request.event_id, total_quantity
        )
        if not available:
            raise ValueError(message)
        
        # Obtener tipo de ticket (asumimos que hay un tipo por defecto)
        stmt_ticket_type = select(TicketType).where(
            TicketType.event_id == request.event_id,
            TicketType.is_child == False
        ).limit(1)
        result_ticket_type = await db.execute(stmt_ticket_type)
        ticket_type = result_ticket_type.scalar_one_or_none()
        
        if not ticket_type:
            raise ValueError("No se encontró tipo de ticket para el evento")
        
        # Calcular precios
        subtotal = float(ticket_type.price) * total_quantity
        discount_total = 0.0  # TODO: Aplicar descuentos si hay
        total = subtotal - discount_total
        
        # Validar que todos los attendees tengan email
        for attendee in request.attendees:
            if not attendee.email:
                raise ValueError(f"Todos los asistentes deben tener un correo electrónico. Falta email para: {attendee.name}")
        
        # Crear orden - user_id es opcional ahora
        order = Order(
            id=uuid.uuid4(),
            user_id=uuid.UUID(request.user_id) if request.user_id else None,
            subtotal=subtotal,
            discount_total=discount_total,
            total=total,
            currency="CLP",
            status="pending",
            payment_provider="mercadopago",
            idempotency_key=request.idempotency_key or self._generate_idempotency_key(request),
            created_at=datetime.utcnow()
        )
        db.add(order)
        await db.flush()
        
        # Crear order item
        order_item = OrderItem(
            id=uuid.uuid4(),
            order_id=order.id,
            event_id=request.event_id,
            ticket_type_id=ticket_type.id,
            quantity=total_quantity,
            unit_price=ticket_type.price,
            final_price=total
        )
        db.add(order_item)
        await db.flush()
        
        # Guardar attendees en cache para recuperarlos después del pago
        # Esto es necesario porque los attendees no se guardan en la BD hasta que se aprueba el pago
        if request.idempotency_key:
            attendees_cache_key = f"purchase:attendees:{request.idempotency_key}"
            # Convertir a dict serializable para cache
            attendees_data = [
                {
                    "name": att.name,
                    "email": att.email,
                    "document_type": att.document_type,
                    "document_number": att.document_number,
                    "is_child": att.is_child,
                    "child_details": att.child_details.dict() if att.child_details else None
                }
                for att in request.attendees
            ]
            await cache_set(attendees_cache_key, attendees_data, expire=86400)  # 24 horas
        
        # Reservar capacidad
        reserved = await self.inventory_service.reserve_capacity(
            db, request.event_id, total_quantity, f"order_{order.id}"
        )
        
        if not reserved:
            await db.rollback()
            raise ValueError("No se pudo reservar capacidad")
        
        # Crear preferencia de pago
        try:
            preference = self.mercado_pago_service.create_preference(
                order_id=str(order.id),
                title=f"Tickets - {event.name}",
                total_amount=total,
                currency="CLP",
                description=f"{total_quantity} ticket(s) para {event.name}"
            )
            
            order.payment_reference = preference["preference_id"]
            payment_link = preference["payment_link"]
            
        except Exception as e:
            # Si falla la creación de preferencia, liberar capacidad y rollback
            await self.inventory_service.release_capacity(
                db, request.event_id, total_quantity, "payment_creation_failed"
            )
            await db.rollback()
            raise ValueError(f"Error creando preferencia de pago: {str(e)}")
        
        await db.commit()
        await db.refresh(order)
        
        response = {
            "order_id": str(order.id),
            "payment_link": payment_link,
            "status": "pending"
        }
        
        # Guardar en cache para idempotencia
        if request.idempotency_key:
            await cache_set(cache_key, response, expire=3600)
        
        return response
    
    async def process_payment_webhook(
        self,
        db: AsyncSession,
        payment_data: Dict
    ) -> bool:
        """
        Procesar webhook de Mercado Pago
        
        Returns:
            True si se procesó correctamente
        """
        payment_id = payment_data.get("data", {}).get("id")
        if not payment_id:
            return False
        
        # Obtener información del pago
        payment_info = self.mercado_pago_service.verify_payment(payment_id)
        
        external_reference = payment_info.get("external_reference")
        if not external_reference:
            return False
        
        # Buscar orden
        stmt = select(Order).where(Order.id == external_reference)
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()
        
        if not order:
            return False
        
        # Actualizar estado según el pago
        payment_status = payment_info.get("status")
        
        if payment_status == "approved":
            order.status = "completed"  # Cambiar a "completed" según el modelo
            order.paid_at = datetime.utcnow()
            await db.flush()
            
            # Generar tickets después de pago exitoso
            try:
                await self._generate_tickets(db, order)
                await db.commit()
            except Exception as e:
                await db.rollback()
                # Log error pero no fallar el webhook
                print(f"Error generando tickets para orden {order.id}: {e}")
                # Marcar orden como paid aunque falle la generación de tickets
                order.status = "completed"
                await db.commit()
            
            return True
        elif payment_status in ["rejected", "cancelled", "refunded"]:
            order.status = "cancelled"
            await db.commit()
            
            # Liberar capacidad
            for order_item in order.order_items:
                await self.inventory_service.release_capacity(
                    db, str(order_item.event_id), order_item.quantity, "payment_failed"
                )
            
            return True
        
        return False
    
    async def get_order_status(
        self,
        db: AsyncSession,
        order_id: str
    ) -> Optional[Dict]:
        """Obtener estado de una orden"""
        stmt = select(Order).where(Order.id == order_id)
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()
        
        if not order:
            return None
        
        return {
            "order_id": str(order.id),
            "status": order.status,
            "total": float(order.total),
            "currency": order.currency,
            "payment_provider": order.payment_provider,
            "payment_reference": order.payment_reference,
            "created_at": order.created_at,
            "paid_at": order.paid_at
        }
    
    async def _generate_tickets(
        self,
        db: AsyncSession,
        order: Order
    ) -> List[Ticket]:
        """
        Generar tickets después de pago exitoso
        
        Args:
            db: Sesión de base de datos
            order: Orden completada
        
        Returns:
            Lista de tickets generados
        """
        # Recuperar attendees del cache usando idempotency_key
        attendees_data = None
        if order.idempotency_key:
            attendees_cache_key = f"purchase:attendees:{order.idempotency_key}"
            attendees_data = await cache_get(attendees_cache_key)
        
        if not attendees_data:
            raise ValueError(f"No se encontraron datos de attendees para orden {order.id}")
        
        tickets = []
        commission_total = 0.0
        attendee_index = 0  # Índice global para rastrear qué attendee corresponde a cada ticket
        
        # Obtener order items
        for order_item in order.order_items:
            # Obtener tipo de ticket
            stmt_ticket_type = select(TicketType).where(TicketType.id == order_item.ticket_type_id)
            result_ticket_type = await db.execute(stmt_ticket_type)
            ticket_type = result_ticket_type.scalar_one_or_none()
            
            if not ticket_type:
                continue
            
            # Crear un ticket por cada attendee
            # IMPORTANTE: Cada ticket recibe el email del attendee correspondiente
            # El índice del attendee corresponde al ticket (attendees[0] -> ticket 1, attendees[1] -> ticket 2, etc.)
            # Usar índice global para asegurar que cada ticket tenga su propio attendee
            for idx in range(order_item.quantity):
                if attendee_index >= len(attendees_data):
                    raise ValueError(f"No hay suficientes attendees para crear todos los tickets. Se necesitan {order_item.quantity} pero solo hay {len(attendees_data)}")
                
                attendee_data = attendees_data[attendee_index]
                attendee_index += 1
                # Crear ticket
                ticket_id = uuid.uuid4()
                qr_signature = generate_qr_signature(str(ticket_id))
                
                # Separar nombre completo en first_name y last_name
                name_parts = attendee_data["name"].split(" ", 1)
                first_name = name_parts[0] if name_parts else attendee_data["name"]
                last_name = name_parts[1] if len(name_parts) > 1 else ""
                
                # Normalizar email (lowercase, trim)
                holder_email = None
                if attendee_data.get("email"):
                    holder_email = attendee_data["email"].lower().strip()
                
                ticket = Ticket(
                    id=ticket_id,
                    order_item_id=order_item.id,
                    event_id=order_item.event_id,
                    holder_first_name=first_name,
                    holder_last_name=last_name,
                    holder_email=holder_email,  # Email del attendee correspondiente
                    holder_document_type=attendee_data.get("document_type"),
                    holder_document_number=attendee_data.get("document_number"),
                    is_child=attendee_data.get("is_child", False),
                    qr_signature=qr_signature,
                    status="issued",
                    issued_at=datetime.utcnow()
                )
                db.add(ticket)
                await db.flush()
                
                # Si es niño, crear detalles de niño
                if attendee_data.get("is_child") and attendee_data.get("child_details"):
                    child_details_data = attendee_data["child_details"]
                    await self._create_child_details(db, ticket, child_details_data)
                
                # Calcular comisión
                if attendee_data.get("is_child"):
                    commission_amount = 1000.0  # CLP para niño
                else:
                    commission_amount = 1500.0  # CLP para adulto
                
                commission_total += commission_amount
                
                # Crear registro de comisión
                commission = OrderCommission(
                    id=uuid.uuid4(),
                    order_id=order.id,
                    ticket_id=ticket.id,
                    ticket_type="child" if attendee_data.get("is_child") else "adult",
                    commission_amount=commission_amount
                )
                db.add(commission)
                
                tickets.append(ticket)
        
        # Actualizar commission_total en la orden
        order.commission_total = commission_total
        await db.flush()
        
        return tickets
    
    async def _create_child_details(
        self,
        db: AsyncSession,
        ticket: Ticket,
        child_details_data: Dict
    ) -> TicketChildDetail:
        """
        Crear detalles de ticket para niño
        
        Args:
            db: Sesión de base de datos
            ticket: Ticket del niño
            child_details_data: Datos del niño del request original
        """
        # Calcular edad si tenemos birth_date
        edad = 0
        fecha_nacimiento = None
        if child_details_data.get("birth_date"):
            if isinstance(child_details_data["birth_date"], str):
                fecha_nacimiento = datetime.fromisoformat(child_details_data["birth_date"]).date()
            else:
                fecha_nacimiento = child_details_data["birth_date"]
            
            # Calcular edad
            today = date.today()
            edad = today.year - fecha_nacimiento.year
            if today.month < fecha_nacimiento.month or (today.month == fecha_nacimiento.month and today.day < fecha_nacimiento.day):
                edad -= 1
        
        # Obtener nombre del ticket holder
        nombre = f"{ticket.holder_first_name} {ticket.holder_last_name}".strip()
        rut = ticket.holder_document_number or ""
        
        child_detail = TicketChildDetail(
            id=uuid.uuid4(),
            ticket_id=ticket.id,
            nombre=nombre,
            rut=rut,
            correo=ticket.holder_email,  # Usar el email del ticket (holder_email)
            fecha_nacimiento=fecha_nacimiento or date.today(),
            edad=edad,
            tipo_documento=ticket.holder_document_type or "rut",
            toma_medicamento=bool(child_details_data.get("medications")),
            es_alergico=bool(child_details_data.get("allergies")),
            detalle_alergias=child_details_data.get("allergies"),
            tiene_necesidad_especial=bool(child_details_data.get("special_needs")),
            detalle_necesidad_especial=child_details_data.get("special_needs"),
            numero_emergencia=child_details_data.get("emergency_contact_phone", ""),
            pais_telefono="CL",
            nombre_contacto_emergencia=child_details_data.get("emergency_contact_name"),
            parentesco_contacto_emergencia=None,
            iglesia=None
        )
        db.add(child_detail)
        await db.flush()
        
        # Crear medicamentos si existen
        if child_details_data.get("medications"):
            for med_data in child_details_data["medications"]:
                medication = TicketChildMedication(
                    id=uuid.uuid4(),
                    ticket_child_id=child_detail.id,
                    nombre_medicamento=med_data.get("name", ""),
                    frecuencia=med_data.get("frequency", ""),
                    observaciones=med_data.get("notes")
                )
                db.add(medication)
        
        return child_detail
    
    def _generate_idempotency_key(self, request: PurchaseRequest) -> str:
        """Generar clave de idempotencia"""
        # Incluir emails en la clave para mejor unicidad
        emails = ",".join([att.email.lower().strip() for att in request.attendees if att.email])
        user_id = request.user_id or "anonymous"
        data = f"{user_id}:{request.event_id}:{len(request.attendees)}:{emails}"
        return hashlib.sha256(data.encode()).hexdigest()

