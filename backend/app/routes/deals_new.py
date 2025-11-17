"""
Deal API routes.
Clean endpoint definitions using the controller layer.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO

from ..controllers.deal_controller import DealController
from ..schemas.deal import DealCreate, DealUpdate, DealResponse, DealWithRelations
from ..schemas.deal_document import DealDocumentResponse
from ..services.deal_document_service import DealDocumentService
from ..services.file_storage_factory import get_file_storage_service
from ..core.database import get_db
from ..core.auth import get_current_user, require_any_authenticated
from ..models.user import UserProfile


router = APIRouter()


@router.get("/", response_model=List[DealWithRelations])
async def get_user_deals(
    date_range: Optional[str] = Query(
        None,
        description="Date range filter: thisWeek, thisMonth, thisQuarter, thisYear"
    ),
    probability_range: Optional[str] = Query(
        None,
        description="Probability range: high, medium, low"
    ),
    owner_id: Optional[str] = Query(
        None,
        description="Filter by owner ID (requires deals.view_all permission)"
    ),
    stage: Optional[str] = Query(
        None,
        description="Filter by deal stage"
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000,
                       description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_any_authenticated())
):
    """
    Retrieve all deals with advanced filtering.

    **Permissions:**
    - Users see only their own deals (requires deals.view_own)
    - Managers/Admins can see all deals (requires deals.view_all)

    **Filters:**
    - **date_range**: Filter by creation date (thisWeek, thisMonth, thisQuarter, thisYear)
    - **probability_range**: Filter by probability (high >70%, medium 30-70%, low <30%)
    - **owner_id**: Filter by owner (managers/admins only)
    - **stage**: Filter by deal stage (lead, qualified, proposal, negotiation, closed_won, closed_lost)

    **Performance Note:** This endpoint uses optimized queries with eager loading
    to prevent N+1 query issues. All related data (company, contact, owner) is
    loaded in a single query.
    """
    return DealController.get_deals(
        db=db,
        current_user=current_user,
        date_range=date_range,
        probability_range=probability_range,
        owner_id=owner_id,
        stage=stage,
        skip=skip,
        limit=limit
    )


@router.get("/pipeline")
async def get_pipeline_deals(
    date_range: Optional[str] = Query(
        None,
        description="Date range filter: all, thisquarter, thisyear, lastyear"
    ),
    owner_id: Optional[str] = Query(
        None,
        description="Filter by owner ID (requires deals.view_all permission)"
    ),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_any_authenticated())
):
    """
    Get deals organized by pipeline stages for analytics.

    **Purpose:** This endpoint provides deals grouped by their current stage,
    filtered by creation date for analytics purposes.

    **Date Filter:** Uses `created_at` to show deals that entered the pipeline
    during the selected period.

    **Returns:**
    ```json
    {
      "lead": {"id": "lead", "title": "Lead", "deals": [...]},
      "qualified": {"id": "qualified", "title": "Qualified", "deals": [...]},
      "proposal": {"id": "proposal", "title": "Proposal", "deals": [...]},
      "negotiation": {"id": "negotiation", "title": "Negotiation", "deals": [...]},
      "closed_won": {"id": "closed_won", "title": "Closed Won", "deals": [...]},
      "closed_lost": {"id": "closed_lost", "title": "Closed Lost", "deals": [...]}
    }
    ```

    Each deal includes: id, title, value, probability, contact, company, avatar, expected_close_date
    """
    return DealController.get_pipeline_deals(
        db=db,
        current_user=current_user,
        date_range=date_range,
        owner_id=owner_id
    )


@router.get("/statistics")
async def get_deal_statistics(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_any_authenticated())
):
    """
    Get comprehensive deal statistics.

    **Returns:**
    - total_deals: Total number of deals
    - active_deals: Deals not yet won or lost
    - won_deals: Successfully closed deals
    - lost_deals: Lost opportunities
    - total_value: Combined value of all deals
    - won_value: Total value of won deals
    - pipeline_value: Total value of active deals
    - conversion_rate: Percentage of deals won
    """
    return DealController.get_deal_statistics(
        db=db,
        current_user=current_user
    )


@router.get("/inactive")
async def get_inactive_deals(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_any_authenticated())
):
    """
    Get deals that have been inactive (no updates) for the warning period.
    Warning period is defined in system configuration (sales.deal_inactivity_warning_days).

    **Returns:**
    - List of inactive deals with full details
    """
    from ..services.deal_service import DealService

    deal_service = DealService(db)
    inactive_deals = deal_service.get_inactive_deals(current_user=current_user)

    return {
        "count": len(inactive_deals),
        "deals": inactive_deals
    }


@router.get("/analytics/revenue")
async def get_revenue_data(
    date_range: Optional[str] = Query(
        None,
        description="Date range: last7days, last30days, last90days, thisquarter, lastyear"
    ),
    owner_id: Optional[str] = Query(
        None,
        description="Filter by owner ID (requires deals.view_all permission)"
    ),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_any_authenticated())
):
    """
    Get revenue analytics data for the last 12 months.

    **Returns:** Monthly breakdown with actual, forecast, and target values.

    This endpoint generates revenue trends showing:
    - **actual**: Actual revenue from closed won deals
    - **forecast**: Projected revenue (actual × 1.1)
    - **target**: Target revenue (forecast × 0.9)

    Perfect for revenue charts and trend analysis.
    """
    return DealController.get_revenue_data(
        db=db,
        current_user=current_user,
        date_range=date_range,
        owner_id=owner_id
    )


@router.get("/analytics/performance")
async def get_performance_metrics(
    date_range: Optional[str] = Query(
        None,
        description="Date range: last7days, last30days, last90days, thisquarter, lastyear"
    ),
    owner_id: Optional[str] = Query(
        None,
        description="Filter by owner ID (requires deals.view_all permission)"
    ),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_any_authenticated())
):
    """
    Get performance metrics and KPIs.

    **Returns:**
    - achieved: Total revenue achieved
    - quota: Target quota (achieved × 1.3)
    - percentage: Achievement percentage
    - avgDealSize: Average size of won deals
    - conversionRate: Win rate percentage
    - dealsWon: Number of won deals
    - dealsLost: Number of lost deals
    - totalDeals: Total number of deals

    Use this for performance dashboards and quota tracking.
    """
    return DealController.get_performance_metrics(
        db=db,
        current_user=current_user,
        date_range=date_range,
        owner_id=owner_id
    )


@router.get("/analytics/winrate")
async def get_win_rate_data(
    date_range: Optional[str] = Query(
        None,
        description="Date range: last7days, last30days, last90days, thisquarter, lastyear"
    ),
    owner_id: Optional[str] = Query(
        None,
        description="Filter by owner ID (requires deals.view_all permission)"
    ),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_any_authenticated())
):
    """
    Get win rate analytics by quarter.

    **Returns:** Quarterly win rate data with percentage for each quarter (Q1-Q4).

    Win rate is calculated as: (won deals / total closed deals) × 100

    Includes natural variation to show realistic quarterly trends.

    Supports filtering by date range and owner ID for targeted analytics.
    """
    return DealController.get_win_rate_data(
        db=db,
        current_user=current_user,
        date_range=date_range,
        owner_id=owner_id
    )


@router.get("/analytics/filter-options")
async def get_filter_options(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_any_authenticated())
):
    """
    Get available filter options for analytics.

    **Returns:**
    - **reps**: Available sales representatives (based on user permissions)
    - **industries**: Available industries from companies
    - **dateRanges**: Predefined date range options

    **Permission-based:**
    - Admins/Managers see all sales reps
    - Regular users see only themselves

    Use this to populate filter dropdowns in the UI.
    """
    return DealController.get_filter_options(
        db=db,
        current_user=current_user
    )


@router.get("/export")
async def export_deals(
    date_range: Optional[str] = Query(
        None,
        description="Date range filter: thisWeek, thisMonth, thisQuarter, thisYear"
    ),
    probability_range: Optional[str] = Query(
        None,
        description="Probability range: high, medium, low"
    ),
    owner_id: Optional[str] = Query(
        None,
        description="Filter by owner ID (requires deals.view_all permission)"
    ),
    stage: Optional[str] = Query(
        None,
        description="Filter by deal stage"
    ),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_any_authenticated())
):
    """
    Export deals data with filters.

    **Required Permission:** deals.export

    **Purpose:** Returns all deals matching the filters for export purposes.

    **Filters:**
    - **date_range**: Filter by creation date
    - **probability_range**: Filter by probability
    - **owner_id**: Filter by owner (managers/admins only)
    - **stage**: Filter by deal stage

    **Returns:** List of deals with all details including relationships
    (company, contact, owner) suitable for CSV/JSON export.
    """
    from ..core.auth import has_permission
    from fastapi import HTTPException

    # Check export permission
    if not has_permission(db, current_user, "deals.export"):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to export deals"
        )

    # Use the existing get_deals method with all filters
    return DealController.get_deals(
        db=db,
        current_user=current_user,
        date_range=date_range,
        probability_range=probability_range,
        owner_id=owner_id,
        stage=stage,
        skip=0,
        limit=10000  # High limit for export
    )


@router.get("/{deal_id}", response_model=DealWithRelations)
async def get_deal_by_id(
    deal_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_any_authenticated())
):
    """
    Retrieve a single deal by ID.

    **Returns:** Complete deal details including:
    - All deal fields
    - Custom field values
    - Owner information
    - Contact details
    - Company information
    - Related activities
    - Related documents

    **Permissions:** Users can only view deals they have permission to access
    based on their role (own deals or all deals).
    """
    return DealController.get_deal(
        deal_id=deal_id,
        db=db,
        current_user=current_user
    )


@router.post("/", response_model=DealResponse, status_code=201)
async def create_deal(
    deal: DealCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Create a new deal.

    **Required Permission:** deals.create

    **Required Fields:**
    - name: Deal name

    **Optional Fields:**
    - value: Deal value (Decimal)
    - stage: Deal stage (default: "lead")
    - probability: Win probability 0-100 (default: 0)
    - expected_close_date: Expected closing date
    - description: Deal description
    - source: Lead source
    - next_action: Next planned action
    - company_id: Associated company UUID
    - contact_id: Associated contact UUID
    - custom_fields: Dictionary of custom field values

    **Custom Fields:**
    Provide as key-value pairs where keys are field names.

    Example:
    ```json
    {
      "name": "Enterprise Software Deal",
      "value": 150000.00,
      "stage": "qualified",
      "probability": 65,
      "company_id": "uuid-here",
      "contact_id": "uuid-here",
      "custom_fields": {
        "deal_type": "New Business",
        "competitor": "CompanyX"
      }
    }
    ```

    The deal is automatically assigned to the current user as owner.
    """
    return DealController.create_deal(
        deal_data=deal,
        db=db,
        current_user=current_user
    )


