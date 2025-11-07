"""
Campaign API routes.
Clean endpoint definitions using the controller layer.
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Body, File, UploadFile
from sqlalchemy.orm import Session

from app.controllers.campaign_controller import CampaignController
from app.schemas.campaign import (
    CampaignCreate, CampaignUpdate, CampaignResponse,
    AddToCampaignRequest, CampaignExecuteRequest
)
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import UserProfile


router = APIRouter()


@router.get(
    "/",
    summary="Get all campaigns",
    description="Retrieve campaigns with optional filters"
)
async def get_campaigns(
    status: Optional[str] = Query(
        None,
        description="Filter by status (comma-separated): draft, scheduled, active, completed, paused, cancelled"
    ),
    type: Optional[str] = Query(
        None,
        description="Filter by type (comma-separated): email, web_form, phone, social_media, manual_entry"
    ),
    search: Optional[str] = Query(
        None,
        description="Search by campaign name or description"
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Retrieve all campaigns for the current user with optional filters.

    - **status**: Filter by one or more statuses (comma-separated)
    - **type**: Filter by one or more types (comma-separated)
    - **search**: Search in campaign name or description
    - **skip**: Pagination offset
    - **limit**: Pagination limit (max 500)

    Returns campaigns with performance metrics.
    """
    controller = CampaignController(db)
    return await controller.get_campaigns(current_user, status, type, search, skip, limit)


