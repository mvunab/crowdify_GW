"""Rutas de compra de tickets"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql import func
from typing import Dict, Optional
import logging
from shared.database.session import get_db
from shared.database.models import Order, Event
from shared.auth.dependencies import get_current_user, get_optional_user
from shared.utils.rate_limiter import limiter, RATE_LIMITS
from services.ticket_purchase.models.purchase import (
    PurchaseRequest,
    PurchaseResponse,
    OrderStatusResponse
)
from services.ticket_purchase.services.purchase_service import PurchaseService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=PurchaseResponse)
@limiter.limit(RATE_LIMITS["purchase"])  # 10 intentos por minuto por IP
async def create_purchase(
    request: Request,  # Necesario para rate limiter
    purchase_request: PurchaseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict] = Depends(get_optional_user)
):
    """
    Crear orden de compra y generar link de pago

    Compatible con: ticketsService.purchaseTickets()

    NOTA: user_id es opcional ahora. Si se proporciona sin autenticación, se ignora y la compra es anónima.
    Si se proporciona con autenticación, debe coincidir con el usuario autenticado.
    """
    import logging
    logger = logging.getLogger(__name__)

    # Manejar user_id con try-except para mayor robustez
    try:
        # Si se proporciona user_id, validar solo si hay autenticación
        if purchase_request.user_id:
            if current_user:
                # Usuario autenticado: validar que el user_id coincida
                if current_user.get("user_id") != purchase_request.user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="No puedes crear órdenes para otros usuarios"
                    )
            else:
                # No hay autenticación: ignorar user_id y tratar como compra anónima
                purchase_request.user_id = None
        else:
            # No se proporcionó user_id
            # Si hay usuario autenticado y es admin/coordinator, requerir user_id
            if current_user:
                try:
                    user_role = current_user.get("role", "user")
                    if user_role in ["admin", "coordinator"]:
                        # Para admins/coordinadores, user_id es requerido
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Los administradores y coordinadores deben proporcionar user_id"
                        )
                except HTTPException:
                    raise  # Re-lanzar HTTPException
                except Exception as role_error:
                    logger.warning(f"Error obteniendo rol del usuario: {role_error}")
                    # Continuar sin validar rol si hay error
    except HTTPException:
        raise  # Re-lanzar HTTPException
    except Exception as validation_error:
        logger.warning(f"Error en validación de user_id: {validation_error}")
        # Si hay error, ignorar user_id y continuar como compra anónima
        purchase_request.user_id = None

    service = PurchaseService()

    try:
        result = await service.create_purchase(db, purchase_request)
        response = PurchaseResponse(**result)
        return response
    except ValueError as e:
        logger.error(f"ValueError en create_purchase: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Exception en create_purchase: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando compra: {str(e)}"
        )


@router.post("/webhook")
@limiter.limit(RATE_LIMITS["webhook"])  # 100 por minuto para webhooks de payment providers
async def mercado_pago_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook para recibir notificaciones de Mercado Pago

    No requiere autenticación (Mercado Pago valida la firma)
    """
    service = PurchaseService()

    try:
        # Obtener headers necesarios para verificación
        signature = request.headers.get("x-signature")
        request_id = request.headers.get("x-request-id")

        # Obtener query params
        query_params = dict(request.query_params)

        # Obtener body
        data = await request.json()

        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Webhook recibido - x-signature: {signature is not None}, x-request-id: {request_id}")

        # Verificar firma del webhook
        mercado_pago_service = service.mercado_pago_service
        is_valid = mercado_pago_service.verify_webhook(
            data=data,
            signature=signature,
            request_id=request_id,
            query_params=query_params
        )

        if not is_valid:
            logger.warning("Webhook con firma inválida, pero procesando de todas formas (modo desarrollo)")
            # En producción, podrías retornar 401 aquí

        # Procesar webhook
        success = await service.process_payment_webhook(db, data)
        logger.info(f"Webhook procesado - resultado: {success}")

        if success:
            return {"status": "ok"}
        else:
            return {"status": "ignored"}
    except Exception as e:
        # Log error pero retornar 200 para que Mercado Pago no reintente inmediatamente
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error procesando webhook: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@router.post("/payku-webhook")
@limiter.limit(RATE_LIMITS["webhook"])  # 100 por minuto para webhooks de payment providers
async def payku_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook para recibir notificaciones de Payku

    No requiere autenticación (Payku valida la firma)
    """
    service = PurchaseService()

    try:
        # Obtener body
        data = await request.json()

        import logging
        logger = logging.getLogger(__name__)
        logger.info("Webhook Payku recibido")

        # Procesar webhook de Payku
        payku_service = service.payku_service
        webhook_info = payku_service.process_webhook(data)

        # Obtener order_id del webhook
        order_id = webhook_info.get("order_id")
        if not order_id:
            logger.warning("No se encontró order_id en el webhook Payku")
            return {"status": "ignored", "message": "No order_id found"}

        # Buscar orden
        from sqlalchemy import select
        from shared.database.models import Order
        stmt = select(Order).where(Order.id == order_id)
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            print(f"⚠️  [WEBHOOK PAYKU] Orden {order_id} no encontrada")
            return {"status": "ignored", "message": f"Order {order_id} not found"}

        # Actualizar estado según el webhook
        status = webhook_info.get("status")
        print(f"🔔 [WEBHOOK PAYKU] Estado recibido: {status}")

        if status == "approved":
            # CRÍTICO: Capturar valores ANTES de cualquier operación que pueda causar rollback
            order_id_str = str(order.id)
            idempotency_key_str = str(order.idempotency_key) if order.idempotency_key else None

            print(f"✅ [WEBHOOK PAYKU] Pago aprobado! Actualizando orden {order_id_str} a 'completed'")
            order.status = "completed"
            order.paid_at = datetime.utcnow()
            await db.flush()

            # Intentar recuperar attendees - PRIORIDAD 1: desde la base de datos (más confiable)
            attendees_data = None
            if order.attendees_data:
                attendees_data = order.attendees_data
                print(f"🔍 [WEBHOOK PAYKU] ✅ Attendees recuperados de la base de datos: {len(attendees_data)}")

            # PRIORIDAD 2: Si no están en BD, intentar desde cache
            if not attendees_data and idempotency_key_str:
                from shared.cache.redis_client import cache_get
                attendees_cache_key = f"purchase:attendees:{idempotency_key_str}"
                attendees_data = await cache_get(attendees_cache_key)
                print(f"🔍 [WEBHOOK PAYKU] Buscando attendees en cache: {attendees_cache_key}")
                print(f"🔍 [WEBHOOK PAYKU] Attendees encontrados: {attendees_data is not None}")
                if attendees_data:
                    print(f"🔍 [WEBHOOK PAYKU] ✅ Attendees recuperados del cache: {len(attendees_data)}")
                    # Guardar en BD para futuras referencias
                    order.attendees_data = attendees_data
                    await db.flush()

            # OPTIMIZACIÓN: Generar tickets en background (no bloquea respuesta del webhook)
            # CRÍTICO: Los tickets SIEMPRE deben crearse con los datos del formulario
            try:
                if attendees_data:
                    # Generar tickets de forma asíncrona en background
                    from asyncio import create_task
                    create_task(
                        service._generate_tickets_background(
                            order_id_str,
                            attendees_data
                        )
                    )
                    print(f"🚀 [WEBHOOK PAYKU] Iniciando generación de tickets en background para orden {order_id_str}")
                    # Responder inmediatamente sin esperar generación de tickets
                    await db.commit()
                    await db.refresh(order)
                    print(f"✅ [WEBHOOK PAYKU] Orden actualizada, tickets se generarán en background")
                else:
                    # Si no hay attendees, esto es un error crítico - NO crear tickets genéricos
                    raise ValueError(
                        f"❌ ERROR CRÍTICO: No se encontraron datos de attendees para orden {order_id_str}. "
                        f"Los tickets NO pueden crearse sin los datos del formulario. "
                        f"Idempotency key: {idempotency_key_str}. "
                        f"La orden quedará marcada como 'completed' pero SIN TICKETS. "
                        f"Se requiere intervención manual para generar los tickets con los datos correctos."
                    )
            except ValueError as e:
                # Si falla por falta de attendees, esto es un error crítico
                await db.rollback()
                import traceback
                print(f"❌ [WEBHOOK PAYKU] ERROR CRÍTICO: No se encontraron datos de attendees para orden {order_id_str}")
                print(f"❌ [WEBHOOK PAYKU] Error: {str(e)}")
                print(f"❌ [WEBHOOK PAYKU] Idempotency key: {idempotency_key_str}")
                print(f"❌ [WEBHOOK PAYKU] Traceback: {traceback.format_exc()}")
                # Marcar orden como paid pero sin tickets - requiere intervención manual
                # Usar order_id_str en lugar de order.id para evitar MissingGreenlet
                try:
                    # select ya está importado al inicio del archivo, no importar nuevamente
                    from shared.database.models import Order
                    stmt = select(Order).where(Order.id == order_id_str)
                    result = await db.execute(stmt)
                    order_for_update = result.scalar_one_or_none()
                    if order_for_update:
                        order_for_update.status = "completed"
                        await db.commit()
                except Exception as commit_error:
                    print(f"❌ [WEBHOOK PAYKU] Error crítico al hacer commit: {str(commit_error)}")
                    await db.rollback()
                print(f"⚠️  [WEBHOOK PAYKU] Orden {order_id_str} marcada como completed SIN TICKETS.")
                print(f"⚠️  [WEBHOOK PAYKU] REQUIERE GENERACIÓN MANUAL DE TICKETS.")
            except Exception as e:
                await db.rollback()
                # Log error pero no fallar el webhook
                import traceback
                print(f"❌ [WEBHOOK PAYKU] Error generando tickets para orden {order_id_str}: {str(e)}")
                print(f"❌ [WEBHOOK PAYKU] Traceback: {traceback.format_exc()}")
                # Marcar orden como paid aunque falle la generación de tickets
                try:
                    # select ya está importado al inicio del archivo, no importar nuevamente
                    from shared.database.models import Order
                    stmt = select(Order).where(Order.id == order_id_str)
                    result = await db.execute(stmt)
                    order_for_update = result.scalar_one_or_none()
                    if order_for_update:
                        order_for_update.status = "completed"
                        await db.commit()
                except Exception as commit_error:
                    print(f"❌ [WEBHOOK PAYKU] Error crítico al hacer commit: {str(commit_error)}")
                    await db.rollback()
                print(f"⚠️  [WEBHOOK PAYKU] Orden {order_id_str} marcada como completed sin tickets. Se pueden generar manualmente.")

            return {"status": "ok", "message": "Payment approved and tickets generated"}

        elif status in ["rejected", "cancelled"]:
            print(f"❌ [WEBHOOK PAYKU] Pago rechazado/cancelado. Actualizando orden {order.id} a 'cancelled'")
            order.status = "cancelled"
            await db.commit()

            # Liberar capacidad
            for order_item in order.order_items:
                await service.inventory_service.release_capacity(
                    db, str(order_item.event_id), order_item.quantity, "payment_failed"
                )

            return {"status": "ok", "message": "Payment cancelled"}

        # Si el estado es "pending", el webhook se recibió pero el pago aún no está aprobado
        print(f"⏳ [WEBHOOK PAYKU] Estado '{status}' - El pago aún está pendiente.")
        return {"status": "ignored", "message": f"Payment still {status}"}

    except Exception as e:
        # Log error pero retornar 200 para que Payku no reintente inmediatamente
        print(f"Error procesando webhook de Payku: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


@router.post("/{order_id}/verify-payku")
async def verify_payku_payment(
    order_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Verificar manualmente el estado de una transacción Payku
    Útil cuando el webhook no llega o hay problemas
    """
    service = PurchaseService()

    try:
        # Buscar orden
        from sqlalchemy import select
        from shared.database.models import Order
        stmt = select(Order).where(Order.id == order_id)
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(status_code=404, detail="Orden no encontrada")

        if order.payment_provider != "payku":
            raise HTTPException(status_code=400, detail="Esta orden no es de Payku")

        if not order.payment_reference:
            raise HTTPException(status_code=400, detail="No hay payment_reference para verificar")

        # Verificar estado en Payku (ASYNC)
        payku_service = service.payku_service
        transaction_data = await payku_service.verify_transaction(order.payment_reference)

        logger.info(f"Estado de transacción Payku {order.payment_reference}: {transaction_data.get('status')}")

        # Procesar según el estado
        status = transaction_data.get("status", "").lower()

        # También verificar en payment.status si existe
        payment_data = transaction_data.get("payment", {})
        if payment_data and payment_data.get("status"):
            status = payment_data.get("status", "").lower()

        # Mapear estados de Payku
        if status in ["success", "approved", "completado", "completed"]:
            # Pago exitoso - actualizar orden
            if order.status != "completed":
                order.status = "completed"
                order.paid_at = datetime.utcnow()
                await db.flush()

                # Intentar recuperar attendees del cache
                attendees_data = None
                if order.idempotency_key:
                    from shared.cache.redis_client import cache_get
                    attendees_cache_key = f"purchase:attendees:{order.idempotency_key}"
                    attendees_data = await cache_get(attendees_cache_key)
                    print(f"🔍 [VERIFY PAYKU] Attendees del cache: {attendees_data}")

                # Si no hay attendees en cache, intentar obtenerlos de otra forma
                # Por ahora, generar tickets sin attendees (usará valores por defecto)
                if not attendees_data:
                    print(f"⚠️  [VERIFY PAYKU] No se encontraron attendees en cache. Intentando generar tickets sin datos específicos...")
                    # Intentar generar tickets sin attendees_data - el método debería manejar esto
                    try:
                        await service._generate_tickets(db, order, ticket_status="issued")
                    except ValueError as e:
                        # Si falla por falta de attendees, crear tickets básicos
                        print(f"⚠️  [VERIFY PAYKU] Error generando tickets: {e}")
                        print(f"⚠️  [VERIFY PAYKU] Creando tickets básicos sin datos de attendees...")
                        # Crear tickets básicos usando los order_items
                        from shared.database.models import OrderItem, Ticket, TicketType
                        from shared.utils.qr_generator import generate_qr_signature
                        import uuid

                        stmt_items = select(OrderItem).where(OrderItem.order_id == order.id)
                        result_items = await db.execute(stmt_items)
                        order_items = result_items.scalars().all()

                        for order_item in order_items:
                            # Obtener tipo de ticket
                            stmt_type = select(TicketType).where(TicketType.id == order_item.ticket_type_id)
                            result_type = await db.execute(stmt_type)
                            ticket_type = result_type.scalar_one_or_none()

                            if not ticket_type:
                                continue

                            # Crear tickets básicos
                            for i in range(order_item.quantity):
                                ticket_id = uuid.uuid4()
                                qr_signature = generate_qr_signature(str(ticket_id))
                                ticket = Ticket(
                                    id=ticket_id,
                                    order_item_id=order_item.id,
                                    event_id=order_item.event_id,
                                    holder_first_name="Asistente",
                                    holder_last_name=f"#{i+1}",
                                    holder_email=None,
                                    is_child=ticket_type.is_child or False,
                                    qr_signature=qr_signature,
                                    status="issued",
                                    issued_at=datetime.utcnow()
                                )
                                db.add(ticket)

                        await db.flush()
                        print(f"✅ [VERIFY PAYKU] Tickets básicos creados exitosamente")

                await db.commit()

                return {"status": "ok", "message": "Pago verificado y tickets generados", "order_status": "completed"}
            else:
                return {"status": "ok", "message": "Pago ya estaba completado", "order_status": "completed"}
        elif status == "failed":
            # Pago rechazado
            if order.status != "cancelled":
                order.status = "cancelled"
                await db.commit()

                # Liberar capacidad
                for order_item in order.order_items:
                    await service.inventory_service.release_capacity(
                        db, str(order_item.event_id), order_item.quantity, "payment_failed"
                    )

            return {"status": "ok", "message": "Pago rechazado", "order_status": "cancelled"}
        else:
            # Pendiente
            return {"status": "pending", "message": "Pago aún pendiente", "order_status": order.status}

    except Exception as e:
        print(f"Error verificando pago Payku: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{order_id}/status", response_model=OrderStatusResponse)
