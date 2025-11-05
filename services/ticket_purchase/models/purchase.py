"""Modelos Pydantic para compra de tickets"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime


class ChildDetailsData(BaseModel):
    birth_date: Optional[datetime] = None
    allergies: Optional[str] = None
    special_needs: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    medications: Optional[List[Dict[str, str]]] = None


class AttendeeData(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    document_type: str  # RUT|PASSPORT
    document_number: str
    is_child: bool = False
    child_details: Optional[ChildDetailsData] = None


class PurchaseRequest(BaseModel):
    user_id: str
    event_id: str
    attendees: List[AttendeeData]
    selected_services: Optional[Dict[str, int]] = None  # {serviceId: quantity}
    idempotency_key: Optional[str] = None


class PurchaseResponse(BaseModel):
    order_id: str
    payment_link: str
    status: str  # pending, completed, failed


class OrderStatusResponse(BaseModel):
    order_id: str
    status: str
    total: float
    currency: str
    payment_provider: Optional[str] = None
    payment_reference: Optional[str] = None
    created_at: datetime
    paid_at: Optional[datetime] = None

