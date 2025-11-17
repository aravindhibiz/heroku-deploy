from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file explicitly
# Path from backend/app/core/config.py to root/.env
env_file = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_file)


class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours instead of 30 minutes

    # Frontend URL for OAuth redirects
    FRONTEND_URL: str = "http://localhost:3000"

    # Google OAuth settings
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # Microsoft SSO settings
    MICROSOFT_CLIENT_ID: Optional[str] = None
    MICROSOFT_CLIENT_SECRET: Optional[str] = None
    MICROSOFT_TENANT_ID: Optional[str] = None
    MICROSOFT_AUTHORITY: Optional[str] = None
    MICROSOFT_REDIRECT_URI: Optional[str] = None
    MICROSOFT_SCOPES: str = "openid email profile User.Read"

    # Microsoft Calendar OAuth settings
    MICROSOFT_CALENDAR_REDIRECT_URI: Optional[str] = None

    # Integration settings
    INTEGRATION_ENCRYPTION_KEY: Optional[str] = None

    # Email settings (SMTP - Outlook/Office365)
    EMAIL_PROVIDER: str = "smtp"
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_SECURE: bool = False
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None
    FROM_EMAIL: Optional[str] = None

    # Legacy SendGrid settings (deprecated)
    SENDGRID_API_KEY: Optional[str] = None

    # Azure Blob Storage settings
    AZURE_STORAGE_ACCOUNT_NAME: Optional[str] = None
    AZURE_STORAGE_ACCOUNT_KEY: Optional[str] = None
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = None
    AZURE_BLOB_CONTAINER_NAME: str = "crm-files"

    # Storage backend configuration
    STORAGE_BACKEND: str = "local"

    class Config:
        # Look for .env file in the backend directory
        env_file = Path(__file__).parent.parent.parent / ".env"
        case_sensitive = False  # Allow case-insensitive environment variables


# Create settings instance
settings = Settings()
