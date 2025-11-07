from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "pending"
    priority: str = "medium"
    due_date: Optional[datetime] = None
    contact_id: Optional[UUID] = None
    deal_id: Optional[UUID] = None
    assigned_to: Optional[UUID] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    contact_id: Optional[UUID] = None
    deal_id: Optional[UUID] = None
    assigned_to: Optional[UUID] = None


class TaskResponse(TaskBase):
    id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskWithRelations(TaskResponse):
    contact: Optional[dict] = None
    deal: Optional[dict] = None
    assigned_user: Optional[dict] = None
    creator: Optional[dict] = None

    class Config:
        from_attributes = True


class TaskStatistics(BaseModel):
    """Task statistics schema."""
    total_tasks: int
    pending_tasks: int
    in_progress_tasks: int
    completed_tasks: int
    overdue_tasks: int
    completion_rate: float
    by_priority: dict
