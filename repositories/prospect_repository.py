"""
Prospect repository for database operations.
"""

from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, desc
from sqlalchemy.exc import IntegrityError

from app.models.prospect import Prospect, ProspectStatus, ProspectSource
from app.models.campaign_contact import CampaignContact
from app.repositories.base_repository import BaseRepository


class ProspectRepository(BaseRepository[Prospect]):
    """Repository for Prospect database operations."""

    def __init__(self, db: Session):
        super().__init__(Prospect, db)

    def check_duplicate(self, email: str = None, phone: str = None, exclude_id: UUID = None) -> Optional[Prospect]:
        """
        Check if a prospect with the given email or phone already exists.

        Args:
            email: Email to check for duplicates
            phone: Phone to check for duplicates
            exclude_id: Optional prospect ID to exclude from check (for updates)

        Returns:
            Existing prospect if found, None otherwise
        """
        if not email and not phone:
            return None

        query = self.db.query(Prospect)

        # Build OR conditions for email or phone match
        conditions = []
        if email:
            conditions.append(Prospect.email == email)
        if phone:
            conditions.append(Prospect.phone == phone)

        query = query.filter(or_(*conditions))

        # Exclude specific ID if provided (for update operations)
        if exclude_id:
            query = query.filter(Prospect.id != exclude_id)

        return query.first()

    def get_by_email(self, email: str) -> Optional[Prospect]:
        """Get prospect by email address."""
        return self.db.query(Prospect).filter(Prospect.email == email).first()

    def get_by_phone(self, phone: str) -> Optional[Prospect]:
        """Get prospect by phone number."""
        return self.db.query(Prospect).filter(Prospect.phone == phone).first()

    def get_by_campaign(
        self,
        campaign_id: UUID,
        status: Optional[List[ProspectStatus]] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Prospect]:
        """
        Get prospects associated with a specific campaign.

        Args:
            campaign_id: Campaign UUID
            status: Optional list of statuses to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of prospects
        """
        query = self.db.query(Prospect).filter(Prospect.campaign_id == campaign_id)

        if status:
            query = query.filter(Prospect.status.in_(status))

        return query.order_by(desc(Prospect.created_at)).offset(skip).limit(limit).all()

    def get_by_status(
        self,
        status: List[ProspectStatus],
        skip: int = 0,
        limit: int = 100
    ) -> List[Prospect]:
        """Get prospects by status."""
        return self.db.query(Prospect)\
            .filter(Prospect.status.in_(status))\
            .order_by(desc(Prospect.created_at))\
            .offset(skip)\
            .limit(limit)\
            .all()

    def get_recent(self, days: int = 7, limit: int = 10) -> List[Prospect]:
        """
        Get recently created prospects.

        Args:
            days: Number of days to look back
            limit: Maximum number of records to return

        Returns:
            List of recent prospects
        """
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        return self.db.query(Prospect)\
            .filter(Prospect.created_at >= cutoff_date)\
            .order_by(desc(Prospect.created_at))\
            .limit(limit)\
            .all()

    def search(
        self,
        search_term: str,
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Prospect], int]:
        """
        Search prospects by name, email, or company.

        Args:
            search_term: Text to search for
            filters: Additional filters (status, source, campaign_id, etc.)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of prospects, total count)
        """
        query = self.db.query(Prospect)

        # Search in name, email, company
        if search_term:
            search_filter = or_(
                Prospect.first_name.ilike(f"%{search_term}%"),
                Prospect.last_name.ilike(f"%{search_term}%"),
                Prospect.email.ilike(f"%{search_term}%"),
                Prospect.company_name.ilike(f"%{search_term}%")
            )
            query = query.filter(search_filter)

        # Apply additional filters
        if filters:
            if 'status' in filters and filters['status']:
                if isinstance(filters['status'], list):
                    query = query.filter(Prospect.status.in_(filters['status']))
                else:
                    query = query.filter(Prospect.status == filters['status'])

            if 'source' in filters and filters['source']:
                if isinstance(filters['source'], list):
                    query = query.filter(Prospect.source.in_(filters['source']))
                else:
                    query = query.filter(Prospect.source == filters['source'])

            if 'campaign_id' in filters and filters['campaign_id']:
                query = query.filter(Prospect.campaign_id == filters['campaign_id'])

            if 'assigned_to' in filters and filters['assigned_to']:
                query = query.filter(Prospect.assigned_to == filters['assigned_to'])

            if 'min_lead_score' in filters and filters['min_lead_score'] is not None:
                query = query.filter(Prospect.lead_score >= filters['min_lead_score'])

            if 'max_lead_score' in filters and filters['max_lead_score'] is not None:
                query = query.filter(Prospect.lead_score <= filters['max_lead_score'])

            if 'created_after' in filters and filters['created_after']:
                query = query.filter(Prospect.created_at >= filters['created_after'])

            if 'created_before' in filters and filters['created_before']:
                query = query.filter(Prospect.created_at <= filters['created_before'])

        # Get total count before pagination
        total = query.count()

        # Apply pagination and ordering
        prospects = query.order_by(desc(Prospect.created_at)).offset(skip).limit(limit).all()

        return prospects, total

    def get_statistics(self, campaign_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        Get prospect statistics.

        Args:
            campaign_id: Optional campaign ID to filter by

        Returns:
            Dictionary with statistics
        """
        query = self.db.query(Prospect)

        if campaign_id:
            query = query.filter(Prospect.campaign_id == campaign_id)

        total = query.count()
        new = query.filter(Prospect.status == ProspectStatus.NEW).count()
        contacted = query.filter(Prospect.status == ProspectStatus.CONTACTED).count()
        qualified = query.filter(Prospect.status == ProspectStatus.QUALIFIED).count()
        converted = query.filter(Prospect.status == ProspectStatus.CONVERTED).count()
        rejected = query.filter(Prospect.status == ProspectStatus.REJECTED).count()

        # Calculate average lead score
        avg_score_result = query.with_entities(func.avg(Prospect.lead_score)).scalar()
        avg_score = float(avg_score_result) if avg_score_result else 0.0

        # Calculate conversion rate
        conversion_rate = (converted / total * 100) if total > 0 else 0.0

        return {
            "total_prospects": total,
            "new_prospects": new,
            "contacted_prospects": contacted,
            "qualified_prospects": qualified,
            "converted_prospects": converted,
            "rejected_prospects": rejected,
            "average_lead_score": round(avg_score, 2),
            "conversion_rate": round(conversion_rate, 2)
        }

    def update_lead_score(self, prospect_id: UUID, score_change: int, reason: str) -> Optional[Prospect]:
        """
        Update prospect lead score.

        Args:
            prospect_id: Prospect UUID
            score_change: Score to add (can be negative)
            reason: Reason for score change

        Returns:
            Updated prospect or None if not found
        """
        prospect = self.get(prospect_id)
        if not prospect:
            return None

        # Update score (ensure it stays within 0-100 range)
        new_score = max(0, min(100, prospect.lead_score + score_change))
        prospect.lead_score = new_score

        self.db.commit()
        self.db.refresh(prospect)

        return prospect

    def mark_as_converted(self, prospect_id: UUID, contact_id: UUID) -> Optional[Prospect]:
        """
        Mark prospect as converted to contact.

        Args:
            prospect_id: Prospect UUID
            contact_id: New contact UUID

        Returns:
            Updated prospect or None if not found
        """
        prospect = self.get(prospect_id)
        if not prospect:
            return None

        prospect.status = ProspectStatus.CONVERTED
        prospect.converted_to_contact_id = contact_id
        prospect.converted_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(prospect)

        return prospect

    def get_with_engagement(self, prospect_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get prospect with engagement history from campaigns.

        Args:
            prospect_id: Prospect UUID

        Returns:
            Dictionary with prospect and engagement data
        """
        prospect = self.get(prospect_id)
        if not prospect:
            return None

        # Get campaign engagement records
        engagements = self.db.query(CampaignContact)\
            .filter(CampaignContact.prospect_id == prospect_id)\
            .all()

        return {
            "prospect": prospect,
            "engagements": engagements,
            "engagement_count": len(engagements),
            "total_opens": sum(e.open_count for e in engagements),
            "total_clicks": sum(e.click_count for e in engagements)
        }

    def bulk_create(self, prospects_data: List[Dict[str, Any]], skip_duplicates: bool = True) -> Dict[str, Any]:
        """
        Bulk create prospects with duplicate handling.

        Args:
            prospects_data: List of prospect dictionaries
            skip_duplicates: If True, skip duplicates; if False, raise error

        Returns:
            Dictionary with results (created_count, skipped_count, created_ids, errors)
        """
        created_ids = []
        errors = []
        skipped_count = 0

        for idx, prospect_data in enumerate(prospects_data):
            try:
                # Check for duplicate
                email = prospect_data.get('email')
                phone = prospect_data.get('phone')
                duplicate = self.check_duplicate(email=email, phone=phone)

                if duplicate:
                    if skip_duplicates:
                        skipped_count += 1
                        errors.append({
                            "row": idx + 1,
                            "email": email,
                            "error": f"Duplicate: Prospect with email/phone already exists (ID: {duplicate.id})"
                        })
                        continue
                    else:
                        raise IntegrityError(f"Duplicate prospect: {email}", None, None)

                # Create prospect
                prospect = self.create(obj_in=prospect_data)
                created_ids.append(prospect.id)

            except Exception as e:
                errors.append({
                    "row": idx + 1,
                    "email": prospect_data.get('email'),
                    "error": str(e)
                })

        return {
            "created_count": len(created_ids),
            "skipped_count": skipped_count,
            "failed_count": len(errors) - skipped_count,
            "created_ids": created_ids,
            "errors": errors
        }
