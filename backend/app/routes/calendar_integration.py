"""
Calendar Integration Routes - API endpoints for Outlook Calendar integration
Handles OAuth flow, connection management, and calendar synchronization
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.auth import get_current_user
from ..core.config import settings
from ..models.user import UserProfile
from ..models.integration import Integration
from ..services.microsoft_sso_service import microsoft_sso_service
from ..services.outlook_calendar_service import OutlookCalendarService
from ..repositories.integration_repository import IntegrationRepository
# Token encryption functions (simplified for now - can add encryption later)
def encrypt_token(token: str) -> str:
    """Placeholder for token encryption - stores plaintext for now"""
    return token

def decrypt_token(token: str) -> str:
    """Placeholder for token decryption - returns plaintext for now"""
    return token

router = APIRouter()


# ==================== OAUTH FLOW ENDPOINTS ====================

@router.get("/outlook-calendar/connect")
async def connect_outlook_calendar(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Initiate OAuth flow for Outlook Calendar integration

    **Process:**
    1. Generate Microsoft OAuth URL with calendar scopes
    2. Store state for CSRF protection
    3. Return auth URL for frontend to open in popup

    **Returns:**
    - auth_url: Microsoft login URL
    - state: CSRF token

    **Frontend Usage:**
    ```javascript
    const response = await api.get('/api/v1/calendar-integration/outlook-calendar/connect');
    window.open(response.auth_url, 'outlook-auth', 'width=500,height=700');
    ```
    """
    # Generate OAuth URL with calendar scopes
    redirect_uri = settings.MICROSOFT_CALENDAR_REDIRECT_URI

    if not redirect_uri:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Calendar redirect URI not configured. Please set MICROSOFT_CALENDAR_REDIRECT_URI in environment variables."
        )

    oauth_data = microsoft_sso_service.get_calendar_authorization_url(
        redirect_uri=redirect_uri
    )

    # Store state in session or cache for validation (simplified for now)
    # In production, store state in Redis/cache with expiry

    return {
        "auth_url": oauth_data["auth_url"],
        "state": oauth_data["state"]
    }