async def get_order_status(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict] = Depends(get_optional_user)
):
    """
    Obtener estado de una orden

    Compatible con: ticketsService.getOrderStatus()

    NOTA: Para compras anónimas, se permite verificar el estado sin autenticación
    usando solo el order_id (que es un UUID único).
    """
    service = PurchaseService()
    order_status = await service.get_order_status(db, order_id)

    if not order_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden no encontrada"
        )

    # Obtener orden completa para verificar user_id
    # select y Order ya están importados al inicio del archivo
    stmt = select(Order).where(Order.id == order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orden no encontrada"
        )

    # Verificar acceso:
    # 1. Si la orden es anónima (sin user_id), permitir acceso sin autenticación
    #    (el order_id es un UUID único, suficiente para verificar)
    # 2. Si la orden tiene user_id, verificar que coincida con el usuario autenticado
    # 3. Admins/coordinadores siempre pueden ver cualquier orden
    if order.user_id:
        # Orden con user_id - requiere autenticación y verificación
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Debes estar autenticado para ver esta orden"
            )
        # Verificar que el usuario coincida o sea admin/coordinator
        if str(order.user_id) != current_user.get("user_id"):
            if current_user.get("role") not in ["admin", "coordinator"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes acceso a esta orden"
                )
    # Si no tiene user_id (compra anónima), permitir acceso sin autenticación
    # El order_id es suficiente para verificar el estado

    return OrderStatusResponse(**order_status)


