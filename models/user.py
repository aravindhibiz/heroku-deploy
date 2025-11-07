from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from ..core.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    role = Column(String, default="sales_rep")
    hashed_password = Column(String, nullable=True)  # Optional for Microsoft SSO users
    microsoft_id = Column(String, unique=True, index=True, nullable=True)  # Microsoft user identifier (oid claim)
    auth_provider = Column(String, default="local", nullable=False)  # 'local' or 'microsoft'
    is_active = Column(Boolean, default=True)
    phone = Column(String)
    avatar_url = Column(Text)

    # Login attempt tracking (for max login attempts feature)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    account_locked_until = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    # Relationships
    integrations = relationship("Integration", back_populates="user")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
