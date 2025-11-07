"""
Activity controller for handling HTTP requests and responses.
Acts as the bridge between routes and business logic.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from services.activity_service import ActivityService
from models.user import UserProfile
from models.activity import Activity
from schemas.activity import (
    ActivityCreate,
    ActivityUpdate,
    ActivityResponse,
    ActivityWithRelations
)
from core.auth import has_any_permission
from core.auth_helpers import (
    get_activities_query_filter,
    check_activity_edit_permission,
    check_activity_delete_permission
)


class ActivityController:
    """
    Controller for Activity operations.

    Handles HTTP request validation, permission checking, and response formatting.
    Delegates business logic to the ActivityService.
    """

    def __init__(self, db: Session):
        """
        Initialize the activity controller.

        Args:
            db: Database session
        """
        self.db = db
        self.service = ActivityService(db)

    async def get_activities(
        self,
        current_user: UserProfile,
        limit: int = 50
    ) -> List[ActivityWithRelations]:
        """
        Get all activities for the current user based on permissions.

        Args:
            current_user: The authenticated user
            limit: Maximum number of activities to return

        Returns:
            List of activities with relations
        """
        # Get base query with permission filtering
        base_query = self.db.query(Activity)
        filtered_query = get_activities_query_filter(
            self.db,
            current_user,
            base_query
        )

        # Get activities through service with relations
        activities = self.service.get_activities_with_relations(
            filtered_query=filtered_query,
            limit=limit
        )

        return activities

    async def get_activity(
        self,
        activity_id: UUID,
        current_user: UserProfile
    ) -> ActivityWithRelations:
        """
        Get a specific activity by ID.

        Args:
            activity_id: UUID of the activity
            current_user: The authenticated user

        Returns:
            Activity with relations and custom fields

        Raises:
            HTTPException: If activity not found
        """
        activity = self.service.get_activity_by_id(activity_id)

        if not activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Activity not found"
            )

        # TODO: Add permission check for viewing specific activity
        # For now, we rely on the list filter

        return activity

    async def create_activity(
        self,
        activity_data: ActivityCreate,
        current_user: UserProfile
    ) -> ActivityResponse:
        """
        Create a new activity.

        Args:
            activity_data: Activity creation data
            current_user: The authenticated user

        Returns:
            The created activity

        Raises:
            HTTPException: If user lacks permission or creation fails
        """
        # Check permissions
        can_create = self._check_create_permission(current_user)

        if not can_create:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied. You don't have permission to create activities."
            )

        try:
            # Create activity through service
            activity = self.service.create_activity(
                activity_data, current_user)
            return activity

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create activity: {str(e)}"
            )

    async def update_activity(
        self,
        activity_id: UUID,
        activity_data: ActivityUpdate,
        current_user: UserProfile
    ) -> ActivityResponse:
        """
        Update an existing activity.

        Args:
            activity_id: UUID of the activity to update
            activity_data: Activity update data
            current_user: The authenticated user

        Returns:
            The updated activity

        Raises:
            HTTPException: If activity not found, user lacks permission, or update fails
        """
        # Get the activity to check if it exists
        db_activity = self.db.query(Activity).filter(
            Activity.id == activity_id
        ).first()

        if not db_activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Activity not found"
            )

        # Check permission to edit this activity
        can_edit = check_activity_edit_permission(
            self.db,
            current_user,
            db_activity
        )

        if not can_edit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied. You don't have permission to edit this activity."
            )

        try:
            # Update activity through service
            activity = self.service.update_activity(activity_id, activity_data)

            if not activity:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Activity not found"
                )

            return activity

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update activity: {str(e)}"
            )

    async def delete_activity(
        self,
        activity_id: UUID,
        current_user: UserProfile
    ) -> Dict[str, str]:
        """
        Delete an activity.

        Args:
            activity_id: UUID of the activity to delete
            current_user: The authenticated user

        Returns:
            Success message

        Raises:
            HTTPException: If activity not found, user lacks permission, or deletion fails
        """
        # Get the activity to check if it exists
        db_activity = self.db.query(Activity).filter(
            Activity.id == activity_id
        ).first()

        if not db_activity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Activity not found"
            )

        # Check permission to delete this activity
        can_delete = check_activity_delete_permission(
            self.db,
            current_user,
            db_activity.user_id
        )

        if not can_delete:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied. You don't have permission to delete this activity."
            )

        try:
            # Delete activity through service
            success = self.service.delete_activity(activity_id)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Activity not found"
                )

            return {"message": "Activity deleted successfully"}

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete activity: {str(e)}"
            )

    def _check_create_permission(self, current_user: UserProfile) -> bool:
        """
        Check if user has permission to create activities.

        Args:
            current_user: The authenticated user

        Returns:
            True if user can create activities, False otherwise
        """
        can_create_all = has_any_permission(
            self.db,
            current_user,
            ["activities.create_all"]
        )
        can_create_own = has_any_permission(
            self.db,
            current_user,
            ["activities.create_own"]
        )

        return can_create_all or can_create_own
