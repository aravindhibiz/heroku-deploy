"""
User Controller - HTTP request/response handling for Users.
Handles validation, permissions, and response formatting.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from services.user_service import UserService
from schemas.user import UserResponse, UserCreate, UserUpdate, UserInvite, UserStats
from models.user import UserProfile


class UserController:
    """Controller for user HTTP operations."""

    def __init__(self, db: Session):
        self.db = db
        self.service = UserService(db)

    def list_users(
        self,
        current_user: UserProfile,
        search: Optional[str] = None,
        role: Optional[str] = None,
        roles: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[UserResponse]:
        """
        Get all users with optional filters.

        Args:
            current_user: Authenticated user
            search: Search term
            role: Filter by role
            roles: Comma-separated roles
            status: Filter by status (active/inactive)

        Returns:
            List of user responses

        Raises:
            HTTPException: If user lacks permission
        """
        # Only admin and managers can list all users
        if current_user.role not in ['admin', 'sales_manager']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to list users"
            )

        # Parse roles if provided
        role_list = None
        if roles:
            role_list = [r.strip() for r in roles.split(',')]

        # Parse status
        is_active = None
        if status:
            is_active = status.lower() == 'active'

        users = self.service.get_all_users(
            search=search,
            role=role,
            roles=role_list,
            is_active=is_active
        )

        return [UserResponse.model_validate(user) for user in users]

    def get_current_user_profile(self, current_user: UserProfile) -> UserResponse:
        """
        Get current user's profile.

        Args:
            current_user: Authenticated user

        Returns:
            User response
        """
        return UserResponse.model_validate(current_user)

    def get_user(self, user_id: UUID, current_user: UserProfile) -> UserResponse:
        """
        Get a single user by ID.

        Args:
            user_id: User UUID
            current_user: Authenticated user

        Returns:
            User response

        Raises:
            HTTPException: If user not found or lacks permission
        """
        # Check access permission
        if not self.service.can_access_user(current_user, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to access this user"
            )

        user = self.service.get_user_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return UserResponse.model_validate(user)

    def create_user(
        self,
        user_data: UserCreate,
        current_user: UserProfile
    ) -> UserResponse:
        """
        Create a new user.

        Args:
            user_data: User creation data
            current_user: Authenticated user (must be admin)

        Returns:
            Created user response

        Raises:
            HTTPException: If validation fails or lacks permission
        """
        # Only admin can create users
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can create users"
            )

        try:
            user = self.service.create_user(user_data)
            return UserResponse.model_validate(user)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    def invite_user(
        self,
        invite_data: UserInvite,
        current_user: UserProfile
    ) -> UserResponse:
        """
        Invite a new user (creates with temporary password).

        Args:
            invite_data: User invitation data
            current_user: Authenticated user (must be admin)

        Returns:
            Created user response

        Raises:
            HTTPException: If validation fails or lacks permission
        """
        # Only admin can invite users
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can invite users"
            )

        try:
            user = self.service.invite_user(invite_data)
            return UserResponse.model_validate(user)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    def update_user(
        self,
        user_id: UUID,
        user_data: UserUpdate,
        current_user: UserProfile
    ) -> UserResponse:
        """
        Update an existing user.

        Args:
            user_id: User UUID
            user_data: Update data
            current_user: Authenticated user

        Returns:
            Updated user response

        Raises:
            HTTPException: If user not found, validation fails, or lacks permission
        """
        # Check modification permission
        if not self.service.can_modify_user(current_user, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to modify this user"
            )

        try:
            updated_user = self.service.update_user(
                user_id, user_data, current_user)

            if not updated_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            return UserResponse.model_validate(updated_user)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    def update_current_user_profile(
        self,
        profile_data: UserUpdate,
        current_user: UserProfile
    ) -> UserResponse:
        """
        Update current user's own profile.

        Args:
            profile_data: Profile update data
            current_user: Authenticated user

        Returns:
            Updated user response
        """
        updated_user = self.service.update_profile(current_user, profile_data)
        return UserResponse.model_validate(updated_user)

    def deactivate_user(
        self,
        user_id: UUID,
        current_user: UserProfile
    ) -> UserResponse:
        """
        Deactivate a user.

        Args:
            user_id: User UUID
            current_user: Authenticated user (must be admin)

        Returns:
            Updated user response

        Raises:
            HTTPException: If user not found or lacks permission
        """
        # Only admin can deactivate users
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can deactivate users"
            )

        # Prevent self-deactivation
        if current_user.id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own account"
            )

        # Get user first to check their role
        target_user = self.service.get_user_by_id(user_id)

        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Prevent deactivating admin users
        if target_user.role == 'admin':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrator accounts cannot be deactivated. Please contact system support if needed."
            )

        user = self.service.deactivate_user(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return UserResponse.model_validate(user)

    def activate_user(
        self,
        user_id: UUID,
        current_user: UserProfile
    ) -> UserResponse:
        """
        Activate a user.

        Args:
            user_id: User UUID
            current_user: Authenticated user (must be admin)

        Returns:
            Updated user response

        Raises:
            HTTPException: If user not found or lacks permission
        """
        # Only admin can activate users
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can activate users"
            )

        user = self.service.activate_user(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return UserResponse.model_validate(user)

    def get_statistics(self, current_user: UserProfile) -> UserStats:
        """
        Get user statistics.

        Args:
            current_user: Authenticated user (must be admin)

        Returns:
            User statistics

        Raises:
            HTTPException: If user lacks permission
        """
        # Only admin can view statistics
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can view user statistics"
            )

        stats = self.service.get_user_statistics()

        return UserStats(**stats)

    def change_password(
        self,
        current_password: str,
        new_password: str,
        current_user: UserProfile
    ) -> dict:
        """
        Change current user's password.

        Args:
            current_password: Current password
            new_password: New password
            current_user: Authenticated user

        Returns:
            Success message

        Raises:
            HTTPException: If validation fails
        """
        try:
            self.service.change_password(
                current_user, current_password, new_password)
            return {"message": "Password changed successfully"}
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    def reset_password(
        self,
        user_id: UUID,
        new_password: str,
        current_user: UserProfile
    ) -> dict:
        """
        Reset user password (admin function).

        Args:
            user_id: User UUID
            new_password: New password
            current_user: Authenticated user (must be admin)

        Returns:
            Success message

        Raises:
            HTTPException: If user not found or lacks permission
        """
        # Only admin can reset passwords
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can reset passwords"
            )

        user = self.service.reset_password(user_id, new_password)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return {"message": "Password reset successfully"}
