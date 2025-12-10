"""Servicio principal de compra de tickets"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Dict, Optional
from datetime import datetime, date
import uuid
import hashlib
from shared.database.models import (
    Order, OrderItem, Ticket, Event, TicketType, EventService,
    TicketChildDetail, TicketChildMedication, OrderCommission, OrderServiceItem
)
from shared.utils.qr_generator import generate_qr_signature
from services.ticket_purchase.models.purchase import PurchaseRequest, AttendeeData
from services.ticket_purchase.services.inventory_service import InventoryService
from services.ticket_purchase.services.mercado_pago_service import MercadoPagoService
from services.ticket_purchase.services.payku_service import PaykuService
from services.notifications.services.email_service import EmailService
from shared.cache.redis_client import cache_get, cache_set
import logging

logger = logging.getLogger(__name__)


class PurchaseService:
    """Servicio para procesar compras de tickets"""
    
    def __init__(self):
        self.inventory_service = InventoryService()
        self._mercado_pago_service = None
        self._payku_service = None
    
    @property
    def mercado_pago_service(self):
        """Lazy initialization de MercadoPagoService solo cuando se necesita"""
        if self._mercado_pago_service is None:
            self._mercado_pago_service = MercadoPagoService()
        return self._mercado_pago_service
    
    @property
    def payku_service(self):
        """Lazy initialization de PaykuService solo cuando se necesita"""
        if self._payku_service is None:
            self._payku_service = PaykuService()
        return self._payku_service
    
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
        # Determinar método de pago PRIMERO
        payment_method = request.payment_method or "mercadopago"
        is_bank_transfer = payment_method == "bank_transfer"
        is_payku = payment_method == "payku"
        
        # Generar idempotency_key base (sin payment_method)
        base_idempotency_key = request.idempotency_key or self._generate_idempotency_key(request)
        
        # Incluir payment_method en el idempotency_key para que sean únicos por método de pago
        # Esto evita conflictos cuando el mismo usuario intenta comprar con diferentes métodos
        import hashlib
        idempotency_key = hashlib.sha256(f"{base_idempotency_key}:{payment_method}".encode()).hexdigest()
        
        # Incluir payment_method en el cache key para diferenciar por método de pago
        cache_key = f"purchase:idempotency:{idempotency_key}"
        
        # Verificar idempotencia en cache
        cached = await cache_get(cache_key)
        if cached:
            # Si es Payku, verificar que la transacción aún sea válida
            if is_payku and cached.get("transaction_id"):
                try:
                    transaction_data = self.payku_service.verify_transaction(cached["transaction_id"])
                    transaction_status = transaction_data.get("status", "").lower()
                    
                    # Si la transacción ya fue pagada o rechazada, invalidar cache y continuar
                    if transaction_status in ["success", "completed", "approved", "failed", "rejected", "cancelled"]:
                        logger.warning(f"Transacción Payku en cache ya fue procesada ({transaction_status}). Invalidando cache.")
                        from shared.cache.redis_client import cache_delete
                        await cache_delete(cache_key)
                        cached = None  # Continuar con la creación/verificación normal
                    # Si está pendiente, usar el cache
                    elif transaction_status in ["pending"]:
                        return cached
                except Exception as e:
                    logger.warning(f"Error verificando transacción Payku en cache: {str(e)}")
                    # Si falla la verificación, invalidar cache por seguridad
                    from shared.cache.redis_client import cache_delete
                    await cache_delete(cache_key)
                    cached = None
            
            # Si no es Payku o el cache es válido, retornar
            if cached:
                return cached
        
        # Verificar en la base de datos si existe una orden con ese idempotency_key Y mismo payment_method
        try:
            stmt_existing = select(Order).where(
                Order.idempotency_key == idempotency_key,
                Order.payment_provider == payment_method
            )
            result_existing = await db.execute(stmt_existing)
            existing_order = result_existing.scalar_one_or_none()
        except Exception as db_error:
            # Error de conexión a la base de datos
            error_msg = str(db_error)
            logger.error(f"Error conectando a la base de datos: {error_msg}")
            # Re-lanzar el error para que el endpoint retorne 500
            raise Exception(f"Error de conexión a la base de datos: {error_msg}. Verifica que la base de datos esté disponible.")
        
        if existing_order:
            # Si el método de pago del request NO coincide con el de la orden existente,
            # crear una nueva orden (no usar idempotencia en este caso)
            if existing_order.payment_provider != payment_method:
                # Continuar con la creación de una nueva orden
                existing_order = None
            else:
                # Si es transferencia bancaria y no tiene tickets, crearlos
                if existing_order.payment_provider == "bank_transfer":
                    # Verificar si tiene tickets
                    from sqlalchemy import func
                    stmt_tickets_count = select(func.count(Ticket.id)).join(
                        OrderItem, Ticket.order_item_id == OrderItem.id
                    ).where(OrderItem.order_id == existing_order.id)
                    result_tickets_count = await db.execute(stmt_tickets_count)
                    tickets_count = result_tickets_count.scalar() or 0
                    
                    if tickets_count == 0:
                        # No tiene tickets, crearlos ahora
                        await db.refresh(existing_order, ["order_items"])
                        if existing_order.order_items:
                            # Preparar attendees_data para esta orden
                            attendees_data_for_existing = [
                                {
                                    "name": att.name,
                                    "email": att.email,
                                    "document_type": att.document_type,
                                    "document_number": att.document_number,
                                    "is_child": att.is_child,
                                    "child_details": att.child_details.dict() if att.child_details and hasattr(att.child_details, 'dict') else (att.child_details if att.child_details else None)
                                }
                                for att in request.attendees
                            ]
                            
                            tickets = await self._generate_tickets(
                                db, existing_order, attendees_data_for_existing, ticket_status="pending"
                            )
                            await db.commit()
                            await db.refresh(existing_order)
                
                # Retornar la orden existente (solo si el método de pago coincide)
                payment_link = None
                
                # Si la orden ya está completada, crear una nueva orden (permitir múltiples compras)
                if existing_order and existing_order.status == "completed":
                    print(f"[DEBUG SERVICE] Orden {existing_order.id} ya está completada. Creando nueva orden para nueva compra...")
                    # Invalidar cache y continuar con la creación de una nueva orden
                    from shared.cache.redis_client import cache_delete
                    await cache_delete(cache_key)
                    # Generar nuevo idempotency_key para la nueva orden (agregar timestamp)
                    import time
                    timestamp = int(time.time() * 1000)  # Timestamp en milisegundos
                    idempotency_key = hashlib.sha256(f"{base_idempotency_key}:{payment_method}:{timestamp}".encode()).hexdigest()
                    cache_key = f"purchase:idempotency:{idempotency_key}"  # Actualizar cache_key también
                    print(f"[DEBUG SERVICE] Nuevo idempotency_key generado: {idempotency_key}")
                    existing_order = None  # Continuar con la creación de una nueva orden
                
                # Si existing_order es None después de invalidar, salir del bloque y crear nueva orden
                if existing_order is None:
                    print(f"[DEBUG SERVICE] No hay orden existente o fue invalidada. Continuando con creación de nueva orden...")
                    # Salir del bloque if existing_order para continuar con la creación de una nueva orden
                    # El código después de este bloque if existing_order: creará una nueva orden
                elif existing_order.payment_provider == "payku":
                    # Para Payku, verificar si la transacción existe y su estado
                    if existing_order.payment_reference:
                        try:
                            # Verificar estado de la transacción en Payku
                            transaction_data = self.payku_service.verify_transaction(existing_order.payment_reference)
                            transaction_status = transaction_data.get("status", "").lower()
                            
                            # Si la transacción ya fue pagada, rechazada o cancelada, invalidar orden y crear nueva
                            if transaction_status in ["success", "completed", "approved", "failed", "rejected", "cancelled"]:
                                logger.warning(f"Transacción Payku {existing_order.payment_reference} ya fue procesada ({transaction_status}). Invalidando orden y creando nueva.")
                                # Invalidar cache y orden existente para crear una nueva orden
                                from shared.cache.redis_client import cache_delete
                                await cache_delete(cache_key)
                                # Generar nuevo idempotency_key para la nueva orden (agregar timestamp)
                                import time
                                timestamp = int(time.time() * 1000)  # Timestamp en milisegundos
                                idempotency_key = hashlib.sha256(f"{base_idempotency_key}:{payment_method}:{timestamp}".encode()).hexdigest()
                                cache_key = f"purchase:idempotency:{idempotency_key}"  # Actualizar cache_key también
                                existing_order = None  # Forzar creación de nueva orden
                                payment_link = None
                            else:
                                # Transacción pendiente, pero Payku no devuelve el payment_link en verify_transaction
                                # Necesitamos crear una nueva transacción con un nuevo order_id
                                logger.warning("Transacción Payku pendiente pero no tenemos payment_link. Invalidando orden para crear nueva.")
                                from shared.cache.redis_client import cache_delete
                                await cache_delete(cache_key)
                                # Generar nuevo idempotency_key para la nueva orden (agregar timestamp)
                                import time
                                timestamp = int(time.time() * 1000)  # Timestamp en milisegundos
                                idempotency_key = hashlib.sha256(f"{base_idempotency_key}:{payment_method}:{timestamp}".encode()).hexdigest()
                                cache_key = f"purchase:idempotency:{idempotency_key}"  # Actualizar cache_key también
                                existing_order = None  # Forzar creación de nueva orden
                                payment_link = None
                        except Exception as e:
                            logger.warning(f"No se pudo verificar transacción Payku existente: {str(e)}. Invalidando orden y creando nueva.")
                            # Si falla la verificación, invalidar y crear nueva orden
                            from shared.cache.redis_client import cache_delete
                            await cache_delete(cache_key)
                            # Generar nuevo idempotency_key para la nueva orden (agregar timestamp)
                            import time
                            timestamp = int(time.time() * 1000)  # Timestamp en milisegundos
                            idempotency_key = hashlib.sha256(f"{base_idempotency_key}:{payment_method}:{timestamp}".encode()).hexdigest()
                            cache_key = f"purchase:idempotency:{idempotency_key}"  # Actualizar cache_key también
                            existing_order = None
                            payment_link = None
                    
                    # Si no tiene payment_reference, invalidar y crear nueva orden
                    if not existing_order or not payment_link:
                        if existing_order:
                            logger.warning("Orden existente sin payment_reference válido. Invalidando y creando nueva orden.")
                            from shared.cache.redis_client import cache_delete
                            await cache_delete(cache_key)
                            # Generar nuevo idempotency_key para la nueva orden (agregar timestamp)
                            import time
                            timestamp = int(time.time() * 1000)  # Timestamp en milisegundos
                            idempotency_key = hashlib.sha256(f"{base_idempotency_key}:{payment_method}:{timestamp}".encode()).hexdigest()
                            cache_key = f"purchase:idempotency:{idempotency_key}"  # Actualizar cache_key también
                            existing_order = None
                        payment_link = None
                
                elif existing_order.payment_provider == "mercadopago":
                    if existing_order.payment_reference:
                        # Si tiene payment_reference, obtener el init_point de la preferencia
                        try:
                            preference = self.mercado_pago_service.get_preference(existing_order.payment_reference)
                            if preference:
                                # Verificar que la preferencia tenga back_urls válidas
                                back_urls = preference.get("back_urls", {})
                                has_valid_back_urls = (
                                    back_urls.get("success") and 
                                    back_urls.get("failure") and 
                                    back_urls.get("pending")
                                )
                                
                                if not has_valid_back_urls:
                                    logger.warning(f"Preferencia existente tiene back_urls inválidas, creando nueva preferencia. back_urls actuales: {back_urls}")
                                    payment_link = None
                                else:
                                    # En sandbox, usar sandbox_init_point si está disponible
                                    environment = self.mercado_pago_service.environment
                                    if environment == "sandbox":
                                        payment_link = preference.get("sandbox_init_point") or preference.get("init_point")
                                    else:
                                        payment_link = preference.get("init_point")
                            else:
                                payment_link = None
                        except Exception as e:
                            logger.warning(f"No se pudo obtener payment_link de preferencia existente: {str(e)}")
                            # Si falla, intentar crear una nueva preferencia
                            payment_link = None
                    
                    # Si no tiene payment_reference o no se pudo obtener el link, crear nueva preferencia
                    if not payment_link:
                        try:
                            # Obtener order_items directamente con JOIN para evitar problemas de lazy loading
                            from sqlalchemy.orm import selectinload
                            
                            # Query directa de order_items con ticket_types usando JOIN
                            stmt_order_items = select(OrderItem, TicketType).join(
                                TicketType, OrderItem.ticket_type_id == TicketType.id, isouter=True
                            ).where(OrderItem.order_id == existing_order.id)
                            
                            result_items = await db.execute(stmt_order_items)
                            rows = result_items.all()
                            
                            # Construir items desde order_items
                            items = []
                            for row in rows:
                                order_item = row[0]
                                ticket_type = row[1] if len(row) > 1 else None
                                
                                ticket_type_name = "Ticket"
                                if ticket_type:
                                    ticket_type_name = ticket_type.name
                                
                                items.append({
                                    "title": f"Ticket - {ticket_type_name}",
                                    "description": f"{order_item.quantity} ticket(s)",
                                    "quantity": order_item.quantity,
                                    "unit_price": float(order_item.unit_price)
                                })
                            
                            # Obtener información del primer attendee si está disponible
                            payer_email = None
                            payer_name = None
                            payer_identification = None
                            if request.attendees and len(request.attendees) > 0:
                                first_attendee = request.attendees[0]
                                payer_email = first_attendee.email
                                payer_name = first_attendee.name
                                if first_attendee.document_type and first_attendee.document_number:
                                    payer_identification = {
                                        "type": first_attendee.document_type,
                                        "number": first_attendee.document_number
                                    }
                            
                            # Crear nueva preferencia
                            preference = self.mercado_pago_service.create_preference(
                                order_id=str(existing_order.id),
                                currency="CLP",
                                items=items,
                                payer_email=payer_email,
                                payer_name=payer_name,
                                payer_identification=payer_identification
                            )
                            
                            existing_order.payment_reference = preference["preference_id"]
                            payment_link = preference["payment_link"]
                            await db.commit()
                        except Exception as e:
                            logger.error(f"Error creando preferencia para orden existente: {str(e)}", exc_info=True)
                            # No propagar el error, simplemente retornar sin payment_link
                            # para que el frontend pueda manejar el error
                            payment_link = None
                
                # Solo retornar si existing_order no es None
                if existing_order is not None:
                    return {
                        "order_id": str(existing_order.id),
                        "payment_link": payment_link,
                        "preference_id": existing_order.payment_reference,
                        "status": existing_order.status,
                        "payment_method": existing_order.payment_provider or "mercadopago"
                    }
                # Si existing_order es None, continuar con la creación de una nueva orden
        
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
        
        # Calcular precios de tickets
        subtotal = float(ticket_type.price) * total_quantity
        
        # Calcular precios de servicios adicionales
        services_subtotal = 0.0
        if request.selected_services:
            stmt_services = select(EventService).where(
                EventService.event_id == request.event_id,
                EventService.id.in_(list(request.selected_services.keys()))
            )
            result_services = await db.execute(stmt_services)
            services = result_services.scalars().all()
            
            for service in services:
                quantity = request.selected_services.get(str(service.id), 0)
                if quantity > 0:
                    services_subtotal += float(service.price) * quantity
        
        discount_total = 0.0  # TODO: Aplicar descuentos si hay
        total = subtotal + services_subtotal - discount_total
        
        # Validar que todos los attendees tengan email
        for attendee in request.attendees:
            if not attendee.email:
                raise ValueError(f"Todos los asistentes deben tener un correo electrónico. Falta email para: {attendee.name}")
        
        # El método de pago ya se determinó arriba
        
        # Preparar datos de attendees ANTES de crear la orden
        # IMPORTANTE: Esto debe hacerse antes de crear el Order para poder guardarlo en attendees_data
        attendees_data = []
        for att in request.attendees:
            child_details_dict = None
            if att.child_details:
                # Si child_details es un objeto Pydantic, usar .dict(), si es dict, usar directamente
                if hasattr(att.child_details, 'dict'):
                    child_details_dict = att.child_details.dict()
                else:
                    child_details_dict = att.child_details
            
            attendees_data.append({
                "name": att.name,
                "email": att.email,
                "document_type": att.document_type,
                "document_number": att.document_number,
                "is_child": att.is_child,
                "child_details": child_details_dict
            })
        
        # Crear orden - user_id es opcional ahora
        # IMPORTANTE: Guardar datos de attendees en la orden para recuperarlos después del pago
        order = Order(
            id=uuid.uuid4(),
            user_id=uuid.UUID(request.user_id) if request.user_id else None,
            subtotal=subtotal + services_subtotal,  # Incluir servicios en subtotal
            discount_total=discount_total,
            total=total,
            currency="CLP",
            status="pending",
            payment_provider=payment_method,
            receipt_url=request.receipt_url if is_bank_transfer else None,
            idempotency_key=idempotency_key,
            attendees_data=attendees_data,  # Guardar datos de attendees en la base de datos
            created_at=datetime.utcnow()
        )
        db.add(order)
        await db.flush()
        
        # Crear order item para tickets
        order_item = OrderItem(
            id=uuid.uuid4(),
            order_id=order.id,
            event_id=request.event_id,
            ticket_type_id=ticket_type.id,
            quantity=total_quantity,
            unit_price=ticket_type.price,
            final_price=subtotal
        )
        db.add(order_item)
        await db.flush()
        
        # Crear order service items para servicios adicionales
        if request.selected_services:
            # Convertir las keys de string a UUID
            service_ids = []
            for key in request.selected_services.keys():
                try:
                    service_ids.append(uuid.UUID(key))
                except (ValueError, TypeError):
                    continue  # Saltar IDs inválidos
            
            if service_ids:
                stmt_services = select(EventService).where(
                    EventService.event_id == request.event_id,
                    EventService.id.in_(service_ids)
                )
                result_services = await db.execute(stmt_services)
                services = result_services.scalars().all()
                
                for service in services:
                    quantity = request.selected_services.get(str(service.id), 0)
                    if quantity > 0:
                        service_item = OrderServiceItem(
                            id=uuid.uuid4(),
                            order_id=order.id,
                            event_id=request.event_id,
                            service_id=service.id,
                            quantity=quantity,
                            unit_price=service.price,
                            final_price=float(service.price) * quantity
                        )
                        db.add(service_item)
        
        await db.flush()
        
        # Guardar attendees en cache para recuperarlos después del pago
        # Necesario para pagos asíncronos (Mercado Pago y Payku) donde el webhook llega después
        # Para transferencias bancarias, creamos tickets inmediatamente, no necesitamos cache
        # IMPORTANTE: Usar order.idempotency_key (hash final) en lugar de request.idempotency_key
        # para que coincida con la búsqueda en get_order_status
        if not is_bank_transfer and order.idempotency_key:
            attendees_cache_key = f"purchase:attendees:{order.idempotency_key}"
            await cache_set(attendees_cache_key, attendees_data, expire=86400)  # 24 horas
            # Datos de attendees guardados en cache (no loguear en producción)
        
        # Reservar capacidad
        reserved = await self.inventory_service.reserve_capacity(
            db, request.event_id, total_quantity, f"order_{order.id}"
        )
        
        if not reserved:
            await db.rollback()
            raise ValueError("No se pudo reservar capacidad")
        
        payment_link = None
        
        # Si es transferencia bancaria, crear tickets inmediatamente con status "pending"
        if is_bank_transfer:
            try:
                # Hacer flush para asegurar que order_items estén disponibles
                await db.flush()
                
                # Refrescar la orden para cargar order_items
                await db.refresh(order, ["order_items"])
                
                # Verificar que order_items esté cargado
                if not order.order_items:
                    raise ValueError("No se encontraron order_items para crear tickets")
                
                # Crear tickets con status "pending" inmediatamente
                tickets = await self._generate_tickets(
                    db, order, attendees_data, ticket_status="pending"
                )
                
                # Actualizar orden - mantener status "pending" hasta verificación manual
                order.status = "pending"
                
                await db.commit()
                await db.refresh(order)
                
                response = {
                    "order_id": str(order.id),
                    "payment_link": None,  # No hay payment_link para transferencias
                    "status": "pending",
                    "payment_method": payment_method  # bank_transfer
                }
                
                # Guardar en cache para idempotencia
                await cache_set(cache_key, response, expire=3600)
                
                return response
                
            except Exception as e:
                # Si falla la creación de tickets, liberar capacidad y rollback
                import traceback
                error_trace = traceback.format_exc()
                logger.error(f"Error creando tickets para transferencia bancaria: {str(e)}", exc_info=True)
                await self.inventory_service.release_capacity(
                    db, request.event_id, total_quantity, "ticket_creation_failed"
                )
                await db.rollback()
                raise ValueError(f"Error creando tickets: {str(e)}")
        
        # Si es Payku, crear transacción de pago
        elif is_payku:
            try:
                # Creando transacción de Payku
                
                # Obtener información del primer attendee para la transacción
                payer_email = None
                if request.attendees and len(request.attendees) > 0:
                    first_attendee = request.attendees[0]
                    payer_email = first_attendee.email
                
                if not payer_email:
                    raise ValueError("Se requiere un email para crear la transacción de Payku")
                
                # Crear descripción del pago
                subject = f"Compra de tickets - {event.name}"
                
                # Crear transacción con Payku
                transaction = self.payku_service.create_transaction(
                    order_id=str(order.id),
                    email=payer_email,
                    amount=total,
                    subject=subject,
                    currency=order.currency or "CLP"
                )
                
                print(f"[DEBUG] Transacción creada: {transaction}")
                
                # Validar que la transacción tenga los campos necesarios
                if not transaction.get("payment_link"):
                    raise ValueError("La transacción no tiene payment_link")
                
                order.payment_reference = transaction.get("transaction_id")
                payment_link = transaction["payment_link"]
                
                print(f"[DEBUG] Payment link obtenido: {payment_link}")
                print(f"[DEBUG] Transaction ID obtenido: {transaction.get('transaction_id')}")
                
            except Exception as e:
                # Si falla la creación de transacción, liberar capacidad y rollback
                import traceback
                error_trace = traceback.format_exc()
                logger.error(f"Error creando transacción de pago: {str(e)}", exc_info=True)
                await self.inventory_service.release_capacity(
                    db, request.event_id, total_quantity, "payment_creation_failed"
                )
                await db.rollback()
                raise ValueError(f"Error creando transacción de pago: {str(e)}")
            
            await db.commit()
            await db.refresh(order)
            
            response = {
                "order_id": str(order.id),
                "payment_link": payment_link,
                "transaction_id": transaction.get("transaction_id"),
                "status": "pending",
                "payment_method": "payku"
            }
            
            # Response final preparado
            
            # Guardar en cache para idempotencia
            await cache_set(cache_key, response, expire=3600)
            
            return response
        
        # Si es Mercado Pago, crear preferencia de pago
        else:
            try:
                # Creando preferencia de Mercado Pago
                print(f"[DEBUG] Payment method recibido: {payment_method}")
                
                # Construir items para la preferencia (tickets + servicios + comisiones)
                items = []
                
                # Item para tickets
                ticket_type_name = ticket_type.name if hasattr(ticket_type, 'name') else "Ticket"
                items.append({
                    "title": f"{ticket_type_name} - {event.name}",
                    "description": f"{total_quantity} ticket(s) para {event.name}",
                    "quantity": total_quantity,
                    "unit_price": float(ticket_type.price)
                })
                
                # Items para servicios adicionales
                if request.selected_services:
                    # Recargar servicios para obtener nombres
                    stmt_services = select(EventService).where(
                        EventService.event_id == request.event_id,
                        EventService.id.in_(list(request.selected_services.keys()))
                    )
                    result_services = await db.execute(stmt_services)
                    services = result_services.scalars().all()
                    
                    for service in services:
                        quantity = request.selected_services.get(str(service.id), 0)
                        if quantity > 0:
                            items.append({
                                "title": service.name or "Servicio adicional",
                                "description": f"{service.name} - {event.name}",
                                "quantity": quantity,
                                "unit_price": float(service.price)
                            })
                
                # --- COMISIONES BLOQUE COMPLETO - COMENTADO TEMPORALMENTE ---
                # Las comisiones ya están incluidas en el precio del ticket por los administradores
                # Comisión: 1500 CLP por cada entrada (adulto o niño)
                # COMMISSION_PER_TICKET = 1500.0
                # 
                # if total_quantity > 0:
                #     items.append({
                #         "title": "Comisión de servicio",
                #         "description": f"Comisión de procesamiento por entrada ({total_quantity} entrada(s))",
                #         "quantity": total_quantity,  # Una comisión por cada entrada
                #         "unit_price": float(COMMISSION_PER_TICKET)  # 1500 CLP por entrada
                #     })
                # 
                # commission_total = total_quantity * COMMISSION_PER_TICKET
                # print(f"[DEBUG] Items para preferencia: {items}")
                # print(f"[DEBUG] Comisiones: {total_quantity} entrada(s) × {COMMISSION_PER_TICKET} CLP = {commission_total} CLP")
                # ------------------------------------
                print(f"[DEBUG] Items para preferencia: {items}")
                
                # Obtener información del primer attendee para la preferencia
                payer_email = None
                payer_name = None
                payer_identification = None
                if request.attendees and len(request.attendees) > 0:
                    first_attendee = request.attendees[0]
                    payer_email = first_attendee.email
                    payer_name = first_attendee.name
                    # Construir identificación si está disponible
                    if first_attendee.document_type and first_attendee.document_number:
                        payer_identification = {
                            "type": first_attendee.document_type,
                            "number": first_attendee.document_number
                        }
                
                # Crear preferencia con múltiples items
                preference = self.mercado_pago_service.create_preference(
                    order_id=str(order.id),
                    currency="CLP",
                    items=items,
                    payer_email=payer_email,
                    payer_name=payer_name,
                    payer_identification=payer_identification
                )
                
                print(f"[DEBUG] Preferencia creada: {preference}")
                
                # Validar que la preferencia tenga los campos necesarios
                if not preference.get("preference_id"):
                    raise ValueError("La preferencia no tiene preference_id")
                
                if not preference.get("payment_link"):
                    print(f"[ERROR] Preferencia creada pero sin payment_link:")
                    print(f"[ERROR]   - preference_id: {preference.get('preference_id')}")
                    print(f"[ERROR]   - preference completa: {preference}")
                    raise ValueError("La preferencia se creó pero no tiene payment_link")
                
                order.payment_reference = preference["preference_id"]
                payment_link = preference["payment_link"]
                
                print(f"[DEBUG] Payment link obtenido: {payment_link}")
                print(f"[DEBUG] Preference ID obtenido: {preference['preference_id']}")
                
            except Exception as e:
                # Si falla la creación de preferencia, liberar capacidad y rollback
                import traceback
                error_trace = traceback.format_exc()
                print(f"[ERROR] Error creando preferencia de pago: {str(e)}")
                print(f"[ERROR] Traceback: {error_trace}")
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
                "preference_id": preference["preference_id"],
                "status": "pending",
                "payment_method": "mercadopago"
            }
            
            # Response final preparado
            
            # Guardar en cache para idempotencia
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
        # Obtener datos de la notificación
        notification_data = payment_data.get("data", {})
        notification_type = payment_data.get("type")
        resource_id = notification_data.get("id")
        
        if not resource_id:
            print("⚠️  Webhook sin ID de recurso")
            return False
        
        # Para notificaciones de tipo "order", usar external_reference directamente
        external_reference = None
        payment_status = None
        
        if notification_type == "order":
            # Las notificaciones de order ya incluyen external_reference
            external_reference = notification_data.get("external_reference")
            payment_status = notification_data.get("status")
            
            # Si no hay external_reference en la notificación, intentar obtenerlo del order
            if not external_reference:
                try:
                    order_info = self.mercado_pago_service.verify_order(resource_id)
                    external_reference = order_info.get("external_reference")
                    payment_status = order_info.get("status")
                except Exception as e:
                    print(f"⚠️  No se pudo obtener order {resource_id} (puede ser simulación): {e}")
                    return False
        else:
            # Para notificaciones de tipo "payment", obtener del pago
            try:
                payment_info = self.mercado_pago_service.verify_payment(resource_id)
                external_reference = payment_info.get("external_reference")
                payment_status = payment_info.get("status")
            except Exception as e:
                print(f"⚠️  No se pudo obtener pago {resource_id} (puede ser simulación): {e}")
                # Intentar obtener external_reference de la notificación directamente
                external_reference = notification_data.get("external_reference")
                if not external_reference:
                    return False
        
        if not external_reference:
            print("⚠️  Webhook sin external_reference")
            return False
        
        # Buscar orden
        stmt = select(Order).where(Order.id == external_reference)
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()
        
        if not order:
            print(f"⚠️  Orden {external_reference} no encontrada (puede ser simulación)")
            return False
        
        # Mapear estados de order a estados de pago
        # Para notificaciones de tipo "order", el status puede ser "processed", "pending", etc.
        # Para notificaciones de tipo "payment", el status es "approved", "pending", etc.
        print(f"🔔 [WEBHOOK] Tipo: {notification_type}, Estado recibido: {payment_status}, Resource ID: {resource_id}")
        print(f"🔔 [WEBHOOK] External Reference: {external_reference}, Order ID: {order.id if order else 'NO ENCONTRADA'}")
        
        if notification_type == "order":
            # Mapear estados de order a estados de pago
            print(f"🔔 [WEBHOOK] Mapeando estado de order: {payment_status}")
            if payment_status == "processed":
                payment_status = "approved"
                print(f"🔔 [WEBHOOK] Estado mapeado a: approved")
            elif payment_status in ["expired", "failed", "canceled"]:
                payment_status = "cancelled"
                print(f"🔔 [WEBHOOK] Estado mapeado a: cancelled")
            elif payment_status == "pending":
                print(f"🔔 [WEBHOOK] Estado sigue siendo pending - el pago aún no se ha completado")
        
        # Actualizar estado según el pago
        print(f"🔔 [WEBHOOK] Estado final a procesar: {payment_status}")
        if payment_status == "approved":
            print(f"✅ [WEBHOOK] Pago aprobado! Actualizando orden {order.id} a 'completed'")
            order.status = "completed"  # Cambiar a "completed" según el modelo
            order.paid_at = datetime.utcnow()
            await db.flush()
            
            # Generar tickets después de pago exitoso (solo para Mercado Pago)
            # Las transferencias bancarias ya tienen tickets creados con status "pending"
            if order.payment_provider == "mercadopago":
                try:
                    await self._generate_tickets(db, order, ticket_status="issued")
                    await db.commit()
                except Exception as e:
                    await db.rollback()
                    # Log error pero no fallar el webhook
                    print(f"Error generando tickets para orden {order.id}: {e}")
                    # Marcar orden como paid aunque falle la generación de tickets
                    order.status = "completed"
                    await db.commit()
            else:
                # Para transferencias bancarias, solo actualizar el estado de la orden
                # Los tickets ya fueron creados con status "pending"
                await db.commit()
            
            return True
        elif payment_status in ["rejected", "cancelled", "refunded"]:
            print(f"❌ [WEBHOOK] Pago rechazado/cancelado. Actualizando orden {order.id} a 'cancelled'")
            order.status = "cancelled"
            await db.commit()
            
            # Liberar capacidad
            for order_item in order.order_items:
                await self.inventory_service.release_capacity(
                    db, str(order_item.event_id), order_item.quantity, "payment_failed"
                )
            
            return True
        
        # Si el estado es "pending", el webhook se recibió pero el pago aún no está aprobado
        print(f"⏳ [WEBHOOK] Estado '{payment_status}' - El pago aún está pendiente. No se actualiza la orden.")
        print(f"⏳ [WEBHOOK] Esto es normal si el pago aún no se ha completado en Mercado Pago.")
        return False
    
    async def get_order_status(
        self,
        db: AsyncSession,
        order_id: str
    ) -> Optional[Dict]:
        """
        Obtener estado de una orden
        
        Si el estado es "pending" y el payment_provider es "payku",
        consulta activamente a Payku para verificar el estado real
        y actualiza la base de datos si es necesario.
        """
        from sqlalchemy.orm import selectinload
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.order_service_items).selectinload(OrderServiceItem.service)
            )
        )
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()
        
        if not order:
            return None
        
        # Si el estado es "pending" y es una orden de Payku, verificar activamente con Payku
        if order.status == "pending" and order.payment_provider == "payku" and order.payment_reference:
            # OPTIMIZACIÓN: Verificar cache primero para evitar consultas repetidas a Payku
            cache_key = f"payku_verify:{order.payment_reference}"
            cached_result = None
            
            try:
                cached_result = await cache_get(cache_key)
                if cached_result:
                    import json
                    from datetime import datetime
                    cached_data = json.loads(cached_result) if isinstance(cached_result, str) else cached_result
                    cache_timestamp_str = cached_data.get('timestamp', '')
                    
                    if cache_timestamp_str:
                        try:
                            cache_timestamp = datetime.fromisoformat(cache_timestamp_str.replace('Z', '+00:00'))
                            cache_age = (datetime.utcnow() - cache_timestamp.replace(tzinfo=None)).total_seconds()
                            
                            # Si el cache es reciente (< 30 segundos), usar cache
                            if cache_age < 30:
                                print(f"🔍 [CACHE] Usando cache de verificación Payku para {order.payment_reference} (age: {cache_age:.1f}s)")
                                # No consultar Payku, usar estado local
                                await db.refresh(order, ["order_service_items"])
                                # Cargar servicios si no están cargados
                                if order.order_service_items:
                                    for service_item in order.order_service_items:
                                        if not service_item.service:
                                            await db.refresh(service_item, ["service"])
                                
                                # Obtener servicios de la orden
                                services_list = []
                                if order.order_service_items:
                                    for service_item in order.order_service_items:
                                        services_list.append({
                                            "service_id": str(service_item.service_id),
                                            "service_name": service_item.service.name if service_item.service else "Servicio",
                                            "quantity": service_item.quantity,
                                            "unit_price": float(service_item.unit_price),
                                            "total_price": float(service_item.final_price)
                                        })
                                
                                return {
                                    "order_id": str(order.id),
                                    "status": order.status,
                                    "total": float(order.total),
                                    "currency": order.currency,
                                    "payment_provider": order.payment_provider,
                                    "payment_reference": order.payment_reference,
                                    "created_at": order.created_at,
                                    "paid_at": order.paid_at,
                                    "attendees_data": order.attendees_data,
                                    "services": services_list if services_list else None
                                }
                        except Exception as cache_parse_error:
                            print(f"⚠️  [CACHE] Error parseando timestamp del cache: {cache_parse_error}")
                            # Continuar con verificación normal
            except Exception as cache_error:
                print(f"⚠️  [CACHE] Error leyendo cache: {cache_error}")
                # Continuar con verificación normal
            
            # Si llegamos aquí, no hay cache válido o expiró, consultar Payku
            try:
                print(f"🔍 [get_order_status] Verificando estado en Payku para orden {order_id}")
                print(f"🔍 [get_order_status] Transaction ID: {order.payment_reference}")
                
                # Consultar estado en Payku
                transaction_data = self.payku_service.verify_transaction(order.payment_reference)
                
                # OPTIMIZACIÓN: Guardar resultado en cache por 30 segundos
                try:
                    import json
                    from datetime import datetime
                    cache_data = {
                        "status": transaction_data.get("status", "").lower(),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    from shared.cache.redis_client import cache_set
                    await cache_set(cache_key, json.dumps(cache_data), expire=30)
                    print(f"🔍 [CACHE] Resultado de verificación Payku guardado en cache por 30s")
                except Exception as cache_set_error:
                    print(f"⚠️  [CACHE] Error guardando cache: {cache_set_error}")
                    # No es crítico, continuar
                
                print(f"🔍 [get_order_status] Respuesta de Payku: {transaction_data}")
                
                # Extraer estado de la transacción
                # Payku puede devolver el estado en diferentes formatos
                status = transaction_data.get("status", "").lower()
                
                # También verificar en payment.status si existe
                payment_data = transaction_data.get("payment", {})
                if payment_data and payment_data.get("status"):
                    status = payment_data.get("status", "").lower()
                
                print(f"🔍 [get_order_status] Estado procesado de Payku: {status}")
                
                # Mapear estados de Payku a estados internos
                status_mapping = {
                    'success': 'completed',
                    'approved': 'completed',
                    'completado': 'completed',
                    'completed': 'completed',
                    'failed': 'cancelled',
                    'rejected': 'cancelled',
                    'cancelled': 'cancelled',
                    'cancelado': 'cancelled',
                    'pending': 'pending',
                    'pendiente': 'pending'
                }
                
                mapped_status = status_mapping.get(status, order.status)
                
                print(f"🔍 [get_order_status] Estado mapeado: {mapped_status} (original: {status})")
                
                # Si el estado cambió, actualizar la orden
                if mapped_status != order.status:
                    print(f"✅ [get_order_status] Estado cambió de '{order.status}' a '{mapped_status}'. Actualizando orden...")
                    
                    # Guardar idempotency_key ANTES de cualquier operación que pueda fallar
                    idempotency_key_str = str(order.idempotency_key) if order.idempotency_key else None
                    
                    order.status = mapped_status
                    
                    if mapped_status == "completed":
                        order.paid_at = datetime.utcnow()
                        await db.flush()
                        
                        # Intentar recuperar attendees - PRIORIDAD 1: desde la base de datos (más confiable)
                        attendees_data = None
                        if order.attendees_data:
                            attendees_data = order.attendees_data
                            print(f"🔍 [get_order_status] ✅ Attendees recuperados de la base de datos: {len(attendees_data)}")
                        
                        # PRIORIDAD 2: Si no están en BD, intentar desde cache
                        if not attendees_data and idempotency_key_str:
                            attendees_cache_key = f"purchase:attendees:{idempotency_key_str}"
                            attendees_data = await cache_get(attendees_cache_key)
                            print(f"🔍 [get_order_status] Attendees del cache: {attendees_data is not None}")
                            if attendees_data:
                                print(f"🔍 [get_order_status] ✅ Attendees recuperados del cache: {len(attendees_data)}")
                                # Guardar en BD para futuras referencias
                                order.attendees_data = attendees_data
                                await db.flush()
                        
                        # OPTIMIZACIÓN: Generar tickets en background (no bloquea respuesta)
                        # CRÍTICO: Los tickets SIEMPRE deben crearse con los datos del formulario
                        try:
                            if attendees_data:
                                # Generar tickets de forma asíncrona en background
                                from asyncio import create_task
                                create_task(
                                    self._generate_tickets_background(
                                        str(order.id),
                                        attendees_data
                                    )
                                )
                                print(f"🚀 [get_order_status] Iniciando generación de tickets en background para orden {order_id}")
                                # Responder inmediatamente sin esperar generación de tickets
                                await db.commit()
                                await db.refresh(order)
                                print(f"✅ [get_order_status] Orden actualizada, tickets se generarán en background")
                            else:
                                # Si no hay attendees, esto es un error crítico - NO crear tickets genéricos
                                raise ValueError(
                                    f"❌ ERROR CRÍTICO: No se encontraron datos de attendees para orden {order_id}. "
                                    f"Los tickets NO pueden crearse sin los datos del formulario. "
                                    f"Idempotency key: {idempotency_key_str}. "
                                    f"La orden quedará marcada como 'completed' pero SIN TICKETS. "
                                    f"Se requiere intervención manual para generar los tickets con los datos correctos."
                                )
                        except Exception as e:
                            await db.rollback()
                            # Log error pero no fallar la verificación
                            import traceback
                            print(f"❌ [get_order_status] Error generando tickets para orden {order_id}: {str(e)}")
                            print(f"❌ [get_order_status] Idempotency key: {idempotency_key_str}")
                            print(f"❌ [get_order_status] Traceback: {traceback.format_exc()}")
                            # Marcar orden como completed aunque falle la generación de tickets
                            # Usar order_id en lugar de order para evitar MissingGreenlet después del rollback
                            # Order ya está importado al inicio del archivo, no importar nuevamente
                            try:
                                stmt = select(Order).where(Order.id == order_id)
                                result = await db.execute(stmt)
                                order_for_update = result.scalar_one_or_none()
                                if order_for_update:
                                    order_for_update.status = "completed"
                                    await db.commit()
                                    print(f"⚠️  [get_order_status] Orden {order_id} marcada como completed sin tickets. Se pueden generar manualmente.")
                            except Exception as commit_error:
                                # Si incluso el commit falla, al menos loguear
                                print(f"❌ [get_order_status] Error crítico al hacer commit: {str(commit_error)}")
                                await db.rollback()
                    elif mapped_status == "cancelled":
                        await db.commit()
                        
                        # Liberar capacidad
                        for order_item in order.order_items:
                            await self.inventory_service.release_capacity(
                                db, str(order_item.event_id), order_item.quantity, "payment_failed"
                            )
                    else:
                        await db.commit()
                    
                    # Refrescar la orden para obtener los valores actualizados
                    await db.refresh(order, ["order_service_items"])
                    # Cargar servicios si no están cargados
                    if order.order_service_items:
                        for service_item in order.order_service_items:
                            if not service_item.service:
                                await db.refresh(service_item, ["service"])
                else:
                    print(f"⏳ [get_order_status] Estado sigue siendo '{order.status}'. No se requiere actualización.")
                    # Asegurar que los servicios estén cargados incluso si no hay actualización
                    await db.refresh(order, ["order_service_items"])
                    if order.order_service_items:
                        for service_item in order.order_service_items:
                            if not service_item.service:
                                await db.refresh(service_item, ["service"])
                    
            except Exception as e:
                # Si falla la verificación con Payku, log el error pero retornar el estado local
                import traceback
                # Guardar el estado antes de intentar acceder a order (puede estar en estado inválido)
                current_status = order.status if hasattr(order, 'status') else "pending"
                print(f"⚠️  [get_order_status] Error verificando estado en Payku: {str(e)}")
                print(f"⚠️  [get_order_status] Traceback: {traceback.format_exc()}")
                print(f"⚠️  [get_order_status] Retornando estado local: {current_status}")
                # Continuar con el estado local si falla la verificación
        
        # Construir respuesta de forma segura
        try:
            # Asegurar que los servicios estén cargados antes de construir la respuesta
            # Esto es importante cuando la orden ya está completada y no entra en el bloque de verificación
            if not hasattr(order, 'order_service_items') or order.order_service_items is None:
                await db.refresh(order, ["order_service_items"])
            
            # Cargar la relación service si no está cargada
            if order.order_service_items:
                for service_item in order.order_service_items:
                    if not hasattr(service_item, 'service') or service_item.service is None:
                        await db.refresh(service_item, ["service"])
            
            # Obtener servicios de la orden
            services_list = []
            if order.order_service_items:
                logger.debug(f"🔍 [get_order_status] Encontrados {len(order.order_service_items)} servicios para orden {order_id}")
                for service_item in order.order_service_items:
                    service_name = service_item.service.name if service_item.service else "Servicio"
                    logger.debug(f"🔍 [get_order_status] Servicio: {service_name}, quantity: {service_item.quantity}, unit_price: {service_item.unit_price}, final_price: {service_item.final_price}")
                    services_list.append({
                        "service_id": str(service_item.service_id),
                        "service_name": service_name,
                        "quantity": service_item.quantity,
                        "unit_price": float(service_item.unit_price),
                        "total_price": float(service_item.final_price)
                    })
            else:
                logger.debug(f"⚠️ [get_order_status] No se encontraron servicios para orden {order_id}")
            
            return {
                "order_id": str(order.id),
                "status": order.status,
                "total": float(order.total),
                "currency": order.currency,
                "payment_provider": order.payment_provider,
                "payment_reference": order.payment_reference,
                "created_at": order.created_at,
                "paid_at": order.paid_at,
                "attendees_data": order.attendees_data,  # Incluir datos de attendees para obtener tickets
                "services": services_list if services_list else None  # Servicios adicionales comprados
            }
        except Exception as e:
            # Si hay error accediendo a order, intentar obtener datos básicos
            import traceback
            print(f"⚠️  [get_order_status] Error construyendo respuesta: {str(e)}")
            print(f"⚠️  [get_order_status] Traceback: {traceback.format_exc()}")
            # Retornar datos mínimos
            return {
                "order_id": order_id,
                "status": "pending",  # Estado por defecto si no se puede obtener
                "total": 0.0,
                "currency": "CLP",
                "payment_provider": "payku",
                "payment_reference": None,
                "created_at": None,
                "paid_at": None
        }
    
    async def _generate_tickets(
        self,
        db: AsyncSession,
        order: Order,
        attendees_data: Optional[List[Dict]] = None,
        ticket_status: str = "issued"
    ) -> List[Ticket]:
        """
        Generar tickets después de pago exitoso o para transferencias bancarias
        
        Args:
            db: Sesión de base de datos
            order: Orden
            attendees_data: Datos de attendees (opcional, si no se proporciona se busca en BD o cache)
            ticket_status: Estado inicial de los tickets ("issued" para Mercado Pago, "pending" para transferencias)
        
        Returns:
            Lista de tickets generados
        """
        # PRIORIDAD 1: Si no se proporcionan attendees_data, intentar recuperarlos de la base de datos
        if not attendees_data:
            if order.attendees_data:
                attendees_data = order.attendees_data
                print(f"🔍 [_generate_tickets] ✅ Attendees recuperados de la base de datos: {len(attendees_data)}")
        
        # PRIORIDAD 2: Si no están en BD, intentar desde cache usando idempotency_key
        if not attendees_data:
            if order.idempotency_key:
                idempotency_key_str = str(order.idempotency_key)
                attendees_cache_key = f"purchase:attendees:{idempotency_key_str}"
                attendees_data = await cache_get(attendees_cache_key)
                if attendees_data:
                    print(f"🔍 [_generate_tickets] ✅ Attendees recuperados del cache: {len(attendees_data)}")
                    # Guardar en BD para futuras referencias
                    order.attendees_data = attendees_data
                    await db.flush()
            
            if not attendees_data:
                raise ValueError(f"No se encontraron datos de attendees para orden {order.id}")
        
        tickets = []
        # --- COMISIONES BLOQUE COMPLETO - COMENTADO TEMPORALMENTE ---
        # Las comisiones ya están incluidas en el precio del ticket por los administradores
        # commission_total = 0.0
        # ------------------------------------
        attendee_index = 0  # Índice global para rastrear qué attendee corresponde a cada ticket
        
        # CRÍTICO: Cargar order_items explícitamente desde la base de datos
        # NO usar order.order_items directamente para evitar lazy loading y MissingGreenlet
        stmt_order_items = select(OrderItem).where(OrderItem.order_id == order.id)
        result_order_items = await db.execute(stmt_order_items)
        order_items_list = result_order_items.scalars().all()
        
        if not order_items_list:
            raise ValueError(f"No se encontraron order_items para la orden {order.id}")
        
        # Obtener order items
        for order_item in order_items_list:
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
                    status=ticket_status,  # "issued" para Mercado Pago, "pending" para transferencias
                    issued_at=datetime.utcnow() if ticket_status == "issued" else datetime.utcnow()  # Siempre establecer issued_at
                )
                db.add(ticket)
                await db.flush()
                
                # Si es niño, crear detalles de niño
                if attendee_data.get("is_child") and attendee_data.get("child_details"):
                    child_details_data = attendee_data["child_details"]
                    await self._create_child_details(db, ticket, child_details_data)
                
                # --- COMISIONES BLOQUE COMPLETO - COMENTADO TEMPORALMENTE ---
                # Las comisiones ya están incluidas en el precio del ticket por los administradores
                # Calcular comisión: 1500 CLP por cada entrada (adulto o niño)
                # commission_amount = 1500.0  # CLP por entrada
                # 
                # commission_total += commission_amount
                # 
                # # Crear registro de comisión
                # commission = OrderCommission(
                #     id=uuid.uuid4(),
                #     order_id=order.id,
                #     ticket_id=ticket.id,
                #     ticket_type="child" if attendee_data.get("is_child") else "adult",
                #     commission_amount=commission_amount
                # )
                # db.add(commission)
                # ------------------------------------
                
                tickets.append(ticket)
        
        # --- COMISIONES BLOQUE COMPLETO - COMENTADO TEMPORALMENTE ---
        # Las comisiones ya están incluidas en el precio del ticket por los administradores
        # Actualizar commission_total en la orden
        # order.commission_total = commission_total
        # ------------------------------------
        await db.flush()
        
        # ✅ ACTUALIZAR capacity_available de los eventos
        # Agrupar tickets por evento para actualizar capacity_available correctamente
        from collections import defaultdict
        tickets_by_event = defaultdict(int)
        for ticket in tickets:
            tickets_by_event[ticket.event_id] += 1
        
        # Actualizar capacity_available para cada evento
        for event_id, tickets_count in tickets_by_event.items():
            stmt_event = select(Event).where(Event.id == event_id)
            result_event = await db.execute(stmt_event)
            event = result_event.scalar_one_or_none()
            
            if event:
                # Calcular capacity_available correctamente: capacity_total - tickets_issued
                # Contar todos los tickets emitidos (status = 'issued') para este evento
                stmt_tickets_count = select(func.count(Ticket.id)).where(
                    Ticket.event_id == event_id,
                    Ticket.status == 'issued'
                )
                result_tickets_count = await db.execute(stmt_tickets_count)
                total_tickets_issued = result_tickets_count.scalar() or 0
                
                # Calcular capacity_available basándose en capacity_total - tickets_issued
                new_capacity_available = max(0, event.capacity_total - total_tickets_issued)
                old_capacity_available = event.capacity_available
                event.capacity_available = new_capacity_available
                
                print(f"✅ [_generate_tickets] Actualizado capacity_available para evento {event_id}: {old_capacity_available} -> {new_capacity_available} (capacity_total: {event.capacity_total}, tickets_issued: {total_tickets_issued})")
                await db.flush()
            else:
                print(f"⚠️  [_generate_tickets] No se encontró el evento {event_id} para actualizar capacity_available")
        
        # Enviar emails con tickets (solo si el status es "issued", no para "pending")
        if ticket_status == "issued" and tickets:
            try:
                await self._send_ticket_emails(db, order, tickets)
            except Exception as e:
                # No fallar la generación de tickets si el email falla
                logger.error(f"Error enviando emails de tickets para orden {order.id}: {e}", exc_info=True)
                print(f"⚠️  [_generate_tickets] Error enviando emails: {e}")
        
        return tickets
    
    async def _send_ticket_emails(
        self,
        db: AsyncSession,
        order: Order,
        tickets: List[Ticket]
    ):
        """
        Enviar emails con tickets a los asistentes
        
        Agrupa tickets por email y envía un email por cada destinatario
        """
        from collections import defaultdict
        from datetime import datetime
        
        # Agrupar tickets por email
        tickets_by_email = defaultdict(list)
        for ticket in tickets:
            if ticket.holder_email:
                tickets_by_email[ticket.holder_email.lower().strip()].append(ticket)
        
        if not tickets_by_email:
            logger.warning(f"No hay emails para enviar tickets de orden {order.id}")
            return
        
        # Obtener información del evento (asumimos que todos los tickets son del mismo evento)
        if not tickets:
            return
        
        first_ticket = tickets[0]
        stmt_event = select(Event).where(Event.id == first_ticket.event_id)
        result_event = await db.execute(stmt_event)
        event = result_event.scalar_one_or_none()
        
        if not event:
            logger.warning(f"No se encontró el evento {first_ticket.event_id} para enviar emails")
            return
        
        # Formatear fecha del evento
        event_date_str = "Fecha no especificada"
        event_location_str = event.location_text or "Ubicación no especificada"
        
        if event.starts_at:
            try:
                if isinstance(event.starts_at, str):
                    event_datetime = datetime.fromisoformat(event.starts_at.replace("Z", "+00:00"))
                else:
                    event_datetime = event.starts_at
                
                # Formatear fecha en español
                event_date_str = event_datetime.strftime("%d de %B, %Y")
                # Reemplazar nombres de meses en inglés por español
                months_es = {
                    "January": "Enero", "February": "Febrero", "March": "Marzo",
                    "April": "Abril", "May": "Mayo", "June": "Junio",
                    "July": "Julio", "August": "Agosto", "September": "Septiembre",
                    "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
                }
                for en, es in months_es.items():
                    event_date_str = event_date_str.replace(en, es)
            except Exception as e:
                logger.warning(f"Error formateando fecha del evento: {e}")
        
        # Inicializar servicio de email
        email_service = EmailService()
        
        # Enviar un email por cada destinatario
        for email, user_tickets in tickets_by_email.items():
            try:
                # Obtener nombre del primer ticket (o usar un nombre genérico)
                first_ticket = user_tickets[0]
                attendee_name = f"{first_ticket.holder_first_name} {first_ticket.holder_last_name}".strip()
                if not attendee_name:
                    attendee_name = "Estimado/a"
                
                # Enviar email con todos los tickets de este usuario
                # Por ahora enviamos un email por ticket, pero podríamos agruparlos
                for ticket in user_tickets:
                    success = await email_service.send_ticket_email(
                        to_email=email,
                        attendee_name=attendee_name,
                        event_name=event.name,
                        event_date=event_date_str,
                        event_location=event_location_str,
                        ticket_id=str(ticket.id)[:8].upper(),  # Mostrar solo primeros 8 caracteres
                        qr_signature=ticket.qr_signature  # Pasar QR signature para generar imagen
                    )
                    
                    if success:
                        logger.info(f"Email enviado exitosamente a {email} para ticket {ticket.id}")
                    else:
                        logger.error(f"Error enviando email a {email} para ticket {ticket.id}")
                
            except Exception as e:
                logger.error(f"Error enviando email a {email}: {e}", exc_info=True)
    
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
            try:
                if isinstance(child_details_data["birth_date"], str):
                    # Intentar parsear como ISO format
                    if "T" in child_details_data["birth_date"]:
                        fecha_nacimiento = datetime.fromisoformat(child_details_data["birth_date"].replace("Z", "+00:00")).date()
                    else:
                        fecha_nacimiento = datetime.fromisoformat(child_details_data["birth_date"]).date()
                elif isinstance(child_details_data["birth_date"], datetime):
                    fecha_nacimiento = child_details_data["birth_date"].date()
                elif isinstance(child_details_data["birth_date"], date):
                    fecha_nacimiento = child_details_data["birth_date"]
            except (ValueError, AttributeError) as e:
                print(f"Error parseando birth_date: {e}, valor: {child_details_data.get('birth_date')}")
                fecha_nacimiento = date.today()  # Usar fecha por defecto si falla
            
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
            medications = child_details_data["medications"]
            # Asegurar que medications es una lista
            if not isinstance(medications, list):
                medications = []
            
            for med_data in medications:
                # Asegurar que med_data es un diccionario
                if not isinstance(med_data, dict):
                    continue
                    
                medication = TicketChildMedication(
                    id=uuid.uuid4(),
                    ticket_child_id=child_detail.id,
                    nombre_medicamento=med_data.get("name", ""),
                    frecuencia=med_data.get("frequency", ""),
                    observaciones=med_data.get("notes")
                )
                db.add(medication)
        
        return child_detail
    
    async def _generate_tickets_background(
        self,
        order_id: str,
        attendees_data: List[Dict]
    ):
        """
        Genera tickets de forma asíncrona en background.
        No bloquea la respuesta del endpoint.
        
        Args:
            order_id: ID de la orden (string)
            attendees_data: Lista de datos de attendees
        """
        from shared.database.connection import async_session_maker
        from uuid import UUID
        
        try:
            # Crear nueva sesión de BD para background task
            if async_session_maker is None:
                print(f"❌ [BACKGROUND] Database no inicializada, no se pueden generar tickets en background")
                return
            
            async with async_session_maker() as db:
                try:
                    # Buscar orden
                    order = await db.get(Order, UUID(order_id))
                    if not order:
                        print(f"❌ [BACKGROUND] Orden {order_id} no encontrada para generar tickets")
                        return
                    
                    # Verificar que la orden sigue siendo "completed"
                    if order.status != "completed":
                        print(f"⚠️  [BACKGROUND] Orden {order_id} no está completada (status: {order.status}), saltando generación de tickets")
                        return
                    
                    # Verificar que no tenga tickets ya generados
                    stmt_tickets = select(Ticket).join(OrderItem).where(OrderItem.order_id == order.id)
                    result_tickets = await db.execute(stmt_tickets)
                    existing_tickets = result_tickets.scalars().all()
                    
                    if existing_tickets:
                        print(f"⚠️  [BACKGROUND] Orden {order_id} ya tiene {len(existing_tickets)} tickets, saltando generación")
                        return
                    
                    # Generar tickets
                    await self._generate_tickets(
                        db,
                        order,
                        ticket_status="issued",
                        attendees_data=attendees_data
                    )
                    await db.commit()
                    print(f"✅ [BACKGROUND] Tickets generados exitosamente para orden {order_id}")
                    
                except Exception as e:
                    await db.rollback()
                    import traceback
                    print(f"❌ [BACKGROUND] Error generando tickets para orden {order_id}: {str(e)}")
                    print(f"❌ [BACKGROUND] Traceback: {traceback.format_exc()}")
        except Exception as e:
            import traceback
            print(f"❌ [BACKGROUND] Error crítico en background task: {str(e)}")
            print(f"❌ [BACKGROUND] Traceback: {traceback.format_exc()}")
    
    def _generate_idempotency_key(self, request: PurchaseRequest) -> str:
        """Generar clave de idempotencia"""
        # Incluir emails en la clave para mejor unicidad
        emails = ",".join([att.email.lower().strip() for att in request.attendees if att.email])
        user_id = request.user_id or "anonymous"
        data = f"{user_id}:{request.event_id}:{len(request.attendees)}:{emails}"
        return hashlib.sha256(data.encode()).hexdigest()