@router.get("/outlook-calendar/callback")
async def outlook_calendar_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """
    OAuth callback handler for Outlook Calendar

    **Query Parameters:**
    - code: Authorization code from Microsoft
    - state: CSRF protection token

    **Process:**
    1. Validate state token
    2. Exchange code for access/refresh tokens
    3. Get user info from Microsoft Graph
    4. Create or update integration in database
    5. Redirect to close popup window

    **Returns:**
    - HTML page that closes the popup and signals success to parent window
    """
    try:
        # TODO: Validate state token (check against stored state in Redis)

        # Exchange authorization code for tokens
        redirect_uri = settings.MICROSOFT_CALENDAR_REDIRECT_URI

        if not redirect_uri:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Calendar redirect URI not configured"
            )

        token_response = microsoft_sso_service.acquire_calendar_token_by_auth_code(
            code,
            redirect_uri=redirect_uri
        )

        if not token_response:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to acquire access token"
            )

        # Get user info to identify the CRM user
        access_token = token_response.get("access_token")
        user_info = microsoft_sso_service.get_user_info(access_token)
        user_email = user_info.get("mail") or user_info.get("userPrincipalName")

        # Find CRM user by email
        from ..models.user import UserProfile
        crm_user = db.query(UserProfile).filter(
            UserProfile.email == user_email
        ).first()

        if not crm_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No CRM user found with email: {user_email}"
            )

        # Check if integration already exists
        integration_repo = IntegrationRepository(db)
        existing_integration = db.query(Integration).filter(
            Integration.user_id == crm_user.id,
            Integration.provider == "outlook_calendar"
        ).first()

        # Calculate token expiry
        expires_in = token_response.get("expires_in", 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        # Encrypt tokens
        encrypted_access_token = encrypt_token(access_token)
        encrypted_refresh_token = encrypt_token(
            token_response.get("refresh_token", "")
        ) if token_response.get("refresh_token") else None

        if existing_integration:
            # Update existing integration
            existing_integration.access_token = encrypted_access_token
            existing_integration.refresh_token = encrypted_refresh_token
            existing_integration.expires_at = expires_at
            existing_integration.status = "connected"
            existing_integration.last_sync = datetime.utcnow()
            db.commit()
        else:
            # Create new integration
            new_integration = Integration(
                user_id=crm_user.id,
                provider="outlook_calendar",
                name="Microsoft Outlook Calendar",
                description="Two-way calendar sync with Outlook",
                status="connected",
                access_token=encrypted_access_token,
                refresh_token=encrypted_refresh_token,
                expires_at=expires_at,
                config={
                    "email": user_email,
                    "scopes": ["Calendars.ReadWrite", "OnlineMeetings.ReadWrite", "User.Read"]
                },
                auto_sync=True,
                sync_frequency="10min",
                last_sync=datetime.utcnow()
            )
            db.add(new_integration)
            db.commit()

        # Return HTML that closes popup and signals success
        return """
        <html>
            <head><title>Connection Successful</title></head>
            <body>
                <script>
                    // Signal parent window and close popup
                    if (window.opener) {
                        window.opener.postMessage({
                            type: 'outlook-calendar-connected',
                            success: true
                        }, '*');
                    }
                    window.close();
                </script>
                <p>Connection successful! This window will close automatically...</p>
                <p>If it doesn't close, you can close it manually.</p>
            </body>
        </html>
        """

    except HTTPException:
        raise
    except Exception as e:
        return f"""
        <html>
            <head><title>Connection Failed</title></head>
            <body>
                <script>
                    if (window.opener) {{
                        window.opener.postMessage({{
                            type: 'outlook-calendar-connected',
                            success: false,
                            error: '{str(e)}'
                        }}, '*');
                    }}
                </script>
                <p>Connection failed: {str(e)}</p>
                <p>You can close this window and try again.</p>
            </body>
        </html>
        """


# ==================== STATUS & MANAGEMENT ENDPOINTS ====================

@router.get("/outlook-calendar/status")
async def get_calendar_integration_status(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get user's Outlook Calendar integration status

    **Returns:**
    - connected: Boolean indicating if integration exists and is active
    - email: Connected Outlook email (if connected)
    - last_sync: Last sync timestamp (if connected)
    - sync_frequency: Configured sync frequency
    - status: Integration status (connected/disconnected/error)

    **Example Response:**
    ```json
    {
        "connected": true,
        "email": "user@company.com",
        "last_sync": "2025-01-15T10:30:00Z",
        "sync_frequency": "10min",
        "status": "connected"
    }
    ```
    """
    integration = db.query(Integration).filter(
        Integration.user_id == current_user.id,
        Integration.provider == "outlook_calendar"
    ).first()

    if not integration:
        return {
            "connected": False,
            "status": "disconnected"
        }

    return {
        "connected": integration.status == "connected",
        "email": integration.config.get("email") if integration.config else None,
        "last_sync": integration.last_sync,
        "sync_frequency": integration.sync_frequency,
        "status": integration.status,
        "auto_sync": integration.auto_sync
    }


@router.post("/outlook-calendar/sync")
async def sync_outlook_calendar(
    start_date: Optional[str] = Query(None, description="Start date in ISO format"),
    end_date: Optional[str] = Query(None, description="End date in ISO format"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Manually trigger Outlook Calendar sync

    **Query Parameters:**
    - start_date: Optional start date (default: 30 days ago)
    - end_date: Optional end date (default: 90 days from now)

    **Process:**
    1. Fetch events from Outlook in date range
    2. Match to existing CRM activities by outlook_event_id
    3. Create new activities for new events
    4. Update existing activities if changed

    **Returns:**
    - success: Boolean
    - events_fetched: Number of events from Outlook
    - created: Number of new activities created
    - updated: Number of activities updated
    - last_sync: Sync timestamp

    **Example Response:**
    ```json
    {
        "success": true,
        "events_fetched": 25,
        "created": 10,
        "updated": 5,
        "last_sync": "2025-01-15T10:35:00Z"
    }
    ```
    """
    # Get integration
    integration = db.query(Integration).filter(
        Integration.user_id == current_user.id,
        Integration.provider == "outlook_calendar"
    ).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outlook Calendar integration not found. Please connect first."
        )

    if integration.status != "connected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integration is not connected. Status: {integration.status}"
        )

    # Parse or set default date range
    if start_date:
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    else:
        start_dt = datetime.utcnow() - timedelta(days=30)

    if end_date:
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    else:
        end_dt = datetime.utcnow() + timedelta(days=90)

    # Decrypt access token
    access_token = decrypt_token(integration.access_token)

    # Initialize calendar service
    calendar_service = OutlookCalendarService(db)

    # Perform sync
    result = await calendar_service.sync_outlook_to_crm(
        user_id=str(current_user.id),
        integration=integration,
        start_date=start_dt,
        end_date=end_dt
    )

    # Update last_sync timestamp
    integration.last_sync = datetime.utcnow()

    if result.get("success"):
        integration.status = "connected"
        integration.error_count = 0
        integration.last_error = None
    else:
        integration.error_count = (integration.error_count or 0) + 1
        integration.last_error = result.get("error")

    db.commit()

    return {
        **result,
        "last_sync": integration.last_sync
    }


