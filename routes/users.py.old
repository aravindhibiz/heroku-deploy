from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from uuid import UUID
from ..core.database import get_db
from ..core.auth import (
    get_current_user, require_admin, require_manager_or_admin,
    require_sales_user, require_any_authenticated, can_access_user_data,
    can_modify_user_data
)
from ..models.user import UserProfile
from ..schemas.user import UserResponse, UserUpdate, UserInvite, UserStats

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
async def get_all_users(
    search: Optional[str] = Query(
        None, description="Search users by name or email"),
    role: Optional[str] = Query(None, description="Filter by role"),
    roles: Optional[str] = Query(
        None, description="Filter by multiple roles (comma-separated)"),
    status: Optional[str] = Query(
        None, description="Filter by status (active/inactive)"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_manager_or_admin())
):
    # Role-based data filtering
    query = db.query(UserProfile)

    # Admin can see all users, managers can see their team + themselves
    if current_user.role != 'admin':
        # For now, sales_manager can see all users
        # TODO: Implement team-based filtering when team structure is defined
        pass

    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                UserProfile.first_name.ilike(search_term),
                UserProfile.last_name.ilike(search_term),
                UserProfile.email.ilike(search_term)
            )
        )

    # Apply role filter
    if role:
        query = query.filter(UserProfile.role == role)
    elif roles:
        role_list = [r.strip() for r in roles.split(',')]
        query = query.filter(UserProfile.role.in_(role_list))

    # Apply status filter
    if status:
        is_active = status.lower() == 'active'
        query = query.filter(UserProfile.is_active == is_active)

    users = query.all()
    return users


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: UserProfile = Depends(get_current_user)
):
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    updates: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    # Update user fields
    update_data = updates.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(current_user, field):
            setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    # Only admin users can get other users
    if current_user.role != 'admin' and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    updates: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    # Check if user can modify this user's data
    if not can_modify_user_data(current_user, str(user_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to modify this user"
        )

    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get the update data
    update_data = updates.dict(exclude_unset=True)

    # Prevent admin from deactivating themselves
    if 'is_active' in update_data and not update_data['is_active']:
        if current_user.id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own account"
            )

        # Prevent deactivating other admin users
        if user.role == 'admin':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrator accounts cannot be deactivated. Please contact system support if needed."
            )

    # Update user fields
    for field, value in update_data.items():
        if hasattr(user, field):
            setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


# Delete endpoint removed to prevent data integrity issues
# Users should be deactivated instead of deleted to maintain
# referential integrity with related contacts, deals, etc.
# Use the deactivate endpoint instead: PUT /{user_id}/deactivate


@router.get("/stats", response_model=UserStats)
async def get_user_stats(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    # Only admin users can get user stats
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    total_users = db.query(UserProfile).count()
    active_users = db.query(UserProfile).filter(
        UserProfile.is_active == True).count()

    # Get role distribution
    role_stats = db.query(
        UserProfile.role,
        func.count(UserProfile.id).label('count')
    ).group_by(UserProfile.role).all()

    roles = {role: count for role, count in role_stats}

    return UserStats(
        total=total_users,
        active=active_users,
        inactive=total_users - active_users,
        roles=roles
    )


@router.post("/invite", response_model=UserResponse)
async def invite_user(
    invite_data: UserInvite,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_admin())
):
    # Only admin users can invite new users (handled by decorator)

    # Check if user already exists
    existing_user = db.query(UserProfile).filter(
        UserProfile.email == invite_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # Create new user with temporary password (in real app, send invitation email)
    from ..core.auth import get_password_hash

    new_user = UserProfile(
        email=invite_data.email,
        first_name=invite_data.first_name,
        last_name=invite_data.last_name,
        role=invite_data.role,
        hashed_password=get_password_hash(
            "temporary123"),  # Temporary password
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user
