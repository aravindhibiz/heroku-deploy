"""
Integration Controller - HTTP handling layer for Integration operations.
Manages request/response, permissions, and error handling.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..services.integration_service_new import IntegrationService
from ..models.user import UserProfile
from ..schemas.integration import (
    IntegrationResponse,
    IntegrationCreate,
    IntegrationUpdate,
    IntegrationLogResponse
)


class IntegrationController:
    """Controller for integration HTTP operations."""

    def __init__(self, db: Session):
        self.db = db
        self.service = IntegrationService(db)

    def list_integrations(
        self,
        current_user: UserProfile,
        include_logs: bool = False
    ) -> List[IntegrationResponse]:
        """
        Get all integrations for the current user.

        Args:
            current_user: Authenticated user
            include_logs: Whether to include logs

        Returns:
            List of integration responses
        """
        integrations = self.service.get_all_integrations(
            current_user.id,
            include_logs
        )
        return [IntegrationResponse.model_validate(i) for i in integrations]

    def get_integration(
        self,
        integration_id: UUID,
        current_user: UserProfile
    ) -> IntegrationResponse:
        """
        Get a specific integration.

        Args:
            integration_id: Integration UUID
            current_user: Authenticated user

        Returns:
            Integration response

        Raises:
            HTTPException: If not found or access denied
        """
        integration = self.service.get_integration_by_id(
            integration_id,
            current_user.id
        )

        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )

        return IntegrationResponse.model_validate(integration)

    def get_integration_by_provider(
        self,
        provider: str,
        current_user: UserProfile
    ) -> Optional[IntegrationResponse]:
        """
        Get integration by provider name.

        Args:
            provider: Provider name
            current_user: Authenticated user

        Returns:
            Integration response or None
        """
        integration = self.service.get_integration_by_provider(
            current_user.id,
            provider
        )

        if not integration:
            return None

        return IntegrationResponse.model_validate(integration)

    def create_integration(
        self,
        integration_data: IntegrationCreate,
        current_user: UserProfile
    ) -> IntegrationResponse:
        """
        Create a new integration.

        Args:
            integration_data: Integration creation data
            current_user: Authenticated user

        Returns:
            Created integration response

        Raises:
            HTTPException: If validation fails
        """
        try:
            integration = self.service.create_integration(
                integration_data,
                current_user.id
            )
            return IntegrationResponse.model_validate(integration)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    def update_integration(
        self,
        integration_id: UUID,
        integration_data: IntegrationUpdate,
        current_user: UserProfile
    ) -> IntegrationResponse:
        """
        Update an integration.

        Args:
            integration_id: Integration UUID
            integration_data: Update data
            current_user: Authenticated user

        Returns:
            Updated integration response

        Raises:
            HTTPException: If not found or validation fails
        """
        try:
            integration = self.service.update_integration(
                integration_id,
                integration_data,
                current_user.id
            )

            if not integration:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Integration not found"
                )

            return IntegrationResponse.model_validate(integration)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    def delete_integration(
        self,
        integration_id: UUID,
        current_user: UserProfile
    ) -> Dict[str, str]:
        """
        Delete an integration.

        Args:
            integration_id: Integration UUID
            current_user: Authenticated user

        Returns:
            Success message

        Raises:
            HTTPException: If not found
        """
        deleted = self.service.delete_integration(
            integration_id,
            current_user.id
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )

        return {"message": "Integration deleted successfully"}

    def connect_integration(
        self,
        integration_id: UUID,
        access_token: str,
        current_user: UserProfile,
        refresh_token: Optional[str] = None,
        expires_at: Optional[str] = None
    ) -> IntegrationResponse:
        """
        Connect an integration with OAuth tokens.

        Args:
            integration_id: Integration UUID
            access_token: OAuth access token
            current_user: Authenticated user
            refresh_token: Optional refresh token
            expires_at: Token expiry (ISO format)

        Returns:
            Connected integration response

        Raises:
            HTTPException: If not found
        """
        from datetime import datetime

        expires = None
        if expires_at:
            try:
                expires = datetime.fromisoformat(expires_at)
            except ValueError:
                pass

        integration = self.service.connect_integration(
            integration_id,
            current_user.id,
            access_token,
            refresh_token,
            expires
        )

        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )

        return IntegrationResponse.model_validate(integration)

    def disconnect_integration(
        self,
        integration_id: UUID,
        current_user: UserProfile
    ) -> Dict[str, str]:
        """
        Disconnect an integration.

        Args:
            integration_id: Integration UUID
            current_user: Authenticated user

        Returns:
            Success message

        Raises:
            HTTPException: If not found
        """
        integration = self.service.disconnect_integration(
            integration_id,
            current_user.id
        )

        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )

        return {"message": "Integration disconnected successfully"}

    def test_integration(
        self,
        integration_id: UUID,
        current_user: UserProfile
    ) -> Dict[str, Any]:
        """
        Test integration connection.

        Args:
            integration_id: Integration UUID
            current_user: Authenticated user

        Returns:
            Test result

        Raises:
            HTTPException: If test fails
        """
        try:
            result = self.service.test_connection(
                integration_id,
                current_user.id
            )
            return result
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Connection test failed: {str(e)}"
            )

    def sync_integration(
        self,
        integration_id: UUID,
        current_user: UserProfile,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Manually trigger integration sync.

        Args:
            integration_id: Integration UUID
            current_user: Authenticated user
            force: Force sync even if recently synced

        Returns:
            Sync result

        Raises:
            HTTPException: If sync fails
        """
        try:
            result = self.service.sync_integration(
                integration_id,
                current_user.id,
                force
            )
            return result
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Sync failed: {str(e)}"
            )

    def get_integration_logs(
        self,
        integration_id: UUID,
        current_user: UserProfile,
        limit: int = 50,
        offset: int = 0,
        action: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[IntegrationLogResponse]:
        """
        Get logs for an integration.

        Args:
            integration_id: Integration UUID
            current_user: Authenticated user
            limit: Maximum results
            offset: Results offset
            action: Optional action filter
            status: Optional status filter

        Returns:
            List of log responses
        """
        logs = self.service.get_integration_logs(
            integration_id,
            current_user.id,
            limit,
            offset,
            action,
            status
        )
        return [IntegrationLogResponse.model_validate(log) for log in logs]

    def get_sync_statistics(
        self,
        integration_id: UUID,
        current_user: UserProfile,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get sync statistics for an integration.

        Args:
            integration_id: Integration UUID
            current_user: Authenticated user
            days: Number of days to analyze

        Returns:
            Statistics dictionary
        """
        return self.service.get_sync_statistics(
            integration_id,
            current_user.id,
            days
        )

    def get_statistics(
        self,
        current_user: UserProfile
    ) -> Dict[str, Any]:
        """
        Get overall integration statistics.

        Args:
            current_user: Authenticated user

        Returns:
            Statistics dictionary
        """
        return self.service.get_statistics(current_user.id)

    def get_supported_providers(self) -> Dict[str, Dict[str, Any]]:
        """
        Get list of supported integration providers.

        Returns:
            Provider configurations
        """
        return self.service.get_supported_providers()

    async def get_oauth_url(
        self,
        provider: str,
        current_user: UserProfile
    ) -> Dict[str, str]:
        """
        Get OAuth authorization URL for a provider.

        Args:
            provider: Provider name
            current_user: Authenticated user

        Returns:
            Dictionary with auth_url

        Raises:
            HTTPException: If provider not supported or OAuth fails
        """
        try:
            auth_url = await self.service.get_oauth_url(
                provider,
                current_user.id
            )
            return {"auth_url": auth_url}
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate OAuth URL: {str(e)}"
            )

    async def handle_oauth_callback(
        self,
        provider: str,
        code: str,
        current_user: UserProfile,
        state: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle OAuth callback and connect integration.

        Args:
            provider: Provider name
            code: OAuth authorization code
            current_user: Authenticated user
            state: OAuth state parameter

        Returns:
            Success message with integration_id

        Raises:
            HTTPException: If OAuth exchange fails
        """
        try:
            integration = await self.service.handle_oauth_callback(
                provider,
                code,
                current_user.id,
                state
            )
            return {
                "message": "Integration connected successfully",
                "integration_id": str(integration.id),
                "provider": provider
            }
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OAuth callback failed: {str(e)}"
            )