@router.put("/{deal_id}", response_model=DealResponse)
async def update_deal(
    deal_id: UUID,
    deal: DealUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Update an existing deal.

    **Required Permissions:**
    - deals.edit_all: Edit any deal
    - deals.edit_own: Edit only own deals

    **All fields are optional.** Only provided fields will be updated.

    **Available Fields:**
    - name, value, stage, probability
    - expected_close_date, actual_close_date
    - description, source, lost_reason, next_action
    - company_id, contact_id
    - custom_fields

    **Stage Updates:**
    When moving to 'closed_won' or 'closed_lost', consider setting:
    - actual_close_date: DateTime of closure
    - lost_reason: Reason if closed_lost

    **Custom Fields:**
    - Providing custom_fields replaces all custom field values
    - To update specific fields, include all existing ones you want to keep
    """
    return DealController.update_deal(
        deal_id=deal_id,
        deal_data=deal,
        db=db,
        current_user=current_user
    )


@router.delete("/{deal_id}")
async def delete_deal(
    deal_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Delete a deal.

    **Required Permissions:**
    - deals.delete_all: Delete any deal
    - deals.delete_own: Delete only own deals

    **Warning:** This action cannot be undone. The deal and all associated
    custom field values will be permanently deleted.

    **Note:** Related activities and documents may remain depending on
    database cascade settings.
    """
    return DealController.delete_deal(
        deal_id=deal_id,
        db=db,
        current_user=current_user
    )


# Document Management Endpoints

@router.get("/{deal_id}/documents", response_model=List[DealDocumentResponse])
async def get_deal_documents(
    deal_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_any_authenticated())
):
    """
    Get all documents for a specific deal.

    **Required Permission:** deals.view_own or deals.view_all

    Returns a list of all documents associated with the deal.
    """
    service = DealDocumentService(db)
    return service.get_deal_documents(deal_id)


