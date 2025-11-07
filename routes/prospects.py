"""
Prospect API routes.
Clean endpoint definitions using the controller layer.
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers.prospect_controller import ProspectController
from app.schemas.prospect import (
    ProspectCreate, ProspectUpdate, ProspectResponse,
    ProspectConversionRequest, BulkProspectCreate
)
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import UserProfile


router = APIRouter()


@router.get(
    "/",
    summary="Get all prospects",
    description="Retrieve prospects with optional filters"
)
async def get_prospects(
    status: Optional[str] = Query(
        None,
        description="Filter by status (comma-separated): new, contacted, qualified, converted, rejected"
    ),
    source: Optional[str] = Query(
        None,
        description="Filter by source (comma-separated): email_campaign, web_form, phone, social_media, manual_entry"
    ),
    campaign_id: Optional[UUID] = Query(
        None,
        description="Filter by campaign ID"
    ),
    search: Optional[str] = Query(
        None,
        description="Search by name, email, or company"
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Retrieve all prospects assigned to the current user with optional filters.

    - **status**: Filter by one or more statuses (comma-separated)
    - **source**: Filter by one or more sources (comma-separated)
    - **campaign_id**: Filter by campaign
    - **search**: Search in name, email, or company name
    - **skip**: Pagination offset
    - **limit**: Pagination limit (max 500)

    Returns prospects with lead scores and conversion status.
    """
    controller = ProspectController(db)
    return await controller.get_prospects(
        current_user, status, source, campaign_id, search, skip, limit
    )


@router.get(
    "/recent",
    summary="Get recent prospects",
    description="Get recently created prospects across all campaigns"
)
async def get_recent_prospects(
    days: int = Query(7, ge=1, le=90, description="Number of days to look back"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of prospects"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get recently created prospects.

    Useful for dashboard widgets showing new prospects.

    - **days**: How many days back to look (default 7)
    - **limit**: Maximum number of prospects to return (default 10)
    """
    controller = ProspectController(db)
    return await controller.get_recent_prospects(current_user, days, limit)


@router.get(
    "/statistics",
    summary="Get prospect statistics",
    description="Get prospect statistics, optionally filtered by campaign"
)
async def get_prospect_statistics(
    campaign_id: Optional[UUID] = Query(None, description="Optional campaign ID filter"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get prospect statistics.

    Returns:
    - Total prospects by status
    - Average lead score
    - Conversion rate
    """
    controller = ProspectController(db)
    return await controller.get_prospect_statistics(current_user, campaign_id)


@router.get(
    "/{prospect_id}",
    response_model=ProspectResponse,
    summary="Get prospect by ID",
    description="Retrieve a single prospect with full details"
)
async def get_prospect_by_id(
    prospect_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Retrieve a specific prospect by ID.

    Returns the prospect with:
    - Full prospect details
    - Lead score
    - Campaign source
    - Conversion status
    """
    controller = ProspectController(db)
    return await controller.get_prospect(prospect_id, current_user)


@router.post(
    "/",
    response_model=ProspectResponse,
    status_code=201,
    summary="Create a new prospect",
    description="Create a new prospect with duplicate detection"
)
async def create_prospect(
    prospect_data: ProspectCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Create a new prospect.

    The system will check for duplicates based on email and phone.
    If a duplicate is found, a 409 Conflict error will be returned.

    Example:
    ```json
    {
      "first_name": "Jane",
      "last_name": "Doe",
      "email": "jane.doe@example.com",
      "phone": "+1234567890",
      "company_name": "Acme Corp",
      "job_title": "Marketing Manager",
      "source": "web_form",
      "campaign_id": "uuid-here",
      "lead_score": 25
    }
    ```
    """
    controller = ProspectController(db)
    return await controller.create_prospect(prospect_data, current_user)


@router.post(
    "/bulk",
    summary="Bulk create prospects",
    description="Create multiple prospects at once with duplicate handling"
)
async def bulk_create_prospects(
    bulk_data: BulkProspectCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Bulk create prospects.

    Options:
    - **skip_duplicates**: If true, skip duplicates; if false, fail on duplicate

    Example:
    ```json
    {
      "prospects": [
        {
          "first_name": "John",
          "last_name": "Doe",
          "email": "john@example.com",
          ...
        },
        {
          "first_name": "Jane",
          "last_name": "Smith",
          "email": "jane@example.com",
          ...
        }
      ],
      "campaign_id": "uuid-here",
      "skip_duplicates": true
    }
    ```

    Returns:
    - created_count: Number of prospects created
    - skipped_count: Number skipped due to duplicates
    - failed_count: Number failed due to errors
    - created_ids: List of created prospect IDs
    - errors: List of errors encountered
    """
    controller = ProspectController(db)
    return await controller.bulk_create_prospects(bulk_data, current_user)


@router.put(
    "/{prospect_id}",
    response_model=ProspectResponse,
    summary="Update a prospect",
    description="Update an existing prospect's information"
)
async def update_prospect(
    prospect_id: UUID,
    prospect_data: ProspectUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Update an existing prospect.

    Only the user assigned to the prospect can update it.

    Note: Changing lead_score will create a history record.
    """
    controller = ProspectController(db)
    return await controller.update_prospect(prospect_id, prospect_data, current_user)


@router.delete(
    "/{prospect_id}",
    summary="Delete a prospect",
    description="Delete a prospect"
)
async def delete_prospect(
    prospect_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Delete a prospect.

    This will also delete:
    - Lead score history
    - Campaign-prospect associations

    Note: If the prospect was already converted to a contact,
    the contact will NOT be deleted.
    """
    controller = ProspectController(db)
    return await controller.delete_prospect(prospect_id, current_user)


@router.post(
    "/{prospect_id}/convert",
    summary="Convert prospect to contact",
    description="Convert a qualified prospect to a contact"
)
async def convert_prospect_to_contact(
    prospect_id: UUID,
    conversion_request: ProspectConversionRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Convert a prospect to a contact.

    This will:
    1. Create a new contact with the prospect's information
    2. Mark the prospect as converted
    3. Link campaign_contacts to the new contact
    4. Optionally create an activity log

    Example:
    ```json
    {
      "notes": "Qualified after product demo call",
      "create_activity": true,
      "assign_to": "uuid-of-user"
    }
    ```

    Returns:
    - prospect_id: Original prospect ID
    - contact_id: Newly created contact ID
    - activity_id: Created activity ID (if requested)
    - message: Success message
    """
    controller = ProspectController(db)
    return await controller.convert_to_contact(prospect_id, conversion_request, current_user)
