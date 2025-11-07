from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid


class NoteBase(BaseModel):
    title: Optional[str] = None
    content: str


class NoteCreate(NoteBase):
    contact_id: uuid.UUID


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class NoteResponse(NoteBase):
    id: uuid.UUID
    contact_id: uuid.UUID
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    author: Optional[dict] = None

    class Config:
        from_attributes = True
