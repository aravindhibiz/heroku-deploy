"""
Integration Service - Business logic layer for Integration operations.
Handles OAuth flows, sync operations, and provider-specific logic.
"""

import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.orm import Session

from ..repositories.integration_repository import (
    IntegrationRepository,
    IntegrationLogRepository,
    IntegrationWebhookRepository
)
from ..models.integration import Integration, IntegrationLog
from ..schemas.integration import IntegrationCreate, IntegrationUpdate


class IntegrationService:
    """Service layer for integration business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = IntegrationRepository(db)
        self.log_repository = IntegrationLogRepository(db)
        self.webhook_repository = IntegrationWebhookRepository(db)

    # Supported providers configuration
    SUPPORTED_PROVIDERS = {
        'gmail': {
            'name': 'Gmail',
            'description': 'Email integration with Gmail',
            'auth_type': 'oauth2',
            'features': ['email_sync', 'contact_sync', 'send_email']
        },
        'google_calendar': {
            'name': 'Google Calendar',
            'description': 'Calendar and meeting integration',
            'auth_type': 'oauth2',
            'features': ['calendar_sync', 'event_sync', 'meeting_sync']
        },
        'twilio': {
            'name': 'Twilio',
            'description': 'SMS and calling integration',
            'auth_type': 'api_key',
            'features': ['sms', 'voice', 'whatsapp']
        },
        'slack': {
            'name': 'Slack',
            'description': 'Team communication integration',
            'auth_type': 'oauth2',
            'features': ['notifications', 'channel_sync']
        },
        'zapier': {
            'name': 'Zapier',
            'description': 'Automation and workflow integration',
            'auth_type': 'webhook',
            'features': ['automation', 'triggers']
        }
    }

    # Sync frequency mappings (in minutes)
    SYNC_FREQUENCIES = {
        '5min': 5,
        '15min': 15,
        '30min': 30,
        '1hour': 60,
        '3hours': 180,
        '6hours': 360,
        '12hours': 720,
        '24hours': 1440,
        'manual': None
    }

    def get_all_integrations(
        self,
        user_id: UUID,
        include_logs: bool = False
    ) -> List[Integration]:
        """
        Get all integrations for a user.

        Args:
            user_id: User UUID
            include_logs: Whether to include logs

        Returns:
            List of integrations
        """
        return self.repository.get_by_user(user_id, include_logs)

    def get_integration_by_id(
        self,
        integration_id: UUID,
        user_id: UUID
    ) -> Optional[Integration]:
        """
        Get a specific integration.

        Args:
            integration_id: Integration UUID
            user_id: User UUID for ownership validation

        Returns:
            Integration or None
        """
        integration = self.repository.get(integration_id)

        # Verify ownership
        if integration and integration.user_id != user_id:
            return None

        return integration

    def get_integration_by_provider(
        self,
        user_id: UUID,
        provider: str
    ) -> Optional[Integration]:
        """
        Get integration by provider.

        Args:
            user_id: User UUID
            provider: Provider name

        Returns:
            Integration or None
        """
        return self.repository.get_by_user_and_provider(user_id, provider)

    def create_integration(
        self,
        integration_data: IntegrationCreate,
        user_id: UUID
    ) -> Integration:
        """
        Create a new integration.

        Args:
            integration_data: Integration creation data
            user_id: User UUID

        Returns:
            Created integration

        Raises:
            ValueError: If provider unsupported or already exists
        """
        # Validate provider
        if integration_data.provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported provider: {integration_data.provider}. "
                f"Supported: {', '.join(self.SUPPORTED_PROVIDERS.keys())}"
            )

        # Check for existing integration
        existing = self.repository.get_by_user_and_provider(
            user_id,
            integration_data.provider
        )
        if existing:
            raise ValueError(
                f"Integration for {integration_data.provider} already exists"
            )

        # Validate sync frequency
        if integration_data.sync_frequency not in self.SYNC_FREQUENCIES:
            raise ValueError(
                f"Invalid sync frequency. "
                f"Valid: {', '.join(self.SYNC_FREQUENCIES.keys())}"
            )

        # Create integration
        integration = Integration(
            user_id=user_id,
            provider=integration_data.provider,
            name=integration_data.name,
            description=integration_data.description,
            config=integration_data.config or {},
            auto_sync=integration_data.auto_sync,
            sync_frequency=integration_data.sync_frequency,
            status='disconnected'
        )

        created = self.repository.create(integration)

        # Log creation
        self.log_repository.create_log(
            created.id,
            'create',
            'success',
            f"Integration created for {integration_data.provider}"
        )

        return created

    def update_integration(
        self,
        integration_id: UUID,
        integration_data: IntegrationUpdate,
        user_id: UUID
    ) -> Optional[Integration]:
        """
        Update an integration.

        Args:
            integration_id: Integration UUID
            integration_data: Update data
            user_id: User UUID for ownership validation

        Returns:
            Updated integration or None

        Raises:
            ValueError: If validation fails
        """
        integration = self.get_integration_by_id(integration_id, user_id)
        if not integration:
            return None

        # Validate sync frequency if provided
        if integration_data.sync_frequency:
            if integration_data.sync_frequency not in self.SYNC_FREQUENCIES:
                raise ValueError(
                    f"Invalid sync frequency. "
                    f"Valid: {', '.join(self.SYNC_FREQUENCIES.keys())}"
                )

        # Update fields
        update_dict = integration_data.dict(exclude_unset=True)
        updated = self.repository.update(integration_id, update_dict)

        # Log update
        self.log_repository.create_log(
            integration_id,
            'update',
            'success',
            f"Integration settings updated"
        )

        return updated

    def delete_integration(
        self,
        integration_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Delete an integration.

        Args:
            integration_id: Integration UUID
            user_id: User UUID for ownership validation

        Returns:
            True if deleted, False if not found
        """
        integration = self.get_integration_by_id(integration_id, user_id)
        if not integration:
            return False

        # Disconnect first if connected
        if integration.status == 'connected':
            self.disconnect_integration(integration_id, user_id)

        # Log deletion
        self.log_repository.create_log(
            integration_id,
            'delete',
            'success',
            f"Integration deleted for {integration.provider}"
        )

        # Delete integration (cascades to logs and webhooks)
        return self.repository.delete(integration_id)

    def connect_integration(
        self,
        integration_id: UUID,
        user_id: UUID,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> Optional[Integration]:
        """
        Connect an integration with OAuth tokens.

        Args:
            integration_id: Integration UUID
            user_id: User UUID
            access_token: OAuth access token
            refresh_token: Optional refresh token
            expires_at: Token expiry

        Returns:
            Connected integration or None
        """
        integration = self.get_integration_by_id(integration_id, user_id)
        if not integration:
            return None

        # Update tokens
        updated = self.repository.update_tokens(
            integration_id,
            access_token,
            refresh_token,
            expires_at
        )

        # Update status
        if updated:
            self.repository.update_status(integration_id, 'connected')

            # Log connection
            self.log_repository.create_log(
                integration_id,
                'connect',
                'success',
                f"Successfully connected to {integration.provider}"
            )

        return updated

    def disconnect_integration(
        self,
        integration_id: UUID,
        user_id: UUID
    ) -> Optional[Integration]:
        """
        Disconnect an integration.

        Args:
            integration_id: Integration UUID
            user_id: User UUID

        Returns:
            Disconnected integration or None
        """
        integration = self.get_integration_by_id(integration_id, user_id)
        if not integration:
            return None

        # Clear tokens and update status
        integration.access_token = None
        integration.refresh_token = None
        integration.expires_at = None
        integration.last_error = None
        integration.error_count = "0"

        updated = self.repository.update_status(integration_id, 'disconnected')

        # Log disconnection
        self.log_repository.create_log(
            integration_id,
            'disconnect',
            'success',
            f"Disconnected from {integration.provider}"
        )

        return updated

    def test_connection(
        self,
        integration_id: UUID,
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Test integration connection.

        Args:
            integration_id: Integration UUID
            user_id: User UUID

        Returns:
            Test result dictionary

        Raises:
            ValueError: If integration not found or not connected
        """
        integration = self.get_integration_by_id(integration_id, user_id)
        if not integration:
            raise ValueError("Integration not found")

        if integration.status != 'connected':
            raise ValueError(
                "Integration must be connected before testing"
            )

        # Log test start
        self.log_repository.create_log(
            integration_id,
            'test',
            'info',
            f"Testing connection to {integration.provider}"
        )

        # Provider-specific test logic would go here
        # For now, return success if connected
        result = {
            'success': True,
            'provider': integration.provider,
            'message': f"Connection to {integration.provider} is active",
            'tested_at': datetime.utcnow().isoformat()
        }

        # Log test result
        self.log_repository.create_log(
            integration_id,
            'test',
            'success',
            result['message']
        )

        return result

    def sync_integration(
        self,
        integration_id: UUID,
        user_id: UUID,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Manually trigger integration sync.

        Args:
            integration_id: Integration UUID
            user_id: User UUID
            force: Force sync even if recently synced

        Returns:
            Sync result dictionary

        Raises:
            ValueError: If integration not found or not connected
        """
        integration = self.get_integration_by_id(integration_id, user_id)
        if not integration:
            raise ValueError("Integration not found")

        if integration.status != 'connected':
            raise ValueError("Integration must be connected to sync")

        # Check if recently synced (unless force=True)
        if not force and integration.last_sync:
            frequency_minutes = self.SYNC_FREQUENCIES.get(
                integration.sync_frequency
            )
            if frequency_minutes:
                next_sync = integration.last_sync + \
                    timedelta(minutes=frequency_minutes)
                if datetime.utcnow() < next_sync:
                    raise ValueError(
                        f"Integration was recently synced. "
                        f"Next sync scheduled at {next_sync.isoformat()}"
                    )

        # Log sync start
        self.log_repository.create_log(
            integration_id,
            'sync',
            'info',
            f"Starting sync for {integration.provider}"
        )

        # Provider-specific sync logic would go here
        # For now, return placeholder result
        result = {
            'success': True,
            'provider': integration.provider,
            'records_processed': 0,
            'records_created': 0,
            'records_updated': 0,
            'records_failed': 0,
            'synced_at': datetime.utcnow().isoformat()
        }

        # Update last sync
        self.repository.update_last_sync(integration_id)

        # Log sync completion
        self.log_repository.create_log(
            integration_id,
            'sync',
            'success',
            f"Sync completed for {integration.provider}",
            details=result,
            records_processed=result['records_processed'],
            records_created=result['records_created'],
            records_updated=result['records_updated'],
            records_failed=result['records_failed']
        )

        return result

    def get_integration_logs(
        self,
        integration_id: UUID,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
        action: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[IntegrationLog]:
        """
        Get logs for an integration.

        Args:
            integration_id: Integration UUID
            user_id: User UUID for ownership validation
            limit: Maximum results
            offset: Results offset
            action: Optional action filter
            status: Optional status filter

        Returns:
            List of logs
        """
        # Verify ownership
        integration = self.get_integration_by_id(integration_id, user_id)
        if not integration:
            return []

        return self.log_repository.get_by_integration(
            integration_id,
            limit,
            offset,
            action,
            status
        )

    def get_sync_statistics(
        self,
        integration_id: UUID,
        user_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get sync statistics for an integration.

        Args:
            integration_id: Integration UUID
            user_id: User UUID
            days: Number of days to analyze

        Returns:
            Statistics dictionary
        """
        # Verify ownership
        integration = self.get_integration_by_id(integration_id, user_id)
        if not integration:
            return {}

        return self.log_repository.get_sync_statistics(integration_id, days)

    def get_statistics(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get overall integration statistics for a user.

        Args:
            user_id: User UUID

        Returns:
            Statistics dictionary
        """
        return self.repository.get_statistics(user_id)

    def get_supported_providers(self) -> Dict[str, Dict[str, Any]]:
        """
        Get list of supported integration providers.

        Returns:
            Dictionary of provider configurations
        """
        return self.SUPPORTED_PROVIDERS

    def is_sync_due(self, integration: Integration) -> bool:
        """
        Check if integration is due for sync.

        Args:
            integration: Integration instance

        Returns:
            True if sync is due
        """
        if not integration.auto_sync:
            return False

        if integration.status != 'connected':
            return False

        if integration.sync_frequency == 'manual':
            return False

        if not integration.last_sync:
            return True

        frequency_minutes = self.SYNC_FREQUENCIES.get(
            integration.sync_frequency
        )
        if not frequency_minutes:
            return False

        next_sync = integration.last_sync + \
            timedelta(minutes=frequency_minutes)
        return datetime.utcnow() >= next_sync

    async def get_oauth_url(self, provider: str, user_id: UUID) -> str:
        """
        Generate OAuth authorization URL for a provider.

        Args:
            provider: Provider name (gmail, google_calendar, etc.)
            user_id: User UUID for state tracking

        Returns:
            OAuth authorization URL

        Raises:
            ValueError: If provider not supported or OAuth not available
        """
        if provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unsupported provider: {provider}. "
                f"Supported: {', '.join(self.SUPPORTED_PROVIDERS.keys())}"
            )

        provider_config = self.SUPPORTED_PROVIDERS[provider]

        if provider_config['auth_type'] != 'oauth2':
            raise ValueError(
                f"Provider {provider} does not use OAuth2 authentication. "
                f"Auth type: {provider_config['auth_type']}"
            )

        # Google OAuth (Gmail, Google Calendar)
        if provider in ['gmail', 'google_calendar']:
            try:
                from google_auth_oauthlib.flow import Flow
                from ..core.config import settings

                # OAuth scopes per provider
                scopes = {
                    'gmail': [
                        'https://www.googleapis.com/auth/gmail.readonly',
                        'https://www.googleapis.com/auth/gmail.send',
                        'https://www.googleapis.com/auth/contacts.readonly'
                    ],
                    'google_calendar': [
                        'https://www.googleapis.com/auth/calendar.readonly',
                        'https://www.googleapis.com/auth/calendar.events'
                    ]
                }

                flow = Flow.from_client_config(
                    {
                        "web": {
                            "client_id": settings.GOOGLE_CLIENT_ID,
                            "client_secret": settings.GOOGLE_CLIENT_SECRET,
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token"
                        }
                    },
                    scopes=scopes[provider]
                )

                flow.redirect_uri = f"{settings.FRONTEND_URL}/integrations/oauth/callback"

                # Include user_id and provider in state for callback
                state = f"{user_id}:{provider}"

                auth_url, _ = flow.authorization_url(
                    access_type='offline',
                    include_granted_scopes='false',
                    state=state,
                    prompt='select_account consent'
                )

                return auth_url

            except ImportError:
                raise ValueError(
                    "Google OAuth libraries not installed. "
                    "Install google-auth-oauthlib and google-api-python-client"
                )
            except Exception as e:
                raise ValueError(f"Failed to generate OAuth URL: {str(e)}")

        # Slack OAuth
        elif provider == 'slack':
            raise ValueError("Slack OAuth not yet implemented")

        else:
            raise ValueError(
                f"OAuth URL generation not implemented for {provider}")

    async def handle_oauth_callback(
        self,
        provider: str,
        code: str,
        user_id: UUID,
        state: Optional[str] = None
    ) -> Integration:
        """
        Handle OAuth callback and store tokens.

        Args:
            provider: Provider name
            code: OAuth authorization code
            user_id: User UUID
            state: OAuth state parameter

        Returns:
            Connected integration

        Raises:
            ValueError: If OAuth exchange fails
        """
        if provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")

        # Google OAuth callback
        if provider in ['gmail', 'google_calendar']:
            try:
                from google_auth_oauthlib.flow import Flow
                from ..core.config import settings

                scopes = {
                    'gmail': [
                        'https://www.googleapis.com/auth/gmail.readonly',
                        'https://www.googleapis.com/auth/gmail.send',
                        'https://www.googleapis.com/auth/contacts.readonly'
                    ],
                    'google_calendar': [
                        'https://www.googleapis.com/auth/calendar.readonly',
                        'https://www.googleapis.com/auth/calendar.events'
                    ]
                }

                flow = Flow.from_client_config(
                    {
                        "web": {
                            "client_id": settings.GOOGLE_CLIENT_ID,
                            "client_secret": settings.GOOGLE_CLIENT_SECRET,
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token"
                        }
                    },
                    scopes=scopes[provider]
                )

                flow.redirect_uri = f"{settings.FRONTEND_URL}/integrations/oauth/callback"

                # Exchange code for tokens
                flow.fetch_token(code=code)
                credentials = flow.credentials

                # Get or create integration
                integration = self.repository.get_by_user_and_provider(
                    user_id,
                    provider
                )

                if not integration:
                    # Create new integration
                    integration_name = (
                        "Gmail Integration" if provider == 'gmail'
                        else "Google Calendar Integration"
                    )

                    from ..models.integration import Integration as IntegrationModel
                    integration = IntegrationModel(
                        user_id=user_id,
                        provider=provider,
                        name=integration_name,
                        description=f"Sync with {provider.replace('_', ' ').title()}",
                        status='connected'
                    )
                    integration = self.repository.create(integration)

                # Update tokens
                integration = self.repository.update_tokens(
                    integration.id,
                    credentials.token,
                    credentials.refresh_token,
                    credentials.expiry
                )

                # Update status
                self.repository.update_status(integration.id, 'connected')
                self.repository.update_last_sync(integration.id)

                # Log connection
                self.log_repository.create_log(
                    integration.id,
                    'connect',
                    'success',
                    f"Successfully connected {provider.replace('_', ' ').title()}"
                )

                return integration

            except Exception as e:
                raise ValueError(f"OAuth callback failed: {str(e)}")

        else:
            raise ValueError(f"OAuth callback not implemented for {provider}")
