from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from uuid import UUID
from ..core.database import get_db
from ..core.auth import (
    get_current_user, require_sales_user, require_any_authenticated,
    can_access_user_data, can_modify_user_data, require_permission,
    has_permission
)
from ..models.user import UserProfile
from ..models.deal import Deal
from ..models.company import Company
from ..models.custom_field import EntityType
from ..schemas.deal import DealCreate, DealUpdate, DealResponse, DealWithRelations
from ..services.custom_field_service import CustomFieldService

router = APIRouter()

# Constants
FILTER_BY_OWNER_ID = "Filter by owner ID"
DEALS_VIEW_ALL_PERMISSION = "deals.view_all"


@router.get("/", response_model=List[DealWithRelations])
async def get_user_deals(
    date_range: Optional[str] = Query(
        None, description="Date range filter: thisWeek, thisMonth, thisQuarter, thisYear"),
    probability_range: Optional[str] = Query(
        None, description="Probability range: high, medium, low"),
    owner_id: Optional[str] = Query(None, description=FILTER_BY_OWNER_ID),
    stage: Optional[str] = Query(None, description="Filter by deal stage"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_any_authenticated())
):
    query = db.query(Deal).options(
        joinedload(Deal.company),
        joinedload(Deal.contact),
        joinedload(Deal.owner)
    )

    # Permission-based filtering using helper function
    from ..core.auth_helpers import get_deals_query_filter
    query = get_deals_query_filter(db, current_user, query)

    # Apply filters
    from datetime import datetime, timedelta

    # Date range filtering
    if date_range:
        now = datetime.now()
        if date_range == "thisWeek":
            start_date = now - timedelta(days=now.weekday())
            query = query.filter(Deal.created_at >= start_date)
        elif date_range == "thisMonth":
            start_date = now.replace(day=1)
            query = query.filter(Deal.created_at >= start_date)
        elif date_range == "thisQuarter":
            quarter_start_month = ((now.month - 1) // 3) * 3 + 1
            start_date = now.replace(month=quarter_start_month, day=1)
            query = query.filter(Deal.created_at >= start_date)
        elif date_range == "thisYear":
            start_date = now.replace(month=1, day=1)
            query = query.filter(Deal.created_at >= start_date)

    # Probability range filtering
    if probability_range:
        if probability_range == "high":
            query = query.filter(Deal.probability > 70)
        elif probability_range == "medium":
            query = query.filter(Deal.probability >= 30,
                                 Deal.probability <= 70)
        elif probability_range == "low":
            query = query.filter(Deal.probability < 30)

    # Owner filtering (for managers/admins)
    if owner_id and has_permission(db, current_user, DEALS_VIEW_ALL_PERMISSION):
        query = query.filter(Deal.owner_id == owner_id)

    # Stage filtering
    if stage:
        query = query.filter(Deal.stage == stage)

    deals = query.order_by(Deal.updated_at.desc()).all()
    return deals


@router.get("/pipeline", response_model=dict)
async def get_pipeline_deals(
    date_range: Optional[str] = Query(
        None, description="Date range filter: thisWeek, thisMonth, thisQuarter, thisYear"),
    probability_range: Optional[str] = Query(
        None, description="Probability range: high, medium, low"),
    owner_id: Optional[str] = Query(None, description=FILTER_BY_OWNER_ID),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_any_authenticated())
):
    query = db.query(Deal).options(
        joinedload(Deal.company),
        joinedload(Deal.contact),
        joinedload(Deal.owner)
    )

    # Permission-based filtering using helper function
    from ..core.auth_helpers import get_deals_query_filter
    query = get_deals_query_filter(db, current_user, query)

    # Apply filters (same as main deals endpoint)
    from datetime import datetime, timedelta

    # Date range filtering
    if date_range:
        now = datetime.now()
        if date_range == "thisWeek":
            start_date = now - timedelta(days=now.weekday())
            query = query.filter(Deal.created_at >= start_date)
        elif date_range == "thisMonth":
            start_date = now.replace(day=1)
            query = query.filter(Deal.created_at >= start_date)
        elif date_range == "thisQuarter":
            quarter_start_month = ((now.month - 1) // 3) * 3 + 1
            start_date = now.replace(month=quarter_start_month, day=1)
            query = query.filter(Deal.created_at >= start_date)
        elif date_range == "thisYear":
            start_date = now.replace(month=1, day=1)
            query = query.filter(Deal.created_at >= start_date)

    # Probability range filtering
    if probability_range:
        if probability_range == "high":
            query = query.filter(Deal.probability > 70)
        elif probability_range == "medium":
            query = query.filter(Deal.probability >= 30,
                                 Deal.probability <= 70)
        elif probability_range == "low":
            query = query.filter(Deal.probability < 30)

    # Owner filtering (for managers/admins)
    if owner_id and has_permission(db, current_user, DEALS_VIEW_ALL_PERMISSION):
        query = query.filter(Deal.owner_id == owner_id)

    deals = query.order_by(Deal.updated_at.desc()).all()

    # Group deals by stage
    pipeline_data = {
        'lead': {'id': 'lead', 'title': 'Lead', 'deals': []},
        'qualified': {'id': 'qualified', 'title': 'Qualified', 'deals': []},
        'proposal': {'id': 'proposal', 'title': 'Proposal', 'deals': []},
        'negotiation': {'id': 'negotiation', 'title': 'Negotiation', 'deals': []},
        'closed_won': {'id': 'closed_won', 'title': 'Closed Won', 'deals': []},
        'closed_lost': {'id': 'closed_lost', 'title': 'Closed Lost', 'deals': []}
    }

    for deal in deals:
        stage = deal.stage or 'lead'
        if stage in pipeline_data:
            pipeline_data[stage]['deals'].append({
                'id': str(deal.id),
                'title': deal.name or 'Untitled Deal',
                'value': float(deal.value or 0),
                'probability': deal.probability or 0,
                'contact': deal.contact.first_name + ' ' + deal.contact.last_name if deal.contact else 'Unknown Contact',
                'company': deal.company.name if deal.company else 'Unknown Company',
                'avatar': f'https://ui-avatars.com/api/?name={deal.contact.first_name[0] if deal.contact else "U"}+{deal.contact.last_name[0] if deal.contact else "C"}&background=random' if deal.contact else 'https://ui-avatars.com/api/?name=U+C&background=random',
                'expected_close_date': deal.expected_close_date.isoformat() if deal.expected_close_date else None
            })

    return pipeline_data


@router.get("/{deal_id}", response_model=DealWithRelations)
async def get_deal_by_id(
    deal_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_any_authenticated())
):
    query = db.query(Deal).options(
        joinedload(Deal.company),
        joinedload(Deal.contact),
        joinedload(Deal.owner),
        joinedload(Deal.activities),
        joinedload(Deal.documents)
    ).filter(Deal.id == deal_id)

    # Permission-based filtering using helper function
    from ..core.auth_helpers import get_deals_query_filter
    query = get_deals_query_filter(db, current_user, query)

    deals = query.all()

    total_value = sum([float(deal.value or 0) for deal in deals])
    won_deals = [deal for deal in deals if deal.stage == 'closed_won']
    lost_deals = [deal for deal in deals if deal.stage == 'closed_lost']
    active_deals = [deal for deal in deals if deal.stage not in [
        'closed_won', 'closed_lost']]

    stats = {
        'total_deals': len(deals),
        'active_deals': len(active_deals),
        'won_deals': len(won_deals),
        'lost_deals': len(lost_deals),
        'total_value': total_value,
        'won_value': sum([float(deal.value or 0) for deal in won_deals]),
        'pipeline_value': sum([float(deal.value or 0) for deal in active_deals]),
        'conversion_rate': round((len(won_deals) / len(deals)) * 100, 2) if deals else 0
    }

    return stats


