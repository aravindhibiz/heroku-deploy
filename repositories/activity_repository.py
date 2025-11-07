"""
Activity repository for data access operations.
Handles all database queries related to activities.
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session, Query, joinedload
from sqlalchemy import desc

from .base_repository import BaseRepository
from ..models.activity import Activity


class ActivityRepository(BaseRepository[Activity]):
    """
    Repository for Activity entity.

    Provides specialized query methods for activities beyond the base CRUD operations.
    """

    def __init__(self, db: Session):
        """
        Initialize the activity repository.

        Args:
            db: Database session
        """
        super().__init__(Activity, db)

    def get_with_relations(self, activity_id: UUID) -> Optional[Activity]:
        """
        Retrieve an activity with all its relationships loaded.

        Args:
            activity_id: UUID of the activity

        Returns:
            Activity with loaded relationships, or None if not found
        """
        return (
            self.db.query(Activity)
            .options(
                joinedload(Activity.contact),
                joinedload(Activity.deal),
                joinedload(Activity.user)
            )
            .filter(Activity.id == activity_id)
            .first()
        )

    def get_by_user(
        self,
        user_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
        load_relations: bool = False
    ) -> List[Activity]:
        """
        Retrieve activities for a specific user.

        Args:
            user_id: UUID of the user
            skip: Number of records to skip
            limit: Maximum number of records to return
            load_relations: Whether to load related entities

        Returns:
            List of activities for the user
        """
        query = self.db.query(Activity).filter(Activity.user_id == user_id)

        if load_relations:
            query = query.options(
                joinedload(Activity.contact),
                joinedload(Activity.deal),
                joinedload(Activity.user)
            )

        return (
            query.order_by(desc(Activity.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_contact(
        self,
        contact_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50
    ) -> List[Activity]:
        """
        Retrieve activities for a specific contact.

        Args:
            contact_id: UUID of the contact
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of activities for the contact
        """
        return (
            self.db.query(Activity)
            .filter(Activity.contact_id == contact_id)
            .order_by(desc(Activity.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_deal(
        self,
        deal_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50
    ) -> List[Activity]:
        """
        Retrieve activities for a specific deal.

        Args:
            deal_id: UUID of the deal
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of activities for the deal
        """
        return (
            self.db.query(Activity)
            .filter(Activity.deal_id == deal_id)
            .order_by(desc(Activity.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_type(
        self,
        activity_type: str,
        *,
        skip: int = 0,
        limit: int = 50
    ) -> List[Activity]:
        """
        Retrieve activities of a specific type.

        Args:
            activity_type: Type of activity (call, email, meeting, note, task)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of activities of the specified type
        """
        return (
            self.db.query(Activity)
            .filter(Activity.type == activity_type)
            .order_by(desc(Activity.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_filtered_query(
        self,
        *,
        base_query: Optional[Query] = None,
        load_relations: bool = True
    ) -> Query:
        """
        Get a base query with optional relationship loading.

        This method is useful for applying additional filters from other layers
        (like permission-based filtering).

        Args:
            base_query: Existing query to build upon, creates new if None
            load_relations: Whether to eagerly load relationships

        Returns:
            SQLAlchemy Query object
        """
        if base_query is None:
            query = self.db.query(Activity)
        else:
            query = base_query

        if load_relations:
            query = query.options(
                joinedload(Activity.contact),
                joinedload(Activity.deal),
                joinedload(Activity.user)
            )

        return query

    def get_recent_activities(
        self,
        *,
        limit: int = 50,
        load_relations: bool = True
    ) -> List[Activity]:
        """
        Retrieve the most recent activities.

        Args:
            limit: Maximum number of records to return
            load_relations: Whether to load related entities

        Returns:
            List of recent activities
        """
        query = self.db.query(Activity)

        if load_relations:
            query = query.options(
                joinedload(Activity.contact),
                joinedload(Activity.deal),
                joinedload(Activity.user)
            )

        return (
            query.order_by(desc(Activity.created_at))
            .limit(limit)
            .all()
        )

    def count_by_user(self, user_id: UUID) -> int:
        """
        Count activities for a specific user.

        Args:
            user_id: UUID of the user

        Returns:
            Number of activities for the user
        """
        return self.db.query(Activity).filter(Activity.user_id == user_id).count()

    def count_by_type(self, activity_type: str) -> int:
        """
        Count activities of a specific type.

        Args:
            activity_type: Type of activity

        Returns:
            Number of activities of the specified type
        """
        return self.db.query(Activity).filter(Activity.type == activity_type).count()
