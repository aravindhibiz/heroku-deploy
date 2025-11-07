from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from core.database import Base


class Integration(Base):
    __tablename__ = "integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey(
        "user_profiles.id"), nullable=False)

    # Integration details
    # gmail, google_calendar, twilio, slack
    provider = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    # connected, disconnected, error
    status = Column(String(20), nullable=False, default='disconnected')

    # OAuth and API credentials (encrypted)
    access_token = Column(Text)  # Encrypted OAuth access token
    refresh_token = Column(Text)  # Encrypted OAuth refresh token
    expires_at = Column(DateTime)

    # Integration configuration
    config = Column(JSON, default={})  # Provider-specific settings

    # Sync information
    last_sync = Column(DateTime)
    # 5min, 15min, 1hour, manual
    sync_frequency = Column(String(20), default='15min')
    auto_sync = Column(Boolean, default=True)

    # Error tracking
    last_error = Column(Text)
    error_count = Column(String(10), default='0')

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("UserProfile", back_populates="integrations")
    logs = relationship(
        "IntegrationLog", back_populates="integration", cascade="all, delete-orphan")


class IntegrationLog(Base):
    __tablename__ = "integration_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(UUID(as_uuid=True), ForeignKey(
        "integrations.id"), nullable=False)

    # Log details
    # sync, connect, disconnect, test, error
    action = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)  # success, error, warning
    message = Column(Text)
    details = Column(JSON, default={})

    # Data stats
    records_processed = Column(String(10), default='0')
    records_created = Column(String(10), default='0')
    records_updated = Column(String(10), default='0')
    records_failed = Column(String(10), default='0')

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    integration = relationship("Integration", back_populates="logs")


class IntegrationWebhook(Base):
    __tablename__ = "integration_webhooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(UUID(as_uuid=True), ForeignKey(
        "integrations.id"), nullable=False)

    # Webhook details
    webhook_url = Column(String(500), nullable=False)
    webhook_secret = Column(String(100))
    events = Column(JSON, default=[])  # List of events to listen for

    # Status
    is_active = Column(Boolean, default=True)
    last_received = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    # Relationships
    integration = relationship("Integration")
