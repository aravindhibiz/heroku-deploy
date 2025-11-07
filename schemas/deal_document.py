"""
Deal Document schemas for request/response validation.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional


class DealDocumentBase(BaseModel):
    """Base schema for deal documents."""
    name: str = Field(..., description="Original filename")
    file_size: Optional[str] = Field(None, description="File size in bytes")
    mime_type: Optional[str] = Field(None, description="MIME type of the file")


class DealDocumentCreate(DealDocumentBase):
    """Schema for creating a deal document."""
    deal_id: UUID = Field(..., description="UUID of the associated deal")
    file_path: str = Field(..., description="Path where file is stored")


class DealDocumentResponse(DealDocumentBase):
    """Schema for deal document response."""
    id: UUID
    deal_id: UUID
    file_path: str
    uploaded_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DealDocumentWithUploader(DealDocumentResponse):
    """Schema for deal document with uploader details."""
    uploader_name: Optional[str] = None

    class Config:
        from_attributes = True
