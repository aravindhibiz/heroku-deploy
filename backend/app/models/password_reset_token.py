"""
Password Reset Token Model

This model stores temporary tokens for password reset functionality.
Tokens expire after a specified duration and can only be used once.
"""

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid
import secrets

from app.core.database import Base


class PasswordResetToken(Base):
    """Password reset token for user authentication"""
    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(100), unique=True, nullable=False, index=True)
    is_used = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    used_at = Column(DateTime, nullable=True)

    # Relationship
    user = relationship("UserProfile", back_populates="password_reset_tokens")

    @staticmethod
    def generate_token():
        """Generate a secure random token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def get_expiration_time(hours=1):
        """Get expiration time (default 1 hour from now)"""
        return datetime.utcnow() + timedelta(hours=hours)

    def is_valid(self):
        """Check if token is still valid (not expired and not used)"""
        return (
            not self.is_used
            and self.expires_at > datetime.utcnow()
        )

    def mark_as_used(self):
        """Mark token as used"""
        self.is_used = True
        self.used_at = datetime.utcnow()
