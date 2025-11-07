from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from core.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    industry = Column(String)
    size = Column(String)
    website = Column(String)
    phone = Column(String)
    email = Column(String)
    address = Column(Text)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    country = Column(String)
    description = Column(Text)
    revenue = Column(Integer)

    # Foreign Key for owner
    owner_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    # Relationships
    owner = relationship("UserProfile")
    contacts = relationship("Contact", back_populates="company")
    deals = relationship("Deal", back_populates="company")
