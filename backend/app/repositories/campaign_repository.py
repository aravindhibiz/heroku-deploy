"""
Campaign repository for database operations.
"""

from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, desc
from decimal import Decimal

from app.models.campaign import Campaign, CampaignStatus, CampaignType
from app.models.campaign_contact import CampaignContact, EngagementStatus
from app.models.prospect import Prospect
from app.models.deal import Deal
from app.repositories.base_repository import BaseRepository


class CampaignRepository(BaseRepository[Campaign]):
    """Repository for Campaign database operations."""

    def __init__(self, db: Session):
        super().__init__(Campaign, db)

    def get_by_owner(
        self,
        owner_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Campaign]:
        """Get campaigns owned by a specific user."""
        return self.db.query(Campaign)\
            .filter(Campaign.owner_id == owner_id)\
            .order_by(desc(Campaign.created_at))\
            .offset(skip)\
            .limit(limit)\
            .all()

    def get_by_status(
        self,
        status: List[CampaignStatus],
        skip: int = 0,
        limit: int = 100
    ) -> List[Campaign]:
        """Get campaigns by status."""
        return self.db.query(Campaign)\
            .filter(Campaign.status.in_(status))\
            .order_by(desc(Campaign.created_at))\
            .offset(skip)\
            .limit(limit)\
            .all()

    def get_active_campaigns(self) -> List[Campaign]:
        """Get all active campaigns."""
        return self.db.query(Campaign)\
            .filter(Campaign.status == CampaignStatus.ACTIVE)\
            .order_by(desc(Campaign.created_at))\
            .all()

    def search(
        self,
        search_term: str,
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Campaign], int]:
        """
        Search campaigns by name or description.

        Args:
            search_term: Text to search for
            filters: Additional filters (status, type, owner_id, etc.)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of campaigns, total count)
        """
        query = self.db.query(Campaign)

        # Search in name and description
        if search_term:
            search_filter = or_(
                Campaign.name.ilike(f"%{search_term}%"),
                Campaign.description.ilike(f"%{search_term}%")
            )
            query = query.filter(search_filter)

        # Apply additional filters
        if filters:
            if 'status' in filters and filters['status']:
                if isinstance(filters['status'], list):
                    query = query.filter(Campaign.status.in_(filters['status']))
                else:
                    query = query.filter(Campaign.status == filters['status'])

            if 'type' in filters and filters['type']:
                if isinstance(filters['type'], list):
                    query = query.filter(Campaign.type.in_(filters['type']))
                else:
                    query = query.filter(Campaign.type == filters['type'])

            if 'owner_id' in filters and filters['owner_id']:
                query = query.filter(Campaign.owner_id == filters['owner_id'])

            if 'category' in filters and filters['category']:
                query = query.filter(Campaign.category == filters['category'])

            if 'tags' in filters and filters['tags']:
                # Filter by tags (JSONB contains)
                for tag in filters['tags']:
                    query = query.filter(Campaign.tags.contains([tag]))

            if 'start_date_after' in filters and filters['start_date_after']:
                query = query.filter(Campaign.start_date >= filters['start_date_after'])

            if 'start_date_before' in filters and filters['start_date_before']:
                query = query.filter(Campaign.start_date <= filters['start_date_before'])

            if 'end_date_after' in filters and filters['end_date_after']:
                query = query.filter(Campaign.end_date >= filters['end_date_after'])

            if 'end_date_before' in filters and filters['end_date_before']:
                query = query.filter(Campaign.end_date <= filters['end_date_before'])

            if 'min_budget' in filters and filters['min_budget'] is not None:
                query = query.filter(Campaign.budget >= filters['min_budget'])

            if 'max_budget' in filters and filters['max_budget'] is not None:
                query = query.filter(Campaign.budget <= filters['max_budget'])

        # Get total count before pagination
        total = query.count()

        # Apply pagination and ordering
        campaigns = query.order_by(desc(Campaign.created_at)).offset(skip).limit(limit).all()

        return campaigns, total

    def get_statistics(self, owner_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        Get campaign statistics.

        Args:
            owner_id: Optional owner ID to filter by

        Returns:
            Dictionary with statistics
        """
        query = self.db.query(Campaign)

        if owner_id:
            query = query.filter(Campaign.owner_id == owner_id)

        total = query.count()
        draft = query.filter(Campaign.status == CampaignStatus.DRAFT).count()
        active = query.filter(Campaign.status == CampaignStatus.ACTIVE).count()
        completed = query.filter(Campaign.status == CampaignStatus.COMPLETED).count()

        # Financial aggregates
        budget_result = query.with_entities(func.sum(Campaign.budget)).scalar()
        total_budget = float(budget_result) if budget_result else 0.0

        spent_result = query.with_entities(func.sum(Campaign.actual_cost)).scalar()
        total_spent = float(spent_result) if spent_result else 0.0

        revenue_result = query.with_entities(func.sum(Campaign.actual_revenue)).scalar()
        total_revenue = float(revenue_result) if revenue_result else 0.0

        # Calculate overall ROI
        overall_roi = ((total_revenue - total_spent) / total_spent * 100) if total_spent > 0 else 0.0

        # Prospect and conversion totals
        prospects_result = query.with_entities(func.sum(Campaign.prospects_generated)).scalar()
        total_prospects = int(prospects_result) if prospects_result else 0

        conversions_result = query.with_entities(func.sum(Campaign.converted_count)).scalar()
        total_conversions = int(conversions_result) if conversions_result else 0

        # Calculate average conversion rate
        delivered_result = query.with_entities(func.sum(Campaign.delivered_count)).scalar()
        total_delivered = int(delivered_result) if delivered_result else 0
        avg_conversion_rate = (total_conversions / total_delivered * 100) if total_delivered > 0 else 0.0

        return {
            "total_campaigns": total,
            "draft_campaigns": draft,
            "active_campaigns": active,
            "completed_campaigns": completed,
            "total_budget": round(total_budget, 2),
            "total_spent": round(total_spent, 2),
            "total_revenue": round(total_revenue, 2),
            "overall_roi": round(overall_roi, 2),
            "total_prospects": total_prospects,
            "total_conversions": total_conversions,
            "average_conversion_rate": round(avg_conversion_rate, 2)
        }

    def update_metrics(self, campaign_id: UUID) -> Optional[Campaign]:
        """
        Recalculate and update campaign metrics from campaign_contacts.

        Args:
            campaign_id: Campaign UUID

        Returns:
            Updated campaign or None if not found
        """
        campaign = self.get(campaign_id)
        if not campaign:
            return None

        # Query campaign_contacts for this campaign
        contacts = self.db.query(CampaignContact)\
            .filter(CampaignContact.campaign_id == campaign_id)\
            .all()

        # Calculate metrics
        sent = len([c for c in contacts if c.sent_at is not None])
        delivered = len([c for c in contacts if c.delivered_at is not None])
        opened = len([c for c in contacts if c.opened_at is not None])
        clicked = len([c for c in contacts if c.clicked_at is not None])
        responded = len([c for c in contacts if c.responded_at is not None])
        bounced = len([c for c in contacts if c.status == EngagementStatus.BOUNCED])
        unsubscribed = len([c for c in contacts if c.status == EngagementStatus.UNSUBSCRIBED])
        converted = len([c for c in contacts if c.converted_at is not None])

        # Update campaign
        campaign.sent_count = sent
        campaign.delivered_count = delivered
        campaign.opened_count = opened
        campaign.clicked_count = clicked
        campaign.responded_count = responded
        campaign.bounced_count = bounced
        campaign.unsubscribed_count = unsubscribed
        campaign.converted_count = converted

        # Count prospects generated
        prospects_count = self.db.query(Prospect)\
            .filter(Prospect.campaign_id == campaign_id)\
            .count()
        campaign.prospects_generated = prospects_count

        # Calculate actual revenue from converted deals
        revenue_result = self.db.query(func.sum(CampaignContact.conversion_value))\
            .filter(CampaignContact.campaign_id == campaign_id)\
            .filter(CampaignContact.converted_at.isnot(None))\
            .scalar()
        campaign.actual_revenue = Decimal(str(revenue_result)) if revenue_result else Decimal("0.00")

        self.db.commit()
        self.db.refresh(campaign)

        return campaign

    def get_conversions(self, campaign_id: UUID) -> List[Dict[str, Any]]:
        """
        Get all deals/conversions from a campaign.

        Args:
            campaign_id: Campaign UUID

        Returns:
            List of conversion data with contact and company details
        """
        from app.models.contact import Contact
        from app.models.company import Company

        conversions = self.db.query(CampaignContact, Deal, Contact, Company)\
            .join(Deal, CampaignContact.deal_id == Deal.id)\
            .outerjoin(Contact, Deal.contact_id == Contact.id)\
            .outerjoin(Company, Contact.company_id == Company.id)\
            .filter(CampaignContact.campaign_id == campaign_id)\
            .filter(CampaignContact.converted_at.isnot(None))\
            .all()

        result = []
        for cc, deal, contact, company in conversions:
            conversion_data = {
                "deal_id": deal.id,
                "deal_name": deal.name,
                "deal_value": deal.value,
                "deal_stage": deal.stage,
                "contact_id": cc.contact_id,
                "prospect_id": cc.prospect_id,
                "converted_at": cc.converted_at,
                "conversion_value": cc.conversion_value
            }

            # Add contact information if available
            if contact:
                conversion_data["contact_name"] = f"{contact.first_name} {contact.last_name}"
                conversion_data["contact_email"] = contact.email

            # Add company information if available
            if company:
                conversion_data["company_name"] = company.name
                conversion_data["company_id"] = company.id

            result.append(conversion_data)

        return result

    def get_performance_timeline(
        self,
        campaign_id: UUID,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get daily performance metrics for a campaign.

        Args:
            campaign_id: Campaign UUID
            days: Number of days to look back

        Returns:
            List of daily metrics
        """
        from app.models.campaign_metric import CampaignMetric

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        metrics = self.db.query(CampaignMetric)\
            .filter(CampaignMetric.campaign_id == campaign_id)\
            .filter(CampaignMetric.recorded_at >= cutoff_date)\
            .filter(CampaignMetric.period_type == "daily")\
            .order_by(CampaignMetric.recorded_at)\
            .all()

        return [
            {
                "date": m.recorded_at,
                "sent": m.sent_count,
                "delivered": m.delivered_count,
                "opened": m.opened_count,
                "clicked": m.clicked_count,
                "converted": m.converted_count,
                "open_rate": float(m.open_rate),
                "click_rate": float(m.click_rate),
                "conversion_rate": float(m.conversion_rate)
            }
            for m in metrics
        ]

    def get_top_performers(
        self,
        campaign_id: UUID,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top performing contacts/prospects from a campaign.

        Args:
            campaign_id: Campaign UUID
            limit: Number of top performers to return

        Returns:
            List of top performers with engagement scores
        """
        performers = self.db.query(CampaignContact)\
            .filter(CampaignContact.campaign_id == campaign_id)\
            .order_by(desc(CampaignContact.open_count + CampaignContact.click_count * 2))\
            .limit(limit)\
            .all()

        result = []
        for cc in performers:
            if cc.contact:
                result.append({
                    "type": "contact",
                    "id": cc.contact_id,
                    "name": f"{cc.contact.first_name} {cc.contact.last_name}",
                    "email": cc.contact.email,
                    "engagement_score": cc.engagement_score,
                    "opens": cc.open_count,
                    "clicks": cc.click_count,
                    "converted": cc.was_converted
                })
            elif cc.prospect:
                result.append({
                    "type": "prospect",
                    "id": cc.prospect_id,
                    "name": f"{cc.prospect.first_name} {cc.prospect.last_name}",
                    "email": cc.prospect.email,
                    "engagement_score": cc.engagement_score,
                    "opens": cc.open_count,
                    "clicks": cc.click_count,
                    "converted": cc.was_converted
                })

        return result

    def mark_as_executed(self, campaign_id: UUID) -> Optional[Campaign]:
        """
        Mark campaign as executed (update last_executed_at timestamp).

        Args:
            campaign_id: Campaign UUID

        Returns:
            Updated campaign or None if not found
        """
        campaign = self.get(campaign_id)
        if not campaign:
            return None

        campaign.last_executed_at = datetime.utcnow()

        # Set actual start date if not set
        if not campaign.actual_start_date:
            campaign.actual_start_date = datetime.utcnow()

        # Change status from scheduled to active
        if campaign.status == CampaignStatus.SCHEDULED:
            campaign.status = CampaignStatus.ACTIVE

        self.db.commit()
        self.db.refresh(campaign)

        return campaign
