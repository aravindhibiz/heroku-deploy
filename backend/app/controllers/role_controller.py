"""
Role Controller - HTTP request/response handling for Roles and Permissions.
Handles validation, permissions, and response formatting for RBAC.
"""

from typing import List, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..services.role_service import RoleService, PermissionService
from ..schemas.role import (
    RoleResponse, RoleCreate, RoleUpdate,
    PermissionResponse, RolePermissionUpdate
)
from ..models.user import UserProfile


class RoleController:
    """Controller for role HTTP operations."""

    def __init__(self, db: Session):
        self.db = db
        self.service = RoleService(db)
        self.permission_service = PermissionService(db)

    def list_roles(self, current_user: UserProfile) -> List[RoleResponse]:
        """
        Get all active roles.

        Args:
            current_user: Authenticated user (must be admin)

        Returns:
            List of role responses

        Raises:
            HTTPException: If user lacks permission
        """
        # Only admin can view roles
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can view roles"
            )

        roles = self.service.get_all_roles()
        return [RoleResponse.model_validate(role) for role in roles]

    def get_role(self, role_id: UUID, current_user: UserProfile) -> RoleResponse:
        """
        Get a single role by ID.

        Args:
            role_id: Role UUID
            current_user: Authenticated user (must be admin)

        Returns:
            Role response

        Raises:
            HTTPException: If role not found or user lacks permission
        """
        # Only admin can view roles
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can view roles"
            )

        role = self.service.get_role_by_id(role_id)

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )

        return RoleResponse.model_validate(role)

    def get_role_by_name(
        self,
        role_name: str,
        current_user: UserProfile
    ) -> RoleResponse:
        """
        Get role by name.

        Args:
            role_name: Role name (display or internal)
            current_user: Authenticated user (must be admin)

        Returns:
            Role response

        Raises:
            HTTPException: If role not found or user lacks permission
        """
        # Only admin can view roles
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can view roles"
            )

        role = self.service.get_role_by_name(role_name)

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role '{role_name}' not found"
            )

        return RoleResponse.model_validate(role)

    def create_role(
        self,
        role_data: RoleCreate,
        current_user: UserProfile
    ) -> RoleResponse:
        """
        Create a new role.

        Args:
            role_data: Role creation data
            current_user: Authenticated user (must be admin)

        Returns:
            Created role response

        Raises:
            HTTPException: If validation fails or user lacks permission
        """
        # Only admin can create roles
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can create roles"
            )

        try:
            role = self.service.create_role(role_data)
            return RoleResponse.model_validate(role)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    def update_role(
        self,
        role_id: UUID,
        role_data: RoleUpdate,
        current_user: UserProfile
    ) -> RoleResponse:
        """
        Update an existing role.

        Args:
            role_id: Role UUID
            role_data: Update data
            current_user: Authenticated user (must be admin)

        Returns:
            Updated role response

        Raises:
            HTTPException: If role not found or user lacks permission
        """
        # Only admin can update roles
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can update roles"
            )

        updated_role = self.service.update_role(role_id, role_data)

        if not updated_role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )

        return RoleResponse.model_validate(updated_role)

    def delete_role(
        self,
        role_id: UUID,
        current_user: UserProfile
    ) -> dict:
        """
        Delete a role (soft delete).

        Args:
            role_id: Role UUID
            current_user: Authenticated user (must be admin)

        Returns:
            Success message

        Raises:
            HTTPException: If role not found, system role, or user lacks permission
        """
        # Only admin can delete roles
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can delete roles"
            )

        try:
            success = self.service.delete_role(role_id)

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Role not found"
                )

            return {"message": "Role deleted successfully"}
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    def get_role_permissions(
        self,
        role_name: str,
        current_user: UserProfile
    ) -> Dict[str, bool]:
        """
        Get permissions for a role as a dictionary.

        Args:
            role_name: Role name (display or internal)
            current_user: Authenticated user (must be admin)

        Returns:
            Dictionary of permission_name -> True

        Raises:
            HTTPException: If user lacks permission
        """
        # Only admin can view permissions
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can view role permissions"
            )

        permissions = self.service.get_role_permissions_dict(role_name)
        return permissions

    def update_role_permissions(
        self,
        role_name: str,
        permission_update: RolePermissionUpdate,
        current_user: UserProfile
    ) -> Dict[str, Any]:
        """
        Update permissions for a role.

        Args:
            role_name: Role name (display or internal)
            permission_update: Permission changes
            current_user: Authenticated user (must be admin)

        Returns:
            Updated permissions with message

        Raises:
            HTTPException: If role not found or user lacks permission
        """
        # Only admin can update permissions
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can update role permissions"
            )

        updated_role = self.service.update_role_permissions_by_name(
            role_name,
            permission_update.permissions
        )

        if not updated_role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role '{role_name}' not found"
            )

        # Return updated permissions
        updated_permissions = {
            permission.name: True
            for permission in updated_role.permissions
        }

        return {
            "role_name": updated_role.display_name,
            "permissions": updated_permissions,
            "message": f"Updated permissions for {updated_role.display_name}"
        }

    def restore_default_permissions(
        self,
        role_name: str,
        current_user: UserProfile
    ) -> Dict[str, Any]:
        """
        Restore default permissions for a role.

        Args:
            role_name: Role name (display or internal)
            current_user: Authenticated user (must be admin)

        Returns:
            Restored permissions with message

        Raises:
            HTTPException: If role not found or user lacks permission
        """
        # Only admin can restore permissions
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can restore default permissions"
            )

        restored_role = self.service.restore_default_permissions(role_name)

        if not restored_role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role '{role_name}' not found"
            )

        # Return restored permissions
        restored_permissions = {
            permission.name: True
            for permission in restored_role.permissions
        }

        return {
            "role_name": restored_role.display_name,
            "permissions": restored_permissions,
            "message": f"Restored default permissions for {restored_role.display_name}"
        }

    def get_role_statistics(self, current_user: UserProfile) -> Dict[str, int]:
        """
        Get role statistics.

        Args:
            current_user: Authenticated user (must be admin)

        Returns:
            Role statistics

        Raises:
            HTTPException: If user lacks permission
        """
        # Only admin can view statistics
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can view role statistics"
            )

        return self.service.get_role_statistics()