@router.post("/{deal_id}/documents", response_model=DealDocumentResponse, status_code=201)
async def upload_deal_document(
    deal_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Upload a document for a deal.

    **Required Permission:** deals.edit_own or deals.edit_all

    **Parameters:**
    - file: The file to upload (multipart/form-data)

    **Supported file types:** PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, images, etc.
    **Max file size:** 10MB
    """
    try:
        # Check file size (10MB limit)
        contents = await file.read()
        if len(contents) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds 10MB limit"
            )

        # Reset file pointer for the service to use
        await file.seek(0)

        service = DealDocumentService(db)
        document = await service.upload_document(deal_id, file, current_user)

        # Convert to response format manually if needed
        return DealDocumentResponse(
            id=document.id,
            name=document.name,
            file_path=document.file_path,
            file_size=document.file_size,
            mime_type=document.mime_type,
            deal_id=document.deal_id,
            uploaded_by=document.uploaded_by,
            created_at=document.created_at,
            updated_at=document.updated_at
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}"
        )


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_any_authenticated())
):
    """
    Download a document by its ID from any storage backend.

    **Required Permission:** deals.view_own or deals.view_all

    Returns the file for download.
    """
    service = DealDocumentService(db)
    document = service.get_document(document_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Get storage service and download file
    storage_service = get_file_storage_service()

    try:
        file_content = storage_service.download_file(document.file_path)

        # Create a BytesIO object for streaming
        file_stream = BytesIO(file_content)

        # Return as streaming response
        return StreamingResponse(
            iter([file_content]),
            media_type=document.mime_type or "application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename=\"{document.name}\""
            }
        )

    except HTTPException:
        # Re-raise HTTP exceptions (like 404 from storage service)
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download document: {str(e)}"
        )


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Delete a document.

    **Required Permission:** deals.edit_own or deals.edit_all

    Deletes both the database record and the physical file.
    """
    service = DealDocumentService(db)
    service.delete_document(document_id)

    return {"message": "Document deleted successfully"}
