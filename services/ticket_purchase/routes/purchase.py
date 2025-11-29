"""Rutas de compra de tickets"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
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
    
    NOTA: user_id es opcional ahora. Si se proporciona, debe coincidir con el usuario autenticado.
    Si no se proporciona, la compra es anónima (solo para usuarios comunes).
    """
    # Si se proporciona user_id, debe coincidir con el usuario autenticado
    if request.user_id:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Debes estar autenticado para crear órdenes con user_id"
            )
        if current_user.get("user_id") != request.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes crear órdenes para otros usuarios"
            )
    else:
        # Compra anónima - permitir si no hay usuario autenticado
        # Si hay usuario autenticado y es admin/coordinator, debe proporcionar user_id
        if current_user:
            user_role = current_user.get("role", "user")
            if user_role in ["admin", "coordinator"]:
                # Para admins/coordinadores, user_id es requerido
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Los administradores y coordinadores deben proporcionar user_id"
                )
    
    service = PurchaseService()
    
    try:
        result = await service.create_purchase(db, request)
        return PurchaseResponse(**result)
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
        data = await request.json()
        success = await service.process_payment_webhook(db, data)
        
        if success:
            return {"status": "ok"}
        else:
            return {"status": "ignored"}
    except Exception as e:
        # Log error pero retornar 200 para que Mercado Pago no reintente inmediatamente
        print(f"Error procesando webhook: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/{order_id}/status", response_model=OrderStatusResponse)
async def get_order_status(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """
    Obtener estado de una orden
    
    Compatible con: ticketsService.getOrderStatus()
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
    
    # Verificar acceso: si la orden tiene user_id, debe coincidir con el usuario autenticado
    # Si no tiene user_id (compra anónima), solo admins/coordinadores pueden verla
    if order:
        if order.user_id:
            # Orden con user_id - verificar que coincida
            if str(order.user_id) != current_user.get("user_id"):
                if current_user.get("role") not in ["admin", "coordinator"]:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="No tienes acceso a esta orden"
                    )
        else:
            # Orden sin user_id (compra anónima) - solo admins/coordinadores pueden verla
            if current_user.get("role") not in ["admin", "coordinator"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes acceso a esta orden"
                )
    
    return OrderStatusResponse(**order_status)