@router.get("/analytics/revenue")
async def get_revenue_data(
    date_range: Optional[str] = Query(
        None, description="Date range filter: last7days, last30days, last90days, thisquarter, lastyear"),
    owner_id: Optional[str] = Query(None, description=FILTER_BY_OWNER_ID),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_any_authenticated())
):
    from sqlalchemy.orm import joinedload

    query = db.query(Deal).options(joinedload(Deal.company))

    # Permission-based filtering using helper function
    from ..core.auth_helpers import get_deals_query_filter
    query = get_deals_query_filter(db, current_user, query)

    # Apply additional filters
    if owner_id and has_permission(db, current_user, "deals.view_all"):
        query = query.filter(Deal.owner_id == owner_id)

    # Apply date range filter
    if date_range:
        from datetime import datetime, timedelta
        now = datetime.now()

        if date_range == 'last7days':
            start_date = now - timedelta(days=7)
            query = query.filter(Deal.actual_close_date >= start_date)
        elif date_range == 'last30days':
            start_date = now - timedelta(days=30)
            query = query.filter(Deal.actual_close_date >= start_date)
        elif date_range == 'last90days':
            start_date = now - timedelta(days=90)
            query = query.filter(Deal.actual_close_date >= start_date)
        elif date_range == 'thisquarter':
            current_quarter = (now.month - 1) // 3 + 1
            quarter_start = datetime(
                now.year, (current_quarter - 1) * 3 + 1, 1)
            query = query.filter(Deal.actual_close_date >= quarter_start)
        elif date_range == 'lastyear':
            year_start = datetime(now.year - 1, 1, 1)
            year_end = datetime(now.year, 1, 1)
            query = query.filter(Deal.actual_close_date >=
                                 year_start, Deal.actual_close_date < year_end)

    deals = query.all()

    # Generate last 12 months of revenue data
    from datetime import datetime, timedelta
    import calendar

    revenue_data = []
    now = datetime.now()

    for i in range(11, -1, -1):
        # Calculate the month
        month_date = datetime(now.year, now.month, 1) - timedelta(days=30*i)
        month_name = calendar.month_abbr[month_date.month]

        # Filter deals closed in this month
        month_deals = [
            deal for deal in deals
            if deal.actual_close_date and
            deal.actual_close_date.month == month_date.month and
            deal.actual_close_date.year == month_date.year
        ]

        actual = sum([float(deal.value or 0)
                     for deal in month_deals if deal.stage == 'closed_won'])

        # Generate forecast (simple projection)
        forecast = actual * 1.1 if actual > 0 else 50000
        target = forecast * 0.9

        revenue_data.append({
            "month": month_name,
            "actual": int(actual),
            "forecast": int(forecast),
            "target": int(target)
        })

    return revenue_data


