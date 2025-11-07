from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from core.database import Base


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String)
    phone = Column(String)
    mobile = Column(String)
    position = Column(String)
    status = Column(String, default="active")
    notes = Column(Text)
    social_linkedin = Column(String)
    social_twitter = Column(String)

    # Foreign Keys
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"))
    owner_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    # Relationships
    company = relationship("Company", back_populates="contacts")
    owner = relationship("UserProfile")
    deals = relationship("Deal", back_populates="contact")
    activities = relationship("Activity", back_populates="contact")
    tasks = relationship("Task", back_populates="contact")
    contact_notes = relationship("Note", back_populates="contact")
