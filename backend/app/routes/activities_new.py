"""
Activity routes - API endpoint definitions only.
Delegates all logic to the ActivityController.
Note: Calendar routes must be defined before {activity_id} route.
"""

from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

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

# Token encryption functions (simplified for now - can add encryption later)
def encrypt_token(token: str) -> str:
    """Placeholder for token encryption - stores plaintext for now"""
    return token

def decrypt_token(token: str) -> str:
    """Placeholder for token decryption - returns plaintext for now"""
    return token

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


# ==================== CALENDAR-SPECIFIC ENDPOINTS ====================
# NOTE: These must come BEFORE /{activity_id} route to avoid path conflicts

@router.get(
    "/calendar",
    response_model=List[ActivityWithRelations],
    summary="Get activities for calendar view",
    description="Get activities within a date range for calendar display, optionally including Outlook events"
)
async def get_calendar_activities(
    start_date: str = Query(..., description="Start date in ISO format (e.g., 2025-01-01)"),
    end_date: str = Query(..., description="End date in ISO format (e.g., 2025-01-31)"),
    include_outlook: bool = Query(True, description="Include synced Outlook events"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get activities for calendar view within a date range.

    **Query Parameters:**
    - start_date: Start of date range (ISO format: YYYY-MM-DD)
    - end_date: End of date range (ISO format: YYYY-MM-DD)
    - include_outlook: Whether to include Outlook synced events (default: true)

    **Returns:**
    - List of activities with scheduled_at within the date range
    - Includes all activity types: meetings, calls, tasks with due dates
    - Each activity includes contact and deal relationships

    **Use Cases:**
    - Display activities in calendar view
    - Show upcoming meetings and calls
    - Filter activities by date range

    **Example:**
    ```
    GET /api/v1/activities/calendar?start_date=2025-01-01&end_date=2025-01-31
    ```
    """
    from ..models.activity import Activity

    try:
        # Parse dates and make them timezone-aware
        # The database stores timezone-aware datetimes, so we need to match that
        from datetime import timezone

        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)

        # If the datetime is naive (no timezone info), assume UTC
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        if end_dt.tzinfo is None:
            # Set end of day for end_date
            end_dt = end_dt.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format: YYYY-MM-DD"
        )

    # Query activities with scheduled_at in date range
    query = db.query(Activity).filter(
        Activity.user_id == current_user.id,
        Activity.scheduled_at.isnot(None),
        Activity.scheduled_at >= start_dt,
        Activity.scheduled_at <= end_dt
    )

    # Optionally filter out Outlook-synced events
    if not include_outlook:
        query = query.filter(Activity.sync_source != 'outlook')

    activities = query.order_by(Activity.scheduled_at).all()

    # Load relationships
    controller = ActivityController(db)
    # Convert to response models with relations
    return [
        ActivityWithRelations.model_validate(activity)
        for activity in activities
    ]


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


@router.post(
    "/calendar",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create activity from calendar",
    description="Create a new activity from calendar view with optional Outlook sync"
)
async def create_calendar_activity(
    activity_data: ActivityCreate,
    sync_to_outlook: bool = Query(False, description="Sync this activity to Outlook Calendar"),
    create_teams_meeting: bool = Query(False, description="Create Teams meeting link"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Create a new activity from calendar view.

    **Request Body:**
    - Activity data including scheduled_at, end_time, location, attendees

    **Query Parameters:**
    - sync_to_outlook: Whether to create event in Outlook Calendar (default: false)
    - create_teams_meeting: Whether to generate Teams meeting link (default: false)

    **Process:**
    1. Create activity in CRM
    2. If sync_to_outlook: Create event in Outlook Calendar
    3. If create_teams_meeting: Generate Teams meeting URL
    4. Store outlook_event_id for sync tracking

    **Returns:**
    - Created activity with sync status

    **Use Cases:**
    - User creates meeting in calendar view
    - User wants meeting in both CRM and Outlook
    - User wants to generate Teams link

    **Example:**
    ```
    POST /api/v1/activities/calendar?sync_to_outlook=true&create_teams_meeting=true
    {
        "type": "meeting",
        "subject": "Q4 Planning Meeting",
        "scheduled_at": "2025-01-15T14:00:00Z",
        "end_time": "2025-01-15T15:00:00Z",
        "location": "Conference Room A",
        "attendees": ["john@acme.com"],
        "contact_id": "uuid..."
    }
    ```
    """
    # Create activity first
    controller = ActivityController(db)
    activity = await controller.create_activity(activity_data, current_user)

    # If sync to Outlook is requested
    if sync_to_outlook:
        from ..models.integration import Integration
        from ..services.outlook_calendar_service import OutlookCalendarService
        from ..core.security import decrypt_token
        from ..models.activity import Activity

        # Get integration
        integration = db.query(Integration).filter(
            Integration.user_id == current_user.id,
            Integration.provider == "outlook_calendar",
            Integration.status == "connected"
        ).first()

        if integration:
            # Get full activity object
            db_activity = db.query(Activity).filter(Activity.id == activity.id).first()

            # Decrypt access token
            access_token = decrypt_token(integration.access_token)
            integration.access_token = access_token  # Temporarily set for service

            # Sync to Outlook
            calendar_service = OutlookCalendarService(db)
            await calendar_service.sync_crm_to_outlook(
                activity=db_activity,
                integration=integration,
                create_teams_meeting=create_teams_meeting
            )

            # Refresh activity to get updated sync status
            db.refresh(db_activity)
            activity = ActivityResponse.model_validate(db_activity)

    return activity


@router.put(
    "/{activity_id}/calendar",
    response_model=ActivityResponse,
    summary="Update activity from calendar",
    description="Update an activity from calendar view (e.g., drag-drop reschedule)"
)
async def update_calendar_activity(
    activity_id: UUID,
    activity_data: ActivityUpdate,
    sync_to_outlook: bool = Query(False, description="Sync changes to Outlook Calendar"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Update an activity from calendar view.

    **Path Parameters:**
    - activity_id: UUID of the activity to update

    **Request Body:**
    - Updated activity data (typically scheduled_at, end_time for rescheduling)

    **Query Parameters:**
    - sync_to_outlook: Whether to update Outlook event (default: false)

    **Process:**
    1. Update activity in CRM
    2. If sync_to_outlook and outlook_event_id exists: Update Outlook event

    **Returns:**
    - Updated activity

    **Use Cases:**
    - Drag-drop reschedule in calendar
    - Update meeting time/location
    - Changes sync to Outlook if originally synced

    **Example:**
    ```
    PUT /api/v1/activities/{id}/calendar?sync_to_outlook=true
    {
        "scheduled_at": "2025-01-16T10:00:00Z",
        "end_time": "2025-01-16T11:00:00Z"
    }
    ```
    """
    # Update activity
    controller = ActivityController(db)
    activity = await controller.update_activity(activity_id, activity_data, current_user)

    # If sync to Outlook is requested and activity has outlook_event_id
    if sync_to_outlook:
        from ..models.integration import Integration
        from ..services.outlook_calendar_service import OutlookCalendarService
        from ..core.security import decrypt_token
        from ..models.activity import Activity

        # Get full activity object
        db_activity = db.query(Activity).filter(Activity.id == activity_id).first()

        if db_activity and db_activity.outlook_event_id:
            # Get integration
            integration = db.query(Integration).filter(
                Integration.user_id == current_user.id,
                Integration.provider == "outlook_calendar",
                Integration.status == "connected"
            ).first()

            if integration:
                # Decrypt access token
                access_token = decrypt_token(integration.access_token)
                integration.access_token = access_token

                # Sync to Outlook
                calendar_service = OutlookCalendarService(db)
                await calendar_service.sync_crm_to_outlook(
                    activity=db_activity,
                    integration=integration
                )

                # Refresh activity
                db.refresh(db_activity)
                activity = ActivityResponse.model_validate(db_activity)

    return activity
