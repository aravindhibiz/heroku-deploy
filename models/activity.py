from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from ..core.database import Base

class Activity(Base):
    __tablename__ = "activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String, nullable=False)  # call, email, meeting, note, task
    subject = Column(String, nullable=False)
    description = Column(Text)
    duration_minutes = Column(Integer)
    outcome = Column(String)

    # Foreign Keys
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"))
    deal_id = Column(UUID(as_uuid=True), ForeignKey("deals.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    contact = relationship("Contact", back_populates="activities")
    deal = relationship("Deal", back_populates="activities")
    user = relationship("UserProfile")