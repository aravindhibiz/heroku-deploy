"""
Activity routes - API endpoint definitions only.
Delegates all logic to the ActivityController.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from ..core.database import get_db
from ..core.auth import get_current_user
from ..models.user import UserProfile
from ..schemas.activity import (
    ActivityCreate,
    ActivityUpdate,
    ActivityResponse,
    ActivityWithRelations
)
from ..controllers.activity_controller import ActivityController


router = APIRouter()


@router.get(
    "/",
    response_model=List[ActivityWithRelations],
    summary="Get all activities",
    description="Retrieve activities with relations based on user permissions (view_all or view_own)"
)
async def get_activities(
    limit: int = Query(
        50, description="Maximum number of activities to return"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Retrieve activities for the current user based on their permissions.

    - **limit**: Maximum number of activities to return (default: 50)
    """
    controller = ActivityController(db)
    return await controller.get_activities(current_user, limit)


@router.get(
    "/{activity_id}",
    response_model=ActivityWithRelations,
    summary="Get activity by ID",
    description="Retrieve a specific activity with all related data and custom fields"
)
async def get_activity(
    activity_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Retrieve a specific activity by its ID.

    - **activity_id**: UUID of the activity to retrieve
    """
    controller = ActivityController(db)
    return await controller.get_activity(activity_id, current_user)


@router.post(
    "/",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new activity",
    description="Create a new activity with optional custom fields"
)
async def create_activity(
    activity_data: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Create a new activity.

    - **activity_data**: Activity creation data including type, subject, and optional fields
    """
    controller = ActivityController(db)
    return await controller.create_activity(activity_data, current_user)


@router.put(
    "/{activity_id}",
    response_model=ActivityResponse,
    summary="Update an activity",
    description="Update an existing activity's data and custom fields"
)
async def update_activity(
    activity_id: UUID,
    activity_data: ActivityUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Update an existing activity.

    - **activity_id**: UUID of the activity to update
    - **activity_data**: Updated activity data
    """
    controller = ActivityController(db)
    return await controller.update_activity(activity_id, activity_data, current_user)


@router.delete(
    "/{activity_id}",
    summary="Delete an activity",
    description="Delete an activity by ID"
)
async def delete_activity(
    activity_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Delete an activity.

    - **activity_id**: UUID of the activity to delete
    """
    controller = ActivityController(db)
    return await controller.delete_activity(activity_id, current_user)
