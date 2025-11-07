"""
Task Service - Business logic layer for Task operations.
Handles task CRUD operations and statistics.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session

from repositories.task_repository import TaskRepository
from models.task import Task
from models.user import UserProfile
from schemas.task import TaskCreate, TaskUpdate


class TaskService:
    """Service layer for task business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = TaskRepository(db)

    def get_user_tasks(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        priority: Optional[str] = None
    ) -> List[Task]:
        """
        Get all tasks assigned to a user with optional filters.

        Args:
            user_id: User UUID
            status: Filter by status
            priority: Filter by priority

        Returns:
            List of tasks with relations
        """
        return self.repository.get_user_tasks(
            assigned_to=user_id,
            status=status,
            priority=priority
        )

    def get_task_by_id(self, task_id: UUID) -> Optional[Task]:
        """
        Get a single task with all relations.

        Args:
            task_id: Task UUID

        Returns:
            Task with relations or None
        """
        return self.repository.get_with_relations(task_id)

    def create_task(
        self,
        task_data: TaskCreate,
        current_user: UserProfile
    ) -> Task:
        """
        Create a new task.

        Args:
            task_data: Task creation data
            current_user: Current user (will be set as creator)

        Returns:
            Created task
        """
        # Build task dictionary
        task_dict = task_data.model_dump()

        # If no assigned_to is provided, assign to current user
        if not task_dict.get('assigned_to'):
            task_dict['assigned_to'] = current_user.id

        # Set creator
        task_dict['created_by'] = current_user.id

        # Create task
        created_task = self.repository.create(obj_in=task_dict)

        return created_task

    def update_task(
        self,
        task_id: UUID,
        task_data: TaskUpdate
    ) -> Optional[Task]:
        """
        Update an existing task.

        Args:
            task_id: Task UUID
            task_data: Update data

        Returns:
            Updated task or None if not found
        """
        task = self.repository.get(task_id)

        if not task:
            return None

        # Update task fields
        update_data = task_data.model_dump(exclude_unset=True)
        updated_task = self.repository.update(db_obj=task, obj_in=update_data)

        return updated_task

    def delete_task(self, task_id: UUID) -> bool:
        """
        Delete a task.

        Args:
            task_id: Task UUID

        Returns:
            True if deleted, False if not found
        """
        return self.repository.delete(id=task_id)

    def get_task_statistics(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get task statistics for a user.

        Args:
            user_id: User UUID

        Returns:
            Dictionary with statistics
        """
        status_counts = self.repository.count_by_status(user_id)
        priority_counts = self.repository.count_by_priority(user_id)

        # Calculate completion rate
        total = status_counts['total']
        completed = status_counts['completed']
        completion_rate = round((completed / total) *
                                100, 2) if total > 0 else 0

        return {
            'total_tasks': total,
            'pending_tasks': status_counts['pending'],
            'in_progress_tasks': status_counts['in_progress'],
            'completed_tasks': completed,
            'overdue_tasks': status_counts['overdue'],
            'completion_rate': completion_rate,
            'by_priority': priority_counts
        }

    def get_overdue_tasks(self, user_id: UUID) -> List[Task]:
        """
        Get overdue tasks for a user.

        Args:
            user_id: User UUID

        Returns:
            List of overdue tasks
        """
        return self.repository.get_overdue_tasks(user_id)

    def get_upcoming_tasks(self, user_id: UUID, days: int = 7) -> List[Task]:
        """
        Get upcoming tasks for a user (due within N days).

        Args:
            user_id: User UUID
            days: Number of days to look ahead

        Returns:
            List of upcoming tasks
        """
        return self.repository.get_upcoming_tasks(user_id, days)

    def get_tasks_by_contact(self, contact_id: UUID) -> List[Task]:
        """
        Get all tasks related to a contact.

        Args:
            contact_id: Contact UUID

        Returns:
            List of tasks
        """
        return self.repository.get_tasks_by_contact(contact_id)

    def get_created_tasks(
        self,
        user_id: UUID,
        status: Optional[str] = None
    ) -> List[Task]:
        """
        Get tasks created by a user.

        Args:
            user_id: User UUID
            status: Optional status filter

        Returns:
            List of tasks
        """
        return self.repository.get_created_by_user(user_id, status)
