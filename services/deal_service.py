"""
Deal service for business logic.
Handles all business rules, analytics, and orchestrates operations for deals.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
import calendar
import random
from sqlalchemy.orm import Session, Query

from repositories.deal_repository import DealRepository
from models.deal import Deal
from models.user import UserProfile
from models.company import Company
from models.custom_field import EntityType
from schemas.deal import (
    DealCreate,
    DealUpdate,
    DealResponse,
    DealWithRelations
)
from schemas.user import UserResponse
from schemas.contact import ContactResponse
from schemas.company import CompanyBasicResponse
from custom_field_service import CustomFieldService


class DealService:
    """
    Service class for Deal business logic.

    This service layer handles all business rules, validations, analytics,
    and orchestration for deal-related operations.
    """

    def __init__(self, db: Session):
        """
        Initialize the deal service.

        Args:
            db: Database session
        """
        self.db = db
        self.repository = DealRepository(db)

    def get_deal_by_id(
        self,
        deal_id: UUID,
        *,
        include_custom_fields: bool = True
    ) -> Optional[DealWithRelations]:
        """
        Retrieve a deal by ID with all relations and custom fields.

        Args:
            deal_id: UUID of the deal
            include_custom_fields: Whether to include custom fields

        Returns:
            Deal with relations and custom fields, or None if not found
        """
        deal = self.repository.get_with_relations(deal_id)

        if not deal:
            return None

        return self._build_deal_response_with_relations(
            deal,
            include_custom_fields=include_custom_fields
        )

    def get_all_deals(
        self,
        *,
        filtered_query: Optional[Query] = None,
        date_range: Optional[str] = None,
        probability_range: Optional[str] = None,
        stage: Optional[str] = None,
        owner_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[DealWithRelations]:
        """
        Retrieve all deals with optional filtering.

        Args:
            filtered_query: Pre-filtered query (for permission filtering)
            date_range: Date range filter
            probability_range: Probability range filter
            stage: Stage filter
            owner_id: Owner ID filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of deals with relations
        """
        # Apply additional filters
        query = self.repository.get_filtered_query(
            base_query=filtered_query,
            date_range=date_range,
            probability_range=probability_range,
            stage=stage,
            owner_id=owner_id
        )

        # Add relations and ordering
        from sqlalchemy.orm import joinedload
        query = query.options(
            joinedload(Deal.company),
            joinedload(Deal.contact),
            joinedload(Deal.owner)
        ).order_by(Deal.updated_at.desc()).offset(skip).limit(limit)

        deals = query.all()

        return [
            self._build_deal_response_with_relations(
                deal, include_custom_fields=True)
            for deal in deals
        ]

    def get_pipeline_deals(
        self,
        *,
        filtered_query: Optional[Query] = None,
        date_range: Optional[str] = None,
        owner_id: Optional[UUID] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get deals organized by pipeline stages.

        Args:
            filtered_query: Pre-filtered query (for permission filtering)
            date_range: Date range filter (uses created_at for pipeline filtering)
            owner_id: Owner ID filter

        Returns:
            Dictionary with stages as keys and deal groups as values
        """
        # Apply pipeline-specific filters (created_at for pipeline view)
        query = self.repository.get_pipeline_filtered_query(
            base_query=filtered_query,
            date_range=date_range,
            owner_id=owner_id
        )

        # Add relations and ordering
        from sqlalchemy.orm import joinedload
        query = query.options(
            joinedload(Deal.company),
            joinedload(Deal.contact),
            joinedload(Deal.owner)
        ).order_by(Deal.updated_at.desc())

        deals = query.all()

        return self.repository.get_pipeline_grouped_by_stage(deals)

    def get_deal_statistics(
        self,
        *,
        filtered_query: Optional[Query] = None
    ) -> Dict[str, Any]:
        """
        Get deal statistics.

        Args:
            filtered_query: Pre-filtered query (for permission filtering)

        Returns:
            Dictionary containing various statistics
        """
        if filtered_query is not None:
            deals = filtered_query.all()
        else:
            deals = self.repository.get_all_with_relations(
                load_relations=False)

        won_deals = self.repository.get_won_deals(deals)
        lost_deals = self.repository.get_lost_deals(deals)
        active_deals = self.repository.get_active_deals(deals)

        total_value = self.repository.calculate_total_value(deals)
        won_value = self.repository.calculate_total_value(won_deals)
        pipeline_value = self.repository.calculate_total_value(active_deals)

        return {
            'total_deals': len(deals),
            'active_deals': len(active_deals),
            'won_deals': len(won_deals),
            'lost_deals': len(lost_deals),
            'total_value': total_value,
            'won_value': won_value,
            'pipeline_value': pipeline_value,
            'conversion_rate': round((len(won_deals) / len(deals)) * 100, 2) if deals else 0
        }

    def get_revenue_data(
        self,
        *,
        filtered_query: Optional[Query] = None,
        date_range: Optional[str] = None,
        owner_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Get revenue analytics data.

        Args:
            filtered_query: Pre-filtered query (for permission filtering)
            date_range: Date range filter
            owner_id: Owner ID filter

        Returns:
            List of monthly revenue data
        """
        # Apply analytics filters
        query = self.repository.get_analytics_filtered_query(
            base_query=filtered_query,
            date_range=date_range,
            owner_id=owner_id
        )

        from sqlalchemy.orm import joinedload
        query = query.options(joinedload(Deal.company))

        deals = query.all()

        # Determine the date range for revenue data based on filter
        revenue_data = []
        now = datetime.now()

        if date_range == 'thisquarter':
            # Show only current quarter months (3 months)
            current_quarter = (now.month - 1) // 3 + 1
            quarter_start_month = (current_quarter - 1) * 3 + 1
            start_date = datetime(now.year, quarter_start_month, 1)

            # Generate data for months in this quarter
            current_month = start_date
            while current_month <= now:
                month_name = calendar.month_abbr[current_month.month]

                # Filter deals closed in this month
                month_deals = self.repository.get_deals_by_month(
                    deals,
                    current_month.month,
                    current_month.year
                )

                won_month_deals = self.repository.get_won_deals(month_deals)
                actual = self.repository.calculate_total_value(won_month_deals)

                # Generate forecast (simple projection)
                forecast = actual * 1.1 if actual > 0 else 50000
                target = forecast * 0.9

                revenue_data.append({
                    "month": month_name,
                    "actual": int(actual),
                    "forecast": int(forecast),
                    "target": int(target),
                    "actualDealsCount": len(won_month_deals),
                    "totalDealsCount": len(month_deals)
                })

                # Move to next month
                if current_month.month == 12:
                    current_month = datetime(current_month.year + 1, 1, 1)
                else:
                    current_month = datetime(
                        current_month.year, current_month.month + 1, 1)

        elif date_range == 'lastquarter':
            # Show only last quarter months (3 months)
            current_quarter = (now.month - 1) // 3 + 1
            last_quarter = current_quarter - 1 if current_quarter > 1 else 4
            last_quarter_year = now.year if current_quarter > 1 else now.year - 1
            last_quarter_start_month = (last_quarter - 1) * 3 + 1

            start_date = datetime(
                last_quarter_year, last_quarter_start_month, 1)

            # Generate data for months in last quarter
            current_month = start_date
            for _ in range(3):  # Always 3 months in a quarter
                month_name = calendar.month_abbr[current_month.month]

                # Filter deals closed in this month
                month_deals = self.repository.get_deals_by_month(
                    deals,
                    current_month.month,
                    current_month.year
                )

                won_month_deals = self.repository.get_won_deals(month_deals)
                actual = self.repository.calculate_total_value(won_month_deals)

                # Generate forecast (simple projection)
                forecast = actual * 1.1 if actual > 0 else 50000
                target = forecast * 0.9

                revenue_data.append({
                    "month": month_name,
                    "actual": int(actual),
                    "forecast": int(forecast),
                    "target": int(target),
                    "actualDealsCount": len(won_month_deals),
                    "totalDealsCount": len(month_deals)
                })

                # Move to next month
                if current_month.month == 12:
                    current_month = datetime(current_month.year + 1, 1, 1)
                else:
                    current_month = datetime(
                        current_month.year, current_month.month + 1, 1)

        elif date_range == 'thisyear':
            # Show all months of current year
            for month in range(1, now.month + 1):
                month_name = calendar.month_abbr[month]

                # Filter deals closed in this month
                month_deals = self.repository.get_deals_by_month(
                    deals,
                    month,
                    now.year
                )

                won_month_deals = self.repository.get_won_deals(month_deals)
                actual = self.repository.calculate_total_value(won_month_deals)

                # Generate forecast (simple projection)
                forecast = actual * 1.1 if actual > 0 else 50000
                target = forecast * 0.9

                revenue_data.append({
                    "month": month_name,
                    "actual": int(actual),
                    "forecast": int(forecast),
                    "target": int(target),
                    "actualDealsCount": len(won_month_deals),
                    "totalDealsCount": len(month_deals)
                })

        elif date_range == 'lastyear':
            # Show all 12 months of last year
            last_year = now.year - 1
            for month in range(1, 13):
                month_name = calendar.month_abbr[month]

                # Filter deals closed in this month
                month_deals = self.repository.get_deals_by_month(
                    deals,
                    month,
                    last_year
                )

                won_month_deals = self.repository.get_won_deals(month_deals)
                actual = self.repository.calculate_total_value(won_month_deals)

                # Generate forecast (simple projection)
                forecast = actual * 1.1 if actual > 0 else 50000
                target = forecast * 0.9

                revenue_data.append({
                    "month": month_name,
                    "actual": int(actual),
                    "forecast": int(forecast),
                    "target": int(target),
                    "actualDealsCount": len(won_month_deals),
                    "totalDealsCount": len(month_deals)
                })

        else:
            # Default: Show last 12 months (All Time)
            for i in range(11, -1, -1):
                # Calculate the month
                month_date = datetime(now.year, now.month, 1) - \
                    timedelta(days=30*i)
                month_name = calendar.month_abbr[month_date.month]

                # Filter deals closed in this month
                month_deals = self.repository.get_deals_by_month(
                    deals,
                    month_date.month,
                    month_date.year
                )

                won_month_deals = self.repository.get_won_deals(month_deals)
                actual = self.repository.calculate_total_value(won_month_deals)

                # Generate forecast (simple projection)
                forecast = actual * 1.1 if actual > 0 else 50000
                target = forecast * 0.9

                revenue_data.append({
                    "month": month_name,
                    "actual": int(actual),
                    "forecast": int(forecast),
                    "target": int(target),
                    "actualDealsCount": len(won_month_deals),
                    "totalDealsCount": len(month_deals)
                })

        return revenue_data

    def get_performance_metrics(
        self,
        *,
        filtered_query: Optional[Query] = None,
        date_range: Optional[str] = None,
        owner_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Get performance metrics.

        Args:
            filtered_query: Pre-filtered query (for permission filtering)
            date_range: Date range filter
            owner_id: Owner ID filter

        Returns:
            Dictionary with performance metrics
        """
        # Apply analytics filters
        query = self.repository.get_analytics_filtered_query(
            base_query=filtered_query,
            date_range=date_range,
            owner_id=owner_id
        )

        from sqlalchemy.orm import joinedload
        query = query.options(joinedload(Deal.company))

        deals = query.all()

        won_deals = self.repository.get_won_deals(deals)
        lost_deals = self.repository.get_lost_deals(deals)
        total_closed = len(won_deals) + len(lost_deals)

        achieved = self.repository.calculate_total_value(won_deals)
        # Assume quota is 30% higher than achieved
        quota = max(achieved * 1.3, 500000)
        avg_deal_size = achieved / len(won_deals) if won_deals else 0
        conversion_rate = round(
            (len(won_deals) / total_closed) * 100) if total_closed > 0 else 0

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

    def get_win_rate_data(
        self,
        *,
        filtered_query: Optional[Query] = None,
        date_range: Optional[str] = None,
        owner_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get win rate analytics data.

        Args:
            filtered_query: Pre-filtered query (for permission filtering)
            date_range: Optional date range filter
            owner_id: Optional owner ID filter

        Returns:
            List of quarterly win rate data with actual numbers
        """
        # Apply analytics filters
        query = self.repository.get_analytics_filtered_query(
            base_query=filtered_query,
            date_range=date_range,
            owner_id=owner_id
        )

        if query is not None:
            deals = query.all()
        else:
            deals = self.repository.get_all_with_relations(
                load_relations=False)

        # Get current year for quarterly analysis
        now = datetime.now()
        current_year = now.year

        # First, get all closed deals (won or lost) regardless of dates
        all_closed_deals = [
            deal for deal in deals
            if deal.stage and deal.stage.lower() in ['closed_won', 'closed-won', 'closed_lost', 'closed-lost']
        ]

        # If no closed deals at all, return empty quarters
        if not all_closed_deals:
            quarters = [
                {"period": "Q1", "start_month": 1, "end_month": 3},
                {"period": "Q2", "start_month": 4, "end_month": 6},
                {"period": "Q3", "start_month": 7, "end_month": 9},
                {"period": "Q4", "start_month": 10, "end_month": 12}
            ]
            return [
                {
                    "period": q["period"],
                    "winRate": 0,
                    "won": 0,
                    "lost": 0,
                    "total": 0
                }
                for q in quarters
            ]

        # Define quarters
        quarters = [
            {"period": "Q1", "start_month": 1, "end_month": 3},
            {"period": "Q2", "start_month": 4, "end_month": 6},
            {"period": "Q3", "start_month": 7, "end_month": 9},
            {"period": "Q4", "start_month": 10, "end_month": 12}
        ]

        win_rate_data = []

        for quarter_info in quarters:
            # Filter deals for this quarter
            quarter_deals = []
            for deal in all_closed_deals:
                # Determine which date to use for quarter assignment
                date_to_use = None

                if deal.actual_close_date:
                    date_to_use = deal.actual_close_date
                elif deal.expected_close_date:
                    date_to_use = deal.expected_close_date
                elif deal.updated_at:
                    date_to_use = deal.updated_at
                elif deal.created_at:
                    date_to_use = deal.created_at

                # Check if deal belongs to this quarter
                if date_to_use and date_to_use.year == current_year:
                    if quarter_info["start_month"] <= date_to_use.month <= quarter_info["end_month"]:
                        quarter_deals.append(deal)

            # Count won and lost deals (handle both formats: closed_won and closed-won)
            won_count = len([
                d for d in quarter_deals
                if d.stage and d.stage.lower() in ['closed_won', 'closed-won']
            ])
            lost_count = len([
                d for d in quarter_deals
                if d.stage and d.stage.lower() in ['closed_lost', 'closed-lost']
            ])
            total_count = won_count + lost_count

            # Calculate win rate
            win_rate = round((won_count / total_count) *
                             100) if total_count > 0 else 0

            win_rate_data.append({
                "period": quarter_info["period"],
                "winRate": win_rate,
                "won": won_count,
                "lost": lost_count,
                "total": total_count
            })

        return win_rate_data

    def get_filter_options(
        self,
        current_user: UserProfile
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        Get available filter options for analytics.

        Args:
            current_user: The authenticated user

        Returns:
            Dictionary with available filter options
        """
        # Get available sales reps (users who own deals)
        if current_user.role in ['admin', 'sales_manager']:
            # Admin and managers can see all users
            users_query = self.db.query(
                UserProfile.id,
                UserProfile.first_name,
                UserProfile.last_name,
                UserProfile.role
            ).distinct()
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
        industries = self.repository.get_distinct_industries()

        industry_options = [
            {"value": industry, "label": industry}
            for industry in sorted(industries)
        ]

        return {
            "reps": reps,
            "industries": industry_options,
            "dateRanges": [
                {"value": "all", "label": "All Time"},
                {"value": "thisquarter", "label": "This Quarter"},
                {"value": "lastquarter", "label": "Last Quarter"},
                {"value": "thisyear", "label": "This Year"},
                {"value": "lastyear", "label": "Last Year"}
            ]
        }

    def create_deal(
        self,
        deal_data: DealCreate,
        current_user: UserProfile
    ) -> DealResponse:
        """
        Create a new deal.

        Args:
            deal_data: Deal creation data
            current_user: The user creating the deal

        Returns:
            The created deal with custom fields

        Raises:
            Exception: If creation fails
        """
        try:
            # Import system config service
            from services.system_config_service_new import SystemConfigService
            config_service = SystemConfigService(self.db)

            # Extract custom fields
            custom_fields_data = deal_data.custom_fields or {}

            # Prepare deal data for creation
            deal_dict = deal_data.dict(exclude={'custom_fields'})
            deal_dict['owner_id'] = current_user.id

            # Check if deal value is required by system configuration
            require_value = config_service.get_configuration_value(
                'sales.require_deal_value',
                default=False
            )
            if require_value and (deal_dict.get('value') is None or deal_dict.get('value') <= 0):
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=400,
                    detail="Deal value is required by system configuration"
                )

            # If no stage provided, use default from system configuration
            if not deal_dict.get('stage'):
                default_stage = config_service.get_configuration_value(
                    'sales.default_pipeline_stage',
                    default='lead'
                )
                deal_dict['stage'] = default_stage

            # Create deal via repository
            db_deal = self.repository.create(obj_in=deal_dict)

            # Save custom field values if provided
            if custom_fields_data:
                CustomFieldService.save_custom_field_values(
                    db=self.db,
                    entity_id=str(db_deal.id),
                    entity_type=EntityType.DEAL,
                    field_values=custom_fields_data
                )

            # Commit the transaction
            self.db.commit()
            self.db.refresh(db_deal)

            return self._build_deal_response(db_deal)

        except Exception as e:
            self.db.rollback()
            raise e

    def update_deal(
        self,
        deal_id: UUID,
        deal_data: DealUpdate
    ) -> Optional[DealResponse]:
        """
        Update an existing deal.

        Args:
            deal_id: UUID of the deal to update
            deal_data: Deal update data

        Returns:
            The updated deal, or None if not found

        Raises:
            Exception: If update fails
        """
        try:
            # Get existing deal
            db_deal = self.repository.get(deal_id)

            if not db_deal:
                return None

            # Extract custom fields
            update_dict = deal_data.dict(exclude_unset=True)
            custom_fields_data = update_dict.pop('custom_fields', None)

            # Check if deal value is required when updating value field
            if 'value' in update_dict:
                from services.system_config_service_new import SystemConfigService
                config_service = SystemConfigService(self.db)
                require_value = config_service.get_configuration_value(
                    'sales.require_deal_value',
                    default=False
                )
                if require_value and (update_dict.get('value') is None or update_dict.get('value') <= 0):
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=400,
                        detail="Deal value is required by system configuration"
                    )

            # Update deal fields
            if update_dict:
                db_deal = self.repository.update(
                    db_obj=db_deal,
                    obj_in=update_dict
                )

            # Update custom field values if provided
            if custom_fields_data is not None:
                CustomFieldService.save_custom_field_values(
                    db=self.db,
                    entity_id=str(db_deal.id),
                    entity_type=EntityType.DEAL,
                    field_values=custom_fields_data
                )

            # Commit the transaction
            self.db.commit()
            self.db.refresh(db_deal)

            return self._build_deal_response(db_deal)

        except Exception as e:
            self.db.rollback()
            raise e

    def delete_deal(self, deal_id: UUID) -> bool:
        """
        Delete a deal.

        Args:
            deal_id: UUID of the deal to delete

        Returns:
            True if deletion was successful, False if deal not found

        Raises:
            Exception: If deletion fails
        """
        try:
            result = self.repository.delete(id=deal_id)

            if result:
                self.db.commit()

            return result

        except Exception as e:
            self.db.rollback()
            raise e

    def _build_deal_response(
        self,
        deal: Deal,
        include_custom_fields: bool = True
    ) -> DealResponse:
        """
        Build a deal response with custom fields.

        Args:
            deal: The deal database object
            include_custom_fields: Whether to include custom fields

        Returns:
            Deal response schema
        """
        # Get custom fields
        custom_fields_dict = None
        if include_custom_fields:
            custom_fields_dict = CustomFieldService.get_entity_custom_fields_dict(
                db=self.db,
                entity_id=str(deal.id),
                entity_type=EntityType.DEAL
            )

        return DealResponse(
            id=deal.id,
            name=deal.name,
            value=float(deal.value) if deal.value is not None else None,
            stage=deal.stage,
            probability=deal.probability,
            expected_close_date=deal.expected_close_date,
            description=deal.description,
            source=deal.source,
            next_action=deal.next_action,
            company_id=deal.company_id,
            contact_id=deal.contact_id,
            owner_id=deal.owner_id,
            actual_close_date=deal.actual_close_date,
            lost_reason=deal.lost_reason,
            created_at=deal.created_at,
            updated_at=deal.updated_at,
            custom_fields=custom_fields_dict
        )

    def _build_deal_response_with_relations(
        self,
        deal: Deal,
        include_custom_fields: bool = True
    ) -> DealWithRelations:
        """
        Build a deal response with relations and custom fields.

        Args:
            deal: The deal database object
            include_custom_fields: Whether to include custom fields

        Returns:
            Deal response schema with relations
        """
        # Get custom fields
        custom_fields_dict = None
        if include_custom_fields:
            custom_fields_dict = CustomFieldService.get_entity_custom_fields_dict(
                db=self.db,
                entity_id=str(deal.id),
                entity_type=EntityType.DEAL
            )

        # Serialize owner properly
        owner_data = None
        if deal.owner:
            owner_data = UserResponse(
                id=deal.owner.id,
                email=deal.owner.email,
                first_name=deal.owner.first_name,
                last_name=deal.owner.last_name,
                avatar_url=deal.owner.avatar_url,
                is_active=deal.owner.is_active,
                created_at=deal.owner.created_at,
                updated_at=deal.owner.updated_at,
                role=deal.owner.role if hasattr(deal.owner, 'role') else None,
                phone=deal.owner.phone if hasattr(
                    deal.owner, 'phone') else None
            )

        # Serialize contact properly
        contact_data = None
        if deal.contact:
            contact_data = ContactResponse(
                id=deal.contact.id,
                first_name=deal.contact.first_name,
                last_name=deal.contact.last_name,
                email=deal.contact.email,
                phone=deal.contact.phone,
                mobile=deal.contact.mobile,
                position=deal.contact.position,
                status=deal.contact.status,
                notes=deal.contact.notes,
                social_linkedin=deal.contact.social_linkedin,
                social_twitter=deal.contact.social_twitter,
                company_id=deal.contact.company_id,
                owner_id=deal.contact.owner_id,
                created_at=deal.contact.created_at,
                updated_at=deal.contact.updated_at,
                custom_fields=None  # Don't load custom fields for nested objects
            )

        # Serialize company properly using CompanyBasicResponse to avoid circular refs
        company_data = None
        if deal.company:
            company_data = CompanyBasicResponse(
                id=deal.company.id,
                name=deal.company.name,
                industry=deal.company.industry,
                size=deal.company.size,
                website=deal.company.website,
                phone=deal.company.phone,
                email=deal.company.email,
                address=deal.company.address,
                city=deal.company.city,
                state=deal.company.state,
                zip_code=deal.company.zip_code,
                country=deal.company.country,
                description=deal.company.description,
                revenue=deal.company.revenue,
                created_at=deal.company.created_at,
                updated_at=deal.company.updated_at
            )

        return DealWithRelations(
            id=deal.id,
            name=deal.name,
            value=deal.value,
            stage=deal.stage,
            probability=deal.probability,
            expected_close_date=deal.expected_close_date,
            description=deal.description,
            source=deal.source,
            next_action=deal.next_action,
            company_id=deal.company_id,
            contact_id=deal.contact_id,
            owner_id=deal.owner_id,
            actual_close_date=deal.actual_close_date,
            lost_reason=deal.lost_reason,
            created_at=deal.created_at,
            updated_at=deal.updated_at,
            custom_fields=custom_fields_dict,
            owner=owner_data,
            contact=contact_data,
            company=company_data
        )

    def get_inactive_deals(
        self,
        current_user: Optional[UserProfile] = None
    ) -> List[DealResponse]:
        """
        Get deals that have been inactive (no updates) for the warning period
        defined in system configuration.

        Args:
            current_user: Optional user to filter deals (if provided, only return deals owned by this user)

        Returns:
            List[DealResponse]: List of inactive deals
        """
        from services.system_config_service_new import SystemConfigService

        # Get inactivity warning threshold from system configuration
        config_service = SystemConfigService(self.db)
        warning_days = config_service.get_configuration_value(
            'sales.deal_inactivity_warning_days',
            default=30
        )

        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=warning_days)

        # Build query for inactive deals
        query = self.db.query(Deal).filter(
            Deal.updated_at < cutoff_date,
            Deal.stage.notin_(['closed_won', 'closed_lost', 'won', 'lost'])  # Exclude closed deals
        )

        # Filter by user if provided
        if current_user:
            query = query.filter(Deal.owner_id == current_user.id)

        # Get inactive deals
        inactive_deals = query.all()

        # Build response with full deal details
        return [self._build_deal_response(deal) for deal in inactive_deals]
