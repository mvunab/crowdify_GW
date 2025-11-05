"""Servicio de gestión de inventario y capacidad"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Tuple
from shared.database.models import Event, TicketType, CapacityLog
from shared.cache.redis_client import DistributedLock
from datetime import datetime
import uuid


class InventoryService:
    """Servicio para manejar inventario y capacidad de eventos"""
    
    @staticmethod
    async def check_capacity(
        db: AsyncSession,
        event_id: str,
        quantity: int
    ) -> Tuple[bool, str]:
        """
        Verificar si hay capacidad disponible
        
        Returns:
            (is_available, message)
        """
        stmt = select(Event).where(Event.id == event_id)
        result = await db.execute(stmt)
        event = result.scalar_one_or_none()
        
        if not event:
            return False, "Evento no encontrado"
        
        if event.capacity_available < quantity:
            return False, f"Capacidad insuficiente. Disponible: {event.capacity_available}, Solicitado: {quantity}"
        
        return True, "OK"
    
    @staticmethod
    async def reserve_capacity(
        db: AsyncSession,
        event_id: str,
        quantity: int,
        reason: str = "ticket_purchase"
    ) -> bool:
        """
        Reservar capacidad usando lock distribuido
        
        Returns:
            True si se reservó, False si no había capacidad
        """
        lock_key = f"event:capacity:{event_id}"
        
        async with DistributedLock(lock_key, timeout=5, expire=10):
            # Verificar capacidad nuevamente dentro del lock
            stmt = select(Event).where(Event.id == event_id)
            result = await db.execute(stmt)
            event = result.scalar_one_or_none()
            
            if not event:
                return False
            
            if event.capacity_available < quantity:
                return False
            
            # Decrementar capacidad
            event.capacity_available -= quantity
            
            # Registrar en log
            capacity_log = CapacityLog(
                id=uuid.uuid4(),
                event_id=event_id,
                delta=-quantity,
                reason=reason,
                created_at=datetime.utcnow()
            )
            db.add(capacity_log)
            
            await db.commit()
            await db.refresh(event)
            
            return True
    
    @staticmethod
    async def release_capacity(
        db: AsyncSession,
        event_id: str,
        quantity: int,
        reason: str = "order_cancelled"
    ):
        """Liberar capacidad reservada"""
        lock_key = f"event:capacity:{event_id}"
        
        async with DistributedLock(lock_key, timeout=5, expire=10):
            stmt = select(Event).where(Event.id == event_id)
            result = await db.execute(stmt)
            event = result.scalar_one_or_none()
            
            if not event:
                return
            
            # Incrementar capacidad (sin exceder el total)
            new_capacity = min(event.capacity_available + quantity, event.capacity_total)
            event.capacity_available = new_capacity
            
            # Registrar en log
            capacity_log = CapacityLog(
                id=uuid.uuid4(),
                event_id=event_id,
                delta=quantity,
                reason=reason,
                created_at=datetime.utcnow()
            )
            db.add(capacity_log)
            
            await db.commit()

