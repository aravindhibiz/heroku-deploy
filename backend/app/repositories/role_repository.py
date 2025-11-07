"""
Role Repository - Data access layer for Role and Permission operations.
Handles all database queries for role-based access control (RBAC).
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from ..repositories.base_repository import BaseRepository
from ..models.role import Role, Permission, role_permissions


class RoleRepository(BaseRepository[Role]):
    """Repository for role data access."""

    def __init__(self, db: Session):
        super().__init__(Role, db)

    def get_with_permissions(self, role_id: UUID) -> Optional[Role]:
        """
        Get role with eager-loaded permissions.

        Args:
            role_id: Role UUID

        Returns:
            Role with permissions or None
        """
        return self.db.query(Role).options(
            joinedload(Role.permissions)
        ).filter(
            Role.id == role_id,
            Role.is_active == True
        ).first()

    def get_by_name(self, name: str) -> Optional[Role]:
        """
        Get role by internal name.

        Args:
            name: Role name (e.g., 'admin', 'sales_manager')

        Returns:
            Role or None
        """
        return self.db.query(Role).options(
            joinedload(Role.permissions)
        ).filter(
            Role.name == name,
            Role.is_active == True
        ).first()

    def get_active_roles(self) -> List[Role]:
        """
        Get all active roles with permissions.

        Returns:
            List of active roles
        """
        return self.db.query(Role).options(
            joinedload(Role.permissions)
        ).filter(Role.is_active == True).all()

    def add_permission_to_role(self, role: Role, permission: Permission) -> Role:
        """
        Add a permission to a role.

        Args:
            role: Role object
            permission: Permission object

        Returns:
            Updated role
        """
        if permission not in role.permissions:
            role.permissions.append(permission)
            self.db.commit()
            self.db.refresh(role)

        return role

    def remove_permission_from_role(self, role: Role, permission: Permission) -> Role:
        """
        Remove a permission from a role.

        Args:
            role: Role object
            permission: Permission object

        Returns:
            Updated role
        """
        if permission in role.permissions:
            role.permissions.remove(permission)
            self.db.commit()
            self.db.refresh(role)

        return role

    def set_role_permissions(
        self,
        role: Role,
        permission_ids: List[UUID]
    ) -> Role:
        """
        Set (replace) all permissions for a role.

        Args:
            role: Role object
            permission_ids: List of permission UUIDs

        Returns:
            Updated role
        """
        # Clear existing permissions
        role.permissions.clear()

        # Add new permissions
        if permission_ids:
            permissions = self.db.query(Permission).filter(
                Permission.id.in_(permission_ids),
                Permission.is_active == True
            ).all()
            role.permissions.extend(permissions)

        self.db.commit()
        self.db.refresh(role)

        return role

    def update_permissions_by_name(
        self,
        role: Role,
        permission_changes: Dict[str, bool]
    ) -> Role:
        """
        Update role permissions by permission names.

        Args:
            role: Role object
            permission_changes: Dict of permission_name -> enabled/disabled

        Returns:
            Updated role
        """
        # Clear existing permissions
        role.permissions.clear()

        # Add enabled permissions
        enabled_permissions = [
            name for name, enabled in permission_changes.items()
            if enabled
        ]

        if enabled_permissions:
            permissions = self.db.query(Permission).filter(
                Permission.name.in_(enabled_permissions),
                Permission.is_active == True
            ).all()
            role.permissions.extend(permissions)

        self.db.commit()
        self.db.refresh(role)

        return role

    def get_role_statistics(self) -> Dict[str, int]:
        """
        Get role statistics.

        Returns:
            Dictionary with statistics
        """
        total = self.count()
        active = self.db.query(Role).filter(Role.is_active == True).count()
        inactive = self.db.query(Role).filter(Role.is_active == False).count()

        return {
            'total': total,
            'active': active,
            'inactive': inactive
        }


class PermissionRepository(BaseRepository[Permission]):
    """Repository for permission data access."""

    def __init__(self, db: Session):
        super().__init__(Permission, db)

    def get_by_name(self, name: str) -> Optional[Permission]:
        """
        Get permission by name.

        Args:
            name: Permission name

        Returns:
            Permission or None
        """
        return self.db.query(Permission).filter(
            Permission.name == name,
            Permission.is_active == True
        ).first()

    def get_by_names(self, names: List[str]) -> List[Permission]:
        """
        Get multiple permissions by names.

        Args:
            names: List of permission names

        Returns:
            List of permissions
        """
        return self.db.query(Permission).filter(
            Permission.name.in_(names),
            Permission.is_active == True
        ).all()

    def get_active_permissions(self) -> List[Permission]:
        """
        Get all active permissions.

        Returns:
            List of active permissions
        """
        return self.db.query(Permission).filter(
            Permission.is_active == True
        ).order_by(Permission.category, Permission.name).all()

    def get_by_category(self, category: str) -> List[Permission]:
        """
        Get permissions by category.

        Args:
            category: Permission category

        Returns:
            List of permissions
        """
        return self.db.query(Permission).filter(
            Permission.category == category,
            Permission.is_active == True
        ).all()

    def get_categories(self) -> List[str]:
        """
        Get all unique permission categories.

        Returns:
            List of category names
        """
        categories = self.db.query(Permission.category).filter(
            Permission.is_active == True
        ).distinct().all()

        return [cat[0] for cat in categories]

    def get_permissions_grouped_by_category(self) -> Dict[str, List[Permission]]:
        """
        Get permissions grouped by category.

        Returns:
            Dictionary with category -> permissions mapping
        """
        permissions = self.get_active_permissions()
        grouped = {}

        for permission in permissions:
            if permission.category not in grouped:
                grouped[permission.category] = []
            grouped[permission.category].append(permission)

        return grouped

    def get_permission_statistics(self) -> Dict[str, Any]:
        """
        Get permission statistics.

        Returns:
            Dictionary with statistics
        """
        total = self.count()
        active = self.db.query(Permission).filter(
            Permission.is_active == True).count()
        categories = self.get_categories()

        # Get count per category
        category_counts = {}
        for category in categories:
            count = self.db.query(Permission).filter(
                Permission.category == category,
                Permission.is_active == True
            ).count()
            category_counts[category] = count

        return {
            'total': total,
            'active': active,
            'categories': len(categories),
            'by_category': category_counts
        }