@router.get(
    "/statistics",
    summary="Get campaign statistics",
    description="Get overall campaign statistics for the current user"
)
async def get_campaign_statistics(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Retrieve overall campaign statistics.

    Returns aggregated metrics across all campaigns:
    - Total campaigns by status
    - Budget and spending
    - Revenue and ROI
    - Prospects and conversions
    """
    controller = CampaignController(db)
    return await controller.get_statistics(current_user)


@router.get(
    "/{campaign_id}",
    summary="Get campaign by ID",
    description="Retrieve a single campaign with full details and metrics"
)
async def get_campaign_by_id(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Retrieve a specific campaign by ID.

    Returns the campaign with:
    - Full campaign details
    - Performance metrics
    - Calculated rates (open rate, click rate, etc.)
    - ROI calculations
    """
    controller = CampaignController(db)
    return await controller.get_campaign(campaign_id, current_user)


@router.post(
    "/",
    response_model=CampaignResponse,
    status_code=201,
    summary="Create a new campaign",
    description="Create a new marketing campaign"
)
async def create_campaign(
    campaign_data: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Create a new campaign.

    The current user will be automatically set as the owner if not specified.

    Example:
    ```json
    {
      "name": "Summer Product Launch 2025",
      "description": "Q2 product launch campaign",
      "type": "email",
      "status": "draft",
      "budget": 5000.00,
      "start_date": "2025-06-01T00:00:00Z",
      "end_date": "2025-06-30T23:59:59Z",
      "email_template_id": "uuid-here",
      "tags": ["product-launch", "Q2"]
    }
    ```
    """
    controller = CampaignController(db)
    return await controller.create_campaign(campaign_data, current_user)


@router.put(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Update a campaign",
    description="Update an existing campaign's information"
)
async def update_campaign(
    campaign_id: UUID,
    campaign_data: CampaignUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Update an existing campaign.

    Only the owner of the campaign can update it.
    """
    controller = CampaignController(db)
    return await controller.update_campaign(campaign_id, campaign_data, current_user)


@router.delete(
    "/{campaign_id}",
    summary="Delete a campaign",
    description="Delete a campaign and all associated data"
)
async def delete_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Delete a campaign.

    This will also delete:
    - Campaign-contact associations
    - Campaign metrics
    - Note: Prospects are NOT deleted, only the campaign reference is removed
    """
    controller = CampaignController(db)
    return await controller.delete_campaign(campaign_id, current_user)


@router.post(
    "/{campaign_id}/audience",
    summary="Add audience to campaign",
    description="Add contacts and/or prospects to a campaign"
)
async def add_audience_to_campaign(
    campaign_id: UUID,
    audience_request: AddToCampaignRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Add contacts and/or prospects to a campaign's target audience.

    Example:
    ```json
    {
      "contact_ids": ["uuid1", "uuid2"],
      "prospect_ids": ["uuid3", "uuid4"]
    }
    ```

    Returns the number of contacts/prospects added.
    """
    controller = CampaignController(db)
    return await controller.add_audience(campaign_id, audience_request, current_user)


@router.get(
    "/{campaign_id}/audience",
    summary="Get campaign audience",
    description="Get all audience members (contacts and prospects) for a campaign"
)
async def get_campaign_audience(
    campaign_id: UUID,
    status: Optional[str] = Query(
        None,
        description="Filter by engagement status (comma-separated)"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get all audience members for a campaign with engagement data.

    Returns:
    - Recipient type (contact or prospect)
    - Name and email
    - Engagement status (sent, opened, clicked, etc.)
    - Engagement timestamps
    - Engagement scores
    """
    controller = CampaignController(db)
    return await controller.get_audience(campaign_id, current_user, status, skip, limit)


@router.delete(
    "/{campaign_id}/audience/{campaign_contact_id}",
    summary="Remove audience member from campaign",
    description="Remove a specific contact or prospect from the campaign audience"
)
async def remove_audience_member(
    campaign_id: UUID,
    campaign_contact_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Remove a specific audience member from the campaign.

    This will delete the campaign_contact association.
    The contact or prospect itself will NOT be deleted.

    Returns:
    - Success message with updated audience count
    """
    controller = CampaignController(db)
    return await controller.remove_audience_member(campaign_id, campaign_contact_id, current_user)


@router.post(
    "/{campaign_id}/execute",
    summary="Execute campaign",
    description="Send/execute a campaign (send emails, etc.)"
)
async def execute_campaign(
    campaign_id: UUID,
    execute_request: CampaignExecuteRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Execute a campaign (send emails, initiate outreach, etc.).

    Options:
    - **send_test_email**: Send test email to specified addresses
    - **schedule_for**: Schedule for future execution

    Example:
    ```json
    {
      "send_test_email": false,
      "schedule_for": null
    }
    ```

    For test sending:
    ```json
    {
      "send_test_email": true,
      "test_email_recipients": ["test@example.com"]
    }
    ```
    """
    controller = CampaignController(db)
    return await controller.execute_campaign(campaign_id, execute_request, current_user)


@router.post(
    "/{campaign_id}/send-pending",
    summary="Send to pending audience members",
    description="Send campaign to newly added audience members who haven't been sent to yet"
)
async def send_to_pending_audience(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Send campaign to all pending (unsent) audience members.

    This is useful for sending to newly added audience members after
    the campaign has already been executed once.

    Returns:
    - Number of emails sent
    - Success/failure counts
    """
    controller = CampaignController(db)
    return await controller.send_to_pending_audience(campaign_id, current_user)


@router.post(
    "/{campaign_id}/audience/{campaign_contact_id}/resend",
    summary="Resend to specific audience member",
    description="Resend campaign to a specific audience member"
)
async def resend_to_audience_member(
    campaign_id: UUID,
    campaign_contact_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Resend campaign to a specific audience member.

    This will reset their status to pending and resend the campaign.
    Useful for retrying bounced emails or resending to specific members.

    Returns:
    - Success message
    - Updated member status
    """
    controller = CampaignController(db)
    return await controller.resend_to_member(campaign_id, campaign_contact_id, current_user)


@router.get(
    "/{campaign_id}/audience/export",
    summary="Export campaign audience",
    description="Export campaign audience to CSV or Excel file"
)
async def export_campaign_audience(
    campaign_id: UUID,
    format: str = Query("csv", regex="^(csv|excel)$", description="Export format: csv or excel"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Export campaign audience to CSV or Excel format.

    Query parameters:
    - format: 'csv' or 'excel' (default: 'csv')

    Returns:
    - File download with audience data
    """
    controller = CampaignController(db)
    return await controller.export_audience(campaign_id, format, current_user)


@router.post(
    "/{campaign_id}/audience/import",
    summary="Import campaign audience",
    description="Import audience members from CSV or Excel file"
)
async def import_campaign_audience(
    campaign_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Import audience members from CSV or Excel file.

    Expected columns:
    - email (required)
    - first_name
    - last_name
    - phone
    - company_name

    Returns:
    - Import statistics (success count, errors)
    """
    controller = CampaignController(db)
    return await controller.import_audience(campaign_id, file, current_user)


@router.get(
    "/{campaign_id}/metrics",
    summary="Get campaign metrics",
    description="Get performance metrics for a campaign"
)
async def get_campaign_metrics(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get campaign performance metrics.

    Returns:
    - Sent, delivered, opened, clicked, converted counts
    - Delivery, open, click, response, conversion rates
    - Bounce rate
    - Budget, cost, revenue, ROI
    """
    controller = CampaignController(db)
    return await controller.get_metrics(campaign_id, current_user)


@router.get(
    "/{campaign_id}/conversions",
    summary="Get campaign conversions",
    description="Get all deals/conversions generated from this campaign"
)
async def get_campaign_conversions(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get all deals/conversions generated from this campaign.

    Returns:
    - Deal ID, name, and value
    - Contact/prospect who converted
    - Conversion timestamp
    """
    controller = CampaignController(db)
    return await controller.get_conversions(campaign_id, current_user)


@router.get(
    "/{campaign_id}/analytics",
    summary="Get campaign analytics",
    description="Get comprehensive analytics including time-series data"
)
async def get_campaign_analytics(
    campaign_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Number of days for time-series data"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get comprehensive campaign analytics.

    Returns:
    - Campaign metrics
    - Time-series performance data (daily metrics)
    - Top performers (most engaged contacts/prospects)
    - Conversion funnel (sent → delivered → opened → clicked → converted)
    """
    controller = CampaignController(db)
    return await controller.get_analytics(campaign_id, current_user, days)


@router.get(
    "/{campaign_id}/prospects",
    summary="Get campaign prospects",
    description="Get all prospects generated by this campaign"
)
async def get_campaign_prospects(
    campaign_id: UUID,
    status: Optional[str] = Query(
        None,
        description="Filter by prospect status (comma-separated)"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get all prospects generated by this campaign.

    This endpoint returns prospects where campaign_id matches.
    For full campaign audience (including contacts), use /audience endpoint.
    """
    from app.controllers.prospect_controller import ProspectController
    controller = ProspectController(db)
    return await controller.get_campaign_prospects(campaign_id, current_user, status, skip, limit)


@router.post(
    "/{campaign_id}/prospects/{prospect_id}/link-deal",
    summary="Link deal to campaign",
    description="Link a deal to a campaign by updating the campaign_contact record"
)
async def link_deal_to_campaign(
    campaign_id: UUID,
    prospect_id: UUID,
    deal_id: UUID = Body(..., embed=True),
    conversion_value: float = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Link a deal to a campaign.

    This updates the campaign_contact record to associate a deal with the prospect conversion.
    This is necessary for deals to appear in the campaign's Conversions tab.

    Args:
    - campaign_id: Campaign UUID
    - prospect_id: Prospect UUID
    - deal_id: Deal UUID that was created
    - conversion_value: Value of the conversion/deal

    Returns:
    - Success message with campaign_contact_id
    """
    controller = CampaignController(db)
    return await controller.link_deal_to_campaign(
        campaign_id=campaign_id,
        prospect_id=prospect_id,
        deal_id=deal_id,
        conversion_value=conversion_value,
        current_user=current_user
    )
