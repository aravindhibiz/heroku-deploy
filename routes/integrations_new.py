"""
Integration Routes - Clean API endpoint definitions for Integrations.
All business logic is in IntegrationController.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.database import get_db
from core.auth import get_current_user
from models.user import UserProfile
from controllers.integration_controller import IntegrationController
from schemas.integration import (
    IntegrationResponse,
    IntegrationCreate,
    IntegrationUpdate,
    IntegrationLogResponse,
    OAuthCallbackRequest
)

router = APIRouter()


# ==================== INTEGRATION ENDPOINTS ====================

@router.get("/", response_model=List[IntegrationResponse])
async def get_integrations(
    include_logs: bool = Query(False, description="Include integration logs"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get all integrations for the current user.

    **Returns:**
    - List of all integrations with their configuration and status
    - Optionally includes recent logs if include_logs=true

    **Use Cases:**
    - View all connected services
    - Check integration status
    - Review sync configurations
    """
    controller = IntegrationController(db)
    return controller.list_integrations(current_user, include_logs)


@router.get("/providers")
async def get_supported_providers(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get list of supported integration providers.

    **Returns:**
    - Dictionary of available providers with features and auth types

    **Providers:**
    - Gmail - Email and contact sync
    - Google Calendar - Calendar and meeting sync
    - Twilio - SMS and calling
    - Slack - Team notifications
    - Zapier - Automation workflows
    """
    controller = IntegrationController(db)
    return controller.get_supported_providers()


@router.get("/stats")
async def get_integration_statistics(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get overall integration statistics for the user.

    **Returns:**
    - Total integrations
    - Connected/disconnected/error counts
    - Breakdown by provider
    - Auto-sync statistics
    """
    controller = IntegrationController(db)
    return controller.get_statistics(current_user)


@router.get("/provider/{provider}", response_model=IntegrationResponse)
async def get_integration_by_provider(
    provider: str,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get integration by provider name.

    **Path Parameters:**
    - provider: Provider name (gmail, google_calendar, twilio, slack, zapier)

    **Returns:**
    - Integration details if exists
    - 404 if integration not found
    """
    controller = IntegrationController(db)
    integration = controller.get_integration_by_provider(
        provider, current_user)

    if not integration:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No integration found for provider: {provider}"
        )

    return integration


@router.get("/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get a specific integration by ID.

    **Path Parameters:**
    - integration_id: Integration UUID

    **Returns:**
    - Complete integration details
    - Configuration and status
    - Last sync information
    """
    controller = IntegrationController(db)
    return controller.get_integration(integration_id, current_user)


@router.post("/", response_model=IntegrationResponse, status_code=201)
async def create_integration(
    integration_data: IntegrationCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Create a new integration.

    **Request Body:**
    - provider: Provider name (required)
    - name: Integration name (required)
    - description: Optional description
    - config: Provider-specific configuration
    - auto_sync: Enable automatic syncing (default: true)
    - sync_frequency: Sync interval (5min, 15min, 1hour, manual, etc.)

    **Validation:**
    - Provider must be supported
    - Only one integration per provider per user
    - Sync frequency must be valid

    **Status:** 201 Created
    """
    controller = IntegrationController(db)
    return controller.create_integration(integration_data, current_user)


@router.put("/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_id: UUID,
    integration_data: IntegrationUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Update an integration's configuration.

    **Path Parameters:**
    - integration_id: Integration UUID

    **Request Body:** (all fields optional)
    - name: Update integration name
    - description: Update description
    - config: Update provider configuration
    - auto_sync: Enable/disable auto-sync
    - sync_frequency: Change sync interval

    **Note:** Does not update connection status or tokens
    """
    controller = IntegrationController(db)
    return controller.update_integration(
        integration_id,
        integration_data,
        current_user
    )


@router.delete("/{integration_id}")
async def delete_integration(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Delete an integration.

    **Path Parameters:**
    - integration_id: Integration UUID

    **Process:**
    - Automatically disconnects if connected
    - Removes all tokens and credentials
    - Deletes all logs and webhooks (cascade)

    **Returns:**
    - Success message
    """
    controller = IntegrationController(db)
    return controller.delete_integration(integration_id, current_user)


# ==================== CONNECTION MANAGEMENT ====================

@router.post("/{integration_id}/connect", response_model=IntegrationResponse)
async def connect_integration(
    integration_id: UUID,
    access_token: str,
    refresh_token: Optional[str] = None,
    expires_at: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Connect an integration with OAuth tokens.

    **Path Parameters:**
    - integration_id: Integration UUID

    **Request Parameters:**
    - access_token: OAuth access token (required)
    - refresh_token: OAuth refresh token (optional)
    - expires_at: Token expiry in ISO format (optional)

    **Process:**
    - Stores encrypted tokens
    - Updates status to 'connected'
    - Logs connection event

    **Use Case:** Called after OAuth callback
    """
    controller = IntegrationController(db)
    return controller.connect_integration(
        integration_id,
        access_token,
        current_user,
        refresh_token,
        expires_at
    )


@router.post("/{integration_id}/disconnect")
async def disconnect_integration(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Disconnect an integration.

    **Path Parameters:**
    - integration_id: Integration UUID

    **Process:**
    - Clears all OAuth tokens
    - Updates status to 'disconnected'
    - Resets error counts
    - Logs disconnection event

    **Returns:**
    - Success message
    """
    controller = IntegrationController(db)
    return controller.disconnect_integration(integration_id, current_user)


@router.post("/{integration_id}/test")
async def test_integration(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Test integration connection.

    **Path Parameters:**
    - integration_id: Integration UUID

    **Requirements:**
    - Integration must be connected

    **Process:**
    - Validates credentials
    - Tests API connectivity
    - Returns provider-specific details

    **Returns:**
    - success: Test result (true/false)
    - message: Test outcome description
    - provider: Provider name
    - tested_at: Timestamp
    """
    controller = IntegrationController(db)
    return controller.test_integration(integration_id, current_user)


# ==================== SYNC OPERATIONS ====================

@router.post("/{integration_id}/sync")
async def sync_integration(
    integration_id: UUID,
    force: bool = Query(
        False, description="Force sync even if recently synced"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Manually trigger integration sync.

    **Path Parameters:**
    - integration_id: Integration UUID

    **Query Parameters:**
    - force: Skip sync frequency check (default: false)

    **Requirements:**
    - Integration must be connected
    - Respects sync frequency unless force=true

    **Process:**
    - Fetches data from provider
    - Updates CRM records
    - Logs sync results
    - Updates last_sync timestamp

    **Returns:**
    - success: Sync result
    - records_processed: Total processed
    - records_created: New records
    - records_updated: Updated records
    - records_failed: Failed records
    - synced_at: Sync timestamp
    """
    controller = IntegrationController(db)
    return controller.sync_integration(integration_id, current_user, force)


@router.get("/{integration_id}/sync/stats")
async def get_sync_statistics(
    integration_id: UUID,
    days: int = Query(30, ge=1, le=365,
                      description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get sync statistics for an integration.

    **Path Parameters:**
    - integration_id: Integration UUID

    **Query Parameters:**
    - days: Analysis period (1-365, default: 30)

    **Returns:**
    - period_days: Analysis period
    - total_syncs: Total sync attempts
    - successful_syncs: Successful syncs
    - failed_syncs: Failed syncs
    - total_records_processed: All processed
    - total_records_created: All created
    - total_records_updated: All updated
    - total_records_failed: All failed
    - success_rate: Percentage of successful syncs
    """
    controller = IntegrationController(db)
    return controller.get_sync_statistics(integration_id, current_user, days)


# ==================== LOGS ====================

@router.get("/{integration_id}/logs", response_model=List[IntegrationLogResponse])
async def get_integration_logs(
    integration_id: UUID,
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    action: Optional[str] = Query(None, description="Filter by action"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get logs for an integration.

    **Path Parameters:**
    - integration_id: Integration UUID

    **Query Parameters:**
    - limit: Maximum results (1-100, default: 50)
    - offset: Skip records (default: 0)
    - action: Filter by action (connect, disconnect, sync, test, error)
    - status: Filter by status (success, error, warning, info)

    **Returns:**
    - List of log entries ordered by newest first
    - Each log includes action, status, message, and details

    **Use Cases:**
    - Audit trail
    - Debugging sync issues
    - Monitoring integration health
    """
    controller = IntegrationController(db)
    return controller.get_integration_logs(
        integration_id,
        current_user,
        limit,
        offset,
        action,
        status
    )


# ==================== OAUTH ENDPOINTS ====================

@router.post("/oauth/url")
async def get_oauth_authorization_url(
    provider: str = Query(...,
                          description="Provider name (gmail, google_calendar, slack)"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get OAuth authorization URL for a provider.

    **Query Parameters:**
    - provider: Provider name (gmail, google_calendar, slack, etc.)

    **Process:**
    1. Validates provider supports OAuth2
    2. Generates authorization URL with scopes
    3. Includes state parameter with user_id:provider

    **Returns:**
    - auth_url: URL to redirect user for authorization

    **Use Case:** Start OAuth flow for connecting integration

    **Example Response:**
    ```json
    {
      "auth_url": "https://accounts.google.com/o/oauth2/auth?..."
    }
    ```
    """
    controller = IntegrationController(db)
    return await controller.get_oauth_url(provider, current_user)


@router.post("/oauth/callback")
async def handle_oauth_callback(
    callback_data: OAuthCallbackRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Handle OAuth callback and connect integration.

    **Request Body:**
    - provider: Provider name
    - code: OAuth authorization code from provider
    - state: Optional state parameter for validation

    **Process:**
    1. Exchanges authorization code for access/refresh tokens
    2. Creates or updates integration record
    3. Stores encrypted tokens
    4. Updates status to 'connected'
    5. Logs connection event

    **Returns:**
    - message: Success message
    - integration_id: UUID of connected integration
    - provider: Provider name

    **Use Case:** Complete OAuth flow after user authorization

    **Example Response:**
    ```json
    {
      "message": "Integration connected successfully",
      "integration_id": "123e4567-e89b-12d3-a456-426614174000",
      "provider": "gmail"
    }
    ```
    """
    controller = IntegrationController(db)
    return await controller.handle_oauth_callback(
        callback_data.provider,
        callback_data.code,
        current_user,
        callback_data.state
    )


# ==================== HEALTH CHECK ====================

@router.get("/test/ping")
async def ping():
    """
    Health check endpoint.

    **Returns:**
    - Simple ping response for testing route availability
    """
    return {
        "status": "ok",
        "service": "integrations",
        "message": "Integration service is running"
    }