@router.get("/analytics/performance")
async def get_performance_metrics(
    date_range: Optional[str] = Query(
        None, description="Date range filter: last7days, last30days, last90days, thisquarter, lastyear"),
    owner_id: Optional[str] = Query(None, description=FILTER_BY_OWNER_ID),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_any_authenticated())
):
    from sqlalchemy.orm import joinedload

    query = db.query(Deal).options(joinedload(Deal.company))

    # Permission-based filtering using helper function
    from ..core.auth_helpers import get_deals_query_filter
    query = get_deals_query_filter(db, current_user, query)

    # Apply additional filters
    if owner_id and has_permission(db, current_user, "deals.view_all"):
        query = query.filter(Deal.owner_id == owner_id)

    # Apply date range filter
    if date_range:
        from datetime import datetime, timedelta
        now = datetime.now()

        if date_range == 'last7days':
            start_date = now - timedelta(days=7)
            query = query.filter(Deal.actual_close_date >= start_date)
        elif date_range == 'last30days':
            start_date = now - timedelta(days=30)
            query = query.filter(Deal.actual_close_date >= start_date)
        elif date_range == 'last90days':
            start_date = now - timedelta(days=90)
            query = query.filter(Deal.actual_close_date >= start_date)
        elif date_range == 'thisquarter':
            current_quarter = (now.month - 1) // 3 + 1
            quarter_start = datetime(
                now.year, (current_quarter - 1) * 3 + 1, 1)
            query = query.filter(Deal.actual_close_date >= quarter_start)
        elif date_range == 'lastyear':
            year_start = datetime(now.year - 1, 1, 1)
            year_end = datetime(now.year, 1, 1)
            query = query.filter(Deal.actual_close_date >=
                                 year_start, Deal.actual_close_date < year_end)

    deals = query.all()

    won_deals = [deal for deal in deals if deal.stage == 'closed_won']
    lost_deals = [deal for deal in deals if deal.stage == 'closed_lost']
    total_closed = len(won_deals) + len(lost_deals)

    achieved = sum([float(deal.value or 0) for deal in won_deals])
    # Assume quota is 30% higher than achieved
    quota = max(achieved * 1.3, 500000)
    avg_deal_size = achieved / len(won_deals) if won_deals else 25000
    conversion_rate = round((len(won_deals) / total_closed)
                            * 100) if total_closed > 0 else 0

    return {
        "achieved": int(achieved),
        "quota": int(quota),
        "percentage": round((achieved / quota) * 100),
        "avgDealSize": int(avg_deal_size),
        "conversionRate": conversion_rate,
        "dealsWon": len(won_deals),
        "dealsLost": len(lost_deals),
        "totalDeals": len(deals)
    }


