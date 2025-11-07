from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from .user import UserResponse
from .company import CompanyBasicResponse


class ContactBase(BaseModel):
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    position: Optional[str] = None
    status: Optional[str] = "active"
    notes: Optional[str] = None
    social_linkedin: Optional[str] = None
    social_twitter: Optional[str] = None


class ContactCreate(ContactBase):
    company_id: Optional[uuid.UUID] = None
    owner_id: Optional[uuid.UUID] = None
    custom_fields: Optional[Dict[str, Any]] = None


class ContactUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    position: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    social_linkedin: Optional[str] = None
    social_twitter: Optional[str] = None
    company_id: Optional[uuid.UUID] = None
    custom_fields: Optional[Dict[str, Any]] = None


class ContactResponse(ContactBase):
    id: uuid.UUID
    company_id: Optional[uuid.UUID] = None
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    custom_fields: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ContactWithRelations(ContactResponse):
    owner: Optional[UserResponse] = None
    company: Optional[CompanyBasicResponse] = None
