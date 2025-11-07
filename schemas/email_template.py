from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid
from models.email_template import TemplateCategory, TemplateStatus


class EmailTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    subject: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    category: TemplateCategory = TemplateCategory.GENERAL
    status: TemplateStatus = TemplateStatus.DRAFT


class EmailTemplateCreate(EmailTemplateBase):
    pass


class EmailTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    subject: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = None
    category: Optional[TemplateCategory] = None
    status: Optional[TemplateStatus] = None


class EmailTemplateResponse(EmailTemplateBase):
    id: uuid.UUID
    usage_count: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


class EmailTemplateListResponse(BaseModel):
    templates: List[EmailTemplateResponse]
    total: int


class SendEmailRequest(BaseModel):
    template_id: Optional[uuid.UUID] = None
    to: str = Field(...,
                    pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    subject: Optional[str] = None  # Override template subject if provided
    content: Optional[str] = None  # Override template content if provided
    merge_data: Optional[dict] = None  # Data for merge field substitution


class SendEmailResponse(BaseModel):
    success: bool
    message: str
    email_log_id: Optional[uuid.UUID] = None
    sender_email: Optional[str] = None  # The email address used as sender


class EmailLogResponse(BaseModel):
    id: uuid.UUID
    template_id: Optional[uuid.UUID] = None
    sender_email: str
    recipient_email: str
    subject: str
    status: str
    sent_at: datetime
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MergeField(BaseModel):
    field: str
    description: str
    example: Optional[str] = None
    category: Optional[str] = "General"  # Category for grouping fields


class MergeFieldsResponse(BaseModel):
    fields: List[MergeField]


class TemplatePreviewRequest(BaseModel):
    template_id: uuid.UUID
    merge_data: dict
    contact_id: Optional[uuid.UUID] = None
    deal_id: Optional[uuid.UUID] = None
    activity_id: Optional[uuid.UUID] = None
    task_id: Optional[uuid.UUID] = None


class TemplatePreviewResponse(BaseModel):
    subject: str
    content: str
