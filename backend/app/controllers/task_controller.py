"""
Task Controller - HTTP request/response handling for Tasks.
Handles validation, permissions, and response formatting.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..services.task_service import TaskService
from ..schemas.task import TaskResponse, TaskCreate, TaskUpdate, TaskStatistics
from ..models.user import UserProfile


class TaskController:
    """Controller for task HTTP operations."""

    def __init__(self, db: Session):
        self.db = db
        self.service = TaskService(db)

    def list_tasks(
        self,
        current_user: UserProfile,
        status: Optional[str] = None,
        priority: Optional[str] = None
    ) -> List[TaskResponse]:
        """
        Get all tasks assigned to the current user with optional filters.

        Args:
            current_user: Authenticated user
            status: Filter by status (pending, in_progress, completed)
            priority: Filter by priority (low, medium, high)

        Returns:
            List of task responses
        """
        tasks = self.service.get_user_tasks(
            user_id=current_user.id,
            status=status,
            priority=priority
        )

        return [TaskResponse.model_validate(task) for task in tasks]

    def get_task(
        self,
        task_id: UUID,
        current_user: UserProfile
    ) -> TaskResponse:
        """
        Get a single task by ID.

        Args:
            task_id: Task UUID
            current_user: Authenticated user

        Returns:
            Task response

        Raises:
            HTTPException: If task not found or user lacks permission
        """
        task = self.service.get_task_by_id(task_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Check permission: user must be assigned to or creator of the task
        if task.assigned_to != current_user.id and task.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this task"
            )

        return TaskResponse.model_validate(task)

    def create_task(
        self,
        task_data: TaskCreate,
        current_user: UserProfile
    ) -> TaskResponse:
        """
        Create a new task.

        Args:
            task_data: Task creation data
            current_user: Authenticated user (will be set as creator)

        Returns:
            Created task response
        """
        task = self.service.create_task(
            task_data=task_data,
            current_user=current_user
        )

        return TaskResponse.model_validate(task)

    def update_task(
        self,
        task_id: UUID,
        task_data: TaskUpdate,
        current_user: UserProfile
    ) -> TaskResponse:
        """
        Update an existing task.

        Args:
            task_id: Task UUID
            task_data: Update data
            current_user: Authenticated user

        Returns:
            Updated task response

        Raises:
            HTTPException: If task not found or user lacks permission
        """
        # Get task to check permissions
        task = self.service.get_task_by_id(task_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Check permission: user must be assigned to the task
        if task.assigned_to != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this task"
            )

        updated_task = self.service.update_task(task_id, task_data)

        if not updated_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        return TaskResponse.model_validate(updated_task)

    def delete_task(
        self,
        task_id: UUID,
        current_user: UserProfile
    ) -> dict:
        """
        Delete a task.

        Args:
            task_id: Task UUID
            current_user: Authenticated user

        Returns:
            Success message

        Raises:
            HTTPException: If task not found or user lacks permission
        """
        # Get task to check permissions
        task = self.service.get_task_by_id(task_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Check permission: user must be assigned to the task
        if task.assigned_to != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this task"
            )

        success = self.service.delete_task(task_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        return {"message": "Task deleted successfully"}

    def get_statistics(self, current_user: UserProfile) -> TaskStatistics:
        """
        Get task statistics for the current user.

        Args:
            current_user: Authenticated user

        Returns:
            Task statistics
        """
        stats = self.service.get_task_statistics(current_user.id)

        return TaskStatistics(**stats)

    def get_overdue_tasks(self, current_user: UserProfile) -> List[TaskResponse]:
        """
        Get overdue tasks for the current user.

        Args:
            current_user: Authenticated user

        Returns:
            List of overdue tasks
        """
        tasks = self.service.get_overdue_tasks(current_user.id)

        return [TaskResponse.model_validate(task) for task in tasks]

    def get_upcoming_tasks(
        self,
        current_user: UserProfile,
        days: int = 7
    ) -> List[TaskResponse]:
        """
        Get upcoming tasks for the current user (due within N days).

        Args:
            current_user: Authenticated user
            days: Number of days to look ahead

        Returns:
            List of upcoming tasks
        """
        tasks = self.service.get_upcoming_tasks(current_user.id, days)

        return [TaskResponse.model_validate(task) for task in tasks]

    def get_contact_tasks(
        self,
        contact_id: UUID,
        current_user: UserProfile
    ) -> List[TaskResponse]:
        """
        Get all tasks related to a contact.

        Args:
            contact_id: Contact UUID
            current_user: Authenticated user

        Returns:
            List of tasks
        """
        tasks = self.service.get_tasks_by_contact(contact_id)

        # Filter to only tasks the user has access to
        accessible_tasks = [
            task for task in tasks
            if task.assigned_to == current_user.id or task.created_by == current_user.id
        ]

        return [TaskResponse.model_validate(task) for task in accessible_tasks]
