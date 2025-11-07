from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from ..core.database import Base

class DealDocument(Base):
    __tablename__ = "deal_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    file_path = Column(Text, nullable=False)
    file_size = Column(String)
    mime_type = Column(String)

    # Foreign Keys
    deal_id = Column(UUID(as_uuid=True), ForeignKey("deals.id"))
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    deal = relationship("Deal", back_populates="documents")
    uploader = relationship("UserProfile")