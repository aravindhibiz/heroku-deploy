from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from ..core.database import Base


class Note(Base):
    __tablename__ = "notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String)
    content = Column(Text, nullable=False)

    # Foreign Keys
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    # Relationships
    contact = relationship("Contact", back_populates="contact_notes")
    author = relationship("UserProfile")
