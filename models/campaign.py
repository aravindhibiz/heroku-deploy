from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, Numeric, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.core.database import Base


class CampaignType(str, enum.Enum):
    """Campaign channel types"""
    EMAIL = "email"
    WEB_FORM = "web_form"
    PHONE = "phone"
    SOCIAL_MEDIA = "social_media"
    MANUAL_ENTRY = "manual_entry"
    EVENT = "event"
    OTHER = "other"


class CampaignStatus(str, enum.Enum):
    """Campaign status workflow"""
    DRAFT = "draft"  # Being created, not ready
    SCHEDULED = "scheduled"  # Ready to go, waiting for start date
    ACTIVE = "active"  # Currently running
    PAUSED = "paused"  # Temporarily stopped
    COMPLETED = "completed"  # Finished successfully
    CANCELLED = "cancelled"  # Stopped before completion


class Campaign(Base):
    """
    Campaign model - marketing campaigns across multiple channels.
    Tracks performance, budget, ROI, and generates prospects.
    """
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Basic Information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Campaign Configuration
    type = Column(SQLEnum(CampaignType), nullable=False, index=True)
    status = Column(SQLEnum(CampaignStatus), default=CampaignStatus.DRAFT, nullable=False, index=True)

    # Scheduling
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    actual_start_date = Column(DateTime(timezone=True), nullable=True)  # When it actually started
    actual_end_date = Column(DateTime(timezone=True), nullable=True)  # When it actually ended

    # Budget & ROI
    budget = Column(Numeric(12, 2), default=0, nullable=False)  # Campaign budget
    actual_cost = Column(Numeric(12, 2), default=0, nullable=False)  # Actual spend
    expected_revenue = Column(Numeric(12, 2), default=0, nullable=True)  # Expected revenue target
    actual_revenue = Column(Numeric(12, 2), default=0, nullable=False)  # Actual revenue from conversions

    # Goals & Targets
    target_audience_size = Column(Integer, default=0, nullable=True)  # How many people to reach
    target_response_rate = Column(Numeric(5, 2), default=0, nullable=True)  # Expected response rate %
    target_conversion_rate = Column(Numeric(5, 2), default=0, nullable=True)  # Expected conversion rate %

    # Performance Metrics (aggregated from campaign_contacts)
    sent_count = Column(Integer, default=0, nullable=False)  # Total sent/attempted
    delivered_count = Column(Integer, default=0, nullable=False)  # Successfully delivered
    opened_count = Column(Integer, default=0, nullable=False)  # Opened (email)
    clicked_count = Column(Integer, default=0, nullable=False)  # Clicked links
    responded_count = Column(Integer, default=0, nullable=False)  # Responded/replied
    bounced_count = Column(Integer, default=0, nullable=False)  # Bounced (email)
    unsubscribed_count = Column(Integer, default=0, nullable=False)  # Unsubscribed
    converted_count = Column(Integer, default=0, nullable=False)  # Converted to deals
    prospects_generated = Column(Integer, default=0, nullable=False)  # New prospects created

    # Email-Specific Configuration (if type=EMAIL)
    email_template_id = Column(UUID(as_uuid=True), ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True)
    email_subject = Column(String(500), nullable=True)
    email_from_name = Column(String(255), nullable=True)
    email_from_email = Column(String(255), nullable=True)

    # Target Audience Configuration
    # Stores filter criteria for selecting contacts/prospects
    audience_filters = Column(JSONB, nullable=True)  # e.g., {"status": ["active"], "tags": ["vip"]}

    # Campaign Settings
    is_automated = Column(Boolean, default=False, nullable=False)  # Is this an automated campaign?
    automation_config = Column(JSONB, nullable=True)  # Automation rules/schedule

    # Tags & Categorization
    tags = Column(JSONB, nullable=True)  # ["product-launch", "Q4-2025"]
    category = Column(String(100), nullable=True, index=True)  # e.g., "Product Launch", "Nurture"

    # Ownership & Tracking
    owner_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_executed_at = Column(DateTime(timezone=True), nullable=True)  # Last time campaign was executed

    # Notes & Additional Info
    notes = Column(Text, nullable=True)

    # Relationships
    owner = relationship("UserProfile", foreign_keys=[owner_id], backref="owned_campaigns")
    creator = relationship("UserProfile", foreign_keys=[created_by], backref="created_campaigns")
    email_template = relationship("EmailTemplate", foreign_keys=[email_template_id])

    # Prospects generated by this campaign
    prospects = relationship("Prospect", back_populates="campaign", foreign_keys="Prospect.campaign_id")

    # Many-to-many with contacts and prospects through campaign_contacts
    campaign_contacts = relationship("CampaignContact", back_populates="campaign", cascade="all, delete-orphan")

    # Performance metrics over time
    metrics = relationship("CampaignMetric", back_populates="campaign", cascade="all, delete-orphan", order_by="CampaignMetric.recorded_at.desc()")

    def __repr__(self):
        return f"<Campaign {self.name} ({self.type}) - {self.status}>"

    @property
    def roi(self):
        """Calculate Return on Investment"""
        if self.actual_cost > 0:
            return ((self.actual_revenue - self.actual_cost) / self.actual_cost) * 100
        return 0.0

    @property
    def open_rate(self):
        """Calculate email open rate percentage"""
        if self.delivered_count > 0:
            return (self.opened_count / self.delivered_count) * 100
        return 0.0

    @property
    def click_rate(self):
        """Calculate click-through rate percentage"""
        if self.opened_count > 0:
            return (self.clicked_count / self.opened_count) * 100
        return 0.0

    @property
    def response_rate(self):
        """Calculate response rate percentage"""
        if self.delivered_count > 0:
            return (self.responded_count / self.delivered_count) * 100
        return 0.0

    @property
    def conversion_rate(self):
        """Calculate conversion rate percentage"""
        if self.delivered_count > 0:
            return (self.converted_count / self.delivered_count) * 100
        return 0.0

    @property
    def delivery_rate(self):
        """Calculate delivery rate percentage"""
        if self.sent_count > 0:
            return (self.delivered_count / self.sent_count) * 100
        return 0.0

    @property
    def bounce_rate(self):
        """Calculate bounce rate percentage"""
        if self.sent_count > 0:
            return (self.bounced_count / self.sent_count) * 100
        return 0.0

    @property
    def is_active(self):
        """Check if campaign is currently active"""
        return self.status == CampaignStatus.ACTIVE

    @property
    def is_scheduled(self):
        """Check if campaign is scheduled for future"""
        return self.status == CampaignStatus.SCHEDULED

    @property
    def is_draft(self):
        """Check if campaign is in draft mode"""
        return self.status == CampaignStatus.DRAFT

    @property
    def days_remaining(self):
        """Calculate days remaining until end date"""
        if self.end_date:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            if self.end_date > now:
                delta = self.end_date - now
                return delta.days
        return 0
