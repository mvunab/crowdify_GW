"""Rutas de compra de tickets"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql import func
from typing import Dict, Optional
from shared.database.session import get_db
from shared.auth.dependencies import get_current_user, get_optional_user
from services.ticket_purchase.models.purchase import (
    PurchaseRequest,
    PurchaseResponse,
    OrderStatusResponse
)
from services.ticket_purchase.services.purchase_service import PurchaseService


router = APIRouter()


@router.post("", response_model=PurchaseResponse)
async def create_purchase(
    request: PurchaseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[Dict] = Depends(get_optional_user)
):
    """
    Crear orden de compra y generar link de pago
    
    Compatible con: ticketsService.purchaseTickets()
    
    NOTA: user_id es opcional ahora. Si se proporciona sin autenticación, se ignora y la compra es anónima.
    Si se proporciona con autenticación, debe coincidir con el usuario autenticado.
    """
    print(f"[DEBUG ROUTE] Request recibido - payment_method: {request.payment_method}")
    print(f"[DEBUG ROUTE] Request completo: {request.dict()}")
    
    # Manejar user_id con try-except para mayor robustez
    try:
        # Si se proporciona user_id, validar solo si hay autenticación
        if request.user_id:
            if current_user:
                # Usuario autenticado: validar que el user_id coincida
                if current_user.get("user_id") != request.user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="No puedes crear órdenes para otros usuarios"
                    )
                print(f"[DEBUG ROUTE] user_id validado: {request.user_id} (usuario autenticado)")
            else:
                # No hay autenticación: ignorar user_id y tratar como compra anónima
                print(f"[DEBUG ROUTE] user_id proporcionado sin autenticación: {request.user_id} - Ignorando y tratando como compra anónima")
                request.user_id = None
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
                    print(f"[WARNING ROUTE] Error obteniendo rol del usuario: {role_error}")
                    # Continuar sin validar rol si hay error
    except HTTPException:
        raise  # Re-lanzar HTTPException
    except Exception as validation_error:
        print(f"[WARNING ROUTE] Error en validación de user_id: {validation_error}")
        # Si hay error, ignorar user_id y continuar como compra anónima
        request.user_id = None
    
    service = PurchaseService()
    
    try:
        result = await service.create_purchase(db, request)
        print(f"[DEBUG ROUTE] Result del servicio: {result}")
        print(f"[DEBUG ROUTE] payment_link en result: {result.get('payment_link')}")
        response = PurchaseResponse(**result)
        print(f"[DEBUG ROUTE] PurchaseResponse creado: {response}")
        print(f"[DEBUG ROUTE] payment_link en response: {response.payment_link}")
        return response
    except ValueError as e:
        import traceback
        print(f"ValueError en create_purchase: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Exception en create_purchase: {str(e)}")
        print(f"Traceback completo: {error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando compra: {str(e)}"
        )


@router.post("/webhook")
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
        
        # Verificar firma del webhook
        mercado_pago_service = service.mercado_pago_service
        is_valid = mercado_pago_service.verify_webhook(
            data=data,
            signature=signature,
            request_id=request_id,
            query_params=query_params
        )
        
        if not is_valid:
            print("⚠️  Webhook con firma inválida, pero procesando de todas formas (modo desarrollo)")
            # En producción, podrías retornar 401 aquí
        
        # Procesar webhook
        success = await service.process_payment_webhook(db, data)
        
        if success:
            return {"status": "ok"}
        else:
            return {"status": "ignored"}
    except Exception as e:
        # Log error pero retornar 200 para que Mercado Pago no reintente inmediatamente
        print(f"Error procesando webhook: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


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
        
        # PRIORIDAD 1: Si es una tarjeta de prueba en sandbox, usar "APRO" directamente
        # Esto es CRÍTICO porque Mercado Pago requiere "APRO" para tarjetas de prueba
        try:
            if is_sandbox and is_test_card and not payer_first_name:
                payer_first_name = "APRO"
                payer_last_name = ""
                print(f"[DEBUG process_payment] ⚠️ TARJETA DE PRUEBA DETECTADA - Usando 'APRO' como nombre del titular (requerido por Mercado Pago)")
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
                        # SOLO en sandbox y SOLO para tarjetas de prueba, usar "APRO"
                        # En producción, usar un valor genérico o el nombre del email
                        if is_sandbox and is_test_card:
                            payer_first_name = "APRO"
                            payer_last_name = ""
                            print(f"[DEBUG process_payment] Usando 'APRO' como nombre del titular para tarjeta de prueba en sandbox")
                        elif payer_email:
                            # En producción o cuando no es tarjeta de prueba, usar el nombre del email
                            email_name = payer_email.split("@")[0]
                            payer_first_name = email_name[:50]  # Limitar longitud
                            payer_last_name = email_name[:50] if not payer_last_name else payer_last_name
                            print(f"[DEBUG process_payment] Usando nombre del email como fallback: {payer_first_name} {payer_last_name}")
                        else:
                            # Último recurso: usar un valor genérico
                            if is_sandbox:
                                payer_first_name = "APRO"
                                payer_last_name = ""
                                print(f"[DEBUG process_payment] Usando 'APRO' como nombre del titular por defecto en sandbox")
                            else:
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
            external_reference=order_id
        )
        
        # Actualizar la orden con el payment_id
        order.payment_reference = str(payment.get("id"))
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
        
        # TODO: Implementar envío de email cuando esté configurado
        # Por ahora solo retornamos la información
        
        return {
            "success": True,
            "order_id": str(order.id),
            "email": target_email,
            "tickets_count": len(tickets),
            "ticket_ids": [str(t.id) for t in tickets],
            "message": "⚠️ Servicio de email no configurado. Los tickets están listos pero no se enviaron.",
            "note": "Configura EMAIL_PROVIDER y EMAIL_API_KEY en .env para habilitar envío de emails"
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