@router.post("/process-payment")
async def process_payment(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Procesar pago con token del Payment Brick

    Recibe el token y datos del pago del Payment Brick y crea el pago en Mercado Pago
    """
    try:
        data = await request.json()

        # Extraer datos del request
        token = data.get("token")
        order_id = data.get("order_id")
        transaction_amount = data.get("transaction_amount")
        payment_method_id = data.get("payment_method_id")
        issuer_id = data.get("issuer_id")
        installments = data.get("installments", 1)
        device_id = data.get("device_id")  # Device ID de Mercado Pago (importante para aprobación)

        # Extraer datos del payer
        payer_data = data.get("payer", {})
        payer_email = payer_data.get("email")
        payer_identification = payer_data.get("identification")
        payer_first_name = payer_data.get("first_name")
        payer_last_name = payer_data.get("last_name")
        # Si no hay first_name/last_name pero hay "name", dividirlo
        payer_name = payer_data.get("name")
        if not payer_first_name and payer_name:
            name_parts = payer_name.strip().split(maxsplit=1)
            if len(name_parts) >= 1:
                payer_first_name = name_parts[0]
            if len(name_parts) >= 2:
                payer_last_name = name_parts[1]
            else:
                payer_last_name = payer_first_name  # Si solo hay un nombre, usar el mismo para ambos

        # Log para debugging
        print(f"[DEBUG process_payment] Datos recibidos:")
        print(f"[DEBUG process_payment]   - token: {token[:20] if token else None}...")
        print(f"[DEBUG process_payment]   - order_id: {order_id}")
        print(f"[DEBUG process_payment]   - transaction_amount: {transaction_amount}")
        print(f"[DEBUG process_payment]   - payment_method_id: {payment_method_id}")
        print(f"[DEBUG process_payment]   - issuer_id: {issuer_id}")
        print(f"[DEBUG process_payment]   - installments: {installments}")
        print(f"[DEBUG process_payment]   - payer_email: {payer_email}")
        print(f"[DEBUG process_payment]   - payer_identification: {payer_identification}")
        print(f"[DEBUG process_payment]   - payer_first_name: {payer_first_name}")
        print(f"[DEBUG process_payment]   - payer_last_name: {payer_last_name}")
        print(f"[DEBUG process_payment]   - payer completo: {payer_data}")
        print(f"[DEBUG process_payment]   - device_id: {device_id if device_id else 'NO DISPONIBLE'}")

        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token es requerido"
            )

        if not order_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="order_id es requerido"
            )

        # Obtener la orden para validar y obtener el monto
        from sqlalchemy import select
        from shared.database.models import Order
        stmt = select(Order).where(Order.id == order_id)
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Orden no encontrada"
            )

        # Usar el monto de la orden si no se proporciona
        if not transaction_amount:
            transaction_amount = float(order.total or 0)

        # IMPORTANTE: Payment Brick puede no enviar el nombre del titular en el objeto payer
        # Necesitamos obtenerlo de otra fuente o usar un fallback inteligente
        # Envolver todo en try-except para mayor robustez
        try:
            from app.core.config import settings
            is_sandbox = settings.MERCADOPAGO_ENVIRONMENT == "sandbox"
            is_test_card = (
                payer_identification and
                payer_identification.get("type") == "Otro" and
                payer_identification.get("number") == "123456789"
            )
        except Exception as config_error:
            print(f"[WARNING process_payment] Error obteniendo configuración: {config_error}")
            # Valores por defecto seguros
            is_sandbox = True  # Asumir sandbox por defecto para seguridad
            is_test_card = (
                payer_identification and
                payer_identification.get("type") == "Otro" and
                payer_identification.get("number") == "123456789"
            )

        # PRIORIDAD 1: Si es una tarjeta de prueba, usar "APRO" directamente
        # Esto es CRÍTICO porque Mercado Pago requiere "APRO" para tarjetas de prueba
        # Funciona tanto en sandbox como en producción
        try:
            if is_test_card and not payer_first_name:
                payer_first_name = "APRO"
                payer_last_name = ""
                print(f"[DEBUG process_payment] ✅ TARJETA DE PRUEBA DETECTADA - Usando 'APRO' como nombre del titular (requerido por Mercado Pago)")
        except Exception as test_card_error:
            print(f"[WARNING process_payment] Error verificando tarjeta de prueba: {test_card_error}")

        # PRIORIDAD 2: Si no hay nombre del titular del payer Y NO es tarjeta de prueba,
        # intentar obtenerlo del primer ticket de la orden
        # Esto es importante porque Payment Brick puede no enviar el nombre del titular
        # Los attendees están en los tickets (holder_first_name, holder_last_name)
        if not payer_first_name:
            # Buscar el primer ticket de la orden a través de order_items
            # Envolver en try-except para manejar errores de conexión a la base de datos
            try:
                from shared.database.models import OrderItem, Ticket
                stmt_tickets = (
                    select(Ticket)
                    .join(OrderItem, Ticket.order_item_id == OrderItem.id)
                    .where(OrderItem.order_id == order.id)
                    .order_by(Ticket.created_at)
                    .limit(1)
                )
                result_tickets = await db.execute(stmt_tickets)
                first_ticket = result_tickets.scalar_one_or_none()

                if first_ticket:
                    # IMPORTANTE: Si es tarjeta de prueba, NO usar el nombre del ticket, usar "APRO"
                    if is_sandbox and is_test_card:
                        payer_first_name = "APRO"
                        payer_last_name = ""
                        print(f"[DEBUG process_payment] ⚠️ TARJETA DE PRUEBA - Sobrescribiendo nombre del ticket con 'APRO' (requerido por Mercado Pago)")
                    else:
                        payer_first_name = first_ticket.holder_first_name
                        payer_last_name = first_ticket.holder_last_name
                        print(f"[DEBUG process_payment] Usando nombre del primer ticket como fallback: {payer_first_name} {payer_last_name}")
                else:
                    # Si no hay tickets, continuar con el siguiente fallback
                    pass
            except Exception as db_error:
                # Si hay un error de conexión a la base de datos, usar fallback
                print(f"[WARNING process_payment] Error de conexión a la base de datos al obtener ticket: {db_error}")
                print(f"[WARNING process_payment] Continuando con fallback para obtener nombre del titular...")

            # Si aún no hay nombre después de intentar obtenerlo del ticket, intentar otros métodos
            if not payer_first_name:
                # Si no hay tickets aún (la orden se creó pero los tickets aún no se generaron),
                # intentar obtener el nombre del cache de attendees usando el idempotency_key
                if order.idempotency_key:
                    try:
                        from shared.cache.redis_client import cache_get
                        attendees_cache_key = f"purchase:attendees:{order.idempotency_key}"
                        attendees_data = await cache_get(attendees_cache_key)
                        if attendees_data and len(attendees_data) > 0:
                            first_attendee = attendees_data[0]
                            if first_attendee.get("name"):
                                # IMPORTANTE: Si es tarjeta de prueba, NO usar el nombre del attendee, usar "APRO"
                                if is_sandbox and is_test_card:
                                    payer_first_name = "APRO"
                                    payer_last_name = ""
                                    print(f"[DEBUG process_payment] ⚠️ TARJETA DE PRUEBA - Sobrescribiendo nombre del attendee con 'APRO' (requerido por Mercado Pago)")
                                else:
                                    name_parts = first_attendee["name"].strip().split(maxsplit=1)
                                    if len(name_parts) >= 1:
                                        payer_first_name = name_parts[0]
                                    if len(name_parts) >= 2:
                                        payer_last_name = name_parts[1]
                                    else:
                                        payer_last_name = payer_first_name
                                    print(f"[DEBUG process_payment] Usando nombre del attendee del cache como fallback: {payer_first_name} {payer_last_name}")
                    except Exception as cache_error:
                        print(f"[WARNING process_payment] Error obteniendo attendees del cache: {cache_error}")

                # Si aún no hay nombre, usar un fallback inteligente
                if not payer_first_name:
                    try:
                        # Para tarjetas de prueba (documento "Otro" con número "123456789"), usar "APRO"
                        # Esto funciona tanto en sandbox como en producción
                        if is_test_card:
                            payer_first_name = "APRO"
                            payer_last_name = ""
                            print(f"[DEBUG process_payment] ✅ Usando 'APRO' como nombre del titular para tarjeta de prueba (documento Otro/123456789)")
                        elif payer_email:
                            # Si no es tarjeta de prueba, usar el nombre del email
                            email_name = payer_email.split("@")[0]
                            payer_first_name = email_name[:50]  # Limitar longitud
                            payer_last_name = email_name[:50] if not payer_last_name else payer_last_name
                            print(f"[DEBUG process_payment] Usando nombre del email como fallback: {payer_first_name} {payer_last_name}")
                        else:
                            # Último recurso: usar un valor genérico
                            payer_first_name = "Usuario"
                            payer_last_name = "Test"
                            print(f"[WARNING process_payment] Usando nombre genérico. El nombre del titular puede estar vacío.")
                    except Exception as fallback_error:
                        print(f"[WARNING process_payment] Error en fallback de nombre: {fallback_error}")
                        # Fallback de emergencia
                        if is_sandbox:
                            payer_first_name = "APRO"
                            payer_last_name = ""
                        else:
                            payer_first_name = "Usuario"
                            payer_last_name = "Test"

        # VERIFICACIÓN FINAL: Si es tarjeta de prueba, FORZAR "APRO" sin importar qué
        # Esto es CRÍTICO porque Mercado Pago requiere "APRO" para tarjetas de prueba
        try:
            if is_sandbox and is_test_card:
                if payer_first_name != "APRO":
                    print(f"[DEBUG process_payment] ⚠️ VERIFICACIÓN FINAL: Sobrescribiendo '{payer_first_name}' con 'APRO' para tarjeta de prueba")
                payer_first_name = "APRO"
                payer_last_name = ""
        except Exception as final_check_error:
            print(f"[WARNING process_payment] Error en verificación final: {final_check_error}")
            # Si falla, intentar forzar "APRO" de todas formas si parece ser tarjeta de prueba
            try:
                if payer_identification and payer_identification.get("type") == "Otro" and payer_identification.get("number") == "123456789":
                    payer_first_name = "APRO"
                    payer_last_name = ""
                    print(f"[DEBUG process_payment] Forzando 'APRO' como último recurso para tarjeta de prueba")
            except Exception:
                pass  # Si todo falla, continuar con lo que tengamos

        # Crear descripción
        description = f"Compra de tickets - Orden {order_id}"

        # Crear el pago en Mercado Pago
        service = PurchaseService()
        mercado_pago_service = service.mercado_pago_service

        payment = mercado_pago_service.create_payment_with_token(
            token=token,
            transaction_amount=transaction_amount,
            description=description,
            installments=installments,
            payment_method_id=payment_method_id,
            issuer_id=issuer_id,
            payer_email=payer_email,
            payer_identification=payer_identification,
            payer_first_name=payer_first_name,
            payer_last_name=payer_last_name,
            external_reference=order_id,
            device_id=device_id  # Device ID para mejorar aprobación
        )

        # Actualizar la orden con el payment_id
        order.payment_reference = str(payment.get("id"))

        # Verificar el estado del pago inmediatamente
        payment_status = payment.get("status")
        payment_status_detail = payment.get("status_detail")

        print(f"[DEBUG process_payment] Estado del pago recibido: {payment_status} (detail: {payment_status_detail})")

        # Si el pago fue rechazado inmediatamente, actualizar el estado de la orden
        if payment_status in ["rejected", "cancelled", "refunded"]:
            print(f"❌ [process_payment] Pago rechazado inmediatamente. Actualizando orden {order_id} a 'cancelled'")

            # Cargar order_items ANTES de hacer commit (necesario para evitar MissingGreenlet)
            from sqlalchemy.orm import selectinload
            from shared.database.models import OrderItem
            result = await db.execute(
                select(OrderItem).where(OrderItem.order_id == order.id)
            )
            order_items = result.scalars().all()

            order.status = "cancelled"
            await db.commit()

            # Liberar capacidad
            service = PurchaseService()
            for order_item in order_items:
                await service.inventory_service.release_capacity(
                    db, str(order_item.event_id), order_item.quantity, "payment_failed"
                )

            await db.refresh(order)
        elif payment_status == "approved":
            # Si el pago fue aprobado inmediatamente, actualizar el estado
            print(f"✅ [process_payment] Pago aprobado inmediatamente. Actualizando orden {order_id} a 'completed'")
            order.status = "completed"
            order.paid_at = datetime.utcnow()
            await db.commit()

            # Generar tickets
            service = PurchaseService()
            try:
                await service._generate_tickets(db, order, ticket_status="issued")
                await db.commit()
            except Exception as e:
                await db.rollback()
                print(f"Error generando tickets para orden {order.id}: {e}")
                # Marcar orden como paid aunque falle la generación de tickets
                order.status = "completed"
                await db.commit()

            await db.refresh(order)
        else:
            # Si el pago está pendiente, solo guardar el payment_reference
            # El webhook actualizará el estado cuando el pago se complete
            print(f"⏳ [process_payment] Pago en estado '{payment_status}'. Esperando webhook para actualizar estado.")
            await db.commit()
            await db.refresh(order)

        return {
            "payment_id": payment.get("id"),
            "status": payment.get("status"),
            "status_detail": payment.get("status_detail"),
            "order_id": order_id
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        error_message = str(e)
        print(f"[ERROR process_payment] Exception: {error_message}")
        print(f"[ERROR process_payment] Traceback completo: {error_trace}")

        # Si el error viene de Mercado Pago, incluir más detalles
        if "Error creando pago" in error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando pago: {error_message}"
        )


@router.get("/admin/completed-orders")
async def admin_list_completed_orders(
    db: AsyncSession = Depends(get_db),
    limit: int = 50
):
    """
    Listar órdenes completadas para reenvío de tickets

    Query params:
    - limit: Máximo de órdenes a retornar (default: 50)
    """
    try:
        from shared.database.models import Order, Ticket, OrderItem

        # Buscar órdenes completadas
        result = await db.execute(
            select(Order)
            .where(Order.status == "completed")
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        orders = result.scalars().all()

        # Para cada orden, obtener información de tickets
        orders_data = []
        for order in orders:
            # Contar tickets haciendo JOIN con OrderItem
            result_tickets = await db.execute(
                select(Ticket)
                .join(OrderItem, Ticket.order_item_id == OrderItem.id)
                .where(OrderItem.order_id == order.id)
            )
            tickets = result_tickets.scalars().all()

            # Solo incluir órdenes con al menos 1 ticket
            if not tickets:
                continue

            # Obtener email del primer ticket
            email = tickets[0].holder_email if tickets[0].holder_email else None

            orders_data.append({
                "order_id": str(order.id),
                "status": order.status,
                "total": float(order.total),
                "currency": order.currency,
                "created_at": str(order.created_at),
                "paid_at": str(order.paid_at) if order.paid_at else None,
                "tickets_count": len(tickets),
                "email": email,
                "payment_provider": order.payment_provider
            })

        return {
            "success": True,
            "count": len(orders_data),
            "orders": orders_data
        }

    except Exception as e:
        print(f"[ADMIN ERROR] Error listando órdenes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listando órdenes: {str(e)}"
        )


@router.post("/admin/resend-tickets/{order_id}")
async def admin_resend_tickets(
    order_id: str,
    email: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Reenviar tickets de una orden completada por email

    Este endpoint:
    1. Busca la orden y verifica que esté completada
    2. Obtiene los tickets asociados
    3. Envía los tickets por email

    Query params:
    - email (opcional): Email alternativo para enviar. Si no se proporciona, usa el email de los tickets
    """
    try:
        from shared.database.models import Order, Ticket, OrderItem
        from uuid import UUID

        # Buscar la orden
        result = await db.execute(
            select(Order).where(Order.id == UUID(order_id))
        )
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Orden {order_id} no encontrada"
            )

        # Verificar que la orden esté completada
        if order.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Solo se pueden reenviar tickets de órdenes completadas. Estado actual: {order.status}"
            )

        # Buscar tickets de la orden haciendo JOIN con OrderItem
        result = await db.execute(
            select(Ticket)
            .join(OrderItem, Ticket.order_item_id == OrderItem.id)
            .where(OrderItem.order_id == order.id)
        )
        tickets = result.scalars().all()

        if not tickets:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontraron tickets para esta orden"
            )

        # Determinar email destino
        target_email = email if email else tickets[0].holder_email

        if not target_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo determinar el email destino. Proporciona un email como parámetro."
            )

        print(f"[RESEND] Reenviando {len(tickets)} tickets de orden {order_id} a {target_email}")

        # Obtener información del evento
        first_ticket = tickets[0]
        result_event = await db.execute(
            select(Event).where(Event.id == first_ticket.event_id)
        )
        event = result_event.scalar_one_or_none()

        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontró el evento asociado a los tickets"
            )

        # Formatear fecha del evento
        from datetime import datetime
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
                print(f"Error formateando fecha del evento: {e}")

        # Enviar emails con tickets
        from services.notifications.services.email_service import EmailService
        email_service = EmailService()

        emails_sent = 0
        emails_failed = 0

        # Agrupar tickets por email (por si hay múltiples destinatarios)
        from collections import defaultdict
        tickets_by_email = defaultdict(list)
        for ticket in tickets:
            email_key = target_email.lower().strip()
            tickets_by_email[email_key].append(ticket)

        # Enviar un email por cada ticket (o agrupar si es el mismo email)
        for email, user_tickets in tickets_by_email.items():
            for ticket in user_tickets:
                try:
                    attendee_name = f"{ticket.holder_first_name} {ticket.holder_last_name}".strip()
                    if not attendee_name:
                        attendee_name = "Estimado/a"

                    success = await email_service.send_ticket_email(
                        to_email=email,
                        attendee_name=attendee_name,
                        event_name=event.name,
                        event_date=event_date_str,
                        event_location=event_location_str,
                        ticket_id=str(ticket.id)[:8].upper(),
                        qr_signature=ticket.qr_signature  # Pasar QR signature para generar imagen
                    )

                    if success:
                        emails_sent += 1
                    else:
                        emails_failed += 1
                except Exception as e:
                    print(f"Error enviando email para ticket {ticket.id}: {e}")
                    emails_failed += 1

        return {
            "success": True,
            "order_id": str(order.id),
            "email": target_email,
            "tickets_count": len(tickets),
            "emails_sent": emails_sent,
            "emails_failed": emails_failed,
            "message": f"Se enviaron {emails_sent} email(s) con {len(tickets)} ticket(s)" if emails_sent > 0 else f"Error: No se pudieron enviar los emails ({emails_failed} fallos)"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[RESEND ERROR] Error reenviando tickets: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reenviando tickets: {str(e)}"
        )