@router.get("/analytics/winrate")
async def get_win_rate_data(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_any_authenticated())
):
    query = db.query(Deal)

    # Permission-based filtering using helper function
    from ..core.auth_helpers import get_deals_query_filter
    query = get_deals_query_filter(db, current_user, query)

    deals = query.all()

    won_deals = len([deal for deal in deals if deal.stage == 'closed_won'])
    lost_deals = len([deal for deal in deals if deal.stage == 'closed_lost'])
    total_closed = won_deals + lost_deals
    base_win_rate = round((won_deals / total_closed) *
                          100) if total_closed > 0 else 0

    # Generate quarterly win rate data with some variation
    import random
    quarters = ['Q1', 'Q2', 'Q3', 'Q4']

    win_rate_data = []
    for quarter in quarters:
        # Add some variation to the base win rate
        variation = random.randint(-10, 10)
        win_rate = max(0, min(100, base_win_rate + variation))

        win_rate_data.append({
            "period": quarter,
            "winRate": win_rate
        })

    return win_rate_data


@router.get("/analytics/filter-options")
async def get_filter_options(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_any_authenticated())
):
    """Get available filter options for analytics filters"""

    # Get available sales reps (users who own deals)
    if current_user.role in ['admin', 'sales_manager']:
        # Admin and managers can see all users
        users_query = db.query(UserProfile.id, UserProfile.first_name,
                               UserProfile.last_name, UserProfile.role).distinct()
        users = users_query.all()

        reps = [
            {
                "value": str(user.id),
                "label": f"{user.first_name} {user.last_name}",
                "role": user.role
            }
            for user in users
        ]
    else:
        # Regular users only see themselves
        reps = [
            {
                "value": str(current_user.id),
                "label": f"{current_user.first_name} {current_user.last_name}",
                "role": current_user.role
            }
        ]

    # Get available industries from companies
    industries_query = db.query(Company.industry).filter(
        Company.industry.isnot(None)).distinct()
    industries = [industry[0]
                  for industry in industries_query.all() if industry[0]]

    industry_options = [
        {"value": industry, "label": industry}
        for industry in sorted(industries)
    ]

    return {
        "reps": reps,
        "industries": industry_options,
        "dateRanges": [
            {"value": "last7days", "label": "Last 7 Days"},
            {"value": "last30days", "label": "Last 30 Days"},
            {"value": "last90days", "label": "Last 90 Days"},
            {"value": "thisquarter", "label": "This Quarter"},
            {"value": "lastyear", "label": "Last Year"}
        ]
    }


