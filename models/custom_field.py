from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey, JSON, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from ..core.database import Base


class FieldType(str, enum.Enum):
    TEXT = "text"
    NUMBER = "number"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    TEXTAREA = "textarea"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"


class EntityType(str, enum.Enum):
    CONTACT = "contact"
    COMPANY = "company"
    DEAL = "deal"
    ACTIVITY = "activity"
    TASK = "task"


class PlacementType(str, enum.Enum):
    FORM = "form"
    DETAIL_VIEW = "detail_view"
    LIST_VIEW = "list_view"
    BOTH = "both"


class CustomField(Base):
    __tablename__ = "custom_fields"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)  # Display name
    # Internal key (auto-generated)
    field_key = Column(String, nullable=False, unique=True)
    description = Column(Text)
    field_type = Column(SQLEnum(FieldType), nullable=False)
    entity_type = Column(SQLEnum(EntityType), nullable=False)
    is_required = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    placement = Column(SQLEnum(PlacementType), default=PlacementType.BOTH)

    # Field configuration (JSON to store type-specific settings)
    field_config = Column(JSON)  # For select options, validation rules, etc.

    # Display properties
    order_index = Column(String, default="0")  # For ordering fields
    help_text = Column(Text)
    placeholder = Column(String)

    # Audit fields
    created_by = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    # Relationships
    creator = relationship("UserProfile")
    field_values = relationship(
        "CustomFieldValue", back_populates="custom_field", cascade="all, delete-orphan")


class CustomFieldValue(Base):
    __tablename__ = "custom_field_values"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    custom_field_id = Column(UUID(as_uuid=True), ForeignKey(
        "custom_fields.id"), nullable=False)
    # ID of the record (contact, company, etc.)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    entity_type = Column(SQLEnum(EntityType), nullable=False)

    # Store all values as text, convert based on field type
    value = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    # Relationships
    custom_field = relationship("CustomField", back_populates="field_values")

    # Note: Could add unique constraint later if needed
    # __table_args__ = (UniqueConstraint('custom_field_id', 'entity_id', name='_field_entity_uc'),)
