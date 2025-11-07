from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
import uuid
from user import UserResponse
from contact import ContactResponse
from company import CompanyBasicResponse


class DealBase(BaseModel):
    name: str
    value: Optional[float] = Field(
        None, description="Deal value as float for proper JSON serialization")
    stage: Optional[str] = "lead"
    probability: Optional[int] = 0
    expected_close_date: Optional[datetime] = None
    description: Optional[str] = None
    source: Optional[str] = None
    next_action: Optional[str] = None


class DealCreate(DealBase):
    company_id: Optional[uuid.UUID] = None
    contact_id: Optional[uuid.UUID] = None
    custom_fields: Optional[Dict[str, Any]] = None


class DealUpdate(BaseModel):
    name: Optional[str] = None
    value: Optional[float] = Field(
        None, description="Deal value as float for proper JSON serialization")
    stage: Optional[str] = None
    probability: Optional[int] = None
    expected_close_date: Optional[datetime] = None
    actual_close_date: Optional[datetime] = None
    description: Optional[str] = None
    source: Optional[str] = None
    lost_reason: Optional[str] = None
    next_action: Optional[str] = None
    company_id: Optional[uuid.UUID] = None
    contact_id: Optional[uuid.UUID] = None
    custom_fields: Optional[Dict[str, Any]] = None


class DealResponse(DealBase):
    id: uuid.UUID
    company_id: Optional[uuid.UUID] = None
    contact_id: Optional[uuid.UUID] = None
    owner_id: uuid.UUID
    actual_close_date: Optional[datetime] = None
    lost_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    custom_fields: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class DealWithRelations(DealResponse):
    owner: Optional[UserResponse] = None
    contact: Optional[ContactResponse] = None
    company: Optional[CompanyBasicResponse] = None
