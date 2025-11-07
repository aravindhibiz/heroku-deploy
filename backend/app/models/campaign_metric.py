from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class CampaignMetric(Base):
    """
    Time-series performance data for campaigns.
    Stores daily/periodic snapshots of campaign metrics for trend analysis.
    """
    __tablename__ = "campaign_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Campaign Reference
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)

    # Metric Period
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    period_type = Column(String(20), default="daily", nullable=False)  # "hourly", "daily", "weekly", "monthly"

    # Performance Metrics Snapshot
    sent_count = Column(Integer, default=0, nullable=False)
    delivered_count = Column(Integer, default=0, nullable=False)
    opened_count = Column(Integer, default=0, nullable=False)
    clicked_count = Column(Integer, default=0, nullable=False)
    responded_count = Column(Integer, default=0, nullable=False)
    bounced_count = Column(Integer, default=0, nullable=False)
    unsubscribed_count = Column(Integer, default=0, nullable=False)
    converted_count = Column(Integer, default=0, nullable=False)

    # Calculated Rates (stored for quick access)
    open_rate = Column(Numeric(5, 2), default=0, nullable=False)  # Percentage
    click_rate = Column(Numeric(5, 2), default=0, nullable=False)  # Percentage
    conversion_rate = Column(Numeric(5, 2), default=0, nullable=False)  # Percentage
    bounce_rate = Column(Numeric(5, 2), default=0, nullable=False)  # Percentage

    # Financial Metrics
    cost_to_date = Column(Numeric(12, 2), default=0, nullable=False)
    revenue_to_date = Column(Numeric(12, 2), default=0, nullable=False)
    roi = Column(Numeric(10, 2), default=0, nullable=False)  # Percentage

    # Additional Metrics
    prospects_generated = Column(Integer, default=0, nullable=False)
    new_contacts_count = Column(Integer, default=0, nullable=False)
    deals_created_count = Column(Integer, default=0, nullable=False)

    # Custom/Extended Metrics (JSON)
    additional_metrics = Column(JSONB, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    campaign = relationship("Campaign", back_populates="metrics")

    def __repr__(self):
        return f"<CampaignMetric Campaign={self.campaign_id} Date={self.recorded_at} Sent={self.sent_count}>"


class LeadScoreHistory(Base):
    """
    Track lead score changes over time for prospects.
    Helps understand what activities improve lead quality.
    """
    __tablename__ = "lead_score_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Prospect Reference
    prospect_id = Column(UUID(as_uuid=True), ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False, index=True)

    # Score Change
    old_score = Column(Integer, nullable=False)
    new_score = Column(Integer, nullable=False)
    score_change = Column(Integer, nullable=False)  # Can be positive or negative

    # Reason for Change
    reason = Column(String(255), nullable=False)  # e.g., "Email opened", "Form submitted", "Manual adjustment"
    activity_type = Column(String(50), nullable=True)  # e.g., "email_open", "link_click", "form_submit"

    # Context
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True)
    campaign_contact_id = Column(UUID(as_uuid=True), ForeignKey("campaign_contacts.id", ondelete="SET NULL"), nullable=True)

    # Who made the change (if manual)
    changed_by = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True)

    # Additional Context
    notes = Column(String(500), nullable=True)
    custom_metadata = Column(JSONB, nullable=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    prospect = relationship("Prospect", back_populates="lead_score_history")
    campaign = relationship("Campaign")
    campaign_contact = relationship("CampaignContact")
    user = relationship("UserProfile")

    def __repr__(self):
        return f"<LeadScoreHistory Prospect={self.prospect_id} {self.old_score}→{self.new_score} ({self.reason})>"
