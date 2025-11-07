from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime
import uuid
from user import UserResponse


class CompanyForActivity(BaseModel):
    id: uuid.UUID
    name: str

    class Config:
        from_attributes = True


class ContactForActivity(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: Optional[str] = None
    company_id: Optional[uuid.UUID] = None
    company: Optional[CompanyForActivity] = None

    class Config:
        from_attributes = True


class DealForActivity(BaseModel):
    id: uuid.UUID
    name: str
    value: Optional[float] = None
    stage: Optional[str] = None

    class Config:
        from_attributes = True


class ActivityBase(BaseModel):
    type: str
    subject: str
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    outcome: Optional[str] = None


class ActivityCreate(ActivityBase):
    contact_id: Optional[uuid.UUID] = None
    deal_id: Optional[uuid.UUID] = None
    custom_fields: Optional[Dict[str, Any]] = None


class ActivityUpdate(BaseModel):
    type: Optional[str] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    outcome: Optional[str] = None
    contact_id: Optional[uuid.UUID] = None
    deal_id: Optional[uuid.UUID] = None
    custom_fields: Optional[Dict[str, Any]] = None


class ActivityResponse(ActivityBase):
    id: uuid.UUID
    contact_id: Optional[uuid.UUID] = None
    deal_id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    custom_fields: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ActivityWithRelations(ActivityResponse):
    contact: Optional[ContactForActivity] = None
    deal: Optional[DealForActivity] = None
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True