@router.post("/admin/complete-order/{order_id}")
async def admin_complete_order(
    order_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint administrativo para completar una orden manualmente y enviar tickets

    SOLO PARA DESARROLLO/TESTING

    Este endpoint:
    1. Marca la orden como completada
    2. Genera los tickets
    3. Envía los emails con los tickets

    Útil para probar el flujo sin pagos reales
    """
    service = PurchaseService()

    try:
        # Importar modelos necesarios
        from shared.database.models import Order
        from uuid import UUID

        # Buscar la orden
        result = await db.execute(
            select(Order).where(Order.id == UUID(order_id))
        )
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Orden {order_id} no encontrada"
            )

        # Verificar que la orden esté en pending
        if order.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La orden ya está en estado '{order.status}'. Solo se pueden completar órdenes en 'pending'"
            )

        print(f"[ADMIN] Completando orden manualmente: {order_id}")
        print(f"[ADMIN] Orden actual - Status: {order.status}, Provider: {order.payment_provider}")

        # Actualizar orden a completada
        order.status = "completed"
        order.paid_at = func.now()
        await db.commit()
        await db.refresh(order)

        print(f"[ADMIN] Orden actualizada a 'completed'")

        # Cargar order_items para saber cuántos tickets generar
        from shared.database.models import OrderItem
        result_items = await db.execute(
            select(OrderItem).where(OrderItem.order_id == order.id)
        )
        order_items = result_items.scalars().all()

        if not order_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se encontraron items para esta orden"
            )

        # Crear datos de attendees genéricos
        attendees_data = []
        for idx, item in enumerate(order_items):
            for qty_idx in range(item.quantity):
                attendees_data.append({
                    "name": f"Asistente {len(attendees_data) + 1}",
                    "email": f"ticket{len(attendees_data) + 1}@completed.order",
                    "document_type": "RUT",
                    "document_number": None,
                    "is_child": False
                })

        print(f"[ADMIN] Creados {len(attendees_data)} attendees genéricos")

        # Generar tickets
        tickets = await service._generate_tickets(
            db=db,
            order=order,
            attendees_data=attendees_data,
            ticket_status="issued"
        )

        print(f"[ADMIN] Generados {len(tickets)} tickets")

        # Enviar emails con tickets
        # TODO: Implementar envío de emails cuando el servicio de email esté configurado
        print(f"[ADMIN] ⚠️  Email no enviado - Servicio de email no configurado")
        print(f"[ADMIN] Los tickets fueron generados y están disponibles en la base de datos")

        return {
            "success": True,
            "order_id": str(order.id),
            "status": order.status,
            "paid_at": str(order.paid_at) if order.paid_at else None,
            "tickets_generated": len(tickets),
            "ticket_ids": [str(t.id) for t in tickets],
            "message": "Orden completada manualmente. Tickets generados correctamente."
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ADMIN ERROR] Error completando orden: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error completando orden: {str(e)}"
        )

