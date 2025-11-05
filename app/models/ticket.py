from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.db.base_class import Base

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_item_id = Column(UUID(as_uuid=True), ForeignKey("order_items.id"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False)
    holder_first_name = Column(String, nullable=False)
    holder_last_name = Column(String, nullable=False)
    holder_document_type = Column(String, nullable=False)  # RUT|PASSPORT
    holder_document_number = Column(String, nullable=False)
    is_child = Column(Boolean, default=False)
    qr_signature = Column(String)
    pdf_object_key = Column(String)
    status = Column(String, default="issued")
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    used_at = Column(DateTime(timezone=True))
