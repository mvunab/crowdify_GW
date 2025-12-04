"""Modelos Pydantic para compra de productos para niños"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict
from uuid import UUID
from datetime import date, datetime


class ChildMedicationData(BaseModel):
    """Datos de medicamento para producto de niño"""
    nombre: str
    dosis: Optional[str] = None
    horario: Optional[str] = None
    observaciones: Optional[str] = None


class ChildDetailsForProduct(BaseModel):
    """Detalles de niño para producto/servicio"""
    nombre: str = Field(..., description="Nombre completo del niño")
    rut: str = Field(..., description="RUT o documento de identidad")
    correo: Optional[EmailStr] = None
    fecha_nacimiento: date = Field(..., description="Fecha de nacimiento")
    edad: int = Field(..., ge=0, le=18, description="Edad del niño")
    tipo_documento: Optional[str] = Field(default="rut", description="Tipo de documento (rut, dni_ar, dni_mx, etc.)")
    
    # Medicamentos y alergias
    toma_medicamento: bool = Field(default=False, description="Si toma medicamentos")
    es_alergico: bool = Field(default=False, description="Si es alérgico")
    detalle_alergias: Optional[str] = None
    
    # Necesidades especiales
    tiene_necesidad_especial: bool = Field(default=False, description="Si tiene necesidades especiales")
    detalle_necesidad_especial: Optional[str] = None
    
    # Contacto de emergencia
    numero_emergencia: str = Field(..., description="Número de teléfono de emergencia")
    pais_telefono: Optional[str] = Field(default="CL", description="Código ISO del país")
    nombre_contacto_emergencia: Optional[str] = None
    parentesco_contacto_emergencia: Optional[str] = None
    
    # Otros
    iglesia: Optional[str] = None
    
    # Medicamentos
    medicamentos: Optional[List[ChildMedicationData]] = []


class ProductPurchaseItem(BaseModel):
    """Item de producto a comprar"""
    service_id: UUID = Field(..., description="ID del servicio/producto")
    quantity: int = Field(..., gt=0, description="Cantidad a comprar")
    child_details: List[ChildDetailsForProduct] = Field(
        ..., 
        description="Detalles de niños (debe coincidir con quantity)"
    )


class BuyerInfo(BaseModel):
    """Información del comprador visitante"""
    name: str = Field(..., description="Nombre completo del comprador")
    email: EmailStr = Field(..., description="Email del comprador")
    phone: str = Field(..., description="Teléfono del comprador")


class ChildProductPurchaseRequest(BaseModel):
    """Request para compra de productos para niños (autenticado)"""
    event_id: UUID = Field(..., description="ID del evento")
    products: List[ProductPurchaseItem] = Field(..., min_items=1, description="Lista de productos a comprar")
    idempotency_key: Optional[str] = Field(None, description="Clave de idempotencia")


class GuestChildProductPurchaseRequest(BaseModel):
    """Request para compra de productos para niños como visitante"""
    event_id: UUID = Field(..., description="ID del evento")
    buyer: BuyerInfo = Field(..., description="Información del comprador")
    products: List[ProductPurchaseItem] = Field(..., min_items=1, description="Lista de productos a comprar")
    idempotency_key: Optional[str] = Field(None, description="Clave de idempotencia")


class ChildProductInfo(BaseModel):
    """Información de un producto para niños"""
    id: UUID
    name: str
    description: Optional[str] = None
    price: float
    stock_available: int
    service_type: str  # child_ticket, child_product
    requires_child_form: bool
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    ticket_type_id: Optional[UUID] = None


class ChildProductsListResponse(BaseModel):
    """Response con lista de productos para niños"""
    event_id: UUID
    products: List[ChildProductInfo]


class PurchasedProductDetail(BaseModel):
    """Detalle de producto comprado"""
    service_id: UUID
    service_name: str
    quantity: int
    unit_price: float
    final_price: float
    child_details: List[ChildDetailsForProduct]


class ChildProductPurchaseStatusResponse(BaseModel):
    """Response con estado de compra de productos"""
    order_id: UUID
    status: str  # pending, completed, failed, cancelled
    total: float
    currency: str
    payment_provider: Optional[str] = None
    payment_reference: Optional[str] = None
    created_at: datetime
    paid_at: Optional[datetime] = None
    products: List[PurchasedProductDetail]
    buyer_info: Optional[BuyerInfo] = None  # Solo si es compra de visitante


