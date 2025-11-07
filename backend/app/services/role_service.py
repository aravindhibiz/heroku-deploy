"""
Role Service - Business logic layer for Role and Permission operations.
Handles RBAC (Role-Based Access Control) business rules.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session

from ..repositories.role_repository import RoleRepository, PermissionRepository
from ..models.role import Role, Permission
from ..schemas.role import RoleCreate, RoleUpdate


class RoleService:
    """Service layer for role business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = RoleRepository(db)
        self.permission_repository = PermissionRepository(db)

    # Role name mapping for display/internal conversion
    ROLE_NAME_MAP = {
        'admin': 'admin',
        'sales_manager': 'sales_manager',
        'sales_rep': 'sales_rep',
        'sales_operations': 'sales_operations',
        'user': 'user',
        'Admin': 'admin',
        'Sales Manager': 'sales_manager',
        'Sales Rep': 'sales_rep',
        'Sales Operations': 'sales_operations',
        'User': 'user'
    }

    def normalize_role_name(self, role_name: str) -> str:
        """
        Convert display name to internal name.

        Args:
            role_name: Display or internal name

        Returns:
            Internal name
        """
        return self.ROLE_NAME_MAP.get(
            role_name,
            role_name.lower().replace(' ', '_')
        )

    def get_all_roles(self) -> List[Role]:
        """
        Get all active roles with permissions.

        Returns:
            List of roles
        """
        return self.repository.get_active_roles()

    def get_role_by_id(self, role_id: UUID) -> Optional[Role]:
        """
        Get a single role by ID with permissions.

        Args:
            role_id: Role UUID

        Returns:
            Role or None
        """
        return self.repository.get_with_permissions(role_id)

    def get_role_by_name(self, role_name: str) -> Optional[Role]:
        """
        Get role by name (handles display and internal names).

        Args:
            role_name: Role name (display or internal)

        Returns:
            Role or None
        """
        internal_name = self.normalize_role_name(role_name)
        return self.repository.get_by_name(internal_name)

    def create_role(self, role_data: RoleCreate) -> Role:
        """
        Create a new role.

        Args:
            role_data: Role creation data

        Returns:
            Created role

        Raises:
            ValueError: If role name already exists
        """
        # Check if role already exists
        existing_role = self.repository.get_by_name(role_data.name)
        if existing_role:
            raise ValueError(f"Role '{role_data.name}' already exists")

        # Create role
        role_dict = role_data.model_dump(exclude={'permission_ids'})
        role_dict['is_active'] = True

        created_role = self.repository.create(obj_in=role_dict)

        # Add permissions if provided
        if role_data.permission_ids:
            self.repository.set_role_permissions(
                created_role,
                role_data.permission_ids
            )

        return created_role

    def update_role(self, role_id: UUID, role_data: RoleUpdate) -> Optional[Role]:
        """
        Update an existing role.

        Args:
            role_id: Role UUID
            role_data: Update data

        Returns:
            Updated role or None
        """
        role = self.repository.get(role_id)

        if not role:
            return None

        # Update basic fields
        update_data = role_data.model_dump(
            exclude_unset=True, exclude={'permission_ids'})

        if update_data:
            updated_role = self.repository.update(
                db_obj=role, obj_in=update_data)
        else:
            updated_role = role

        # Update permissions if provided
        if role_data.permission_ids is not None:
            updated_role = self.repository.set_role_permissions(
                updated_role,
                role_data.permission_ids
            )

        return updated_role

    def delete_role(self, role_id: UUID) -> bool:
        """
        Soft delete a role (set is_active = False).

        Args:
            role_id: Role UUID

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If attempting to delete system role
        """
        role = self.repository.get(role_id)

        if not role:
            return False

        # Prevent deletion of system roles
        system_roles = ['admin', 'sales_manager', 'sales_rep']
        if role.name in system_roles:
            raise ValueError(f"System role '{role.name}' cannot be deleted")

        # Soft delete
        update_data = {'is_active': False}
        self.repository.update(db_obj=role, obj_in=update_data)

        return True

    def get_role_permissions_dict(self, role_name: str) -> Dict[str, bool]:
        """
        Get role permissions as a dictionary.

        Args:
            role_name: Role name (display or internal)

        Returns:
            Dictionary of permission_name -> True for granted permissions
        """
        role = self.get_role_by_name(role_name)

        if not role:
            return {}

        return {permission.name: True for permission in role.permissions}

    def update_role_permissions_by_name(
        self,
        role_name: str,
        permission_changes: Dict[str, bool]
    ) -> Optional[Role]:
        """
        Update role permissions using permission names.

        Args:
            role_name: Role name (display or internal)
            permission_changes: Dict of permission_name -> enabled/disabled

        Returns:
            Updated role or None
        """
        role = self.get_role_by_name(role_name)

        if not role:
            return None

        return self.repository.update_permissions_by_name(role, permission_changes)

    def restore_default_permissions(self, role_name: str) -> Optional[Role]:
        """
        Restore default permissions for a role.

        Args:
            role_name: Role name (display or internal)

        Returns:
            Updated role or None
        """
        from ..seeds.permissions_seed import get_default_role_permissions

        role = self.get_role_by_name(role_name)

        if not role:
            return None

        # Get default permissions
        default_permissions = get_default_role_permissions()
        permission_names = default_permissions.get(role.name, [])

        # Get permission objects
        permissions = self.permission_repository.get_by_names(permission_names)
        permission_ids = [p.id for p in permissions]

        # Set permissions
        return self.repository.set_role_permissions(role, permission_ids)

    def get_role_statistics(self) -> Dict[str, int]:
        """
        Get role statistics.

        Returns:
            Dictionary with statistics
        """
        return self.repository.get_role_statistics()


class PermissionService:
    """Service layer for permission business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = PermissionRepository(db)

    def get_all_permissions(self) -> List[Permission]:
        """
        Get all active permissions.

        Returns:
            List of permissions
        """
        return self.repository.get_active_permissions()

    def get_permission_by_id(self, permission_id: UUID) -> Optional[Permission]:
        """
        Get a single permission by ID.

        Args:
            permission_id: Permission UUID

        Returns:
            Permission or None
        """
        return self.repository.get(permission_id)

    def get_permission_by_name(self, name: str) -> Optional[Permission]:
        """
        Get permission by name.

        Args:
            name: Permission name

        Returns:
            Permission or None
        """
        return self.repository.get_by_name(name)

    def get_permissions_by_category(self, category: str) -> List[Permission]:
        """
        Get permissions by category.

        Args:
            category: Permission category

        Returns:
            List of permissions
        """
        return self.repository.get_by_category(category)

    def get_permissions_grouped(self) -> Dict[str, List[Permission]]:
        """
        Get permissions grouped by category.

        Returns:
            Dictionary with category -> permissions mapping
        """
        return self.repository.get_permissions_grouped_by_category()

    def get_categories(self) -> List[str]:
        """
        Get all permission categories.

        Returns:
            List of category names
        """
        return self.repository.get_categories()

    def get_permission_statistics(self) -> Dict[str, Any]:
        """
        Get permission statistics.

        Returns:
            Dictionary with statistics
        """
        return self.repository.get_permission_statistics()
