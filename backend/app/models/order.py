from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.db.base_class import Base

class Order(Base):
    __tablename__ = "orders"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    subtotal = Column(Numeric(12,2), nullable=False, server_default="0")
    discount_total = Column(Numeric(12,2), nullable=False, server_default="0")
    total = Column(Numeric(12,2), nullable=False, server_default="0")
    currency = Column(String, default="CLP")
    status = Column(String, default="pending")
    payment_provider = Column(String)
    payment_reference = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True))
    idempotency_key = Column(String, unique=True)

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    ticket_type_id = Column(UUID(as_uuid=True), ForeignKey("ticket_types.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12,2), nullable=False)
    final_price = Column(Numeric(12,2), nullable=False)
