"""
CampaignContact repository for database operations.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from app.models.campaign_contact import CampaignContact, EngagementStatus
from app.repositories.base_repository import BaseRepository


class CampaignContactRepository(BaseRepository[CampaignContact]):
    """Repository for CampaignContact (junction table) database operations."""

    def __init__(self, db: Session):
        super().__init__(CampaignContact, db)

    def add_contact_to_campaign(
        self,
        campaign_id: UUID,
        contact_id: UUID,
        email_sent_to: Optional[str] = None
    ) -> CampaignContact:
        """
        Add a contact to a campaign.

        Args:
            campaign_id: Campaign UUID
            contact_id: Contact UUID
            email_sent_to: Email address to send to

        Returns:
            Created CampaignContact record
        """
        # Check if already exists
        existing = self.db.query(CampaignContact)\
            .filter(CampaignContact.campaign_id == campaign_id)\
            .filter(CampaignContact.contact_id == contact_id)\
            .first()

        if existing:
            return existing

        # Create new record
        cc = CampaignContact(
            campaign_id=campaign_id,
            contact_id=contact_id,
            prospect_id=None,
            email_sent_to=email_sent_to,
            status=EngagementStatus.PENDING
        )

        self.db.add(cc)
        self.db.commit()
        self.db.refresh(cc)

        return cc

    def add_prospect_to_campaign(
        self,
        campaign_id: UUID,
        prospect_id: UUID,
        email_sent_to: Optional[str] = None
    ) -> CampaignContact:
        """
        Add a prospect to a campaign.

        Args:
            campaign_id: Campaign UUID
            prospect_id: Prospect UUID
            email_sent_to: Email address to send to

        Returns:
            Created CampaignContact record
        """
        # Check if already exists
        existing = self.db.query(CampaignContact)\
            .filter(CampaignContact.campaign_id == campaign_id)\
            .filter(CampaignContact.prospect_id == prospect_id)\
            .first()

        if existing:
            return existing

        # Create new record
        cc = CampaignContact(
            campaign_id=campaign_id,
            contact_id=None,
            prospect_id=prospect_id,
            email_sent_to=email_sent_to,
            status=EngagementStatus.PENDING
        )

        self.db.add(cc)
        self.db.commit()
        self.db.refresh(cc)

        return cc

    def get_campaign_audience(
        self,
        campaign_id: UUID,
        status: Optional[List[EngagementStatus]] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[CampaignContact]:
        """
        Get all audience members for a campaign.

        Args:
            campaign_id: Campaign UUID
            status: Optional list of statuses to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of CampaignContact records
        """
        query = self.db.query(CampaignContact)\
            .filter(CampaignContact.campaign_id == campaign_id)

        if status:
            query = query.filter(CampaignContact.status.in_(status))

        return query.order_by(desc(CampaignContact.created_at)).offset(skip).limit(limit).all()

    def get_contact_campaigns(self, contact_id: UUID) -> List[CampaignContact]:
        """Get all campaigns a contact is part of."""
        return self.db.query(CampaignContact)\
            .filter(CampaignContact.contact_id == contact_id)\
            .order_by(desc(CampaignContact.created_at))\
            .all()

    def get_prospect_campaigns(self, prospect_id: UUID) -> List[CampaignContact]:
        """Get all campaigns a prospect is part of."""
        return self.db.query(CampaignContact)\
            .filter(CampaignContact.prospect_id == prospect_id)\
            .order_by(desc(CampaignContact.created_at))\
            .all()

    def mark_as_sent(
        self,
        campaign_contact_id: UUID,
        email_message_id: Optional[str] = None,
        email_subject: Optional[str] = None
    ) -> Optional[CampaignContact]:
        """
        Mark a campaign contact as sent.

        Args:
            campaign_contact_id: CampaignContact UUID
            email_message_id: Email provider message ID
            email_subject: Email subject line

        Returns:
            Updated CampaignContact or None if not found
        """
        cc = self.get(campaign_contact_id)
        if not cc:
            return None

        cc.status = EngagementStatus.SENT
        cc.sent_at = datetime.utcnow()
        if email_message_id:
            cc.email_message_id = email_message_id
        if email_subject:
            cc.email_subject = email_subject

        self.db.commit()
        self.db.refresh(cc)

        return cc

    def mark_as_delivered(self, campaign_contact_id: UUID) -> Optional[CampaignContact]:
        """Mark a campaign contact as delivered."""
        cc = self.get(campaign_contact_id)
        if not cc:
            return None

        cc.status = EngagementStatus.DELIVERED
        cc.delivered_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(cc)

        return cc

    def mark_as_opened(self, campaign_contact_id: UUID) -> Optional[CampaignContact]:
        """Mark a campaign contact as opened."""
        cc = self.get(campaign_contact_id)
        if not cc:
            return None

        now = datetime.utcnow()

        if not cc.opened_at:
            cc.opened_at = now
            cc.status = EngagementStatus.OPENED

        cc.open_count += 1

        self.db.commit()
        self.db.refresh(cc)

        return cc

    def mark_as_clicked(self, campaign_contact_id: UUID) -> Optional[CampaignContact]:
        """Mark a campaign contact as clicked."""
        cc = self.get(campaign_contact_id)
        if not cc:
            return None

        now = datetime.utcnow()

        if not cc.clicked_at:
            cc.clicked_at = now
            cc.status = EngagementStatus.CLICKED

        cc.click_count += 1

        self.db.commit()
        self.db.refresh(cc)

        return cc

    def mark_as_responded(self, campaign_contact_id: UUID) -> Optional[CampaignContact]:
        """Mark a campaign contact as responded."""
        cc = self.get(campaign_contact_id)
        if not cc:
            return None

        cc.status = EngagementStatus.RESPONDED
        cc.responded_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(cc)

        return cc

    def mark_as_converted(
        self,
        campaign_contact_id: UUID,
        deal_id: UUID,
        conversion_value: float
    ) -> Optional[CampaignContact]:
        """
        Mark a campaign contact as converted to deal.

        Args:
            campaign_contact_id: CampaignContact UUID
            deal_id: Deal UUID
            conversion_value: Deal value

        Returns:
            Updated CampaignContact or None if not found
        """
        cc = self.get(campaign_contact_id)
        if not cc:
            return None

        cc.status = EngagementStatus.CONVERTED
        cc.converted_at = datetime.utcnow()
        cc.deal_id = deal_id
        cc.conversion_value = conversion_value

        self.db.commit()
        self.db.refresh(cc)

        return cc

    def mark_as_bounced(
        self,
        campaign_contact_id: UUID,
        bounce_type: str = "hard",
        error_message: Optional[str] = None
    ) -> Optional[CampaignContact]:
        """
        Mark a campaign contact as bounced.

        Args:
            campaign_contact_id: CampaignContact UUID
            bounce_type: "hard" or "soft" bounce
            error_message: Error message from email provider

        Returns:
            Updated CampaignContact or None if not found
        """
        cc = self.get(campaign_contact_id)
        if not cc:
            return None

        cc.status = EngagementStatus.BOUNCED
        cc.bounced_at = datetime.utcnow()
        cc.bounce_type = bounce_type
        if error_message:
            cc.error_message = error_message

        self.db.commit()
        self.db.refresh(cc)

        return cc

    def mark_as_unsubscribed(self, campaign_contact_id: UUID) -> Optional[CampaignContact]:
        """Mark a campaign contact as unsubscribed."""
        cc = self.get(campaign_contact_id)
        if not cc:
            return None

        cc.status = EngagementStatus.UNSUBSCRIBED
        cc.unsubscribed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(cc)

        return cc

    def bulk_add_contacts(
        self,
        campaign_id: UUID,
        contact_ids: List[UUID]
    ) -> Dict[str, Any]:
        """
        Bulk add contacts to a campaign.

        Args:
            campaign_id: Campaign UUID
            contact_ids: List of contact UUIDs

        Returns:
            Dictionary with results (added_count, skipped_count)
        """
        added_count = 0
        skipped_count = 0

        for contact_id in contact_ids:
            # Check if already exists
            existing = self.db.query(CampaignContact)\
                .filter(CampaignContact.campaign_id == campaign_id)\
                .filter(CampaignContact.contact_id == contact_id)\
                .first()

            if existing:
                skipped_count += 1
                continue

            # Create new record
            cc = CampaignContact(
                campaign_id=campaign_id,
                contact_id=contact_id,
                prospect_id=None,
                status=EngagementStatus.PENDING
            )
            self.db.add(cc)
            added_count += 1

        self.db.commit()

        return {
            "added_count": added_count,
            "skipped_count": skipped_count,
            "total_requested": len(contact_ids)
        }

    def bulk_add_prospects(
        self,
        campaign_id: UUID,
        prospect_ids: List[UUID]
    ) -> Dict[str, Any]:
        """
        Bulk add prospects to a campaign.

        Args:
            campaign_id: Campaign UUID
            prospect_ids: List of prospect UUIDs

        Returns:
            Dictionary with results (added_count, skipped_count)
        """
        added_count = 0
        skipped_count = 0

        for prospect_id in prospect_ids:
            # Check if already exists
            existing = self.db.query(CampaignContact)\
                .filter(CampaignContact.campaign_id == campaign_id)\
                .filter(CampaignContact.prospect_id == prospect_id)\
                .first()

            if existing:
                skipped_count += 1
                continue

            # Create new record
            cc = CampaignContact(
                campaign_id=campaign_id,
                contact_id=None,
                prospect_id=prospect_id,
                status=EngagementStatus.PENDING
            )
            self.db.add(cc)
            added_count += 1

        self.db.commit()

        return {
            "added_count": added_count,
            "skipped_count": skipped_count,
            "total_requested": len(prospect_ids)
        }

    def remove_from_campaign(
        self,
        campaign_id: UUID,
        contact_id: Optional[UUID] = None,
        prospect_id: Optional[UUID] = None
    ) -> bool:
        """
        Remove a contact or prospect from a campaign.

        Args:
            campaign_id: Campaign UUID
            contact_id: Contact UUID (optional)
            prospect_id: Prospect UUID (optional)

        Returns:
            True if removed, False if not found
        """
        query = self.db.query(CampaignContact)\
            .filter(CampaignContact.campaign_id == campaign_id)

        if contact_id:
            query = query.filter(CampaignContact.contact_id == contact_id)
        elif prospect_id:
            query = query.filter(CampaignContact.prospect_id == prospect_id)
        else:
            return False

        cc = query.first()
        if not cc:
            return False

        self.db.delete(cc)
        self.db.commit()

        return True

    def reset_for_resend(self, campaign_contact_id: UUID) -> bool:
        """
        Reset a campaign_contact status to pending for resending.

        Args:
            campaign_contact_id: CampaignContact UUID

        Returns:
            True if reset, False if not found
        """
        cc = self.db.query(CampaignContact)\
            .filter(CampaignContact.id == campaign_contact_id)\
            .first()

        if not cc:
            return False

        # Reset status to pending
        cc.status = EngagementStatus.PENDING

        # Clear timestamps and counters
        cc.sent_at = None
        cc.delivered_at = None
        cc.opened_at = None
        cc.clicked_at = None
        cc.responded_at = None
        cc.bounced_at = None
        cc.converted_at = None

        cc.open_count = 0
        cc.click_count = 0
        # Note: engagement_score is likely a computed property, don't set it directly

        # Clear error info
        cc.error_message = None
        cc.bounce_type = None

        self.db.commit()
        self.db.refresh(cc)

        return True