@router.post("/", response_model=DealResponse)
async def create_deal(
    deal_data: DealCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Create a new deal"""

    # Check if user has permission to create deals
    if not has_permission(db, current_user, "deals.create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to create deals"
        )

    try:
        # Extract custom fields before creating deal
        custom_fields_data = deal_data.custom_fields or {}

        # Create deal with current user as owner
        deal_dict = deal_data.model_dump(exclude={'owner_id', 'custom_fields'})
        db_deal = Deal(
            **deal_dict,
            owner_id=current_user.id
        )

        db.add(db_deal)
        db.commit()
        db.refresh(db_deal)

        # Save custom field values if provided
        if custom_fields_data:
            CustomFieldService.save_custom_field_values(
                db=db,
                entity_id=str(db_deal.id),
                entity_type=EntityType.DEAL,
                field_values=custom_fields_data
            )
            db.commit()  # Commit custom field values

        # Get custom fields for response
        custom_fields_dict = CustomFieldService.get_entity_custom_fields_dict(
            db=db,
            entity_id=str(db_deal.id),
            entity_type=EntityType.DEAL
        )

        # Build response with custom fields
        response_data = {
            "id": db_deal.id,
            "name": db_deal.name,
            "value": db_deal.value,
            "stage": db_deal.stage,
            "probability": db_deal.probability,
            "expected_close_date": db_deal.expected_close_date,
            "description": db_deal.description,
            "source": db_deal.source,
            "next_action": db_deal.next_action,
            "company_id": db_deal.company_id,
            "contact_id": db_deal.contact_id,
            "owner_id": db_deal.owner_id,
            "created_at": db_deal.created_at,
            "updated_at": db_deal.updated_at,
            "actual_close_date": db_deal.actual_close_date,
            "custom_fields": custom_fields_dict if custom_fields_dict else None
        }

        return response_data

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create deal: {str(e)}"
        )


@router.put("/{deal_id}", response_model=DealResponse)
async def update_deal(
    deal_id: UUID,
    deal_data: DealUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Update an existing deal"""
    # Get the deal first
    deal = db.query(Deal).filter(Deal.id == deal_id).first()

    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found"
        )

    # Check edit permission using helper function
    from ..core.auth_helpers import check_deal_edit_permission
    if not check_deal_edit_permission(db, current_user, deal):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this deal"
        )

    try:
        # Extract custom fields before updating deal
        update_data = deal_data.model_dump(exclude_unset=True)
        custom_fields_data = update_data.pop('custom_fields', None)

        # Update deal fields
        for field, value in update_data.items():
            setattr(deal, field, value)

        db.commit()
        db.refresh(deal)

        # Update custom field values if provided
        if custom_fields_data is not None:
            CustomFieldService.save_custom_field_values(
                db=db,
                entity_id=str(deal.id),
                entity_type=EntityType.DEAL,
                field_values=custom_fields_data
            )
            db.commit()  # Commit custom field values

        # Get custom fields for response
        custom_fields_dict = CustomFieldService.get_entity_custom_fields_dict(
            db=db,
            entity_id=str(deal.id),
            entity_type=EntityType.DEAL
        )

        # Build response with custom fields
        response_data = {
            "id": deal.id,
            "name": deal.name,
            "value": deal.value,
            "stage": deal.stage,
            "probability": deal.probability,
            "expected_close_date": deal.expected_close_date,
            "description": deal.description,
            "source": deal.source,
            "next_action": deal.next_action,
            "company_id": deal.company_id,
            "contact_id": deal.contact_id,
            "owner_id": deal.owner_id,
            "created_at": deal.created_at,
            "updated_at": deal.updated_at,
            "actual_close_date": deal.actual_close_date,
            "custom_fields": custom_fields_dict if custom_fields_dict else None
        }

        return response_data

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update deal: {str(e)}"
        )


@router.delete("/{deal_id}")
async def delete_deal(
    deal_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Delete a deal"""
    # Get the deal first
    deal = db.query(Deal).filter(Deal.id == deal_id).first()

    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found"
        )

    # Check delete permission using helper function
    from ..core.auth_helpers import check_deal_delete_permission
    if not check_deal_delete_permission(db, current_user, deal):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this deal"
        )

    db.delete(deal)
    db.commit()

    return {"message": "Deal deleted successfully"}
