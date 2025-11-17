"""
User Service - Business logic layer for User operations.
Handles user management, invitations, password changes, statistics, and SSO integration.
"""

from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
import os

from ..repositories.user_repository import UserRepository
from ..models.user import UserProfile
from ..models.password_reset_token import PasswordResetToken
from ..schemas.user import UserCreate, UserUpdate, UserInvite
from ..core.security import get_password_hash, verify_password
from ..services.smtp_service import SMTPService
from ..core.config import settings


class UserService:
    """Service layer for user business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = UserRepository(db)

    def get_all_users(
        self,
        search: Optional[str] = None,
        role: Optional[str] = None,
        roles: Optional[List[str]] = None,
        is_active: Optional[bool] = None
    ) -> List[UserProfile]:
        """
        Get all users with optional filters.

        Args:
            search: Search term
            role: Filter by role
            roles: Filter by multiple roles
            is_active: Filter by active status

        Returns:
            List of users
        """
        return self.repository.search_users(
            search=search,
            role=role,
            roles=roles,
            is_active=is_active
        )

    def get_user_by_id(self, user_id: UUID) -> Optional[UserProfile]:
        """
        Get a single user by ID.

        Args:
            user_id: User UUID

        Returns:
            User or None
        """
        return self.repository.get(user_id)

    def get_user_by_email(self, email: str) -> Optional[UserProfile]:
        """
        Get user by email address.

        Args:
            email: User email

        Returns:
            User or None
        """
        return self.repository.get_by_email(email)

    def create_user(self, user_data: UserCreate) -> UserProfile:
        """
        Create a new user.

        Args:
            user_data: User creation data

        Returns:
            Created user

        Raises:
            ValueError: If email already exists
        """
        # Check if email already exists
        if self.repository.email_exists(user_data.email):
            raise ValueError("User with this email already exists")

        # Hash password
        hashed_password = get_password_hash(user_data.password)

        # Build user dictionary
        user_dict = user_data.model_dump(exclude={'password'})
        user_dict['hashed_password'] = hashed_password
        user_dict['is_active'] = True

        # Create user
        created_user = self.repository.create(obj_in=user_dict)

        return created_user

    def invite_user(self, invite_data: UserInvite) -> UserProfile:
        """
        Invite a new user (creates user and sends invitation email with password setup link).

        Args:
            invite_data: User invitation data

        Returns:
            Created user

        Raises:
            ValueError: If email already exists or SMTP configuration is missing
        """
        # Check if email already exists
        if self.repository.email_exists(invite_data.email):
            raise ValueError("User with this email already exists")

        # Create user without password (they'll set it via email link)
        user_dict = {
            'email': invite_data.email,
            'first_name': invite_data.first_name,
            'last_name': invite_data.last_name,
            'role': invite_data.role,
            # Placeholder password - user must set via reset link
            'hashed_password': get_password_hash("PLACEHOLDER_MUST_RESET"),
            'is_active': True
        }

        created_user = self.repository.create(obj_in=user_dict)

        # Generate password reset token for the new user
        reset_token = PasswordResetToken(
            user_id=created_user.id,
            token=PasswordResetToken.generate_token(),
            expires_at=PasswordResetToken.get_expiration_time(hours=72)  # 72 hours for invitation
        )
        self.db.add(reset_token)
        self.db.commit()

        # Send invitation email with password setup link
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
            setup_link = f"{frontend_url}/reset-password?token={reset_token.token}"

            # Get company info from system configuration (if available)
            try:
                from ..routes.auth import get_company_info
                company_info = get_company_info(self.db)
                company_name = company_info['company_name']
                company_email = company_info['company_email']
                company_phone = company_info['company_phone']
                company_address = company_info['company_address']
            except:
                # Fallback to default values
                company_name = "CRM Platform"
                company_email = settings.FROM_EMAIL
                company_phone = ""
                company_address = ""

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
                        <h1>Welcome to {company_name}!</h1>
                    </div>
                    <div class="content">
                        <p>Hello {created_user.first_name},</p>
                        <p>You've been invited to join {company_name}'s CRM platform as a <strong>{created_user.role.replace('_', ' ').title()}</strong>.</p>
                        <p>To get started, you'll need to set up your password by clicking the button below:</p>
                        <p style="text-align: center;">
                            <a href="{setup_link}" class="button">Set Up Your Password</a>
                        </p>
                        <p>Or copy and paste this link into your browser:</p>
                        <p style="word-break: break-all; background: white; padding: 10px; border-radius: 5px;">{setup_link}</p>
                        <p><strong>This link will expire in 72 hours.</strong></p>
                        <p>After setting up your password, you'll be able to log in with:</p>
                        <ul>
                            <li><strong>Email:</strong> {created_user.email}</li>
                            <li><strong>Password:</strong> The password you create</li>
                        </ul>
                        <p>If you have any questions, please contact your administrator.</p>
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

            smtp_service.send_email(
                to_email=created_user.email,
                subject=f"Welcome to {company_name} - Set Up Your Account",
                html_content=html_content,
                from_name=company_name
            )

        except Exception as e:
            # Log the error but don't fail user creation
            # The admin can manually send the invitation or provide credentials
            print(f"Warning: Failed to send invitation email to {created_user.email}: {str(e)}")
            # Could optionally delete the user here if email sending is critical
            # For now, we'll keep the user and let admin handle it

        return created_user

    def update_user(
        self,
        user_id: UUID,
        user_data: UserUpdate,
        current_user: UserProfile
    ) -> Optional[UserProfile]:
        """
        Update an existing user.

        Args:
            user_id: User UUID
            user_data: Update data
            current_user: User making the update

        Returns:
            Updated user or None if not found

        Raises:
            ValueError: If validation fails
        """
        user = self.repository.get(user_id)

        if not user:
            return None

        # Validation: Prevent self-deactivation
        update_data = user_data.model_dump(exclude_unset=True)
        if 'is_active' in update_data and not update_data['is_active']:
            if current_user.id == user_id:
                raise ValueError("You cannot deactivate your own account")

            # Prevent deactivating admin users
            if user.role == 'admin':
                raise ValueError(
                    "Administrator accounts cannot be deactivated. "
                    "Please contact system support if needed."
                )

        # Check email uniqueness if being updated
        if 'email' in update_data and update_data['email'] != user.email:
            if self.repository.email_exists(update_data['email'], exclude_user_id=user_id):
                raise ValueError("Email already exists")

        # Update user
        updated_user = self.repository.update(db_obj=user, obj_in=update_data)

        return updated_user

    def update_profile(
        self,
        user: UserProfile,
        profile_data: UserUpdate
    ) -> UserProfile:
        """
        Update user's own profile (limited fields).

        Args:
            user: Current user
            profile_data: Profile update data

        Returns:
            Updated user
        """
        # Only allow updating specific fields for self-update
        allowed_fields = {'first_name', 'last_name', 'phone', 'avatar_url'}
        update_data = {
            k: v for k, v in profile_data.model_dump(exclude_unset=True).items()
            if k in allowed_fields
        }

        updated_user = self.repository.update(db_obj=user, obj_in=update_data)

        return updated_user

    def change_password(
        self,
        user: UserProfile,
        current_password: str,
        new_password: str
    ) -> UserProfile:
        """
        Change user password.

        Args:
            user: User object
            current_password: Current password (for verification)
            new_password: New password

        Returns:
            Updated user

        Raises:
            ValueError: If current password is incorrect
        """
        # Verify current password
        if not verify_password(current_password, user.hashed_password):
            raise ValueError("Current password is incorrect")

        # Hash and update password
        hashed_password = get_password_hash(new_password)
        updated_user = self.repository.update_password(user, hashed_password)

        return updated_user

    def reset_password(self, user_id: UUID, new_password: str) -> Optional[UserProfile]:
        """
        Reset user password (admin function).

        Args:
            user_id: User UUID
            new_password: New password

        Returns:
            Updated user or None
        """
        user = self.repository.get(user_id)

        if not user:
            return None

        hashed_password = get_password_hash(new_password)
        updated_user = self.repository.update_password(user, hashed_password)

        return updated_user

    def deactivate_user(self, user_id: UUID) -> Optional[UserProfile]:
        """
        Deactivate a user.

        Args:
            user_id: User UUID

        Returns:
            Updated user or None
        """
        return self.repository.deactivate_user(user_id)

    def activate_user(self, user_id: UUID) -> Optional[UserProfile]:
        """
        Activate a user.

        Args:
            user_id: User UUID

        Returns:
            Updated user or None
        """
        return self.repository.activate_user(user_id)

    def get_user_statistics(self) -> Dict[str, Any]:
        """
        Get user statistics.

        Returns:
            Dictionary with statistics
        """
        return self.repository.get_statistics()

    def get_active_users(self) -> List[UserProfile]:
        """
        Get all active users.

        Returns:
            List of active users
        """
        return self.repository.get_active_users()

    def get_users_by_role(self, role: str, active_only: bool = True) -> List[UserProfile]:
        """
        Get users by role.

        Args:
            role: Role name
            active_only: Only return active users

        Returns:
            List of users
        """
        return self.repository.get_by_role(role, active_only)

    def get_recently_created_users(self, limit: int = 10) -> List[UserProfile]:
        """
        Get recently created users.

        Args:
            limit: Maximum number of users

        Returns:
            List of recently created users
        """
        return self.repository.get_recently_created(limit)

    def can_access_user(self, current_user: UserProfile, target_user_id: UUID) -> bool:
        """
        Check if current user can access target user's data.

        Args:
            current_user: User making the request
            target_user_id: Target user ID

        Returns:
            True if access allowed
        """
        # Admin can access all users
        if current_user.role == 'admin':
            return True

        # Users can access their own data
        if current_user.id == target_user_id:
            return True

        # Managers can access their team (TODO: implement team structure)
        if current_user.role == 'sales_manager':
            return True  # For now, allow all

        return False

    def can_modify_user(self, current_user: UserProfile, target_user_id: UUID) -> bool:
        """
        Check if current user can modify target user's data.

        Args:
            current_user: User making the request
            target_user_id: Target user ID

        Returns:
            True if modification allowed
        """
        # Admin can modify all users
        if current_user.role == 'admin':
            return True

        # Users can modify their own profile (limited fields)
        if current_user.id == target_user_id:
            return True

        return False

    def get_user_by_microsoft_id(self, microsoft_id: str) -> Optional[UserProfile]:
        """
        Get user by Microsoft ID.

        Args:
            microsoft_id: Microsoft user identifier (oid)

        Returns:
            User or None
        """
        return self.db.query(UserProfile).filter(
            UserProfile.microsoft_id == microsoft_id
        ).first()

    def link_microsoft_account(
        self,
        user: UserProfile,
        microsoft_id: str
    ) -> UserProfile:
        """
        Link Microsoft account to existing user.

        Args:
            user: Existing user to link
            microsoft_id: Microsoft user ID

        Returns:
            Updated user

        Raises:
            ValueError: If microsoft_id is already linked to another user
        """
        # Check if microsoft_id is already used by another user
        existing_microsoft_user = self.get_user_by_microsoft_id(microsoft_id)
        if existing_microsoft_user and existing_microsoft_user.id != user.id:
            raise ValueError("This Microsoft account is already linked to another user")

        # Update user with Microsoft credentials
        user.microsoft_id = microsoft_id
        user.auth_provider = "microsoft"

        self.db.commit()
        self.db.refresh(user)

        print(f"✅ Linked Microsoft account to user: {user.email}")
        return user

    def create_microsoft_user(
        self,
        email: str,
        microsoft_id: str,
        first_name: str,
        last_name: str,
        role: str = "sales_rep"
    ) -> UserProfile:
        """
        Create a new Microsoft SSO user.

        Args:
            email: User's email
            microsoft_id: Microsoft user identifier
            first_name: User's first name
            last_name: User's last name
            role: User's role (default: sales_rep)

        Returns:
            Created user

        Raises:
            ValueError: If email already exists
        """
        # Check if email already exists
        if self.repository.email_exists(email):
            raise ValueError("User with this email already exists")

        # Create user without password
        user_dict = {
            'email': email.lower().strip(),
            'first_name': first_name.strip(),
            'last_name': last_name.strip(),
            'role': role,
            'hashed_password': None,  # No password for SSO users
            'microsoft_id': microsoft_id,
            'auth_provider': 'microsoft',
            'is_active': True
        }

        created_user = self.repository.create(obj_in=user_dict)

        print(f"✅ Created new Microsoft SSO user: {email}")
        return created_user

    def get_or_create_microsoft_user(
        self,
        email: str,
        microsoft_id: str,
        first_name: str,
        last_name: str
    ) -> Tuple[UserProfile, bool]:
        """
        Get existing user or create new one for Microsoft SSO.

        Logic:
        1. If user exists with microsoft_id -> return existing user
        2. If user exists with email but no microsoft_id -> link accounts
        3. If user doesn't exist -> create new user

        Args:
            email: User's email from Microsoft
            microsoft_id: Microsoft user identifier (oid)
            first_name: User's first name
            last_name: User's last name

        Returns:
            Tuple of (UserProfile, is_new_user: bool)

        Raises:
            ValueError: If account linking fails
        """
        # Check if user exists with microsoft_id
        existing_user = self.get_user_by_microsoft_id(microsoft_id)
        if existing_user:
            print(f"✅ Found existing Microsoft user: {email}")
            return existing_user, False

        # Check if user exists with email
        existing_user = self.get_user_by_email(email)
        if existing_user:
            # Link Microsoft account to existing user
            print(f"🔗 Linking Microsoft account to existing user: {email}")
            linked_user = self.link_microsoft_account(existing_user, microsoft_id)
            return linked_user, False

        # Create new user for Microsoft SSO
        print(f"➕ Creating new Microsoft SSO user: {email}")
        new_user = self.create_microsoft_user(
            email=email,
            microsoft_id=microsoft_id,
            first_name=first_name,
            last_name=last_name,
            role="sales_rep"  # Default role for new SSO users
        )

        return new_user, True
