"""Modelos SQLAlchemy compatibles con Supabase"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Date, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from shared.database.connection import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    # Nota: password_hash NO existe aquí - las contraseñas están en auth.users (Supabase Auth)
    first_name = Column(String, nullable=True)  # NULLABLE en Supabase
    last_name = Column(String, nullable=True)  # NULLABLE en Supabase
    phone = Column(String, nullable=True)
    country = Column(String, nullable=True)
    city = Column(String, nullable=True)
    role = Column(String, nullable=False, server_default="user")  # user, admin, scanner, coordinator
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relaciones
    orders = relationship("Order", back_populates="user")
    organizer = relationship("Organizer", back_populates="user", uselist=False)


class Organizer(Base):
    __tablename__ = "organizers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_name = Column(String, nullable=False)
    contact_email = Column(String)
    contact_phone = Column(String, nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relaciones
    user = relationship("User", back_populates="organizer")
    events = relationship("Event", back_populates="organizer")


class Event(Base):
    __tablename__ = "events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organizer_id = Column(UUID(as_uuid=True), ForeignKey("organizers.id"), nullable=False)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # Admin que creó el evento
    name = Column(String, nullable=False)
    location_text = Column(String, nullable=False)  # NOT NULL en Supabase
    point_location = Column(String, nullable=True)  # Nueva columna en Supabase
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=False)  # NOT NULL en Supabase
    capacity_total = Column(Integer, nullable=False, server_default="0")
    capacity_available = Column(Integer, nullable=False, server_default="0")
    allow_children = Column(Boolean, nullable=True, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    category = Column(String, nullable=False, server_default="otro")  # Nueva columna
    description = Column(String, nullable=True)  # Nueva columna
    image_url = Column(String, nullable=True)  # Nueva columna
    
    # Relaciones
    organizer = relationship("Organizer", back_populates="events")
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])  # Relación con el admin creador
    ticket_types = relationship("TicketType", back_populates="event", cascade="all, delete-orphan")
    price_windows = relationship("PriceWindow", back_populates="event", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="event")
    order_items = relationship("OrderItem", back_populates="event")
    capacity_logs = relationship("CapacityLog", back_populates="event")
    event_services = relationship("EventService", back_populates="event", cascade="all, delete-orphan")


class TicketType(Base):
    __tablename__ = "ticket_types"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    name = Column(String, nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    is_child = Column(Boolean, nullable=True, server_default="false")
    per_adult_child_limit = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relaciones
    event = relationship("Event", back_populates="ticket_types")
    order_items = relationship("OrderItem", back_populates="ticket_type")


class PriceWindow(Base):
    __tablename__ = "price_windows"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    price_multiplier = Column(Numeric(6, 3), nullable=True, server_default="1.0")
    fixed_discount = Column(Numeric(12, 2), nullable=True, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relaciones
    event = relationship("Event", back_populates="price_windows")


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # Opcional - solo para admins/coordinadores
    subtotal = Column(Numeric(12, 2), nullable=False, server_default="0")
    discount_total = Column(Numeric(12, 2), nullable=False, server_default="0")
    total = Column(Numeric(12, 2), nullable=False, server_default="0")
    commission_total = Column(Numeric(12, 2), nullable=True, server_default="0")  # Comisiones por tickets
    currency = Column(String, nullable=True, server_default="CLP")
    status = Column(String, nullable=False, server_default="pending")  # pending, processing, completed, cancelled, refunded
    payment_provider = Column(String, nullable=True)
    payment_reference = Column(String, nullable=True)
    idempotency_key = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relaciones
    user = relationship("User", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    order_service_items = relationship("OrderServiceItem", back_populates="order", cascade="all, delete-orphan")
    commissions = relationship("OrderCommission", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    ticket_type_id = Column(UUID(as_uuid=True), ForeignKey("ticket_types.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    final_price = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relaciones
    order = relationship("Order", back_populates="order_items")
    event = relationship("Event", back_populates="order_items")
    ticket_type = relationship("TicketType", back_populates="order_items")
    tickets = relationship("Ticket", back_populates="order_item")


class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_item_id = Column(UUID(as_uuid=True), ForeignKey("order_items.id"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    holder_first_name = Column(String, nullable=False)
    holder_last_name = Column(String, nullable=False)
    holder_email = Column(String, nullable=True, index=True)  # Email del titular para búsqueda pública
    holder_document_type = Column(String, nullable=True)  # NULLABLE en Supabase
    holder_document_number = Column(String, nullable=True)  # NULLABLE en Supabase
    is_child = Column(Boolean, nullable=True, server_default="false")
    qr_signature = Column(String, unique=True, index=True, nullable=False)
    pdf_object_key = Column(String, nullable=True)
    status = Column(String, nullable=False, server_default="issued")  # issued, validated, used, cancelled
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    validated_at = Column(DateTime(timezone=True), nullable=True)  # Cuando fue validado
    used_at = Column(DateTime(timezone=True), nullable=True)  # Cuando fue usado
    scanned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # Usuario que escaneó
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relaciones
    order_item = relationship("OrderItem", back_populates="tickets")
    event = relationship("Event", back_populates="tickets")
    scanner_user = relationship("User", foreign_keys=[scanned_by])
    child_details = relationship("TicketChildDetail", back_populates="ticket", cascade="all, delete-orphan", uselist=False)
    commissions = relationship("OrderCommission", back_populates="ticket")


class CapacityLog(Base):
    __tablename__ = "capacity_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    delta = Column(Integer, nullable=False)
    reason = Column(String, nullable=True)
    caused_by_user = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # Usuario que causó el cambio
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relaciones
    event = relationship("Event", back_populates="capacity_logs")
    user = relationship("User", foreign_keys=[caused_by_user])


class EventService(Base):
    __tablename__ = "event_services"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(12, 2), nullable=False, server_default="0")
    stock = Column(Integer, nullable=False, server_default="0")  # Stock total
    stock_available = Column(Integer, nullable=False, server_default="0")  # Stock disponible
    service_type = Column(String, nullable=False, server_default="general")  # general, food, parking, child_ticket
    min_age = Column(Integer, nullable=True)  # Para child_ticket
    max_age = Column(Integer, nullable=True)  # Para child_ticket
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relaciones
    event = relationship("Event", back_populates="event_services")
    order_service_items = relationship("OrderServiceItem", back_populates="service")


class TicketChildDetail(Base):
    """
    Modelo de detalles de ticket para niños
    Estructura basada en Supabase (campos en español)
    """
    __tablename__ = "ticket_child_details"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=False, unique=True)
    
    # Campos en español (como en Supabase)
    nombre = Column(String, nullable=False)  # Nombre del niño
    rut = Column(String, nullable=False)  # RUT o documento
    correo = Column(String, nullable=True)  # Email
    fecha_nacimiento = Column(Date, nullable=False)  # Fecha de nacimiento (DATE en Supabase)
    edad = Column(Integer, nullable=False)  # Edad
    tipo_documento = Column(String, nullable=True, server_default="rut")  # rut, dni_ar, dni_mx, etc.
    
    # Medicamentos y alergias
    toma_medicamento = Column(Boolean, nullable=False, server_default="false")
    es_alergico = Column(Boolean, nullable=False, server_default="false")
    detalle_alergias = Column(Text, nullable=True)
    
    # Necesidades especiales
    tiene_necesidad_especial = Column(Boolean, nullable=False, server_default="false")
    detalle_necesidad_especial = Column(Text, nullable=True)
    
    # Contacto de emergencia
    numero_emergencia = Column(String, nullable=False)
    pais_telefono = Column(String, nullable=True, server_default="CL")  # Código ISO del país
    nombre_contacto_emergencia = Column(String, nullable=True)
    parentesco_contacto_emergencia = Column(String, nullable=True)
    
    # Otros
    iglesia = Column(String, nullable=True)  # Iglesia (campo opcional)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relaciones
    ticket = relationship("Ticket", back_populates="child_details")
    medications = relationship("TicketChildMedication", back_populates="child_detail", cascade="all, delete-orphan")


class TicketChildMedication(Base):
    """
    Medicamentos de niños en tickets
    FK a ticket_child_details (no directamente a tickets)
    """
    __tablename__ = "ticket_child_medications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_child_id = Column(UUID(as_uuid=True), ForeignKey("ticket_child_details.id"), nullable=False)
    
    # Campos en español (como en Supabase)
    nombre_medicamento = Column(String, nullable=False)
    frecuencia = Column(String, nullable=False)
    observaciones = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relaciones
    child_detail = relationship("TicketChildDetail", back_populates="medications")


class OrderServiceItem(Base):
    """
    Servicios adicionales vendidos en órdenes
    """
    __tablename__ = "order_service_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey("event_services.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    final_price = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relaciones
    order = relationship("Order", back_populates="order_service_items")
    event = relationship("Event")
    service = relationship("EventService", back_populates="order_service_items")


class OrderCommission(Base):
    """
    Comisiones por ticket vendido
    """
    __tablename__ = "order_commissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey("tickets.id"), nullable=True)
    ticket_type = Column(String, nullable=False)  # 'adult' o 'child'
    commission_amount = Column(Numeric(12, 2), nullable=False)  # 1500 para adulto, 1000 para niño
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relaciones
    order = relationship("Order", back_populates="commissions")
    ticket = relationship("Ticket")

