"""
Campaign Service - Business logic layer for Campaign operations.
Handles campaign CRUD, execution, metrics, and analytics.
"""

from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.repositories.campaign_repository import CampaignRepository
from app.repositories.campaign_contact_repository import CampaignContactRepository
from app.repositories.prospect_repository import ProspectRepository
from app.models.campaign import Campaign, CampaignStatus, CampaignType
from app.models.campaign_contact import CampaignContact, EngagementStatus
from app.models.email_template import EmailTemplate
from app.schemas.campaign import (
    CampaignCreate, CampaignUpdate, CampaignResponse,
    CampaignFilter, AddToCampaignRequest, CampaignExecuteRequest
)


class CampaignService:
    """Service layer for campaign business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = CampaignRepository(db)
        self.campaign_contact_repo = CampaignContactRepository(db)
        self.prospect_repo = ProspectRepository(db)

    def create_campaign(
        self,
        campaign_data: CampaignCreate,
        created_by: UUID
    ) -> Campaign:
        """
        Create a new campaign.

        Args:
            campaign_data: Campaign creation data
            created_by: User ID creating the campaign

        Returns:
            Created campaign
        """
        campaign_dict = campaign_data.dict(exclude_unset=True)
        campaign_dict['created_by'] = created_by

        # Set owner_id if not provided
        if 'owner_id' not in campaign_dict or not campaign_dict['owner_id']:
            campaign_dict['owner_id'] = created_by

        # Validate email template if provided
        if campaign_data.email_template_id:
            template = self.db.query(EmailTemplate).filter(
                EmailTemplate.id == campaign_data.email_template_id
            ).first()
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Email template not found"
                )

        campaign = self.repository.create(obj_in=campaign_dict)
        return campaign

    def get_campaign(self, campaign_id: UUID) -> Optional[Campaign]:
        """Get a campaign by ID."""
        return self.repository.get(campaign_id)

    def get_campaigns(
        self,
        filters: CampaignFilter,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Campaign], int]:
        """
        Get campaigns with filtering and pagination.

        Args:
            filters: Filter criteria
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (campaigns list, total count)
        """
        filter_dict = filters.dict(exclude_none=True)
        search_term = filter_dict.pop('search', '')

        return self.repository.search(
            search_term=search_term,
            filters=filter_dict,
            skip=skip,
            limit=limit
        )

    def get_user_campaigns(
        self,
        owner_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Campaign]:
        """Get campaigns owned by a specific user."""
        return self.repository.get_by_owner(
            owner_id=owner_id,
            skip=skip,
            limit=limit
        )

    def get_active_campaigns(self) -> List[Campaign]:
        """Get all active campaigns."""
        return self.repository.get_active_campaigns()

    def update_campaign(
        self,
        campaign_id: UUID,
        campaign_data: CampaignUpdate
    ) -> Optional[Campaign]:
        """
        Update a campaign.

        Args:
            campaign_id: Campaign UUID
            campaign_data: Update data

        Returns:
            Updated campaign or None if not found
        """
        campaign = self.repository.get(campaign_id)
        if not campaign:
            return None

        update_dict = campaign_data.dict(exclude_unset=True)

        # Validate email template if being changed
        if 'email_template_id' in update_dict and update_dict['email_template_id']:
            template = self.db.query(EmailTemplate).filter(
                EmailTemplate.id == update_dict['email_template_id']
            ).first()
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Email template not found"
                )

        return self.repository.update(db_obj=campaign, obj_in=update_dict)

    def delete_campaign(self, campaign_id: UUID) -> bool:
        """
        Delete a campaign.

        Args:
            campaign_id: Campaign UUID

        Returns:
            True if deleted, False if not found
        """
        return self.repository.delete(id=campaign_id)

    def add_audience_to_campaign(
        self,
        campaign_id: UUID,
        audience_request: AddToCampaignRequest
    ) -> Dict[str, Any]:
        """
        Add contacts and/or prospects to a campaign.

        Args:
            campaign_id: Campaign UUID
            audience_request: Request with contact_ids and prospect_ids

        Returns:
            Dictionary with addition results

        Raises:
            HTTPException: If campaign not found
        """
        campaign = self.repository.get(campaign_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
            )

        added_contacts = 0
        added_prospects = 0

        # Add contacts
        if audience_request.contact_ids:
            result = self.campaign_contact_repo.bulk_add_contacts(
                campaign_id=campaign_id,
                contact_ids=audience_request.contact_ids
            )
            added_contacts = result['added_count']

        # Add prospects
        if audience_request.prospect_ids:
            result = self.campaign_contact_repo.bulk_add_prospects(
                campaign_id=campaign_id,
                prospect_ids=audience_request.prospect_ids
            )
            added_prospects = result['added_count']

        # Update campaign target audience size
        total_audience = len(self.campaign_contact_repo.get_campaign_audience(campaign_id))
        campaign.target_audience_size = total_audience
        self.db.commit()

        return {
            "campaign_id": campaign_id,
            "added_contacts": added_contacts,
            "added_prospects": added_prospects,
            "total_audience": total_audience,
            "message": f"Added {added_contacts} contacts and {added_prospects} prospects to campaign"
        }

    def get_campaign_audience(
        self,
        campaign_id: UUID,
        status: Optional[List[EngagementStatus]] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get campaign audience members with details.

        Args:
            campaign_id: Campaign UUID
            status: Optional engagement status filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of audience member details
        """
        audience_members = self.campaign_contact_repo.get_campaign_audience(
            campaign_id=campaign_id,
            status=status,
            skip=skip,
            limit=limit
        )

        result = []
        for cc in audience_members:
            member_data = {
                "id": cc.id,
                "campaign_contact_id": cc.id,
                "recipient_type": cc.recipient_type,
                "recipient_id": cc.recipient_id,
                "status": cc.status.value,
                "sent_at": cc.sent_at,
                "opened_at": cc.opened_at,
                "clicked_at": cc.clicked_at,
                "responded_at": cc.responded_at,
                "converted_at": cc.converted_at,
                "engagement_score": cc.engagement_score,
                "open_count": cc.open_count,
                "click_count": cc.click_count
            }

            # Add contact or prospect details
            if cc.contact:
                member_data["name"] = f"{cc.contact.first_name} {cc.contact.last_name}"
                member_data["email"] = cc.contact.email
                member_data["company"] = cc.contact.company.name if cc.contact.company else None
            elif cc.prospect:
                member_data["name"] = f"{cc.prospect.first_name} {cc.prospect.last_name}"
                member_data["email"] = cc.prospect.email
                member_data["company"] = cc.prospect.company_name
                member_data["lead_score"] = cc.prospect.lead_score

            result.append(member_data)

        return result

    def remove_audience_member(
        self,
        campaign_id: UUID,
        campaign_contact_id: UUID
    ) -> Dict[str, Any]:
        """
        Remove an audience member from the campaign.

        Args:
            campaign_id: Campaign UUID
            campaign_contact_id: CampaignContact UUID

        Returns:
            Success message with updated count

        Raises:
            HTTPException: If campaign_contact not found
        """
        # Verify the campaign_contact exists and belongs to this campaign
        campaign_contact = self.campaign_contact_repo.get(campaign_contact_id)

        if not campaign_contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audience member not found"
            )

        if str(campaign_contact.campaign_id) != str(campaign_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audience member does not belong to this campaign"
            )

        # Remove the campaign contact
        if campaign_contact.contact_id:
            self.campaign_contact_repo.remove_from_campaign(
                campaign_id=campaign_id,
                contact_id=campaign_contact.contact_id
            )
        elif campaign_contact.prospect_id:
            self.campaign_contact_repo.remove_from_campaign(
                campaign_id=campaign_id,
                prospect_id=campaign_contact.prospect_id
            )

        # Update campaign's target audience size
        campaign = self.repository.get(campaign_id)
        if campaign:
            campaign.target_audience_size = max(0, (campaign.target_audience_size or 0) - 1)
            self.db.commit()

        return {
            "message": "Audience member removed successfully",
            "campaign_id": campaign_id,
            "campaign_contact_id": campaign_contact_id,
            "target_audience_size": campaign.target_audience_size if campaign else 0
        }

    def execute_campaign(
        self,
        campaign_id: UUID,
        execute_request: CampaignExecuteRequest,
        executed_by: UUID
    ) -> Dict[str, Any]:
        """
        Execute a campaign (send emails, etc.).

        Args:
            campaign_id: Campaign UUID
            execute_request: Execution parameters
            executed_by: User ID executing the campaign

        Returns:
            Execution result

        Raises:
            HTTPException: If campaign not found or cannot be executed
        """
        campaign = self.repository.get(campaign_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
            )

        # Validate campaign can be executed
        if campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.SCHEDULED, CampaignStatus.ACTIVE]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Campaign with status '{campaign.status}' cannot be executed"
            )

        # For email campaigns, validate template
        if campaign.type == CampaignType.EMAIL and not campaign.email_template_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email campaign requires an email template"
            )

        # Get audience
        audience = self.campaign_contact_repo.get_campaign_audience(
            campaign_id=campaign_id,
            status=[EngagementStatus.PENDING]
        )

        if not audience:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Campaign has no audience members to send to"
            )

        # Handle test email
        if execute_request.send_test_email:
            return self._send_test_email(campaign, execute_request.test_email_recipients)

        # Handle scheduled execution
        if execute_request.schedule_for:
            campaign.status = CampaignStatus.SCHEDULED
            campaign.start_date = execute_request.schedule_for
            self.db.commit()

            return {
                "campaign_id": campaign_id,
                "status": "scheduled",
                "scheduled_for": execute_request.schedule_for,
                "message": f"Campaign scheduled for {execute_request.schedule_for}"
            }

        # Execute immediately
        sent_count = 0

        if campaign.type == CampaignType.EMAIL:
            sent_count = self._execute_email_campaign(campaign, audience)
        else:
            # For non-email campaigns, just mark as sent
            for cc in audience:
                self.campaign_contact_repo.mark_as_sent(cc.id)
                sent_count += 1

        # Mark campaign as executed
        self.repository.mark_as_executed(campaign_id)

        # Update metrics
        self.repository.update_metrics(campaign_id)

        return {
            "campaign_id": campaign_id,
            "status": "executed",
            "sent_count": sent_count,
            "message": f"Campaign executed successfully. Sent to {sent_count} recipients."
        }

    def send_to_pending_audience(
        self,
        campaign_id: UUID,
        executed_by: UUID
    ) -> Dict[str, Any]:
        """
        Send campaign to pending (unsent) audience members only.

        Args:
            campaign_id: Campaign UUID
            executed_by: User ID executing the send

        Returns:
            Execution result with sent count

        Raises:
            HTTPException: If campaign not found or cannot be executed
        """
        campaign = self.repository.get(campaign_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
            )

        # For email campaigns, validate template
        if campaign.type == CampaignType.EMAIL and not campaign.email_template_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email campaign requires an email template"
            )

        # Get only pending audience members
        pending_audience = self.campaign_contact_repo.get_campaign_audience(
            campaign_id=campaign_id,
            status=[EngagementStatus.PENDING]
        )

        if not pending_audience:
            return {
                "campaign_id": campaign_id,
                "status": "no_pending",
                "sent_count": 0,
                "message": "No pending audience members to send to"
            }

        # Execute send
        sent_count = 0

        if campaign.type == CampaignType.EMAIL:
            sent_count = self._execute_email_campaign(campaign, pending_audience)
        else:
            # For non-email campaigns, just mark as sent
            for cc in pending_audience:
                self.campaign_contact_repo.mark_as_sent(cc.id)
                sent_count += 1

        # Update metrics
        self.repository.update_metrics(campaign_id)

        return {
            "campaign_id": campaign_id,
            "status": "sent",
            "sent_count": sent_count,
            "message": f"Sent to {sent_count} new audience member(s)"
        }

    def resend_to_member(
        self,
        campaign_id: UUID,
        campaign_contact_id: UUID,
        executed_by: UUID
    ) -> Dict[str, Any]:
        """
        Resend campaign to a specific audience member.

        Args:
            campaign_id: Campaign UUID
            campaign_contact_id: CampaignContact UUID
            executed_by: User ID executing the resend

        Returns:
            Resend result

        Raises:
            HTTPException: If campaign_contact not found or cannot be resent
        """
        # Get the campaign
        campaign = self.repository.get(campaign_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
            )

        # Get the campaign_contact
        campaign_contact = self.campaign_contact_repo.get(campaign_contact_id)
        if not campaign_contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audience member not found"
            )

        # Verify it belongs to this campaign
        if str(campaign_contact.campaign_id) != str(campaign_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audience member does not belong to this campaign"
            )

        # For email campaigns, validate template
        if campaign.type == CampaignType.EMAIL and not campaign.email_template_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email campaign requires an email template"
            )

        # Reset the member status to pending
        self.campaign_contact_repo.reset_for_resend(campaign_contact_id)

        # Get member name for response
        member_name = "Unknown"
        if campaign_contact.contact:
            member_name = f"{campaign_contact.contact.first_name} {campaign_contact.contact.last_name}"
        elif campaign_contact.prospect:
            member_name = f"{campaign_contact.prospect.first_name} {campaign_contact.prospect.last_name}"

        # Resend to this member
        if campaign.type == CampaignType.EMAIL:
            # Get the refreshed campaign_contact with pending status
            refreshed_cc = self.campaign_contact_repo.get(campaign_contact_id)
            sent_count = self._execute_email_campaign(campaign, [refreshed_cc])

            if sent_count == 0:
                return {
                    "campaign_id": campaign_id,
                    "campaign_contact_id": campaign_contact_id,
                    "status": "failed",
                    "message": f"Failed to resend to {member_name}"
                }
        else:
            # For non-email campaigns, just mark as sent
            self.campaign_contact_repo.mark_as_sent(campaign_contact_id)

        # Update metrics
        self.repository.update_metrics(campaign_id)

        return {
            "campaign_id": campaign_id,
            "campaign_contact_id": campaign_contact_id,
            "status": "resent",
            "message": f"Campaign resent to {member_name}"
        }

    def get_campaign_metrics(self, campaign_id: UUID) -> Dict[str, Any]:
        """
        Get campaign performance metrics.

        Args:
            campaign_id: Campaign UUID

        Returns:
            Campaign metrics

        Raises:
            HTTPException: If campaign not found
        """
        campaign = self.repository.get(campaign_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
            )

        # Update metrics first
        self.repository.update_metrics(campaign_id)
        campaign = self.repository.get(campaign_id)  # Refresh

        return {
            "campaign_id": campaign_id,
            "campaign_name": campaign.name,
            "sent_count": campaign.sent_count,
            "delivered_count": campaign.delivered_count,
            "opened_count": campaign.opened_count,
            "clicked_count": campaign.clicked_count,
            "responded_count": campaign.responded_count,
            "bounced_count": campaign.bounced_count,
            "converted_count": campaign.converted_count,
            "prospects_generated": campaign.prospects_generated,
            "delivery_rate": campaign.delivery_rate,
            "open_rate": campaign.open_rate,
            "click_rate": campaign.click_rate,
            "response_rate": campaign.response_rate,
            "conversion_rate": campaign.conversion_rate,
            "bounce_rate": campaign.bounce_rate,
            "budget": float(campaign.budget),
            "actual_cost": float(campaign.actual_cost),
            "actual_revenue": float(campaign.actual_revenue),
            "roi": campaign.roi
        }

    def get_campaign_conversions(self, campaign_id: UUID) -> List[Dict[str, Any]]:
        """Get all deals/conversions from a campaign."""
        return self.repository.get_conversions(campaign_id)

    def get_campaign_analytics(
        self,
        campaign_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive campaign analytics.

        Args:
            campaign_id: Campaign UUID
            days: Number of days for time-series data

        Returns:
            Analytics data with metrics, timeline, and top performers
        """
        campaign = self.repository.get(campaign_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found"
            )

        metrics = self.get_campaign_metrics(campaign_id)
        timeline = self.repository.get_performance_timeline(campaign_id, days)
        top_performers = self.repository.get_top_performers(campaign_id, limit=10)

        # Calculate conversion funnel
        funnel = {
            "sent": campaign.sent_count,
            "delivered": campaign.delivered_count,
            "opened": campaign.opened_count,
            "clicked": campaign.clicked_count,
            "responded": campaign.responded_count,
            "converted": campaign.converted_count
        }

        return {
            "campaign_id": campaign_id,
            "metrics": metrics,
            "time_series": timeline,
            "top_performers": top_performers,
            "conversion_funnel": funnel
        }

    def get_campaign_statistics(
        self,
        owner_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get overall campaign statistics, optionally filtered by owner."""
        return self.repository.get_statistics(owner_id=owner_id)

    def _execute_email_campaign(
        self,
        campaign: Campaign,
        audience: List[CampaignContact]
    ) -> int:
        """
        Execute email campaign by sending emails to audience via SMTP.

        Args:
            campaign: Campaign object
            audience: List of CampaignContact objects

        Returns:
            Number of emails sent
        """
        from app.services.smtp_service import SMTPService
        from app.services.email_template_service_new import EmailTemplateService
        from app.core.config import settings
        import time

        sent_count = 0

        # Get email template
        template = self.db.query(EmailTemplate).filter(
            EmailTemplate.id == campaign.email_template_id
        ).first()

        if not template:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email template not found"
            )

        # Initialize SMTP service
        smtp_service = SMTPService(
            smtp_host=settings.SMTP_HOST,
            smtp_port=settings.SMTP_PORT,
            smtp_user=settings.SMTP_USER,
            smtp_pass=settings.SMTP_PASS,
            from_email=settings.FROM_EMAIL,
            smtp_secure=settings.SMTP_SECURE
        )

        # Initialize email template service for merge field processing
        email_template_service = EmailTemplateService(self.db)

        # Get sender email and name from campaign or use defaults
        from_email = campaign.email_from_email or settings.FROM_EMAIL
        from_name = campaign.email_from_name or "CRM System"
        email_subject = campaign.email_subject or template.subject

        print(f"\n{'='*60}")
        print(f"📧 EXECUTING EMAIL CAMPAIGN: {campaign.name}")
        print(f"Template: {template.name}")
        print(f"Audience Size: {len(audience)}")
        print(f"From: {from_name} <{from_email}>")
        print(f"{'='*60}\n")

        # Send emails to each audience member
        for cc in audience:
            try:
                recipient_email = None
                recipient_name = None
                merge_data = {}

                # Get recipient details and prepare merge data
                if cc.contact:
                    recipient_email = cc.contact.email
                    recipient_name = f"{cc.contact.first_name} {cc.contact.last_name}"
                    merge_data = {
                        'first_name': cc.contact.first_name or '',
                        'last_name': cc.contact.last_name or '',
                        'full_name': recipient_name,
                        'email': cc.contact.email or '',
                        'phone': cc.contact.phone or '',
                        'position': cc.contact.position or '',
                    }
                    if cc.contact.company:
                        merge_data['company_name'] = cc.contact.company.name or ''
                        merge_data['company_address'] = cc.contact.company.address or ''
                        merge_data['company_phone'] = cc.contact.company.phone or ''
                elif cc.prospect:
                    recipient_email = cc.prospect.email
                    recipient_name = f"{cc.prospect.first_name} {cc.prospect.last_name}"
                    merge_data = {
                        'first_name': cc.prospect.first_name or '',
                        'last_name': cc.prospect.last_name or '',
                        'full_name': recipient_name,
                        'email': cc.prospect.email or '',
                        'phone': cc.prospect.phone or '',
                    }

                if not recipient_email:
                    continue

                # Process template with merge data
                processed = email_template_service.process_template(
                    template=template,
                    merge_data=merge_data,
                    sender=None  # Campaign sending doesn't need sender user
                )

                # Send email via SMTP
                result = smtp_service.send_email(
                    to_email=recipient_email,
                    subject=email_subject,
                    html_content=processed['content'],
                    from_email=from_email,
                    from_name=from_name
                )

                if result.get('success'):
                    # Mark as sent in campaign tracking
                    self.campaign_contact_repo.mark_as_sent(
                        campaign_contact_id=cc.id,
                        email_subject=email_subject
                    )
                    sent_count += 1
                    print(f"✅ Sent to {recipient_email}")
                else:
                    # Mark as failed
                    self.campaign_contact_repo.mark_as_bounced(
                        campaign_contact_id=cc.id,
                        error_message=result.get('message', 'Unknown error')
                    )
                    print(f"❌ Failed to send to {recipient_email}: {result.get('message')}")

                # Rate limiting - 100ms delay between emails (10 emails per second)
                time.sleep(0.1)

            except Exception as e:
                # Log error and mark as failed
                self.campaign_contact_repo.mark_as_bounced(
                    campaign_contact_id=cc.id,
                    error_message=str(e)
                )
                print(f"❌ Error sending to {recipient_email}: {str(e)}")

        print(f"\n{'='*60}")
        print(f"📊 Campaign Complete: {sent_count}/{len(audience)} emails sent")
        print(f"{'='*60}\n")

        return sent_count

    def _send_test_email(
        self,
        campaign: Campaign,
        test_recipients: List[str]
    ) -> Dict[str, Any]:
        """
        Send test email for campaign.

        Args:
            campaign: Campaign object
            test_recipients: List of email addresses to send test to

        Returns:
            Test send result
        """
        if not test_recipients:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No test recipients provided"
            )

        # For MVP, just return success
        # In production, implement actual test email sending

        return {
            "campaign_id": campaign.id,
            "status": "test_sent",
            "sent_count": len(test_recipients),
            "recipients": test_recipients,
            "message": f"Test email sent to {len(test_recipients)} recipients"
        }

    def link_deal_to_campaign(
        self,
        campaign_id: UUID,
        prospect_id: UUID,
        deal_id: UUID,
        conversion_value: float
    ) -> Dict[str, Any]:
        """
        Link a deal to a campaign by updating the campaign_contact record.

        Args:
            campaign_id: Campaign UUID
            prospect_id: Prospect UUID
            deal_id: Deal UUID
            conversion_value: Value of the conversion

        Returns:
            Success message
        """
        from datetime import datetime

        # Find the campaign_contact record for this prospect in this campaign
        campaign_contact = self.db.query(CampaignContact).filter(
            CampaignContact.campaign_id == campaign_id,
            CampaignContact.prospect_id == prospect_id
        ).first()

        if not campaign_contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign contact association not found"
            )

        # Update the campaign_contact with the deal information
        campaign_contact.deal_id = deal_id
        campaign_contact.conversion_value = conversion_value
        campaign_contact.converted_at = datetime.utcnow()
        campaign_contact.status = EngagementStatus.CONVERTED

        self.db.commit()
        self.db.refresh(campaign_contact)

        # Update campaign metrics
        self.repository.update_metrics(campaign_id)

        return {
            "success": True,
            "message": "Deal successfully linked to campaign",
            "campaign_contact_id": campaign_contact.id,
            "deal_id": deal_id
        }