class PermissionController:
    """Controller for permission HTTP operations."""

    def __init__(self, db: Session):
        self.db = db
        self.service = PermissionService(db)

    def list_permissions(
        self,
        current_user: UserProfile
    ) -> List[PermissionResponse]:
        """
        Get all active permissions.

        Args:
            current_user: Authenticated user (must be admin)

        Returns:
            List of permission responses

        Raises:
            HTTPException: If user lacks permission
        """
        # Only admin can view permissions
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can view permissions"
            )

        permissions = self.service.get_all_permissions()
        return [PermissionResponse.model_validate(p) for p in permissions]

    def get_permissions_grouped(
        self,
        current_user: UserProfile
    ) -> Dict[str, List[PermissionResponse]]:
        """
        Get permissions grouped by category.

        Args:
            current_user: Authenticated user (must be admin)

        Returns:
            Dictionary of category -> permissions

        Raises:
            HTTPException: If user lacks permission
        """
        # Only admin can view permissions
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can view permissions"
            )

        grouped = self.service.get_permissions_grouped()

        # Convert to response models
        result = {}
        for category, permissions in grouped.items():
            result[category] = [
                PermissionResponse.model_validate(p) for p in permissions
            ]

        return result

    def get_permission_statistics(
        self,
        current_user: UserProfile
    ) -> Dict[str, Any]:
        """
        Get permission statistics.

        Args:
            current_user: Authenticated user (must be admin)

        Returns:
            Permission statistics

        Raises:
            HTTPException: If user lacks permission
        """
        # Only admin can view statistics
        if current_user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can view permission statistics"
            )

        return self.service.get_permission_statistics()
