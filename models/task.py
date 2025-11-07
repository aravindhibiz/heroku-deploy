from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from core.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default="pending")  # pending, in_progress, completed
    priority = Column(String, default="medium")  # low, medium, high
    due_date = Column(DateTime(timezone=True))

    # Foreign Keys
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"))
    deal_id = Column(UUID(as_uuid=True), ForeignKey("deals.id"))
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    contact = relationship("Contact", back_populates="tasks")
    assigned_user = relationship("UserProfile", foreign_keys=[assigned_to])
    creator = relationship("UserProfile", foreign_keys=[created_by])