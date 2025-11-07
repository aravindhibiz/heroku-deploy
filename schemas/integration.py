from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


class IntegrationBase(BaseModel):
    provider: str
    name: str
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = {}
    auto_sync: bool = True
    sync_frequency: str = "15min"


class IntegrationCreate(IntegrationBase):
    pass


class IntegrationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    auto_sync: Optional[bool] = None
    sync_frequency: Optional[str] = None


class IntegrationResponse(IntegrationBase):
    id: UUID
    user_id: UUID
    status: str
    last_sync: Optional[datetime] = None
    last_error: Optional[str] = None
    error_count: str = "0"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IntegrationLogResponse(BaseModel):
    id: UUID
    integration_id: UUID
    action: str
    status: str
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = {}
    records_processed: str = "0"
    records_created: str = "0"
    records_updated: str = "0"
    records_failed: str = "0"
    created_at: datetime

    class Config:
        from_attributes = True


class OAuthCallbackRequest(BaseModel):
    provider: str
    code: str
    state: Optional[str] = None


class IntegrationTestRequest(BaseModel):
    integration_id: UUID


class IntegrationSyncRequest(BaseModel):
    integration_id: UUID
    force: bool = False


# Gmail specific schemas
class GmailConfig(BaseModel):
    sync_emails: bool = True
    sync_contacts: bool = True
    email_sync_days: int = 30
    auto_log_emails: bool = True
    create_contacts_from_emails: bool = False


# Google Calendar specific schemas
class GoogleCalendarConfig(BaseModel):
    sync_calendar: bool = True
    calendar_id: Optional[str] = "primary"
    sync_events_days_forward: int = 30
    sync_events_days_back: int = 7
    auto_create_activities: bool = True
    meeting_default_duration: int = 30  # minutes
