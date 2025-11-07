from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from uuid import UUID
from ..core.database import get_db
from ..core.auth import get_current_user
from ..models.user import UserProfile
from ..models.task import Task
from ..schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskWithRelations

router = APIRouter()


@router.get("/", response_model=List[TaskWithRelations])
async def get_user_tasks(
    status: Optional[str] = Query(None, description="Filter by task status"),
    priority: Optional[str] = Query(
        None, description="Filter by task priority"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    query = db.query(Task).options(
        joinedload(Task.contact),
        joinedload(Task.assigned_user),
        joinedload(Task.creator)
    ).filter(Task.assigned_to == current_user.id)

    if status:
        query = query.filter(Task.status == status)
    if priority:
        query = query.filter(Task.priority == priority)

    tasks = query.order_by(Task.due_date.asc().nullslast()).all()
    return tasks


@router.get("/{task_id}", response_model=TaskWithRelations)
async def get_task_by_id(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    task = db.query(Task).options(
        joinedload(Task.contact),
        joinedload(Task.assigned_user),
        joinedload(Task.creator)
    ).filter(
        Task.id == task_id,
        Task.assigned_to == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return task


@router.post("/", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    # If no assigned_to is provided, assign to current user
    if not task_data.assigned_to:
        task_data.assigned_to = current_user.id

    db_task = Task(
        **task_data.dict(),
        created_by=current_user.id
    )

    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    return db_task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    task_data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.assigned_to == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Update task fields
    update_data = task_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)

    return task


@router.delete("/{task_id}")
async def delete_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.assigned_to == current_user.id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    db.delete(task)
    db.commit()

    return {"message": "Task deleted successfully"}


@router.get("/stats/overview")
async def get_task_stats(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    tasks = db.query(Task).filter(Task.assigned_to == current_user.id).all()

    pending_tasks = [task for task in tasks if task.status == 'pending']
    in_progress_tasks = [
        task for task in tasks if task.status == 'in_progress']
    completed_tasks = [task for task in tasks if task.status == 'completed']

    # Get overdue tasks
    from datetime import datetime
    now = datetime.now()
    overdue_tasks = [
        task for task in tasks
        if task.due_date and task.due_date < now and task.status != 'completed'
    ]

    return {
        'total_tasks': len(tasks),
        'pending_tasks': len(pending_tasks),
        'in_progress_tasks': len(in_progress_tasks),
        'completed_tasks': len(completed_tasks),
        'overdue_tasks': len(overdue_tasks),
        'completion_rate': round((len(completed_tasks) / len(tasks)) * 100, 2) if tasks else 0
    }
