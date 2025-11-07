from sqlalchemy import Column, String, DateTime, Text, Integer, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from ..core.database import Base

class Deal(Base):
    __tablename__ = "deals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    value = Column(Numeric(precision=10, scale=2))
    stage = Column(String, default="lead")
    probability = Column(Integer, default=0)
    expected_close_date = Column(DateTime(timezone=True))
    actual_close_date = Column(DateTime(timezone=True))
    description = Column(Text)
    source = Column(String)
    lost_reason = Column(String)
    next_action = Column(Text)

    # Foreign Keys
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"))
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"))
    owner_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    company = relationship("Company", back_populates="deals")
    contact = relationship("Contact", back_populates="deals")
    owner = relationship("UserProfile")
    activities = relationship("Activity", back_populates="deal")
    documents = relationship("DealDocument", back_populates="deal")