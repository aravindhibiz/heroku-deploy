"""
Task Repository - Data access layer for Task entity.
Handles all database operations for tasks.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from models.task import Task
from base_repository import BaseRepository


class TaskRepository(BaseRepository[Task]):
    """Repository for Task entity with specialized query methods."""

    def __init__(self, db: Session):
        super().__init__(Task, db)

    def get_with_relations(self, task_id: UUID) -> Optional[Task]:
        """
        Get a task with all its relations eagerly loaded.

        Args:
            task_id: UUID of the task

        Returns:
            Task with relations or None if not found
        """
        return self.db.query(Task).options(
            joinedload(Task.contact),
            joinedload(Task.assigned_user),
            joinedload(Task.creator)
        ).filter(Task.id == task_id).first()

    def get_user_tasks(
        self,
        assigned_to: UUID,
        status: Optional[str] = None,
        priority: Optional[str] = None
    ) -> List[Task]:
        """
        Get all tasks assigned to a specific user with optional filters.

        Args:
            assigned_to: User UUID
            status: Filter by status (pending, in_progress, completed)
            priority: Filter by priority (low, medium, high)

        Returns:
            List of tasks with relations
        """
        query = self.db.query(Task).options(
            joinedload(Task.contact),
            joinedload(Task.assigned_user),
            joinedload(Task.creator)
        ).filter(Task.assigned_to == assigned_to)

        if status:
            query = query.filter(Task.status == status)

        if priority:
            query = query.filter(Task.priority == priority)

        return query.order_by(Task.due_date.asc().nullslast()).all()

    def get_created_by_user(
        self,
        created_by: UUID,
        status: Optional[str] = None
    ) -> List[Task]:
        """
        Get all tasks created by a specific user.

        Args:
            created_by: Creator user UUID
            status: Optional status filter

        Returns:
            List of tasks
        """
        query = self.db.query(Task).options(
            joinedload(Task.contact),
            joinedload(Task.assigned_user),
            joinedload(Task.creator)
        ).filter(Task.created_by == created_by)

        if status:
            query = query.filter(Task.status == status)

        return query.order_by(Task.due_date.asc().nullslast()).all()

    def get_tasks_by_contact(self, contact_id: UUID) -> List[Task]:
        """
        Get all tasks related to a specific contact.

        Args:
            contact_id: Contact UUID

        Returns:
            List of tasks
        """
        return self.db.query(Task).options(
            joinedload(Task.assigned_user),
            joinedload(Task.creator)
        ).filter(Task.contact_id == contact_id).all()

    def get_overdue_tasks(self, assigned_to: UUID) -> List[Task]:
        """
        Get overdue tasks for a user (past due date and not completed).

        Args:
            assigned_to: User UUID

        Returns:
            List of overdue tasks
        """
        now = datetime.now()
        return self.db.query(Task).options(
            joinedload(Task.contact),
            joinedload(Task.assigned_user),
            joinedload(Task.creator)
        ).filter(
            and_(
                Task.assigned_to == assigned_to,
                Task.due_date < now,
                Task.status != 'completed'
            )
        ).order_by(Task.due_date.asc()).all()

    def count_by_status(self, assigned_to: UUID) -> dict:
        """
        Count tasks by status for a user.

        Args:
            assigned_to: User UUID

        Returns:
            Dictionary with status counts
        """
        query = self.db.query(Task).filter(Task.assigned_to == assigned_to)

        total = query.count()
        pending = query.filter(Task.status == 'pending').count()
        in_progress = query.filter(Task.status == 'in_progress').count()
        completed = query.filter(Task.status == 'completed').count()

        # Count overdue
        now = datetime.now()
        overdue = query.filter(
            and_(
                Task.due_date < now,
                Task.status != 'completed'
            )
        ).count()

        return {
            'total': total,
            'pending': pending,
            'in_progress': in_progress,
            'completed': completed,
            'overdue': overdue
        }

    def count_by_priority(self, assigned_to: UUID) -> dict:
        """
        Count tasks by priority for a user.

        Args:
            assigned_to: User UUID

        Returns:
            Dictionary with priority counts
        """
        query = self.db.query(Task).filter(Task.assigned_to == assigned_to)

        low = query.filter(Task.priority == 'low').count()
        medium = query.filter(Task.priority == 'medium').count()
        high = query.filter(Task.priority == 'high').count()

        return {
            'low': low,
            'medium': medium,
            'high': high
        }

    def get_upcoming_tasks(self, assigned_to: UUID, days: int = 7) -> List[Task]:
        """
        Get tasks due within the next N days.

        Args:
            assigned_to: User UUID
            days: Number of days to look ahead (default: 7)

        Returns:
            List of upcoming tasks
        """
        from datetime import timedelta
        now = datetime.now()
        future = now + timedelta(days=days)

        return self.db.query(Task).options(
            joinedload(Task.contact),
            joinedload(Task.assigned_user),
            joinedload(Task.creator)
        ).filter(
            and_(
                Task.assigned_to == assigned_to,
                Task.due_date.between(now, future),
                Task.status != 'completed'
            )
        ).order_by(Task.due_date.asc()).all()
