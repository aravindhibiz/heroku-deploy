from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Numeric, Boolean, Text, Enum as SQLEnum, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.core.database import Base


class EngagementStatus(str, enum.Enum):
    """Engagement status for campaign recipients"""
    PENDING = "pending"  # Scheduled but not sent yet
    SENT = "sent"  # Sent/attempted
    DELIVERED = "delivered"  # Confirmed delivery
    OPENED = "opened"  # Opened (email)
    CLICKED = "clicked"  # Clicked a link
    RESPONDED = "responded"  # Replied or took action
    CONVERTED = "converted"  # Became a deal/customer
    BOUNCED = "bounced"  # Failed delivery
    UNSUBSCRIBED = "unsubscribed"  # Opted out
    FAILED = "failed"  # Failed to send


class CampaignContact(Base):
    """
    Junction table connecting campaigns to contacts and prospects.
    Tracks individual engagement metrics per person per campaign.

    Each row represents one person's participation in one campaign.
    """
    __tablename__ = "campaign_contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Campaign Reference
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)

    # Recipient Reference (either contact OR prospect, not both)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=True, index=True)
    prospect_id = Column(UUID(as_uuid=True), ForeignKey("prospects.id", ondelete="CASCADE"), nullable=True, index=True)

    # Engagement Status
    status = Column(SQLEnum(EngagementStatus), default=EngagementStatus.PENDING, nullable=False, index=True)

    # Engagement Timestamps
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)  # First open
    clicked_at = Column(DateTime(timezone=True), nullable=True)  # First click
    responded_at = Column(DateTime(timezone=True), nullable=True)  # First response
    converted_at = Column(DateTime(timezone=True), nullable=True)  # Conversion to deal
    bounced_at = Column(DateTime(timezone=True), nullable=True)
    unsubscribed_at = Column(DateTime(timezone=True), nullable=True)

    # Engagement Counts
    open_count = Column(Integer, default=0, nullable=False)  # Number of times opened
    click_count = Column(Integer, default=0, nullable=False)  # Number of times clicked

    # Lead Scoring
    lead_score_change = Column(Integer, default=0, nullable=False)  # Points earned from this campaign

    # Email-Specific Tracking
    email_sent_to = Column(String(255), nullable=True)  # Actual email address used
    email_message_id = Column(String(255), nullable=True)  # Email provider message ID
    email_subject = Column(String(500), nullable=True)  # Subject line sent

    # Conversion Tracking
    deal_id = Column(UUID(as_uuid=True), ForeignKey("deals.id", ondelete="SET NULL"), nullable=True)  # If converted, which deal?
    conversion_value = Column(Numeric(12, 2), nullable=True)  # Deal value at time of conversion

    # Error Tracking
    error_message = Column(Text, nullable=True)  # If failed/bounced, why?
    bounce_type = Column(String(50), nullable=True)  # "hard" or "soft" bounce

    # Additional Context
    notes = Column(Text, nullable=True)
    custom_metadata = Column(JSONB, nullable=True)  # Additional custom data

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Check constraint: either contact_id OR prospect_id must be set, but not both
    __table_args__ = (
        CheckConstraint(
            '(contact_id IS NOT NULL AND prospect_id IS NULL) OR (contact_id IS NULL AND prospect_id IS NOT NULL)',
            name='check_contact_or_prospect'
        ),
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="campaign_contacts")
    contact = relationship("Contact", backref="campaign_participations")
    prospect = relationship("Prospect", back_populates="campaign_associations")
    deal = relationship("Deal", backref="campaign_associations")

    def __repr__(self):
        recipient_type = "Contact" if self.contact_id else "Prospect"
        recipient_id = self.contact_id or self.prospect_id
        return f"<CampaignContact Campaign={self.campaign_id} {recipient_type}={recipient_id} Status={self.status}>"

    @property
    def recipient_type(self):
        """Returns whether this is for a contact or prospect"""
        return "contact" if self.contact_id else "prospect"

    @property
    def recipient_id(self):
        """Returns the ID of the recipient (contact or prospect)"""
        return self.contact_id or self.prospect_id

    @property
    def was_opened(self):
        """Check if recipient opened the message"""
        return self.opened_at is not None

    @property
    def was_clicked(self):
        """Check if recipient clicked a link"""
        return self.clicked_at is not None

    @property
    def was_converted(self):
        """Check if recipient converted to a deal"""
        return self.status == EngagementStatus.CONVERTED and self.deal_id is not None

    @property
    def was_delivered(self):
        """Check if message was successfully delivered"""
        return self.delivered_at is not None

    @property
    def engagement_score(self):
        """Calculate engagement score based on actions taken"""
        score = 0
        if self.was_delivered:
            score += 1
        if self.was_opened:
            score += 2
        if self.was_clicked:
            score += 3
        if self.responded_at:
            score += 5
        if self.was_converted:
            score += 10
        return score
