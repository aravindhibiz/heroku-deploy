"""
Deal repository for data access operations.
Handles all database queries and relationships for deals.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, Query, joinedload
from sqlalchemy import and_, or_, func

from .base_repository import BaseRepository
from ..models.deal import Deal
from ..models.company import Company


class DealRepository(BaseRepository[Deal]):
    """
    Repository for Deal data access.

    Extends BaseRepository with deal-specific queries including
    pipeline management, analytics, and complex filtering.
    """

    def __init__(self, db: Session):
        """
        Initialize deal repository.

        Args:
            db: Database session
        """
        super().__init__(Deal, db)

    def get_with_relations(self, deal_id: UUID) -> Optional[Deal]:
        """
        Get a deal with all its relationships loaded.

        Args:
            deal_id: UUID of the deal

        Returns:
            Deal with relations, or None if not found
        """
        return self.db.query(self.model).options(
            joinedload(Deal.company),
            joinedload(Deal.contact),
            joinedload(Deal.owner),
            joinedload(Deal.activities),
            joinedload(Deal.documents)
        ).filter(Deal.id == deal_id).first()

    def get_all_with_relations(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        load_relations: bool = True
    ) -> List[Deal]:
        """
        Get all deals with optional relations.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            load_relations: Whether to load company, contact, owner

        Returns:
            List of deals
        """
        query = self.db.query(self.model)

        if load_relations:
            query = query.options(
                joinedload(Deal.company),
                joinedload(Deal.contact),
                joinedload(Deal.owner)
            )

        return query.order_by(Deal.updated_at.desc()).offset(skip).limit(limit).all()

    def get_by_owner(
        self,
        owner_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[Deal]:
        """
        Get deals by owner.

        Args:
            owner_id: UUID of the owner
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of deals owned by the user
        """
        return self.db.query(self.model).options(
            joinedload(Deal.company),
            joinedload(Deal.contact),
            joinedload(Deal.owner)
        ).filter(
            Deal.owner_id == owner_id
        ).order_by(Deal.updated_at.desc()).offset(skip).limit(limit).all()

    def get_by_stage(self, stage: str) -> List[Deal]:
        """
        Get deals by stage.

        Args:
            stage: Deal stage (lead, qualified, proposal, etc.)

        Returns:
            List of deals in the stage
        """
        return self.db.query(self.model).options(
            joinedload(Deal.company),
            joinedload(Deal.contact),
            joinedload(Deal.owner)
        ).filter(Deal.stage == stage).order_by(Deal.updated_at.desc()).all()

    def get_by_company(self, company_id: UUID) -> List[Deal]:
        """
        Get all deals for a company.

        Args:
            company_id: UUID of the company

        Returns:
            List of deals for the company
        """
        return self.db.query(self.model).options(
            joinedload(Deal.contact),
            joinedload(Deal.owner)
        ).filter(Deal.company_id == company_id).all()

    def get_by_contact(self, contact_id: UUID) -> List[Deal]:
        """
        Get all deals for a contact.

        Args:
            contact_id: UUID of the contact

        Returns:
            List of deals for the contact
        """
        return self.db.query(self.model).options(
            joinedload(Deal.company),
            joinedload(Deal.owner)
        ).filter(Deal.contact_id == contact_id).all()

    def get_filtered_query(
        self,
        base_query: Optional[Query] = None,
        *,
        date_range: Optional[str] = None,
        probability_range: Optional[str] = None,
        stage: Optional[str] = None,
        owner_id: Optional[UUID] = None
    ) -> Query:
        """
        Build a filtered query for deals.

        Args:
            base_query: Optional base query to build on
            date_range: Date range filter (thisWeek, thisMonth, thisQuarter, thisYear)
            probability_range: Probability range (high, medium, low)
            stage: Deal stage filter
            owner_id: Owner ID filter

        Returns:
            Filtered query
        """
        query = base_query if base_query is not None else self.db.query(
            self.model)

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
                query = query.filter(
                    and_(Deal.probability >= 30, Deal.probability <= 70)
                )
            elif probability_range == "low":
                query = query.filter(Deal.probability < 30)

        # Stage filtering
        if stage:
            query = query.filter(Deal.stage == stage)

        # Owner filtering
        if owner_id:
            query = query.filter(Deal.owner_id == owner_id)

        return query

    def get_pipeline_filtered_query(
        self,
        base_query: Optional[Query] = None,
        *,
        date_range: Optional[str] = None,
        owner_id: Optional[UUID] = None
    ) -> Query:
        """
        Build a filtered query for pipeline deals (uses created_at for date filtering).

        Args:
            base_query: Optional base query to build on
            date_range: Date range filter (thisquarter, thisyear, lastyear)
            owner_id: Owner ID filter

        Returns:
            Filtered query
        """
        query = base_query if base_query is not None else self.db.query(
            self.model)

        # Apply date range filter on created_at (for pipeline view)
        if date_range:
            now = datetime.now()

            if date_range == 'thisquarter':
                current_quarter = (now.month - 1) // 3 + 1
                quarter_start = datetime(
                    now.year, (current_quarter - 1) * 3 + 1, 1)
                query = query.filter(Deal.created_at >= quarter_start)
            elif date_range == 'lastquarter':
                current_quarter = (now.month - 1) // 3 + 1
                last_quarter = current_quarter - 1 if current_quarter > 1 else 4
                last_quarter_year = now.year if current_quarter > 1 else now.year - 1
                quarter_start = datetime(
                    last_quarter_year, (last_quarter - 1) * 3 + 1, 1)
                quarter_end = datetime(
                    now.year if current_quarter > 1 else now.year, (current_quarter - 1) * 3 + 1, 1)
                query = query.filter(
                    and_(
                        Deal.created_at >= quarter_start,
                        Deal.created_at < quarter_end
                    )
                )
            elif date_range == 'thisyear':
                year_start = datetime(now.year, 1, 1)
                query = query.filter(Deal.created_at >= year_start)
            elif date_range == 'lastyear':
                year_start = datetime(now.year - 1, 1, 1)
                year_end = datetime(now.year, 1, 1)
                query = query.filter(
                    and_(
                        Deal.created_at >= year_start,
                        Deal.created_at < year_end
                    )
                )

        # Owner filtering
        if owner_id:
            query = query.filter(Deal.owner_id == owner_id)

        return query

    def get_analytics_filtered_query(
        self,
        base_query: Optional[Query] = None,
        *,
        date_range: Optional[str] = None,
        owner_id: Optional[UUID] = None
    ) -> Query:
        """
        Build a filtered query for analytics endpoints.

        Args:
            base_query: Optional base query to build on
            date_range: Date range filter (last7days, last30days, last90days, thisquarter, lastyear)
            owner_id: Owner ID filter

        Returns:
            Filtered query
        """
        query = base_query if base_query is not None else self.db.query(
            self.model)

        # Apply date range filter
        if date_range:
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
            elif date_range == 'lastquarter':
                current_quarter = (now.month - 1) // 3 + 1
                last_quarter = current_quarter - 1 if current_quarter > 1 else 4
                last_quarter_year = now.year if current_quarter > 1 else now.year - 1
                quarter_start = datetime(
                    last_quarter_year, (last_quarter - 1) * 3 + 1, 1)
                quarter_end = datetime(
                    now.year if current_quarter > 1 else now.year, (current_quarter - 1) * 3 + 1, 1)
                query = query.filter(
                    and_(
                        Deal.actual_close_date >= quarter_start,
                        Deal.actual_close_date < quarter_end
                    )
                )
            elif date_range == 'thisyear':
                year_start = datetime(now.year, 1, 1)
                query = query.filter(Deal.actual_close_date >= year_start)
            elif date_range == 'lastyear':
                year_start = datetime(now.year - 1, 1, 1)
                year_end = datetime(now.year, 1, 1)
                query = query.filter(
                    and_(
                        Deal.actual_close_date >= year_start,
                        Deal.actual_close_date < year_end
                    )
                )

        # Owner filtering
        if owner_id:
            query = query.filter(Deal.owner_id == owner_id)

        return query

    def get_pipeline_grouped_by_stage(
        self,
        deals: List[Deal]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Group deals by stage for pipeline view.

        Args:
            deals: List of deals to group

        Returns:
            Dictionary with stages as keys and deal groups as values
        """
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
                    'avatar': f'https://ui-avatars.com/api/?name={deal.contact.first_name[0] if deal.contact and deal.contact.first_name else "U"}+{deal.contact.last_name[0] if deal.contact and deal.contact.last_name else "C"}&background=random' if deal.contact else 'https://ui-avatars.com/api/?name=U+C&background=random',
                    'expected_close_date': deal.expected_close_date.isoformat() if deal.expected_close_date else None
                })

        return pipeline_data

    def get_won_deals(self, deals: List[Deal]) -> List[Deal]:
        """Get deals that are closed won."""
        return [deal for deal in deals if deal.stage == 'closed_won']

    def get_lost_deals(self, deals: List[Deal]) -> List[Deal]:
        """Get deals that are closed lost."""
        return [deal for deal in deals if deal.stage == 'closed_lost']

    def get_active_deals(self, deals: List[Deal]) -> List[Deal]:
        """Get deals that are not closed."""
        return [deal for deal in deals if deal.stage not in ['closed_won', 'closed_lost']]

    def calculate_total_value(self, deals: List[Deal]) -> float:
        """Calculate total value of deals."""
        return sum([float(deal.value or 0) for deal in deals])

    def get_deals_by_month(
        self,
        deals: List[Deal],
        month: int,
        year: int
    ) -> List[Deal]:
        """
        Get deals closed in a specific month.

        Args:
            deals: List of deals to filter
            month: Month number (1-12)
            year: Year

        Returns:
            List of deals closed in the month
        """
        return [
            deal for deal in deals
            if deal.actual_close_date and
            deal.actual_close_date.month == month and
            deal.actual_close_date.year == year
        ]

    def count_by_stage(self) -> Dict[str, int]:
        """
        Count deals by stage.

        Returns:
            Dictionary with stage counts
        """
        results = self.db.query(
            Deal.stage,
            func.count(Deal.id).label('count')
        ).group_by(Deal.stage).all()

        return {result.stage: result.count for result in results}

    def get_distinct_industries(self) -> List[str]:
        """
        Get distinct industries from companies associated with deals.

        Returns:
            List of industry names
        """
        results = self.db.query(Company.industry).join(
            Deal, Deal.company_id == Company.id
        ).filter(
            Company.industry.isnot(None)
        ).distinct().all()

        return [industry[0] for industry in results if industry[0]]
