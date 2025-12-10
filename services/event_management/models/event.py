"""Modelos Pydantic para eventos"""
from pydantic import BaseModel, field_serializer
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from uuid import UUID


class TicketTypeResponse(BaseModel):
    """Modelo de respuesta para tipos de ticket"""
    id: str
    event_id: str
    name: str
    price: float
    is_child: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EventServiceResponse(BaseModel):
    """Modelo de respuesta para servicios del evento"""
    id: str
    event_id: str
    name: str
    description: Optional[str] = None
    price: float
    service_type: str = "general"  # general, food, parking, child_ticket
    stock_total: int = 0  # Cantidad inicial
    stock_available: int = 0  # Cantidad disponible
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EventResponse(BaseModel):
    id: str
    organizer_id: str
    name: str
    location_text: Optional[str] = None
    point_location: Optional[str] = None
    starts_at: datetime
    ends_at: Optional[datetime] = None
    capacity_total: int
    capacity_available: int
    allow_children: bool
    category: Optional[str] = "otro"
    description: Optional[str] = None
    image_url: Optional[str] = None
    ticket_types: List[TicketTypeResponse] = []
    event_services: List[EventServiceResponse] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_serializer('starts_at', 'ends_at')
    def serialize_datetime(self, dt: Optional[datetime], _info) -> Optional[str]:
        """Serializar datetime a ISO 8601 - hora de Chile directamente (sin timezone)"""
        if dt is None:
            return None
        # La hora en la BD es hora de Chile directamente, devolverla como ISO sin timezone
        # Si tiene timezone, removerlo
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt.isoformat()
    
    @field_serializer('created_at', 'updated_at')
    def serialize_datetime_utc(self, dt: Optional[datetime], _info) -> Optional[str]:
        """Serializar datetime a ISO 8601 con timezone UTC explícito (para timestamps del sistema)"""
        if dt is None:
            return None
        # Asegurar que el datetime tenga timezone UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        elif dt.tzinfo != timezone.utc:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat()

    class Config:
        from_attributes = True


class EventCreate(BaseModel):
    organizer_id: str
    name: str
    location_text: Optional[str] = None
    starts_at: datetime
    ends_at: Optional[datetime] = None
    capacity_total: int
    allow_children: bool = False
    category: Optional[str] = "otro"
    description: Optional[str] = None
    image_url: Optional[str] = None
    price: Optional[float] = None
    services: Optional[List[Dict[str, Any]]] = None


class EventUpdate(BaseModel):
    name: Optional[str] = None
    location_text: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    capacity_total: Optional[int] = None
    capacity_available: Optional[int] = None
    allow_children: Optional[bool] = None
    category: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    price: Optional[float] = None
    services: Optional[List[Dict[str, Any]]] = None  # ✅ Agregado soporte para services
