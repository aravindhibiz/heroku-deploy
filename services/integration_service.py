import os
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from uuid import UUID
import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from models.integration import Integration, IntegrationLog
from models.user import UserProfile
from core.config import settings


class IntegrationService:
    def __init__(self, db: Session):
        self.db = db

        # OAuth configurations
        self.oauth_configs = {
            'gmail': {
                'scopes': [
                    'https://www.googleapis.com/auth/gmail.readonly',
                    'https://www.googleapis.com/auth/gmail.send',
                    'https://www.googleapis.com/auth/contacts.readonly'
                ],
                'redirect_uri': f"{settings.FRONTEND_URL}/integrations/oauth/callback"
            },
            'google_calendar': {
                'scopes': [
                    'https://www.googleapis.com/auth/calendar.readonly',
                    'https://www.googleapis.com/auth/calendar.events'
                ],
                'redirect_uri': f"{settings.FRONTEND_URL}/integrations/oauth/callback"
            }
        }

    async def get_oauth_url(self, provider: str, user_id: UUID) -> str:
        """Generate OAuth authorization URL"""
        if provider not in self.oauth_configs:
            raise ValueError(f"Unsupported provider: {provider}")

        config = self.oauth_configs[provider]

        # Google OAuth flow
        if provider in ['gmail', 'google_calendar']:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token"
                    }
                },
                scopes=config['scopes']
            )
            flow.redirect_uri = config['redirect_uri']

            # Include user_id and provider in state for callback
            state = f"{user_id}:{provider}"

            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='false',  # Don't include previously granted scopes
                state=state,
                prompt='select_account consent'  # Force account selection and consent
            )

            return auth_url

        raise ValueError(f"OAuth not implemented for provider: {provider}")

    async def handle_oauth_callback(self, provider: str, code: str, user_id: UUID, state: Optional[str] = None) -> Integration:
        """Handle OAuth callback and store tokens"""
        if provider not in self.oauth_configs:
            raise ValueError(f"Unsupported provider: {provider}")

        config = self.oauth_configs[provider]

        # Google OAuth callback
        if provider in ['gmail', 'google_calendar']:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token"
                    }
                },
                scopes=config['scopes']
            )
            flow.redirect_uri = config['redirect_uri']

            # Exchange code for tokens
            flow.fetch_token(code=code)
            credentials = flow.credentials

            # Get or create integration
            integration = self.db.query(Integration).filter(
                Integration.user_id == user_id,
                Integration.provider == provider
            ).first()

            if not integration:
                # Create new integration
                integration_name = "Gmail Integration" if provider == 'gmail' else "Google Calendar Integration"
                integration = Integration(
                    user_id=user_id,
                    provider=provider,
                    name=integration_name,
                    description=f"Sync with {provider.replace('_', ' ').title()}",
                    status='connected'
                )
                self.db.add(integration)

            # Store encrypted tokens (in production, use proper encryption)
            integration.access_token = credentials.token
            integration.refresh_token = credentials.refresh_token
            integration.token_expires_at = credentials.expiry
            integration.status = 'connected'
            integration.last_sync = datetime.utcnow()

            self.db.commit()
            self.db.refresh(integration)

            # Log the connection
            await self._log_integration_action(
                integration.id,
                'connect',
                'success',
                f"Successfully connected {provider.replace('_', ' ').title()}"
            )

            return integration

        raise ValueError(
            f"OAuth callback not implemented for provider: {provider}")

    async def test_integration(self, integration_id: UUID) -> Dict[str, Any]:
        """Test integration connection"""
        integration = self.db.query(Integration).filter(
            Integration.id == integration_id
        ).first()

        if not integration:
            raise ValueError("Integration not found")

        try:
            if integration.provider == 'gmail':
                result = await self._test_gmail_connection(integration)
            elif integration.provider == 'google_calendar':
                result = await self._test_calendar_connection(integration)
            else:
                raise ValueError(
                    f"Test not implemented for provider: {integration.provider}")

            # Update integration status
            integration.status = 'connected' if result['success'] else 'error'
            integration.last_error = None if result['success'] else result.get(
                'error')
            self.db.commit()

            # Log the test
            await self._log_integration_action(
                integration_id,
                'test',
                'success' if result['success'] else 'error',
                result.get('message', 'Connection test completed')
            )

            return result

        except Exception as e:
            integration.status = 'error'
            integration.last_error = str(e)
            self.db.commit()

            await self._log_integration_action(
                integration_id,
                'test',
                'error',
                f"Connection test failed: {str(e)}"
            )

            raise e

    async def sync_integration(self, integration_id: UUID, force: bool = False) -> Dict[str, Any]:
        """Sync integration data"""
        integration = self.db.query(Integration).filter(
            Integration.id == integration_id
        ).first()

        if not integration:
            raise ValueError("Integration not found")

        if integration.status != 'connected':
            raise ValueError("Integration is not connected")

        try:
            if integration.provider == 'gmail':
                result = await self._sync_gmail_data(integration, force)
            elif integration.provider == 'google_calendar':
                result = await self._sync_calendar_data(integration, force)
            else:
                raise ValueError(
                    f"Sync not implemented for provider: {integration.provider}")

            # Update last sync time
            integration.last_sync = datetime.utcnow()
            integration.sync_status = 'idle'
            self.db.commit()

            # Log the sync
            await self._log_integration_action(
                integration_id,
                'sync',
                'success',
                f"Sync completed: {result.get('summary', '')}",
                result
            )

            return result

        except Exception as e:
            integration.sync_status = 'error'
            integration.last_error = str(e)
            self.db.commit()

            await self._log_integration_action(
                integration_id,
                'sync',
                'error',
                f"Sync failed: {str(e)}"
            )

            raise e

    async def disconnect_integration(self, integration_id: UUID, user_id: UUID):
        """Disconnect an integration"""
        integration = self.db.query(Integration).filter(
            Integration.id == integration_id,
            Integration.user_id == user_id
        ).first()

        if not integration:
            raise ValueError("Integration not found")

        # Clear tokens
        integration.access_token = None
        integration.refresh_token = None
        integration.token_expires_at = None
        integration.status = 'disconnected'
        integration.last_error = None

        self.db.commit()

        await self._log_integration_action(
            integration_id,
            'disconnect',
            'success',
            f"Successfully disconnected {integration.provider.replace('_', ' ').title()}"
        )

    async def _test_gmail_connection(self, integration: Integration) -> Dict[str, Any]:
        """Test Gmail connection"""
        try:
            credentials = self._get_google_credentials(integration)
            service = build('gmail', 'v1', credentials=credentials)

            # Test by getting user profile
            profile = service.users().getProfile(userId='me').execute()

            return {
                'success': True,
                'message': f"Connected to Gmail account: {profile.get('emailAddress')}",
                'details': {
                    'email': profile.get('emailAddress'),
                    'messages_total': profile.get('messagesTotal', 0),
                    'threads_total': profile.get('threadsTotal', 0)
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to connect to Gmail'
            }

    async def _test_calendar_connection(self, integration: Integration) -> Dict[str, Any]:
        """Test Google Calendar connection"""
        try:
            credentials = self._get_google_credentials(integration)
            service = build('calendar', 'v3', credentials=credentials)

            # Test by getting calendar list
            calendars = service.calendarList().list().execute()

            primary_calendar = None
            for calendar in calendars.get('items', []):
                if calendar.get('primary'):
                    primary_calendar = calendar
                    break

            return {
                'success': True,
                'message': f"Connected to Google Calendar",
                'details': {
                    'calendars_count': len(calendars.get('items', [])),
                    'primary_calendar': primary_calendar.get('summary') if primary_calendar else 'None'
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to connect to Google Calendar'
            }

    async def _sync_gmail_data(self, integration: Integration, force: bool = False) -> Dict[str, Any]:
        """Sync Gmail data (placeholder implementation)"""
        # This is a simplified implementation
        # In production, this would:
        # 1. Fetch emails from Gmail API
        # 2. Match emails to existing contacts/deals
        # 3. Create new contacts if enabled
        # 4. Log emails as activities

        return {
            'success': True,
            'summary': 'Gmail sync completed (placeholder)',
            'emails_processed': 0,
            'contacts_created': 0,
            'activities_created': 0
        }

    async def _sync_calendar_data(self, integration: Integration, force: bool = False) -> Dict[str, Any]:
        """Sync Google Calendar data (placeholder implementation)"""
        # This is a simplified implementation
        # In production, this would:
        # 1. Fetch calendar events from Google Calendar API
        # 2. Create/update activities in CRM
        # 3. Sync meeting details with deals/contacts

        return {
            'success': True,
            'summary': 'Calendar sync completed (placeholder)',
            'events_processed': 0,
            'activities_created': 0,
            'activities_updated': 0
        }

    def _get_google_credentials(self, integration: Integration) -> Credentials:
        """Get Google credentials from integration"""
        if not integration.access_token:
            raise ValueError("No access token available")

        credentials = Credentials(
            token=integration.access_token,
            refresh_token=integration.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )

        # Refresh token if expired
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())

            # Update stored tokens
            integration.access_token = credentials.token
            integration.token_expires_at = credentials.expiry
            self.db.commit()

        return credentials

    async def _log_integration_action(
        self,
        integration_id: UUID,
        action: str,
        status: str,
        message: str,
        details: Dict[str, Any] = None
    ):
        """Log integration action"""
        log = IntegrationLog(
            integration_id=integration_id,
            action=action,
            status=status,
            message=message,
            details=details or {}
        )

        self.db.add(log)
        self.db.commit()
