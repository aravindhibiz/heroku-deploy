"""
Prospect Controller - HTTP request/response handling for Prospect endpoints.
Handles authentication, authorization, and HTTP-specific logic.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.services.prospect_service import ProspectService
from app.schemas.prospect import (
    ProspectCreate, ProspectUpdate, ProspectResponse,
    ProspectFilter, ProspectConversionRequest,
    BulkProspectCreate
)
from app.models.user import UserProfile
from app.models.prospect import ProspectStatus, ProspectSource


class ProspectController:
    """Controller for handling prospect HTTP requests."""

    def __init__(self, db: Session):
        self.db = db
        self.service = ProspectService(db)

    async def get_prospects(
        self,
        current_user: UserProfile,
        status: Optional[str] = None,
        source: Optional[str] = None,
        campaign_id: Optional[UUID] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get prospects with filters.

        Args:
            current_user: Authenticated user
            status: Status filter (comma-separated)
            source: Source filter (comma-separated)
            campaign_id: Campaign ID filter
            search: Search term
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            Dictionary with prospects and total count
        """
        # Parse filters
        status_list = None
        if status:
            try:
                status_list = [ProspectStatus(s.strip()) for s in status.split(',') if s.strip()]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid status value"
                )

        source_list = None
        if source:
            try:
                source_list = [ProspectSource(s.strip()) for s in source.split(',') if s.strip()]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid source value"
                )

        # Create filter object
        # For MVP, filter by assigned_to = current_user
        prospect_filter = ProspectFilter(
            status=status_list,
            source=source_list,
            campaign_id=campaign_id,
            search=search,
            assigned_to=current_user.id  # Only show user's assigned prospects
        )

        prospects, total = self.service.get_prospects(
            filters=prospect_filter,
            skip=skip,
            limit=limit
        )

        # Convert to response models
        prospect_responses = [
            ProspectResponse.from_orm(p) for p in prospects
        ]

        return {
            "prospects": prospect_responses,
            "total": total,
            "skip": skip,
            "limit": limit
        }

    async def get_campaign_prospects(
        self,
        campaign_id: UUID,
        current_user: UserProfile,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get prospects for a specific campaign.

        Args:
            campaign_id: Campaign UUID
            current_user: Authenticated user
            status: Status filter (comma-separated)
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            Dictionary with prospects and total count
        """
        # Parse status filter
        status_list = None
        if status:
            try:
                status_list = [ProspectStatus(s.strip()) for s in status.split(',') if s.strip()]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid status value"
                )

        prospects = self.service.get_campaign_prospects(
            campaign_id=campaign_id,
            status=status_list,
            skip=skip,
            limit=limit
        )

        # Convert to response models
        prospect_responses = [
            ProspectResponse.from_orm(p) for p in prospects
        ]

        return {
            "campaign_id": campaign_id,
            "prospects": prospect_responses,
            "total": len(prospect_responses)
        }

    async def get_recent_prospects(
        self,
        current_user: UserProfile,
        days: int = 7,
        limit: int = 10
    ) -> List[ProspectResponse]:
        """
        Get recently created prospects.

        Args:
            current_user: Authenticated user
            days: Number of days to look back
            limit: Maximum number of prospects

        Returns:
            List of recent prospects
        """
        prospects = self.service.get_recent_prospects(days=days, limit=limit)

        return [ProspectResponse.from_orm(p) for p in prospects]

    async def get_prospect(
        self,
        prospect_id: UUID,
        current_user: UserProfile
    ) -> ProspectResponse:
        """
        Get a single prospect by ID.

        Args:
            prospect_id: Prospect UUID
            current_user: Authenticated user

        Returns:
            Prospect details

        Raises:
            HTTPException: If prospect not found or access denied
        """
        prospect = self.service.get_prospect(prospect_id)

        if not prospect:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prospect not found"
            )

        # Check if user has access (assigned to them)
        if prospect.assigned_to != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this prospect"
            )

        return ProspectResponse.from_orm(prospect)

    async def create_prospect(
        self,
        prospect_data: ProspectCreate,
        current_user: UserProfile
    ) -> ProspectResponse:
        """
        Create a new prospect.

        Args:
            prospect_data: Prospect creation data
            current_user: Authenticated user

        Returns:
            Created prospect
        """
        prospect = self.service.create_prospect(
            prospect_data=prospect_data,
            created_by=current_user.id
        )

        return ProspectResponse.from_orm(prospect)

    async def update_prospect(
        self,
        prospect_id: UUID,
        prospect_data: ProspectUpdate,
        current_user: UserProfile
    ) -> ProspectResponse:
        """
        Update a prospect.

        Args:
            prospect_id: Prospect UUID
            prospect_data: Update data
            current_user: Authenticated user

        Returns:
            Updated prospect

        Raises:
            HTTPException: If prospect not found or access denied
        """
        prospect = self.service.get_prospect(prospect_id)

        if not prospect:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prospect not found"
            )

        # Check if user has access
        if prospect.assigned_to != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this prospect"
            )

        updated_prospect = self.service.update_prospect(
            prospect_id=prospect_id,
            prospect_data=prospect_data,
            updated_by=current_user.id
        )

        if not updated_prospect:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prospect not found"
            )

        return ProspectResponse.from_orm(updated_prospect)

    async def delete_prospect(
        self,
        prospect_id: UUID,
        current_user: UserProfile
    ) -> Dict[str, str]:
        """
        Delete a prospect.

        Args:
            prospect_id: Prospect UUID
            current_user: Authenticated user

        Returns:
            Success message

        Raises:
            HTTPException: If prospect not found or access denied
        """
        prospect = self.service.get_prospect(prospect_id)

        if not prospect:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prospect not found"
            )

        # Check if user has access
        if prospect.assigned_to != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this prospect"
            )

        success = self.service.delete_prospect(prospect_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prospect not found"
            )

        return {"message": "Prospect deleted successfully"}

    async def convert_to_contact(
        self,
        prospect_id: UUID,
        conversion_request: ProspectConversionRequest,
        current_user: UserProfile
    ) -> Dict[str, Any]:
        """
        Convert a prospect to a contact.

        Args:
            prospect_id: Prospect UUID
            conversion_request: Conversion parameters
            current_user: Authenticated user

        Returns:
            Conversion result

        Raises:
            HTTPException: If prospect not found or access denied
        """
        prospect = self.service.get_prospect(prospect_id)

        if not prospect:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prospect not found"
            )

        # Check if user has access
        if prospect.assigned_to != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to convert this prospect"
            )

        return self.service.convert_to_contact(
            prospect_id=prospect_id,
            conversion_request=conversion_request,
            converted_by=current_user.id
        )

    async def get_prospect_statistics(
        self,
        current_user: UserProfile,
        campaign_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Get prospect statistics.

        Args:
            current_user: Authenticated user
            campaign_id: Optional campaign ID filter

        Returns:
            Prospect statistics
        """
        return self.service.get_prospect_statistics(campaign_id=campaign_id)

    async def bulk_create_prospects(
        self,
        bulk_data: BulkProspectCreate,
        current_user: UserProfile
    ) -> Dict[str, Any]:
        """
        Bulk create prospects.

        Args:
            bulk_data: Bulk prospect data
            current_user: Authenticated user

        Returns:
            Bulk creation result
        """
        return self.service.bulk_create_prospects(
            bulk_data=bulk_data,
            created_by=current_user.id
        )
