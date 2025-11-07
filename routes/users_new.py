"""
User Routes - Clean API endpoint definitions.
All business logic is in UserController.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.database import get_db
from core.auth import get_current_user
from models.user import UserProfile
from controllers.user_controller import UserController
from schemas.user import (
    UserResponse, UserCreate, UserUpdate, UserInvite, UserStats,
    PasswordChange, PasswordReset
)

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
async def get_users(
    search: Optional[str] = Query(
        None, description="Search users by name or email"),
    role: Optional[str] = Query(None, description="Filter by role"),
    roles: Optional[str] = Query(
        None, description="Filter by multiple roles (comma-separated)"),
    status: Optional[str] = Query(
        None, description="Filter by status (active/inactive)"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get all users with optional filters.

    **Permissions:** Admin or Manager

    **Filters:**
    - **search**: Search by first name, last name, or email
    - **role**: Filter by specific role (admin, sales_manager, sales_rep)
    - **roles**: Filter by multiple roles (comma-separated)
    - **status**: Filter by active/inactive status

    Returns users ordered by creation date (newest first).
    """
    controller = UserController(db)
    return controller.list_users(
        current_user=current_user,
        search=search,
        role=role,
        roles=roles,
        status=status
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get current authenticated user's profile.

    Returns the profile of the currently logged-in user.
    """
    controller = UserController(None)  # No DB needed for this endpoint
    return controller.get_current_user_profile(current_user=current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    profile_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Update current user's own profile.

    **Allowed fields:**
    - first_name
    - last_name
    - phone
    - avatar_url

    Other fields like role and is_active cannot be self-updated.
    """
    controller = UserController(db)
    return controller.update_current_user_profile(
        profile_data=profile_data,
        current_user=current_user
    )


@router.post("/me/change-password")
async def change_password(
    password_data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Change current user's password.

    Requires current password for verification.

    **Request Body:**
    - **current_password**: Current password
    - **new_password**: New password
    """
    controller = UserController(db)
    return controller.change_password(
        current_password=password_data.current_password,
        new_password=password_data.new_password,
        current_user=current_user
    )


@router.get("/stats", response_model=UserStats)
async def get_user_statistics(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get user statistics.

    **Permissions:** Admin only

    Returns:
    - Total users
    - Active users
    - Inactive users
    - Role distribution
    """
    controller = UserController(db)
    return controller.get_statistics(current_user=current_user)


@router.post("/invite", response_model=UserResponse, status_code=201)
async def invite_user(
    invite_data: UserInvite,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Invite a new user to the system.

    **Permissions:** Admin only

    Creates a new user account with a temporary password.
    In production, this should send an invitation email with a password reset link.

    **Required fields:**
    - email
    - first_name
    - last_name
    - role
    """
    controller = UserController(db)
    return controller.invite_user(
        invite_data=invite_data,
        current_user=current_user
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get a single user by ID.

    **Permissions:**
    - Admin: Can view any user
    - Manager: Can view any user (TODO: restrict to team members)
    - User: Can only view their own profile
    """
    controller = UserController(db)
    return controller.get_user(
        user_id=user_id,
        current_user=current_user
    )


@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Create a new user.

    **Permissions:** Admin only

    **Required fields:**
    - email
    - password
    - first_name
    - last_name
    - role (default: sales_rep)
    """
    controller = UserController(db)
    return controller.create_user(
        user_data=user_data,
        current_user=current_user
    )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Update an existing user.

    **Permissions:**
    - Admin: Can update any user
    - User: Can update their own profile (limited fields)

    **Validation:**
    - Users cannot deactivate themselves
    - Admin accounts cannot be deactivated
    - Email must be unique
    """
    controller = UserController(db)
    return controller.update_user(
        user_id=user_id,
        user_data=user_data,
        current_user=current_user
    )


@router.put("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Deactivate a user account.

    **Permissions:** Admin only

    **Validation:**
    - Cannot deactivate yourself
    - Cannot deactivate admin accounts

    Deactivated users cannot log in but their data is preserved
    for referential integrity with contacts, deals, activities, etc.
    """
    controller = UserController(db)
    return controller.deactivate_user(
        user_id=user_id,
        current_user=current_user
    )


@router.put("/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Activate a previously deactivated user account.

    **Permissions:** Admin only

    Re-enables login for the user.
    """
    controller = UserController(db)
    return controller.activate_user(
        user_id=user_id,
        current_user=current_user
    )


@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: UUID,
    password_data: PasswordReset,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Reset a user's password (admin function).

    **Permissions:** Admin only

    Sets a new password for the user without requiring their current password.
    User should be notified to change their password after reset.

    **Request Body:**
    - **new_password**: New password to set
    """
    controller = UserController(db)
    return controller.reset_password(
        user_id=user_id,
        new_password=password_data.new_password,
        current_user=current_user
    )
