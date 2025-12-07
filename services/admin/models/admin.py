"""Modelos Pydantic para administración"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime


# ==================== ORGANIZER ====================

class OrganizerResponse(BaseModel):
    """Respuesta con información del organizador"""
    id: str
    org_name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ==================== USERS / SCANNERS ====================

class UserResponse(BaseModel):
    """Respuesta con información de usuario"""
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class ScannerResponse(BaseModel):
    """Respuesta con información de scanner"""
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class ScannersListResponse(BaseModel):
    """Respuesta con lista de scanners"""
    scanners: List[ScannerResponse]


class UsersListResponse(BaseModel):
    """Respuesta con lista de usuarios"""
    users: List[UserResponse]


class UpdateUserRoleRequest(BaseModel):
    """Request para cambiar rol de usuario"""
    role: str


class CreateScannerRequest(BaseModel):
    """Request para crear nuevo scanner"""
    email: EmailStr
    first_name: str
    last_name: str
    password: str


class DeleteScannerResponse(BaseModel):
    """Respuesta al eliminar scanner"""
    message: str
    user_id: str


# ==================== STATS ====================

class StatsPeriod(BaseModel):
    """Período de tiempo para estadísticas"""
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None


class DashboardStatsResponse(BaseModel):
    """Respuesta con estadísticas del dashboard"""
    total_events: int
    active_events: int
    total_tickets_sold: int
    total_revenue: float
    currency: str = "CLP"
    period: Optional[StatsPeriod] = None


# ==================== EVENTS ADMIN ====================

class TicketTypeInfo(BaseModel):
    """Información de tipo de ticket"""
    id: str
    name: str
    price: float
    is_child: bool

    class Config:
        from_attributes = True


class EventServiceInfo(BaseModel):
    """Información de servicio del evento"""
    id: str
    name: str
    description: Optional[str] = None
    price: float
    service_type: str = "general"  # general, food, parking, child_ticket
    stock_total: int = 0  # Cantidad inicial
    stock_available: int = 0  # Cantidad disponible
    min_age: Optional[int] = None
    max_age: Optional[int] = None

    class Config:
        from_attributes = True


class OrganizerInfo(BaseModel):
    """Información básica del organizador"""
    id: str
    org_name: str


class ServiceStats(BaseModel):
    """Estadísticas de servicios adicionales"""
    id: str
    name: str
    service_type: str
    stock: int
    sold: int
    remaining: int


class EventStats(BaseModel):
    """Estadísticas de un evento"""
    tickets_sold: int
    tickets_remaining: int
    revenue: float
    sales_percentage: float
    services_stats: Optional[List[ServiceStats]] = []


class AdminEventResponse(BaseModel):
    """Respuesta con evento y estadísticas para admin"""
    id: str
    name: str
    description: Optional[str] = None  # ✅ Agregado
    location_text: Optional[str] = None
    point_location: Optional[str] = None
    starts_at: datetime
    ends_at: Optional[datetime] = None
    capacity_total: int
    capacity_available: int
    category: str
    image_url: Optional[str] = None
    organizer: OrganizerInfo
    ticket_types: List[TicketTypeInfo]
    event_services: List[EventServiceInfo] = []  # ✅ Agregado
    stats: EventStats


class AdminEventsListResponse(BaseModel):
    """Respuesta con lista de eventos para admin"""
    events: List[AdminEventResponse]


# ==================== TICKETS ADMIN ====================

class OrderUserInfo(BaseModel):
    """Información del usuario que compró"""
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class OrderInfo(BaseModel):
    """Información de la orden"""
    user: OrderUserInfo


class OrderItemInfo(BaseModel):
    """Información del order item"""
    order_id: str
    order: OrderInfo


class ChildMedication(BaseModel):
    """Medicamento de niño"""
    nombre_medicamento: str
    frecuencia: str
    observaciones: Optional[str] = None


class ChildDetails(BaseModel):
    """Detalles de ticket de niño"""
    nombre: str
    rut: str
    tipo_documento: str
    fecha_nacimiento: str  # ISO date string
    edad: int
    correo: Optional[str] = None
    toma_medicamento: bool
    es_alergico: bool
    detalle_alergias: Optional[str] = None
    nombre_contacto_emergencia: Optional[str] = None
    parentesco_contacto_emergencia: Optional[str] = None
    numero_emergencia: str
    pais_telefono: str
    iglesia: Optional[str] = None
    tiene_necesidad_especial: bool
    detalle_necesidad_especial: Optional[str] = None
    medicamentos: Optional[List[ChildMedication]] = []


class AdminTicketResponse(BaseModel):
    """Respuesta con ticket para admin"""
    id: str
    holder_first_name: str
    holder_last_name: str
    holder_document_type: Optional[str] = None
    holder_document_number: Optional[str] = None
    is_child: bool
    status: str
    qr_signature: str
    issued_at: datetime
    validated_at: Optional[datetime] = None
    used_at: Optional[datetime] = None
    order_item: OrderItemInfo
    child_details: Optional[ChildDetails] = None


class TicketsSummary(BaseModel):
    """Resumen de tickets"""
    total: int
    adults: int
    children: int
    by_status: Dict[str, int]


class EventInfo(BaseModel):
    """Información básica del evento"""
    id: str
    name: str


class AdminTicketsListResponse(BaseModel):
    """Respuesta con lista de tickets para admin"""
    event: EventInfo
    tickets: List[AdminTicketResponse]
    summary: TicketsSummary


# ==================== CHILDREN EXPORT ====================

class ChildComprador(BaseModel):
    """Información del comprador"""
    nombre: str
    email: str


class ChildExportData(BaseModel):
    """Datos de niño para export"""
    ticket_id: str
    nombre: str
    rut: str
    tipo_documento: str
    fecha_nacimiento: str
    edad: int
    correo: Optional[str] = None
    toma_medicamento: bool
    es_alergico: bool
    detalle_alergias: Optional[str] = None
    nombre_contacto_emergencia: Optional[str] = None
    parentesco_contacto_emergencia: Optional[str] = None
    numero_emergencia: str
    pais_telefono: str
    iglesia: Optional[str] = None
    tiene_necesidad_especial: bool
    detalle_necesidad_especial: Optional[str] = None
    medicamentos: List[ChildMedication]
    ticket_status: str
    comprador: ChildComprador


class ChildrenExportResponse(BaseModel):
    """Respuesta con datos de niños para export"""
    event: EventInfo
    children: List[ChildExportData]


class ChildTicketInfo(BaseModel):
    """Información de ticket infantil para listado global"""
    ticket_id: str
    event_id: str
    event_name: str
    event_date: str
    nombre: str
    rut: str
    edad: int
    es_alergico: bool
    detalle_alergias: Optional[str] = None
    toma_medicamento: bool
    medicamentos: List[Dict]
    tiene_necesidad_especial: bool
    detalle_necesidad_especial: Optional[str] = None
    iglesia: Optional[str] = None
    nombre_contacto_emergencia: Optional[str] = None
    parentesco_contacto_emergencia: Optional[str] = None
    numero_emergencia: str
    issued_at: str


class GlobalChildTicketsResponse(BaseModel):
    """Respuesta para listado global de tickets infantiles"""
    tickets: List[ChildTicketInfo]
    total_count: int


# ==================== PENDING ORDERS ====================

class TicketDetailResponse(BaseModel):
    """Detalle de ticket en orden"""
    id: str
    holder_first_name: str
    holder_last_name: str
    holder_email: Optional[str] = None
    status: str
    event_id: str
    event_name: Optional[str] = None

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    """Respuesta con información de orden"""
    id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    subtotal: float
    discount_total: float
    total: float
    commission_total: float
    currency: str
    status: str
    payment_provider: Optional[str] = None
    payment_reference: Optional[str] = None
    receipt_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    paid_at: Optional[datetime] = None
    tickets_count: int = 0
    tickets: Optional[List[TicketDetailResponse]] = None

    class Config:
        from_attributes = True


class OrdersListResponse(BaseModel):
    """Respuesta con lista de órdenes pendientes"""
    orders: List[OrderResponse]


# ==================== MANUAL TICKETS ====================

class BuyerInfo(BaseModel):
    """Información del comprador para creación manual"""
    first_name: str
    last_name: str
    email: EmailStr
    document_type: Optional[str] = "RUT"  # Opcional, por defecto RUT
    document_number: Optional[str] = ""  # Opcional


class ManualTicketService(BaseModel):
    """Servicio adicional para creación manual"""
    service_id: str
    quantity: int


class CreateManualTicketsRequest(BaseModel):
    """Request para crear tickets manualmente"""
    event_id: str
    buyer: BuyerInfo
    quantity: int
    services: Optional[List[ManualTicketService]] = None
    notes: Optional[str] = None


class CreateManualTicketsResponse(BaseModel):
    """Respuesta al crear tickets manualmente"""
    order_id: str
    tickets_created: int
    message: str = "Tickets creados exitosamente"