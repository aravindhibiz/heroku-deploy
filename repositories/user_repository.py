"""
User Repository - Data access layer for User operations.
Handles all database queries for user management.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_

from repositories.base_repository import BaseRepository
from models.user import UserProfile


class UserRepository(BaseRepository[UserProfile]):
    """Repository for user data access."""

    def __init__(self, db: Session):
        super().__init__(UserProfile, db)

    def get_by_email(self, email: str) -> Optional[UserProfile]:
        """
        Get user by email address.

        Args:
            email: User email

        Returns:
            User or None if not found
        """
        return self.db.query(UserProfile).filter(
            UserProfile.email == email
        ).first()

    def get_active_users(self) -> List[UserProfile]:
        """
        Get all active users.

        Returns:
            List of active users
        """
        return self.db.query(UserProfile).filter(
            UserProfile.is_active == True
        ).all()

    def search_users(
        self,
        search: Optional[str] = None,
        role: Optional[str] = None,
        roles: Optional[List[str]] = None,
        is_active: Optional[bool] = None
    ) -> List[UserProfile]:
        """
        Search users with multiple filters.

        Args:
            search: Search term for name or email
            role: Filter by specific role
            roles: Filter by multiple roles
            is_active: Filter by active status

        Returns:
            List of matching users
        """
        query = self.db.query(UserProfile)

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
            query = query.filter(UserProfile.role.in_(roles))

        # Apply active status filter
        if is_active is not None:
            query = query.filter(UserProfile.is_active == is_active)

        return query.order_by(UserProfile.created_at.desc()).all()

    def get_by_role(self, role: str, active_only: bool = True) -> List[UserProfile]:
        """
        Get all users with a specific role.

        Args:
            role: Role name
            active_only: Only return active users

        Returns:
            List of users
        """
        query = self.db.query(UserProfile).filter(UserProfile.role == role)

        if active_only:
            query = query.filter(UserProfile.is_active == True)

        return query.all()

    def get_role_counts(self) -> Dict[str, int]:
        """
        Get count of users by role.

        Returns:
            Dictionary with role counts
        """
        role_stats = self.db.query(
            UserProfile.role,
            func.count(UserProfile.id).label('count')
        ).group_by(UserProfile.role).all()

        return {role: count for role, count in role_stats}

    def count_active_users(self) -> int:
        """
        Count active users.

        Returns:
            Number of active users
        """
        return self.db.query(UserProfile).filter(
            UserProfile.is_active == True
        ).count()

    def count_inactive_users(self) -> int:
        """
        Count inactive users.

        Returns:
            Number of inactive users
        """
        return self.db.query(UserProfile).filter(
            UserProfile.is_active == False
        ).count()

    def update_password(self, user: UserProfile, hashed_password: str) -> UserProfile:
        """
        Update user password.

        Args:
            user: User object
            hashed_password: New hashed password

        Returns:
            Updated user
        """
        user.hashed_password = hashed_password
        self.db.commit()
        self.db.refresh(user)
        return user

    def deactivate_user(self, user_id: UUID) -> Optional[UserProfile]:
        """
        Deactivate a user.

        Args:
            user_id: User UUID

        Returns:
            Updated user or None
        """
        user = self.get(user_id)
        if not user:
            return None

        user.is_active = False
        self.db.commit()
        self.db.refresh(user)
        return user

    def activate_user(self, user_id: UUID) -> Optional[UserProfile]:
        """
        Activate a user.

        Args:
            user_id: User UUID

        Returns:
            Updated user or None
        """
        user = self.get(user_id)
        if not user:
            return None

        user.is_active = True
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_admins(self, active_only: bool = True) -> List[UserProfile]:
        """
        Get all admin users.

        Args:
            active_only: Only return active admins

        Returns:
            List of admin users
        """
        return self.get_by_role('admin', active_only)

    def get_managers(self, active_only: bool = True) -> List[UserProfile]:
        """
        Get all manager users.

        Args:
            active_only: Only return active managers

        Returns:
            List of manager users
        """
        return self.get_by_role('sales_manager', active_only)

    def email_exists(self, email: str, exclude_user_id: Optional[UUID] = None) -> bool:
        """
        Check if email already exists.

        Args:
            email: Email to check
            exclude_user_id: Optional user ID to exclude from check (for updates)

        Returns:
            True if email exists, False otherwise
        """
        query = self.db.query(UserProfile).filter(UserProfile.email == email)

        if exclude_user_id:
            query = query.filter(UserProfile.id != exclude_user_id)

        return query.first() is not None

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive user statistics.

        Returns:
            Dictionary with statistics
        """
        total = self.count()
        active = self.count_active_users()
        inactive = self.count_inactive_users()
        role_counts = self.get_role_counts()

        return {
            'total': total,
            'active': active,
            'inactive': inactive,
            'roles': role_counts
        }

    def get_recently_created(self, limit: int = 10) -> List[UserProfile]:
        """
        Get recently created users.

        Args:
            limit: Maximum number of users to return

        Returns:
            List of recently created users
        """
        return self.db.query(UserProfile).order_by(
            UserProfile.created_at.desc()
        ).limit(limit).all()
