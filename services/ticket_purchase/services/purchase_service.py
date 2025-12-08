"""Servicio principal de compra de tickets"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
from shared.cache.redis_client import cache_get, cache_set


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
        
        print(f"[DEBUG SERVICE] Payment method recibido: {payment_method}")
        print(f"[DEBUG SERVICE] Is bank transfer: {is_bank_transfer}")
        print(f"[DEBUG SERVICE] Is payku: {is_payku}")
        
        # Generar idempotency_key base (sin payment_method)
        base_idempotency_key = request.idempotency_key or self._generate_idempotency_key(request)
        
        # Incluir payment_method en el idempotency_key para que sean únicos por método de pago
        # Esto evita conflictos cuando el mismo usuario intenta comprar con diferentes métodos
        import hashlib
        idempotency_key = hashlib.sha256(f"{base_idempotency_key}:{payment_method}".encode()).hexdigest()
        
        print(f"[DEBUG SERVICE] Base idempotency_key: {base_idempotency_key}")
        print(f"[DEBUG SERVICE] Final idempotency_key (con payment_method): {idempotency_key}")
        
        # Incluir payment_method en el cache key para diferenciar por método de pago
        cache_key = f"purchase:idempotency:{idempotency_key}"
        
        # Verificar idempotencia en cache
        cached = await cache_get(cache_key)
        if cached:
            print(f"[DEBUG SERVICE] Orden encontrada en cache: {cached}")
            
            # Si es Payku, verificar que la transacción aún sea válida
            if is_payku and cached.get("transaction_id"):
                try:
                    transaction_data = self.payku_service.verify_transaction(cached["transaction_id"])
                    transaction_status = transaction_data.get("status", "").lower()
                    
                    print(f"[DEBUG SERVICE] Estado de transacción Payku en cache: {transaction_status}")
                    
                    # Si la transacción ya fue pagada o rechazada, invalidar cache y continuar
                    if transaction_status in ["success", "completed", "approved", "failed", "rejected", "cancelled"]:
                        print(f"[WARNING] Transacción Payku en cache ya fue procesada ({transaction_status}). Invalidando cache...")
                        from shared.cache.redis_client import cache_delete
                        await cache_delete(cache_key)
                        cached = None  # Continuar con la creación/verificación normal
                    # Si está pendiente, usar el cache
                    elif transaction_status in ["pending"]:
                        print(f"[DEBUG SERVICE] Transacción Payku aún pendiente. Usando cache.")
                        return cached
                except Exception as e:
                    print(f"[WARNING] Error verificando transacción Payku en cache: {str(e)}")
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
            print(f"[ERROR SERVICE] ❌ Error conectando a la base de datos: {error_msg}")
            print(f"[ERROR SERVICE] ❌ Esto puede ser un problema temporal de red o la base de datos está caída")
            print(f"[ERROR SERVICE] ❌ Verifica que la base de datos esté disponible y que DATABASE_URL sea correcta")
            # Re-lanzar el error para que el endpoint retorne 500
            raise Exception(f"Error de conexión a la base de datos: {error_msg}. Verifica que la base de datos esté disponible.")
        
        if existing_order:
            print(f"[DEBUG SERVICE] Orden existente encontrada: {existing_order.id}")
            print(f"[DEBUG SERVICE] Payment provider de orden existente: {existing_order.payment_provider}")
            
            # Si el método de pago del request NO coincide con el de la orden existente,
            # crear una nueva orden (no usar idempotencia en este caso)
            if existing_order.payment_provider != payment_method:
                print(f"[DEBUG SERVICE] Método de pago diferente. Creando nueva orden...")
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
                            
                            print(f"[DEBUG SERVICE] Estado de transacción Payku existente: {transaction_status}")
                            
                            # Si la transacción ya fue pagada, rechazada o cancelada, invalidar orden y crear nueva
                            if transaction_status in ["success", "completed", "approved", "failed", "rejected", "cancelled"]:
                                print(f"[WARNING] Transacción Payku {existing_order.payment_reference} ya fue procesada ({transaction_status}). Invalidando orden y creando nueva...")
                                # Invalidar cache y orden existente para crear una nueva orden
                                from shared.cache.redis_client import cache_delete
                                await cache_delete(cache_key)
                                # Generar nuevo idempotency_key para la nueva orden (agregar timestamp)
                                import time
                                timestamp = int(time.time() * 1000)  # Timestamp en milisegundos
                                idempotency_key = hashlib.sha256(f"{base_idempotency_key}:{payment_method}:{timestamp}".encode()).hexdigest()
                                cache_key = f"purchase:idempotency:{idempotency_key}"  # Actualizar cache_key también
                                print(f"[DEBUG SERVICE] Nuevo idempotency_key generado: {idempotency_key}")
                                existing_order = None  # Forzar creación de nueva orden
                                payment_link = None
                            else:
                                # Transacción pendiente, pero Payku no devuelve el payment_link en verify_transaction
                                # Necesitamos crear una nueva transacción con un nuevo order_id
                                print(f"[WARNING] Transacción Payku pendiente pero no tenemos payment_link. Invalidando orden para crear nueva...")
                                from shared.cache.redis_client import cache_delete
                                await cache_delete(cache_key)
                                # Generar nuevo idempotency_key para la nueva orden (agregar timestamp)
                                import time
                                timestamp = int(time.time() * 1000)  # Timestamp en milisegundos
                                idempotency_key = hashlib.sha256(f"{base_idempotency_key}:{payment_method}:{timestamp}".encode()).hexdigest()
                                cache_key = f"purchase:idempotency:{idempotency_key}"  # Actualizar cache_key también
                                print(f"[DEBUG SERVICE] Nuevo idempotency_key generado: {idempotency_key}")
                                existing_order = None  # Forzar creación de nueva orden
                                payment_link = None
                        except Exception as e:
                            print(f"[WARNING] No se pudo verificar transacción Payku existente: {str(e)}")
                            print(f"[WARNING] Invalidando orden y creando nueva...")
                            # Si falla la verificación, invalidar y crear nueva orden
                            from shared.cache.redis_client import cache_delete
                            await cache_delete(cache_key)
                            # Generar nuevo idempotency_key para la nueva orden (agregar timestamp)
                            import time
                            timestamp = int(time.time() * 1000)  # Timestamp en milisegundos
                            idempotency_key = hashlib.sha256(f"{base_idempotency_key}:{payment_method}:{timestamp}".encode()).hexdigest()
                            cache_key = f"purchase:idempotency:{idempotency_key}"  # Actualizar cache_key también
                            print(f"[DEBUG SERVICE] Nuevo idempotency_key generado: {idempotency_key}")
                            existing_order = None
                            payment_link = None
                    
                    # Si no tiene payment_reference, invalidar y crear nueva orden
                    if not existing_order or not payment_link:
                        if existing_order:
                            print(f"[WARNING] Orden existente sin payment_reference válido. Invalidando y creando nueva orden...")
                            from shared.cache.redis_client import cache_delete
                            await cache_delete(cache_key)
                            # Generar nuevo idempotency_key para la nueva orden (agregar timestamp)
                            import time
                            timestamp = int(time.time() * 1000)  # Timestamp en milisegundos
                            idempotency_key = hashlib.sha256(f"{base_idempotency_key}:{payment_method}:{timestamp}".encode()).hexdigest()
                            cache_key = f"purchase:idempotency:{idempotency_key}"  # Actualizar cache_key también
                            print(f"[DEBUG SERVICE] Nuevo idempotency_key generado: {idempotency_key}")
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
                                    print(f"[WARNING] Preferencia existente tiene back_urls inválidas, creando nueva preferencia")
                                    print(f"[WARNING] back_urls actuales: {back_urls}")
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
                            print(f"[WARNING] No se pudo obtener payment_link de preferencia existente: {str(e)}")
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
                            print(f"[ERROR] Error creando preferencia para orden existente: {str(e)}")
                            import traceback
                            print(traceback.format_exc())
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
        
        # Crear orden - user_id es opcional ahora
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
        
        # Preparar datos de attendees
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
        
        # Guardar attendees en cache para recuperarlos después del pago
        # Necesario para pagos asíncronos (Mercado Pago y Payku) donde el webhook llega después
        # Para transferencias bancarias, creamos tickets inmediatamente, no necesitamos cache
        if not is_bank_transfer and request.idempotency_key:
            attendees_cache_key = f"purchase:attendees:{request.idempotency_key}"
            await cache_set(attendees_cache_key, attendees_data, expire=86400)  # 24 horas
            print(f"[DEBUG SERVICE] ✅ Datos de attendees guardados en cache: {attendees_cache_key}")
            print(f"[DEBUG SERVICE]   - Attendees count: {len(attendees_data)}")
            print(f"[DEBUG SERVICE]   - Payment method: {payment_method}")
        
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
                print(f"Error creando tickets para transferencia bancaria: {str(e)}")
                print(f"Traceback: {error_trace}")
                await self.inventory_service.release_capacity(
                    db, request.event_id, total_quantity, "ticket_creation_failed"
                )
                await db.rollback()
                raise ValueError(f"Error creando tickets: {str(e)}")
        
        # Si es Payku, crear transacción de pago
        elif is_payku:
            try:
                print(f"[DEBUG] Creando transacción de Payku para orden {order.id}")
                print(f"[DEBUG] Payment method recibido: {payment_method}")
                
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
                print(f"[ERROR] Error creando transacción de pago: {str(e)}")
                print(f"[ERROR] Traceback: {error_trace}")
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
            
            print(f"[DEBUG] Response final: {response}")
            
            # Guardar en cache para idempotencia
            await cache_set(cache_key, response, expire=3600)
            
            return response
        
        # Si es Mercado Pago, crear preferencia de pago
        else:
            try:
                print(f"[DEBUG] Creando preferencia de Mercado Pago para orden {order.id}")
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
                
                # Agregar comisión de servicio por cada entrada
                # Comisión: 1500 CLP por cada entrada (adulto o niño)
                COMMISSION_PER_TICKET = 1500.0
                
                if total_quantity > 0:
                    items.append({
                        "title": "Comisión de servicio",
                        "description": f"Comisión de procesamiento por entrada ({total_quantity} entrada(s))",
                        "quantity": total_quantity,  # Una comisión por cada entrada
                        "unit_price": float(COMMISSION_PER_TICKET)  # 1500 CLP por entrada
                    })
                
                commission_total = total_quantity * COMMISSION_PER_TICKET
                print(f"[DEBUG] Items para preferencia: {items}")
                print(f"[DEBUG] Comisiones: {total_quantity} entrada(s) × {COMMISSION_PER_TICKET} CLP = {commission_total} CLP")
                
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
            
            print(f"[DEBUG] Response final: {response}")
            
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
        order: Order,
        attendees_data: Optional[List[Dict]] = None,
        ticket_status: str = "issued"
    ) -> List[Ticket]:
        """
        Generar tickets después de pago exitoso o para transferencias bancarias
        
        Args:
            db: Sesión de base de datos
            order: Orden
            attendees_data: Datos de attendees (opcional, si no se proporciona se busca en cache)
            ticket_status: Estado inicial de los tickets ("issued" para Mercado Pago, "pending" para transferencias)
        
        Returns:
            Lista de tickets generados
        """
        # Si no se proporcionan attendees_data, recuperarlos del cache usando idempotency_key
        if not attendees_data:
            if order.idempotency_key:
                attendees_cache_key = f"purchase:attendees:{order.idempotency_key}"
                attendees_data = await cache_get(attendees_cache_key)
            
            if not attendees_data:
                raise ValueError(f"No se encontraron datos de attendees para orden {order.id}")
        
        tickets = []
        commission_total = 0.0
        attendee_index = 0  # Índice global para rastrear qué attendee corresponde a cada ticket
        
        # Obtener order items - si order.order_items está vacío, cargarlos explícitamente
        if not order.order_items:
            # Cargar order_items explícitamente desde la base de datos
            stmt_order_items = select(OrderItem).where(OrderItem.order_id == order.id)
            result_order_items = await db.execute(stmt_order_items)
            order_items_list = result_order_items.scalars().all()
        else:
            order_items_list = list(order.order_items)
        
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
                
                # Calcular comisión: 1500 CLP por cada entrada (adulto o niño)
                commission_amount = 1500.0  # CLP por entrada
                
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
    
    def _generate_idempotency_key(self, request: PurchaseRequest) -> str:
        """Generar clave de idempotencia"""
        # Incluir emails en la clave para mejor unicidad
        emails = ",".join([att.email.lower().strip() for att in request.attendees if att.email])
        user_id = request.user_id or "anonymous"
        data = f"{user_id}:{request.event_id}:{len(request.attendees)}:{emails}"
        return hashlib.sha256(data.encode()).hexdigest()

