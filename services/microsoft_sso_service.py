"""
Microsoft SSO Service using MSAL (Microsoft Authentication Library)

This service handles:
1. OAuth2 authorization flow with Microsoft/Azure AD
2. Token validation and user info extraction
3. Integration with Microsoft Graph API
"""

import msal
import requests
import secrets
from typing import Dict, Optional, Tuple
from core.config import settings


class MicrosoftSSOService:
    """Service for handling Microsoft SSO authentication"""

    def __init__(self):
        """Initialize MSAL Confidential Client Application"""
        # Build authority URL from tenant ID if not provided
        if settings.MICROSOFT_AUTHORITY:
            self.authority = settings.MICROSOFT_AUTHORITY
        elif settings.MICROSOFT_TENANT_ID:
            self.authority = f"https://login.microsoftonline.com/{settings.MICROSOFT_TENANT_ID}"
        else:
            raise ValueError("Either MICROSOFT_AUTHORITY or MICROSOFT_TENANT_ID must be configured")

        # Parse scopes from comma or space-separated string
        self.scopes = [
            scope.strip()
            for scope in settings.MICROSOFT_SCOPES.replace(',', ' ').split()
            if scope.strip()
        ]

        # Initialize MSAL app
        self.msal_app = msal.ConfidentialClientApplication(
            client_id=settings.MICROSOFT_CLIENT_ID,
            client_credential=settings.MICROSOFT_CLIENT_SECRET,
            authority=self.authority
        )

        self.redirect_uri = settings.MICROSOFT_REDIRECT_URI
        self.graph_api_endpoint = "https://graph.microsoft.com/v1.0"

    def get_authorization_url(self, state: Optional[str] = None) -> Dict[str, str]:
        """
        Generate Microsoft authorization URL for OAuth flow

        Args:
            state: Optional CSRF protection token (will be generated if not provided)

        Returns:
            Dict with auth_url and state
        """
        if not state:
            state = secrets.token_urlsafe(32)

        auth_url = self.msal_app.get_authorization_request_url(
            scopes=self.scopes,
            state=state,
            redirect_uri=self.redirect_uri
        )

        return {
            "auth_url": auth_url,
            "state": state
        }

    def acquire_token_by_auth_code(self, auth_code: str) -> Optional[Dict]:
        """
        Exchange authorization code for access token

        Args:
            auth_code: Authorization code from Microsoft callback

        Returns:
            Token response dict with access_token, id_token, etc.
            None if token acquisition fails
        """
        try:
            result = self.msal_app.acquire_token_by_authorization_code(
                code=auth_code,
                scopes=self.scopes,
                redirect_uri=self.redirect_uri
            )

            if "error" in result:
                print(f"❌ Microsoft token acquisition error: {result.get('error')}")
                print(f"❌ Error description: {result.get('error_description')}")
                return None

            return result

        except Exception as e:
            print(f"❌ Exception during token acquisition: {str(e)}")
            return None

    def validate_token(self, access_token: str) -> Optional[Dict]:
        """
        Validate Microsoft access token by attempting to use it

        Args:
            access_token: Microsoft access token

        Returns:
            User info dict if token is valid, None otherwise
        """
        try:
            user_info = self.get_user_info(access_token)
            return user_info
        except Exception as e:
            print(f"❌ Token validation failed: {str(e)}")
            return None

    def get_user_info(self, access_token: str) -> Dict:
        """
        Fetch user information from Microsoft Graph API

        Args:
            access_token: Valid Microsoft access token

        Returns:
            Dict containing user information:
            {
                'id': 'microsoft_user_id',
                'userPrincipalName': 'user@domain.com',
                'mail': 'user@domain.com',
                'displayName': 'First Last',
                'givenName': 'First',
                'surname': 'Last'
            }

        Raises:
            Exception if API call fails
        """
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        response = requests.get(
            f"{self.graph_api_endpoint}/me",
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            raise Exception(f"Failed to fetch user info: {response.status_code} - {response.text}")

        return response.json()

    def extract_user_data(self, token_response: Dict) -> Tuple[str, str, str, str]:
        """
        Extract user data from Microsoft token response and Graph API

        Args:
            token_response: Token response from MSAL

        Returns:
            Tuple of (email, microsoft_id, first_name, last_name)

        Raises:
            ValueError if required data is missing
        """
        # Get access token from response
        access_token = token_response.get("access_token")
        if not access_token:
            raise ValueError("No access token in response")

        # Fetch user info from Graph API
        user_info = self.get_user_info(access_token)

        # Extract email (prefer 'mail' over 'userPrincipalName')
        email = user_info.get("mail") or user_info.get("userPrincipalName")
        if not email:
            raise ValueError("No email found in Microsoft user profile")

        # Extract Microsoft ID (oid or id)
        microsoft_id = user_info.get("id")
        if not microsoft_id:
            # Try to get from ID token claims if available
            id_token_claims = token_response.get("id_token_claims", {})
            microsoft_id = id_token_claims.get("oid") or id_token_claims.get("sub")

        if not microsoft_id:
            raise ValueError("No Microsoft ID (oid) found in token")

        # Extract name components
        first_name = user_info.get("givenName", "")
        last_name = user_info.get("surname", "")

        # If names are missing, try to split displayName
        if not first_name and not last_name:
            display_name = user_info.get("displayName", "")
            if display_name:
                name_parts = display_name.split(" ", 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ""

        # Ensure we have at least a first name
        if not first_name:
            first_name = email.split("@")[0]  # Use email prefix as fallback

        return email, microsoft_id, first_name, last_name

    def acquire_token_silent(self, microsoft_id: str) -> Optional[Dict]:
        """
        Attempt to acquire token silently using cached tokens

        This is used for SharePoint seamless login scenario

        Args:
            microsoft_id: Microsoft user ID (oid)

        Returns:
            Token response if successful, None otherwise
        """
        try:
            accounts = self.msal_app.get_accounts()

            # Find account matching the microsoft_id
            account = None
            for acc in accounts:
                if acc.get("home_account_id", "").startswith(microsoft_id):
                    account = acc
                    break

            if account:
                result = self.msal_app.acquire_token_silent(
                    scopes=self.scopes,
                    account=account
                )

                if result and "access_token" in result:
                    return result

            return None

        except Exception as e:
            print(f"❌ Silent token acquisition failed: {str(e)}")
            return None


# Create singleton instance
microsoft_sso_service = MicrosoftSSOService()
