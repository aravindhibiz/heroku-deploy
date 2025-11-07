from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, Numeric, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.core.database import Base


class ProspectStatus(str, enum.Enum):
    """Prospect status workflow"""
    NEW = "NEW"  # Just captured, not yet reviewed
    CONVERTED = "CONVERTED"  # Moved to contacts table
    REJECTED = "REJECTED"  # Not a good fit


class ProspectSource(str, enum.Enum):
    """Source channels for prospects"""
    EMAIL_CAMPAIGN = "EMAIL_CAMPAIGN"
    WEB_FORM = "WEB_FORM"
    PHONE = "PHONE"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"
    MANUAL_ENTRY = "MANUAL_ENTRY"
    REFERRAL = "REFERRAL"
    OTHER = "OTHER"


class Prospect(Base):
    """
    Prospect model - stores potential leads from marketing campaigns.
    These are separate from contacts until qualified and converted.
    """
    __tablename__ = "prospects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Basic Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    email = Column(String(255), unique=True, nullable=True, index=True)  # Unique constraint for deduplication
    phone = Column(String(50), unique=True, nullable=True, index=True)  # Unique constraint for deduplication

    # Company Information
    company_name = Column(String(255), nullable=True)
    job_title = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)

    # Additional Details
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Source Tracking
    source = Column(SQLEnum(ProspectSource), default=ProspectSource.OTHER, nullable=False)
    source_details = Column(Text, nullable=True)  # Additional context about source

    # Status & Workflow
    status = Column(SQLEnum(ProspectStatus), default=ProspectStatus.NEW, nullable=False, index=True)

    # Lead Scoring
    lead_score = Column(Integer, default=0, nullable=False)  # 0-100 score based on engagement

    # Campaign Association
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)

    # Conversion Tracking
    converted_to_contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    converted_at = Column(DateTime(timezone=True), nullable=True)

    # Ownership
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_contacted_at = Column(DateTime(timezone=True), nullable=True)

    # Social Media (optional)
    linkedin_url = Column(String(255), nullable=True)
    twitter_handle = Column(String(100), nullable=True)

    # Website
    website = Column(String(255), nullable=True)

    # Address (optional for some use cases)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)

    # Relationships
    campaign = relationship("Campaign", back_populates="prospects", foreign_keys=[campaign_id])
    converted_to_contact = relationship("Contact", foreign_keys=[converted_to_contact_id])
    assigned_user = relationship("UserProfile", foreign_keys=[assigned_to], backref="assigned_prospects")
    creator = relationship("UserProfile", foreign_keys=[created_by], backref="created_prospects")

    # Many-to-many with campaigns through campaign_contacts
    campaign_associations = relationship("CampaignContact", back_populates="prospect", cascade="all, delete-orphan")

    # Lead score history
    lead_score_history = relationship("LeadScoreHistory", back_populates="prospect", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Prospect {self.first_name} {self.last_name} ({self.email}) - {self.status}>"

    @property
    def full_name(self):
        """Returns full name of prospect"""
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_converted(self):
        """Check if prospect has been converted to contact"""
        return self.status == ProspectStatus.CONVERTED and self.converted_to_contact_id is not None
