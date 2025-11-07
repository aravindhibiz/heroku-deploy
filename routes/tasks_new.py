"""
Task Routes - Clean API endpoint definitions.
All business logic is in TaskController.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.database import get_db
from core.auth import get_current_user
from models.user import UserProfile
from controllers.task_controller import TaskController
from schemas.task import TaskResponse, TaskCreate, TaskUpdate, TaskStatistics

router = APIRouter()


@router.get("/", response_model=List[TaskResponse])
async def get_tasks(
    status: Optional[str] = Query(
        None, description="Filter by status (pending, in_progress, completed)"),
    priority: Optional[str] = Query(
        None, description="Filter by priority (low, medium, high)"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get all tasks assigned to the current user.

    **Filters:**
    - **status**: pending, in_progress, completed
    - **priority**: low, medium, high

    Returns tasks with all related entities (contact, deal, assigned user, creator).
    """
    controller = TaskController(db)
    return controller.list_tasks(
        current_user=current_user,
        status=status,
        priority=priority
    )


@router.get("/stats/overview", response_model=TaskStatistics)
async def get_task_statistics(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get task statistics for the current user.

    Returns:
    - Total tasks
    - Tasks by status (pending, in_progress, completed, overdue)
    - Completion rate
    - Tasks by priority (low, medium, high)
    """
    controller = TaskController(db)
    return controller.get_statistics(current_user=current_user)


@router.get("/overdue", response_model=List[TaskResponse])
async def get_overdue_tasks(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get all overdue tasks for the current user.

    Returns tasks that:
    - Have a due date in the past
    - Are not completed
    - Are assigned to the current user
    """
    controller = TaskController(db)
    return controller.get_overdue_tasks(current_user=current_user)


@router.get("/upcoming", response_model=List[TaskResponse])
async def get_upcoming_tasks(
    days: int = Query(7, description="Number of days to look ahead"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get upcoming tasks due within the specified number of days.

    **Parameters:**
    - **days**: Number of days to look ahead (default: 7)

    Returns tasks that are due within the next N days.
    """
    controller = TaskController(db)
    return controller.get_upcoming_tasks(
        current_user=current_user,
        days=days
    )


@router.get("/contact/{contact_id}", response_model=List[TaskResponse])
async def get_contact_tasks(
    contact_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get all tasks related to a specific contact.

    Only returns tasks that the current user has access to
    (assigned to them or created by them).
    """
    controller = TaskController(db)
    return controller.get_contact_tasks(
        contact_id=contact_id,
        current_user=current_user
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get a single task by ID.

    Returns task with all relations (contact, deal, assigned user, creator).
    User must be assigned to or creator of the task.
    """
    controller = TaskController(db)
    return controller.get_task(
        task_id=task_id,
        current_user=current_user
    )


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Create a new task.

    **Auto-assignment:**
    - If `assigned_to` is not provided, task is assigned to the current user
    - `created_by` is automatically set to the current user

    **Required fields:**
    - title

    **Optional fields:**
    - description
    - status (default: "pending")
    - priority (default: "medium")
    - due_date
    - contact_id
    - deal_id
    - assigned_to
    """
    controller = TaskController(db)
    return controller.create_task(
        task_data=task,
        current_user=current_user
    )


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    task: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Update an existing task.

    Only the assigned user can update the task.
    All fields are optional.
    """
    controller = TaskController(db)
    return controller.update_task(
        task_id=task_id,
        task_data=task,
        current_user=current_user
    )


@router.delete("/{task_id}")
async def delete_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Delete a task.

    Only the assigned user can delete the task.
    """
    controller = TaskController(db)
    return controller.delete_task(
        task_id=task_id,
        current_user=current_user
    )
