"""
Prospect Service - Business logic layer for Prospect operations.
Handles prospect CRUD, duplicate detection, conversion workflow, and lead scoring.
"""

from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.repositories.prospect_repository import ProspectRepository
from app.repositories.campaign_contact_repository import CampaignContactRepository
from app.models.prospect import Prospect, ProspectStatus, ProspectSource
from app.models.contact import Contact
from app.models.activity import Activity
from app.models.campaign_metric import LeadScoreHistory
from app.schemas.prospect import (
    ProspectCreate, ProspectUpdate, ProspectResponse,
    ProspectConversionRequest, ProspectFilter,
    BulkProspectCreate
)


class ProspectService:
    """Service layer for prospect business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = ProspectRepository(db)
        self.campaign_contact_repo = CampaignContactRepository(db)

    def create_prospect(
        self,
        prospect_data: ProspectCreate,
        created_by: UUID
    ) -> Prospect:
        """
        Create a new prospect with duplicate detection.

        Args:
            prospect_data: Prospect creation data
            created_by: User ID creating the prospect

        Returns:
            Created prospect

        Raises:
            HTTPException: If duplicate found
        """
        # Check for duplicates
        duplicate = self.repository.check_duplicate(
            email=prospect_data.email,
            phone=prospect_data.phone
        )

        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Prospect with email '{prospect_data.email}' or phone '{prospect_data.phone}' already exists"
            )

        # Create prospect
        prospect_dict = prospect_data.dict(exclude_unset=True)
        prospect_dict['created_by'] = created_by

        # Convert empty strings to None for unique fields to avoid constraint violations
        if 'phone' in prospect_dict and prospect_dict['phone'] == '':
            prospect_dict['phone'] = None
        if 'email' in prospect_dict and prospect_dict['email'] == '':
            prospect_dict['email'] = None

        # Set default assigned_to if not provided
        if 'assigned_to' not in prospect_dict or not prospect_dict['assigned_to']:
            prospect_dict['assigned_to'] = created_by

        prospect = self.repository.create(obj_in=prospect_dict)

        # Create initial lead score history
        self._create_lead_score_history(
            prospect_id=prospect.id,
            old_score=0,
            new_score=prospect.lead_score,
            reason="Initial prospect creation",
            activity_type="created",
            changed_by=created_by
        )

        return prospect

    def get_prospect(self, prospect_id: UUID) -> Optional[Prospect]:
        """Get a prospect by ID."""
        return self.repository.get(prospect_id)

    def get_prospects(
        self,
        filters: ProspectFilter,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Prospect], int]:
        """
        Get prospects with filtering and pagination.

        Args:
            filters: Filter criteria
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (prospects list, total count)
        """
        filter_dict = filters.dict(exclude_none=True)
        search_term = filter_dict.pop('search', '')

        return self.repository.search(
            search_term=search_term,
            filters=filter_dict,
            skip=skip,
            limit=limit
        )

    def get_campaign_prospects(
        self,
        campaign_id: UUID,
        status: Optional[List[ProspectStatus]] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Prospect]:
        """Get prospects for a specific campaign."""
        return self.repository.get_by_campaign(
            campaign_id=campaign_id,
            status=status,
            skip=skip,
            limit=limit
        )

    def get_recent_prospects(self, days: int = 7, limit: int = 10) -> List[Prospect]:
        """Get recently created prospects across all campaigns."""
        return self.repository.get_recent(days=days, limit=limit)

    def update_prospect(
        self,
        prospect_id: UUID,
        prospect_data: ProspectUpdate,
        updated_by: Optional[UUID] = None
    ) -> Optional[Prospect]:
        """
        Update a prospect.

        Args:
            prospect_id: Prospect UUID
            prospect_data: Update data
            updated_by: User ID performing the update (for conversion tracking)

        Returns:
            Updated prospect or None if not found

        Raises:
            HTTPException: If duplicate email/phone found or conversion fails
        """
        prospect = self.repository.get(prospect_id)
        if not prospect:
            return None

        # Check for duplicates if email or phone is being changed
        update_dict = prospect_data.dict(exclude_unset=True)

        # Convert empty strings to None for unique fields to avoid constraint violations
        if 'phone' in update_dict and update_dict['phone'] == '':
            update_dict['phone'] = None
        if 'email' in update_dict and update_dict['email'] == '':
            update_dict['email'] = None

        if 'email' in update_dict or 'phone' in update_dict:
            duplicate = self.repository.check_duplicate(
                email=update_dict.get('email', prospect.email),
                phone=update_dict.get('phone', prospect.phone),
                exclude_id=prospect_id
            )

            if duplicate:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Another prospect with this email or phone already exists"
                )

        # Track lead score changes
        if 'lead_score' in update_dict and update_dict['lead_score'] != prospect.lead_score:
            old_score = prospect.lead_score
            new_score = update_dict['lead_score']
            self._create_lead_score_history(
                prospect_id=prospect_id,
                old_score=old_score,
                new_score=new_score,
                reason="Manual score adjustment",
                activity_type="manual_adjustment"
            )

        # Check if status is being changed to CONVERTED
        if 'status' in update_dict and update_dict['status'] == ProspectStatus.CONVERTED:
            # Only auto-convert if the prospect is not already converted
            if prospect.status != ProspectStatus.CONVERTED and not prospect.is_converted:
                # Trigger automatic conversion to contact
                from app.schemas.prospect import ProspectConversionRequest
                conversion_request = ProspectConversionRequest(
                    notes="Automatically converted via status update",
                    create_activity=True,
                    assign_to=prospect.assigned_to
                )

                # Convert the prospect to contact
                self.convert_to_contact(
                    prospect_id=prospect_id,
                    conversion_request=conversion_request,
                    converted_by=updated_by or prospect.assigned_to or prospect.created_by
                )

                # Return the updated prospect (conversion updates it internally)
                return self.repository.get(prospect_id)

        # Note: last_contacted_at is no longer automatically updated since we removed CONTACTED status
        # It can be updated manually if needed

        return self.repository.update(db_obj=prospect, obj_in=update_dict)

    def delete_prospect(self, prospect_id: UUID) -> bool:
        """Delete a prospect."""
        return self.repository.delete(id=prospect_id)

    def convert_to_contact(
        self,
        prospect_id: UUID,
        conversion_request: ProspectConversionRequest,
        converted_by: UUID
    ) -> Dict[str, Any]:
        """
        Convert a prospect to a contact.

        Args:
            prospect_id: Prospect UUID
            conversion_request: Conversion parameters
            converted_by: User ID performing the conversion

        Returns:
            Dictionary with prospect_id, contact_id, and optionally activity_id

        Raises:
            HTTPException: If prospect not found or already converted
        """
        prospect = self.repository.get(prospect_id)
        if not prospect:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prospect not found"
            )

        if prospect.is_converted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prospect has already been converted to a contact"
            )

        # Check if contact with same email already exists
        existing_contact = self.db.query(Contact).filter(
            Contact.email == prospect.email).first()
        if existing_contact:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Contact with email '{prospect.email}' already exists"
            )

        # Create new contact from prospect data
        contact = Contact(
            first_name=prospect.first_name,
            last_name=prospect.last_name,
            email=prospect.email,
            phone=prospect.phone,
            mobile=prospect.phone,  # Copy phone to mobile as well
            position=prospect.job_title,
            notes=f"Converted from prospect. Original notes: {prospect.notes or 'None'}",
            status='lead',  # New contacts from prospects start as leads
            owner_id=conversion_request.assign_to or prospect.assigned_to or converted_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # Try to find company by name if prospect has company_name
        if prospect.company_name:
            from app.models.company import Company
            company = self.db.query(Company).filter(
                Company.name.ilike(prospect.company_name)
            ).first()
            if company:
                contact.company_id = company.id

        self.db.add(contact)
        self.db.flush()  # Flush to get the contact ID

        # Mark prospect as converted
        self.repository.mark_as_converted(
            prospect_id=prospect_id,
            contact_id=contact.id
        )

        # Create activity log if requested
        activity_id = None
        if conversion_request.create_activity:
            activity = Activity(
                type='note',
                subject=f'Prospect converted to contact',
                description=f'Prospect {prospect.full_name} was converted to a contact. '
                f'Campaign source: {prospect.campaign.name if prospect.campaign else "N/A"}. '
                f'{conversion_request.notes or ""}',
                contact_id=contact.id,
                user_id=converted_by,
                created_at=datetime.utcnow()
            )
            self.db.add(activity)
            self.db.flush()
            activity_id = activity.id

        # Update campaign_contacts to link to new contact instead of prospect
        campaign_contacts = self.campaign_contact_repo.get_prospect_campaigns(
            prospect_id)
        for cc in campaign_contacts:
            cc.contact_id = contact.id
            cc.prospect_id = None

        self.db.commit()
        self.db.refresh(contact)

        return {
            "prospect_id": prospect_id,
            "contact_id": contact.id,
            "activity_id": activity_id,
            "message": "Prospect successfully converted to contact"
        }

    def update_lead_score(
        self,
        prospect_id: UUID,
        score_change: int,
        reason: str,
        activity_type: str,
        campaign_id: Optional[UUID] = None,
        campaign_contact_id: Optional[UUID] = None,
        changed_by: Optional[UUID] = None
    ) -> Optional[Prospect]:
        """
        Update prospect lead score and create history record.

        Args:
            prospect_id: Prospect UUID
            score_change: Score to add (can be negative)
            reason: Reason for score change
            activity_type: Type of activity causing change
            campaign_id: Optional campaign ID
            campaign_contact_id: Optional campaign contact ID
            changed_by: Optional user ID

        Returns:
            Updated prospect or None if not found
        """
        prospect = self.repository.get(prospect_id)
        if not prospect:
            return None

        old_score = prospect.lead_score
        prospect = self.repository.update_lead_score(
            prospect_id=prospect_id,
            score_change=score_change,
            reason=reason
        )

        if prospect:
            self._create_lead_score_history(
                prospect_id=prospect_id,
                old_score=old_score,
                new_score=prospect.lead_score,
                reason=reason,
                activity_type=activity_type,
                campaign_id=campaign_id,
                campaign_contact_id=campaign_contact_id,
                changed_by=changed_by
            )

        return prospect

    def get_prospect_statistics(
        self,
        campaign_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get prospect statistics, optionally filtered by campaign."""
        return self.repository.get_statistics(campaign_id=campaign_id)

    def bulk_create_prospects(
        self,
        bulk_data: BulkProspectCreate,
        created_by: UUID
    ) -> Dict[str, Any]:
        """
        Bulk create prospects with duplicate handling.

        Args:
            bulk_data: Bulk prospect creation data
            created_by: User ID creating the prospects

        Returns:
            Dictionary with creation results
        """
        prospects_data = []
        for prospect_create in bulk_data.prospects:
            prospect_dict = prospect_create.dict(exclude_unset=True)
            prospect_dict['created_by'] = created_by

            # Set campaign_id if provided at bulk level
            if bulk_data.campaign_id and 'campaign_id' not in prospect_dict:
                prospect_dict['campaign_id'] = bulk_data.campaign_id

            # Set assigned_to if not provided
            if 'assigned_to' not in prospect_dict or not prospect_dict['assigned_to']:
                prospect_dict['assigned_to'] = created_by

            prospects_data.append(prospect_dict)

        return self.repository.bulk_create(
            prospects_data=prospects_data,
            skip_duplicates=bulk_data.skip_duplicates
        )

    def get_prospect_with_engagement(
        self,
        prospect_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get prospect with full engagement history from campaigns."""
        return self.repository.get_with_engagement(prospect_id)

    def _create_lead_score_history(
        self,
        prospect_id: UUID,
        old_score: int,
        new_score: int,
        reason: str,
        activity_type: str,
        campaign_id: Optional[UUID] = None,
        campaign_contact_id: Optional[UUID] = None,
        changed_by: Optional[UUID] = None
    ) -> LeadScoreHistory:
        """
        Create a lead score history record.

        Args:
            prospect_id: Prospect UUID
            old_score: Previous score
            new_score: New score
            reason: Reason for change
            activity_type: Type of activity
            campaign_id: Optional campaign ID
            campaign_contact_id: Optional campaign contact ID
            changed_by: Optional user ID

        Returns:
            Created LeadScoreHistory record
        """
        history = LeadScoreHistory(
            prospect_id=prospect_id,
            old_score=old_score,
            new_score=new_score,
            score_change=new_score - old_score,
            reason=reason,
            activity_type=activity_type,
            campaign_id=campaign_id,
            campaign_contact_id=campaign_contact_id,
            changed_by=changed_by,
            created_at=datetime.utcnow()
        )

        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)

        return history
