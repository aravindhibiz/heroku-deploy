from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List, Dict, Optional
from ..core.database import get_db
from ..core.security import create_access_token, verify_password, get_password_hash
from ..core.config import settings
from ..core.auth import get_current_user, get_user_permissions
from ..models.user import UserProfile
from ..models.password_reset_token import PasswordResetToken
from ..schemas.user import (
    UserCreate, UserLogin, Token, UserResponse,
    ForgotPasswordRequest, ForgotPasswordResponse,
    ResetPasswordRequest, ResetPasswordResponse,
    MicrosoftSSOLogin
)
from ..services.smtp_service import SMTPService
from ..services.microsoft_sso_service import microsoft_sso_service
from ..services.user_service import UserService
from ..services.system_config_service_new import SystemConfigService
import secrets
import urllib.parse

router = APIRouter()


def get_session_timeout_minutes(db: Session) -> int:
    """
    Get session timeout from system configuration.
    Falls back to config.py setting if not found in database.

    Args:
        db: Database session

    Returns:
        int: Session timeout in minutes
    """
    try:
        config_service = SystemConfigService(db)
        timeout = config_service.get_configuration_value(
            'security.session_timeout_minutes',
            default=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        return int(timeout)
    except Exception:
        # Fallback to hardcoded setting if anything goes wrong
        return settings.ACCESS_TOKEN_EXPIRE_MINUTES


def get_company_info(db: Session) -> Dict[str, str]:
    """
    Get company information from system configuration.
    Returns dict with company_name, company_email, company_phone, company_address.

    Args:
        db: Database session

    Returns:
        Dict[str, str]: Company information
    """
    try:
        config_service = SystemConfigService(db)
        return {
            'company_name': config_service.get_configuration_value('general.company_name', default='SalesForce Lite'),
            'company_email': config_service.get_configuration_value('general.company_email', default='info@salesforcelite.com'),
            'company_phone': config_service.get_configuration_value('general.company_phone', default=''),
            'company_address': config_service.get_configuration_value('general.company_address', default='')
        }
    except Exception:
        # Fallback to defaults if anything goes wrong
        return {
            'company_name': 'SalesForce Lite',
            'company_email': 'info@salesforcelite.com',
            'company_phone': '',
            'company_address': ''
        }


# Public registration disabled - users must be invited by an admin
# @router.post("/register", response_model=Token)
# async def register(user: UserCreate, db: Session = Depends(get_db)):
#     # Check if user already exists
#     db_user = db.query(UserProfile).filter(
#         UserProfile.email == user.email).first()
#     if db_user:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Email already registered"
#         )
#
#     # Create new user
#     hashed_password = get_password_hash(user.password)
#     db_user = UserProfile(
#         email=user.email,
#         first_name=user.first_name,
#         last_name=user.last_name,
#         role=user.role,
#         phone=user.phone,
#         hashed_password=hashed_password
#     )
#
#     db.add(db_user)
#     db.commit()
#     db.refresh(db_user)
#
#     # Create access token with session timeout from system configuration
#     session_timeout = get_session_timeout_minutes(db)
#     access_token_expires = timedelta(minutes=session_timeout)
#     access_token = create_access_token(
#         data={"sub": str(db_user.id)}, expires_delta=access_token_expires
#     )
#
#     return {
#         "access_token": access_token,
#         "token_type": "bearer",
#         "user": UserResponse.model_validate(db_user)
#     }


@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    from datetime import datetime

    # Get security settings from system configuration
    config_service = SystemConfigService(db)
    max_attempts = config_service.get_configuration_value('security.max_login_attempts', default=5)
    lockout_minutes = config_service.get_configuration_value('security.lockout_duration_minutes', default=30)

    # Find user
    user = db.query(UserProfile).filter(
        UserProfile.email == user_credentials.email).first()

    # Check if account is locked
    if user and user.account_locked_until:
        if datetime.utcnow() < user.account_locked_until:
            remaining_minutes = int((user.account_locked_until - datetime.utcnow()).total_seconds() / 60)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is locked due to too many failed login attempts. Please try again in {remaining_minutes} minutes.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            # Unlock account - lockout period has expired
            user.account_locked_until = None
            user.failed_login_attempts = 0
            db.commit()

    # Verify password
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        # Track failed login attempt
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1

            # Lock account if max attempts reached
            if user.failed_login_attempts >= max_attempts:
                user.account_locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Account locked due to {max_attempts} failed login attempts. Please try again in {lockout_minutes} minutes.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact your administrator.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Successful login - reset failed attempts
    user.failed_login_attempts = 0
    user.account_locked_until = None
    db.commit()

    # Create access token with session timeout from system configuration
    session_timeout = get_session_timeout_minutes(db)
    access_token_expires = timedelta(minutes=session_timeout)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user)
    }


