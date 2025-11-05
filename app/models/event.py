from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.db.base_class import Base

class Event(Base):
    __tablename__ = "events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organizer_id = Column(UUID(as_uuid=True), ForeignKey("organizers.id"), nullable=False)
    name = Column(String, nullable=False)
    location_text = Column(String)
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True))
    capacity_total = Column(Integer, nullable=False)
    capacity_available = Column(Integer, nullable=False)
    allow_children = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TicketType(Base):
    __tablename__ = "ticket_types"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    name = Column(String, nullable=False)
    price = Column(Numeric(12,2), nullable=False)
    is_child = Column(Boolean, default=False)
    per_adult_child_limit = Column(Integer)

class PriceWindow(Base):
    __tablename__ = "price_windows"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    price_multiplier = Column(Numeric(6,3))
    fixed_discount = Column(Numeric(12,2))

class CapacityLog(Base):
    __tablename__ = "capacity_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    delta = Column(Integer, nullable=False)
    reason = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
