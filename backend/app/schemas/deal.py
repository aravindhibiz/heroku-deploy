from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from decimal import Decimal
import uuid
from .user import UserResponse
from .contact import ContactResponse
from .company import CompanyBasicResponse


class DealBase(BaseModel):
    name: str
    value: Optional[float] = Field(
        None, description="Deal value as float for proper JSON serialization")
    stage: Optional[str] = "lead"
    probability: Optional[int] = 0
    expected_close_date: Optional[Union[datetime, date]] = None
    description: Optional[str] = None
    source: Optional[str] = None
    next_action: Optional[str] = None

    @field_validator('expected_close_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if v is None:
            return v
        if isinstance(v, (datetime, date)):
            return v
        # Handle string dates in YYYY-MM-DD format
        if isinstance(v, str):
            try:
                # Try parsing as date first
                return datetime.strptime(v, '%Y-%m-%d').date()
            except ValueError:
                try:
                    # Try parsing as datetime
                    return datetime.fromisoformat(v.replace('Z', '+00:00'))
                except ValueError:
                    return v
        return v


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
    expected_close_date: Optional[Union[datetime, date]] = None
    actual_close_date: Optional[Union[datetime, date]] = None
    description: Optional[str] = None
    source: Optional[str] = None
    lost_reason: Optional[str] = None
    next_action: Optional[str] = None

    @field_validator('expected_close_date', 'actual_close_date', mode='before')
    @classmethod
    def parse_date(cls, v):
        if v is None:
            return v
        if isinstance(v, (datetime, date)):
            return v
        # Handle string dates in YYYY-MM-DD format
        if isinstance(v, str):
            try:
                # Try parsing as date first
                return datetime.strptime(v, '%Y-%m-%d').date()
            except ValueError:
                try:
                    # Try parsing as datetime
                    return datetime.fromisoformat(v.replace('Z', '+00:00'))
                except ValueError:
                    return v
        return v
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
