"""
Deal controller for handling HTTP requests and responses.
Manages request validation, permission checks, and service delegation.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, Query

from models.user import UserProfile
from models.deal import Deal
from schemas.deal import (
    DealCreate,
    DealUpdate,
    DealResponse,
    DealWithRelations
)
from services.deal_service import DealService
from core.auth import has_permission
from core.auth_helpers import (
    get_deals_query_filter,
    check_deal_edit_permission,
    check_deal_delete_permission
)


class DealController:
    """
    Controller class for Deal HTTP operations.

    This controller handles HTTP-specific concerns like permission checks,
    error responses, and delegates business logic to the service layer.
    """

    @staticmethod
    def get_deals(
        db: Session,
        current_user: UserProfile,
        date_range: Optional[str] = None,
        probability_range: Optional[str] = None,
        owner_id: Optional[str] = None,
        stage: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[DealWithRelations]:
        """
        Handle GET request to retrieve all deals with filtering.

        Args:
            db: Database session
            current_user: The authenticated user
            date_range: Date range filter
            probability_range: Probability range filter
            owner_id: Owner ID filter
            stage: Stage filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of deals
        """
        # Get permission-filtered base query
        base_query = db.query(Deal)
        filtered_query = get_deals_query_filter(db, current_user, base_query)

        # Apply owner filter only if user has permission
        owner_filter = None
        if owner_id and has_permission(db, current_user, "deals.view_all"):
            try:
                owner_filter = UUID(owner_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid owner_id format"
                )

        # Delegate to service
        service = DealService(db)
        return service.get_all_deals(
            filtered_query=filtered_query,
            date_range=date_range,
            probability_range=probability_range,
            stage=stage,
            owner_id=owner_filter,
            skip=skip,
            limit=limit
        )

    @staticmethod
    def get_pipeline_deals(
        db: Session,
        current_user: UserProfile,
        date_range: Optional[str] = None,
        owner_id: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Handle GET request to retrieve pipeline deals grouped by stage.

        Args:
            db: Database session
            current_user: The authenticated user
            date_range: Date range filter (uses created_at for pipeline view)
            owner_id: Owner ID filter

        Returns:
            Dictionary with pipeline data
        """
        # Get permission-filtered base query
        base_query = db.query(Deal)
        filtered_query = get_deals_query_filter(db, current_user, base_query)

        # Apply owner filter only if user has permission
        owner_filter = None
        if owner_id and has_permission(db, current_user, "deals.view_all"):
            try:
                owner_filter = UUID(owner_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid owner_id format"
                )

        # Delegate to service
        service = DealService(db)
        return service.get_pipeline_deals(
            filtered_query=filtered_query,
            date_range=date_range,
            owner_id=owner_filter
        )

    @staticmethod
    def get_deal(
        deal_id: UUID,
        db: Session,
        current_user: UserProfile
    ) -> DealWithRelations:
        """
        Handle GET request to retrieve a single deal by ID.

        Args:
            deal_id: UUID of the deal
            db: Database session
            current_user: The authenticated user

        Returns:
            Deal details

        Raises:
            HTTPException: If deal not found or user doesn't have permission
        """
        # Delegate to service
        service = DealService(db)
        deal = service.get_deal_by_id(deal_id)

        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deal with id {deal_id} not found"
            )

        # Check permission using helper
        base_query = db.query(Deal).filter(Deal.id == deal_id)
        filtered_query = get_deals_query_filter(db, current_user, base_query)

        if not filtered_query.first():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this deal"
            )

        return deal

    @staticmethod
    def get_deal_statistics(
        db: Session,
        current_user: UserProfile
    ) -> Dict[str, Any]:
        """
        Handle GET request to retrieve deal statistics.

        Args:
            db: Database session
            current_user: The authenticated user

        Returns:
            Dictionary containing statistics
        """
        # Get permission-filtered base query
        base_query = db.query(Deal)
        filtered_query = get_deals_query_filter(db, current_user, base_query)

        # Delegate to service
        service = DealService(db)
        return service.get_deal_statistics(filtered_query=filtered_query)

    @staticmethod
    def get_revenue_data(
        db: Session,
        current_user: UserProfile,
        date_range: Optional[str] = None,
        owner_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Handle GET request to retrieve revenue analytics.

        Args:
            db: Database session
            current_user: The authenticated user
            date_range: Date range filter
            owner_id: Owner ID filter

        Returns:
            List of monthly revenue data
        """
        # Get permission-filtered base query
        base_query = db.query(Deal)
        filtered_query = get_deals_query_filter(db, current_user, base_query)

        # Apply owner filter only if user has permission
        owner_filter = None
        if owner_id and has_permission(db, current_user, "deals.view_all"):
            try:
                owner_filter = UUID(owner_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid owner_id format"
                )

        # Delegate to service
        service = DealService(db)
        return service.get_revenue_data(
            filtered_query=filtered_query,
            date_range=date_range,
            owner_id=owner_filter
        )

    @staticmethod
    def get_performance_metrics(
        db: Session,
        current_user: UserProfile,
        date_range: Optional[str] = None,
        owner_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle GET request to retrieve performance metrics.

        Args:
            db: Database session
            current_user: The authenticated user
            date_range: Date range filter
            owner_id: Owner ID filter

        Returns:
            Dictionary with performance metrics
        """
        # Get permission-filtered base query
        base_query = db.query(Deal)
        filtered_query = get_deals_query_filter(db, current_user, base_query)

        # Apply owner filter only if user has permission
        owner_filter = None
        if owner_id and has_permission(db, current_user, "deals.view_all"):
            try:
                owner_filter = UUID(owner_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid owner_id format"
                )

        # Delegate to service
        service = DealService(db)
        return service.get_performance_metrics(
            filtered_query=filtered_query,
            date_range=date_range,
            owner_id=owner_filter
        )

    @staticmethod
    def get_win_rate_data(
        db: Session,
        current_user: UserProfile,
        date_range: Optional[str] = None,
        owner_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Handle GET request to retrieve win rate analytics.

        Args:
            db: Database session
            current_user: The authenticated user
            date_range: Optional date range filter
            owner_id: Optional owner ID filter

        Returns:
            List of quarterly win rate data
        """
        # Get permission-filtered base query
        base_query = db.query(Deal)
        filtered_query = get_deals_query_filter(db, current_user, base_query)

        # Delegate to service with filters
        service = DealService(db)
        return service.get_win_rate_data(
            filtered_query=filtered_query,
            date_range=date_range,
            owner_id=owner_id
        )

    @staticmethod
    def get_filter_options(
        db: Session,
        current_user: UserProfile
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        Handle GET request to retrieve available filter options.

        Args:
            db: Database session
            current_user: The authenticated user

        Returns:
            Dictionary with available filter options
        """
        # Delegate to service
        service = DealService(db)
        return service.get_filter_options(current_user)

    @staticmethod
    def create_deal(
        deal_data: DealCreate,
        db: Session,
        current_user: UserProfile
    ) -> DealResponse:
        """
        Handle POST request to create a new deal.

        Args:
            deal_data: Deal creation data
            db: Database session
            current_user: The authenticated user

        Returns:
            Created deal

        Raises:
            HTTPException: If user doesn't have permission or creation fails
        """
        # Check permission
        if not has_permission(db, current_user, "deals.create"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to create deals"
            )

        try:
            # Delegate to service
            service = DealService(db)
            return service.create_deal(deal_data, current_user)

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create deal: {str(e)}"
            )

    @staticmethod
    def update_deal(
        deal_id: UUID,
        deal_data: DealUpdate,
        db: Session,
        current_user: UserProfile
    ) -> DealResponse:
        """
        Handle PUT request to update a deal.

        Args:
            deal_id: UUID of the deal to update
            deal_data: Deal update data
            db: Database session
            current_user: The authenticated user

        Returns:
            Updated deal

        Raises:
            HTTPException: If deal not found, user doesn't have permission, or update fails
        """
        # Get the deal first
        service = DealService(db)
        db_deal = service.repository.get(deal_id)

        if not db_deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deal not found"
            )

        # Check edit permission using helper function
        if not check_deal_edit_permission(db, current_user, db_deal):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to edit this deal"
            )

        try:
            # Delegate to service
            deal = service.update_deal(deal_id, deal_data)

            if not deal:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Deal with id {deal_id} not found"
                )

            return deal

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update deal: {str(e)}"
            )

    @staticmethod
    def delete_deal(
        deal_id: UUID,
        db: Session,
        current_user: UserProfile
    ) -> dict:
        """
        Handle DELETE request to delete a deal.

        Args:
            deal_id: UUID of the deal to delete
            db: Database session
            current_user: The authenticated user

        Returns:
            Success message

        Raises:
            HTTPException: If deal not found, user doesn't have permission, or deletion fails
        """
        # Get the deal first
        service = DealService(db)
        db_deal = service.repository.get(deal_id)

        if not db_deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deal not found"
            )

        # Check delete permission using helper function
        if not check_deal_delete_permission(db, current_user, db_deal):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this deal"
            )

        try:
            # Delegate to service
            success = service.delete_deal(deal_id)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Deal with id {deal_id} not found"
                )

            return {"message": "Deal deleted successfully"}

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete deal: {str(e)}"
            )
