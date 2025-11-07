from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean, Enum as SqlEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from core.database import Base


class TemplateCategory(enum.Enum):
    GENERAL = "general"
    ONBOARDING = "onboarding"
    FOLLOWUP = "followup"
    CLOSING = "closing"
    NURTURING = "nurturing"
    REMINDER = "reminder"


class TemplateStatus(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"


class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(SqlEnum(TemplateCategory), nullable=False,
                      default=TemplateCategory.GENERAL)
    status = Column(SqlEnum(TemplateStatus), nullable=False,
                    default=TemplateStatus.DRAFT)
    usage_count = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())
    # Optional: track who created the template
    created_by = Column(UUID(as_uuid=True), nullable=True)

    def __repr__(self):
        return f"<EmailTemplate(name='{self.name}', category='{self.category}')>"


class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Optional: track if template was used
    template_id = Column(UUID(as_uuid=True), nullable=True)
    sender_email = Column(String(255), nullable=False)
    recipient_email = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(50), nullable=False)  # sent, failed, pending

    # Email metadata
    cc = Column(Text, nullable=True)  # JSON string of CC emails
    bcc = Column(Text, nullable=True)  # JSON string of BCC emails

    # Tracking
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    opened_at = Column(DateTime(timezone=True), nullable=True)
    clicked_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<EmailLog(recipient='{self.recipient_email}', status='{self.status}')>"