@router.get("/me/permissions")
async def get_my_permissions(
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's permissions based on their role"""
    permissions = get_user_permissions(db, current_user)

    # Organize permissions by category for easier frontend consumption
    permissions_by_category = {}
    for perm in permissions:
        parts = perm.split('.')
        if len(parts) == 2:
            category, action = parts
            if category not in permissions_by_category:
                permissions_by_category[category] = []
            permissions_by_category[category].append(action)

    return {
        "permissions": permissions,
        "permissions_by_category": permissions_by_category,
        "role": current_user.role
    }


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Request a password reset token.
    Sends an email with a reset link to the user.
    """
    # Find user by email
    user = db.query(UserProfile).filter(UserProfile.email == request.email).first()

    # Always return success to prevent email enumeration attacks
    # Don't reveal if the email exists or not
    if not user:
        return {
            "message": "If an account exists with this email, you will receive a password reset link shortly.",
            "email": request.email
        }

    # Check if user is active
    if not user.is_active:
        return {
            "message": "If an account exists with this email, you will receive a password reset link shortly.",
            "email": request.email
        }

    # Invalidate any existing tokens for this user
    existing_tokens = db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.is_used == False
    ).all()
    for token in existing_tokens:
        token.is_used = True

    # Generate new reset token
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=PasswordResetToken.generate_token(),
        expires_at=PasswordResetToken.get_expiration_time(hours=1)
    )

    db.add(reset_token)
    db.commit()
    db.refresh(reset_token)

    # Send password reset email
    try:
        # Validate SMTP configuration
        if not settings.SMTP_HOST:
            raise ValueError("SMTP_HOST is not configured in environment variables")
        if not settings.SMTP_USER:
            raise ValueError("SMTP_USER is not configured in environment variables")
        if not settings.SMTP_PASS:
            raise ValueError("SMTP_PASS is not configured in environment variables")
        if not settings.FROM_EMAIL:
            raise ValueError("FROM_EMAIL is not configured in environment variables")

        # Initialize SMTP service
        smtp_service = SMTPService(
            smtp_host=settings.SMTP_HOST,
            smtp_port=settings.SMTP_PORT,
            smtp_user=settings.SMTP_USER,
            smtp_pass=settings.SMTP_PASS,
            from_email=settings.FROM_EMAIL,
            smtp_secure=settings.SMTP_SECURE
        )

        frontend_url = settings.FRONTEND_URL or "http://localhost:3000"
        reset_link = f"{frontend_url}/reset-password?token={reset_token.token}"

        # Get company info from system configuration
        company_info = get_company_info(db)
        company_name = company_info['company_name']
        company_email = company_info['company_email']
        company_phone = company_info['company_phone']
        company_address = company_info['company_address']

        # Build footer with company contact info
        footer_contact = []
        if company_address:
            footer_contact.append(company_address)
        if company_email:
            footer_contact.append(f"Email: {company_email}")
        if company_phone:
            footer_contact.append(f"Phone: {company_phone}")
        footer_text = " | ".join(footer_contact) if footer_contact else ""

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Reset Request</h1>
                </div>
                <div class="content">
                    <p>Hello {user.first_name},</p>
                    <p>We received a request to reset your password for your {company_name} account.</p>
                    <p>Click the button below to reset your password:</p>
                    <p style="text-align: center;">
                        <a href="{reset_link}" class="button">Reset Password</a>
                    </p>
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; background: white; padding: 10px; border-radius: 5px;">{reset_link}</p>
                    <p><strong>This link will expire in 1 hour.</strong></p>
                    <p>If you didn't request a password reset, please ignore this email. Your password will remain unchanged.</p>
                    <p>Best regards,<br>The {company_name} Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message, please do not reply to this email.</p>
                    {f"<p>{footer_text}</p>" if footer_text else ""}
                </div>
            </div>
        </body>
        </html>
        """

        result = smtp_service.send_email(
            to_email=user.email,
            subject=f"Reset Your Password - {company_name}",
            html_content=html_content,
            from_name=company_name
        )
    except ValueError as ve:
        pass
    except Exception as e:
        pass
        # Don't fail the request if email sending fails
        # User can still use the token if they have it

    return {
        "message": "If an account exists with this email, you will receive a password reset link shortly.",
        "email": request.email
    }


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Reset password using a valid reset token.
    """
    # Find the reset token
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == request.token
    ).first()

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Validate the token
    if not reset_token.is_valid():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Get the user
    user = db.query(UserProfile).filter(UserProfile.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Validate password strength (at least 8 characters)
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )

    # Update user's password
    user.hashed_password = get_password_hash(request.new_password)

    # Mark token as used
    reset_token.mark_as_used()

    db.commit()

    # Send confirmation email (optional)
    try:
        # Initialize SMTP service
        smtp_service = SMTPService(
            smtp_host=settings.SMTP_HOST,
            smtp_port=settings.SMTP_PORT,
            smtp_user=settings.SMTP_USER,
            smtp_pass=settings.SMTP_PASS,
            from_email=settings.FROM_EMAIL,
            smtp_secure=settings.SMTP_SECURE
        )

        # Get company info from system configuration
        company_info = get_company_info(db)
        company_name = company_info['company_name']
        company_email = company_info['company_email']
        company_phone = company_info['company_phone']
        company_address = company_info['company_address']

        # Build footer with company contact info
        footer_contact = []
        if company_address:
            footer_contact.append(company_address)
        if company_email:
            footer_contact.append(f"Email: {company_email}")
        if company_phone:
            footer_contact.append(f"Phone: {company_phone}")
        footer_text = " | ".join(footer_contact) if footer_contact else ""

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .success {{ background: #4caf50; color: white; padding: 15px; border-radius: 5px; text-align: center; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Reset Successful</h1>
                </div>
                <div class="content">
                    <div class="success">
                        <strong>✓ Your password has been successfully reset!</strong>
                    </div>
                    <p>Hello {user.first_name},</p>
                    <p>This is a confirmation that your password for your {company_name} account has been successfully changed.</p>
                    <p>If you did not make this change, please contact your administrator immediately.</p>
                    <p>Best regards,<br>The {company_name} Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message, please do not reply to this email.</p>
                    {f"<p>{footer_text}</p>" if footer_text else ""}
                </div>
            </div>
        </body>
        </html>
        """

        result = smtp_service.send_email(
            to_email=user.email,
            subject=f"Password Changed Successfully - {company_name}",
            html_content=html_content,
            from_name=company_name
        )

    except Exception as e:
        pass

    return {
        "message": "Password has been reset successfully. You can now log in with your new password."
    }


# ==========================================
# MICROSOFT SSO ENDPOINTS
# ==========================================

# In-memory state storage for CSRF protection
# In production, use Redis or database
_oauth_states = {}


@router.get("/microsoft/login")
async def microsoft_login():
    """
    Initiate Microsoft OAuth login flow.
    Returns the Microsoft authorization URL for the frontend to open in a popup.
    """
    try:
        # Generate CSRF state token
        state = secrets.token_urlsafe(32)

        # Get Microsoft authorization URL
        auth_data = microsoft_sso_service.get_authorization_url(state=state)

        # Store state temporarily (expires after 10 minutes)
        _oauth_states[state] = True

        return {
            "auth_url": auth_data["auth_url"],
            "state": state
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate Microsoft login: {str(e)}"
        )


@router.get("/microsoft/callback")
async def microsoft_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Handle Microsoft OAuth callback.
    Exchanges authorization code for access token and creates/finds user.
    Redirects to frontend with JWT token.
    """
    # Handle error from Microsoft
    if error:
        error_msg = error_description or error
        frontend_url = settings.FRONTEND_URL or "http://localhost:3000"
        error_encoded = urllib.parse.quote(f"Microsoft login failed: {error_msg}")
        return RedirectResponse(
            url=f"{frontend_url}/login?error={error_encoded}"
        )

    # Validate required parameters
    if not code or not state:
        frontend_url = settings.FRONTEND_URL or "http://localhost:3000"
        return RedirectResponse(
            url=f"{frontend_url}/login?error=Invalid+callback+parameters"
        )

    # Validate state (CSRF protection)
    if state not in _oauth_states:
        frontend_url = settings.FRONTEND_URL or "http://localhost:3000"
        return RedirectResponse(
            url=f"{frontend_url}/login?error=Invalid+state+token"
        )

    # Remove used state
    del _oauth_states[state]

    try:
        # Exchange authorization code for access token
        token_response = microsoft_sso_service.acquire_token_by_auth_code(code)

        if not token_response:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to acquire token from Microsoft"
            )

        # Extract user data from token response
        email, microsoft_id, first_name, last_name = microsoft_sso_service.extract_user_data(token_response)

        # Get or create user
        user_service = UserService(db)
        user, is_new = user_service.get_or_create_microsoft_user(
            email=email,
            microsoft_id=microsoft_id,
            first_name=first_name,
            last_name=last_name
        )

        # Check if user is active
        if not user.is_active:
            frontend_url = settings.FRONTEND_URL or "http://localhost:3000"
            return RedirectResponse(
                url=f"{frontend_url}/login?error=Account+deactivated"
            )

        # Create JWT access token with session timeout from system configuration
        session_timeout = get_session_timeout_minutes(db)
        access_token_expires = timedelta(minutes=session_timeout)
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires
        )

        # Prepare user data for frontend
        user_data = UserResponse.model_validate(user)
        user_json = urllib.parse.quote(user_data.model_dump_json())

        # Redirect to frontend success page with token and user data
        frontend_url = settings.FRONTEND_URL or "http://localhost:3000"
        redirect_url = f"{frontend_url}/auth/microsoft/success?token={access_token}&user={user_json}"

        return RedirectResponse(url=redirect_url)

    except ValueError as ve:
        frontend_url = settings.FRONTEND_URL or "http://localhost:3000"
        error_encoded = urllib.parse.quote(str(ve))
        return RedirectResponse(
            url=f"{frontend_url}/login?error={error_encoded}"
        )
    except Exception as e:
        frontend_url = settings.FRONTEND_URL or "http://localhost:3000"
        return RedirectResponse(
            url=f"{frontend_url}/login?error=Authentication+failed"
        )


@router.post("/microsoft/silent", response_model=Token)
async def microsoft_silent_login(
    sso_data: MicrosoftSSOLogin,
    db: Session = Depends(get_db)
):
    """
    Handle silent SSO login for SharePoint integration.
    Frontend provides Microsoft access token, backend validates and returns JWT.
    """
    try:
        # Validate Microsoft token and get user info
        user_info = microsoft_sso_service.validate_token(sso_data.access_token)

        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Microsoft access token"
            )

        # Extract user data
        email = sso_data.email
        microsoft_id = sso_data.microsoft_id
        first_name = sso_data.first_name or user_info.get("givenName", "")
        last_name = sso_data.last_name or user_info.get("surname", "")

        # Ensure we have required data
        if not email or not microsoft_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required user information"
            )

        # Get or create user
        user_service = UserService(db)
        user, is_new = user_service.get_or_create_microsoft_user(
            email=email,
            microsoft_id=microsoft_id,
            first_name=first_name or email.split("@")[0],
            last_name=last_name or ""
        )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been deactivated. Please contact your administrator."
            )

        # Create JWT access token with session timeout from system configuration
        session_timeout = get_session_timeout_minutes(db)
        access_token_expires = timedelta(minutes=session_timeout)
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserResponse.model_validate(user)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Silent SSO failed: {str(e)}"
        )