@router.delete("/outlook-calendar/{integration_id}")
async def disconnect_outlook_calendar(
    integration_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Disconnect Outlook Calendar integration

    **Path Parameters:**
    - integration_id: Integration UUID

    **Process:**
    - Removes integration from database
    - Deletes stored tokens
    - Does NOT delete existing CRM activities (data preserved)

    **Returns:**
    - Success message

    **Note:** Already synced activities remain in CRM with historical data
    """
    integration = db.query(Integration).filter(
        Integration.id == integration_id,
        Integration.user_id == current_user.id,
        Integration.provider == "outlook_calendar"
    ).first()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Outlook Calendar integration not found"
        )

    db.delete(integration)
    db.commit()

    return {
        "success": True,
        "message": "Outlook Calendar integration disconnected successfully",
        "note": "Historical calendar data has been preserved in CRM activities"
    }


# ==================== SYNC TO OUTLOOK ENDPOINT ====================

@router.post("/activities/{activity_id}/sync-to-outlook")
async def sync_activity_to_outlook(
    activity_id: UUID,
    create_teams_meeting: bool = Query(False, description="Create Teams meeting link"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Sync a CRM activity to Outlook Calendar

    **Path Parameters:**
    - activity_id: Activity UUID

    **Query Parameters:**
    - create_teams_meeting: Whether to generate Teams meeting link (default: false)

    **Process:**
    1. Get activity from CRM
    2. Check if user has Outlook integration
    3. Create or update event in Outlook
    4. Store outlook_event_id in activity
    5. Generate Teams link if requested

    **Returns:**
    - success: Boolean
    - event_id: Outlook event ID
    - meeting_link: Teams meeting URL (if created)

    **Use Cases:**
    - User creates meeting in CRM and wants it in Outlook
    - User wants to generate Teams link for existing activity
    """
    from ..models.activity import Activity

    # Get activity
    activity = db.query(Activity).filter(
        Activity.id == activity_id,
        Activity.user_id == current_user.id
    ).first()

    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found"
        )

    # Get integration
    integration = db.query(Integration).filter(
        Integration.user_id == current_user.id,
        Integration.provider == "outlook_calendar"
    ).first()

    if not integration or integration.status != "connected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Outlook Calendar integration not connected"
        )

    # Decrypt access token
    access_token = decrypt_token(integration.access_token)
    integration.access_token = access_token  # Temporarily set for service

    # Initialize calendar service
    calendar_service = OutlookCalendarService(db)

    # Sync to Outlook
    result = await calendar_service.sync_crm_to_outlook(
        activity=activity,
        integration=integration,
        create_teams_meeting=create_teams_meeting
    )

    return result
