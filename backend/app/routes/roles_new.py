"""
Role Routes - Clean API endpoint definitions for Roles and Permissions.
All business logic is in RoleController and PermissionController.
"""

from typing import List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.auth import get_current_user
from ..models.user import UserProfile
from ..controllers.role_controller import RoleController, PermissionController
from ..schemas.role import (
    RoleResponse, RoleCreate, RoleUpdate,
    PermissionResponse, RolePermissionUpdate
)

router = APIRouter()


# ==================== ROLE ENDPOINTS ====================

@router.get("/", response_model=List[RoleResponse])
async def get_roles(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get all active roles with their permissions.

    **Permissions:** Admin only

    Returns all roles in the system with their associated permissions.
    """
    controller = RoleController(db)
    return controller.list_roles(current_user=current_user)


@router.get("/stats")
async def get_role_statistics(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get role statistics.

    **Permissions:** Admin only

    Returns:
    - Total roles
    - Active roles
    - Inactive roles
    """
    controller = RoleController(db)
    return controller.get_role_statistics(current_user=current_user)


@router.get("/by-name/{role_name}", response_model=RoleResponse)
async def get_role_by_name(
    role_name: str,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get a role by name (supports display and internal names).

    **Permissions:** Admin only

    **Supported names:**
    - admin, Admin
    - sales_manager, Sales Manager
    - sales_rep, Sales Rep
    - sales_operations, Sales Operations
    """
    controller = RoleController(db)
    return controller.get_role_by_name(
        role_name=role_name,
        current_user=current_user
    )


@router.get("/by-name/{role_name}/permissions")
async def get_role_permissions_by_name(
    role_name: str,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get permissions for a specific role by name.

    **Permissions:** Admin only

    Returns a dictionary of permission_name -> true for granted permissions.
    """
    controller = RoleController(db)
    return controller.get_role_permissions(
        role_name=role_name,
        current_user=current_user
    )


@router.put("/by-name/{role_name}/permissions")
async def update_role_permissions_by_name(
    role_name: str,
    permission_update: RolePermissionUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Update permissions for a specific role by name.

    **Permissions:** Admin only

    **Request Body:**
    ```json
    {
      "permissions": {
        "contacts.create": true,
        "contacts.view": true,
        "contacts.edit": false
      }
    }
    ```

    Permissions set to `true` will be granted, `false` will be revoked.
    """
    controller = RoleController(db)
    return controller.update_role_permissions(
        role_name=role_name,
        permission_update=permission_update,
        current_user=current_user
    )


@router.post("/by-name/{role_name}/restore-defaults")
async def restore_default_permissions_for_role(
    role_name: str,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Restore default permissions for a role.

    **Permissions:** Admin only

    Resets the role's permissions to the system defaults.
    Useful for undoing permission changes.
    """
    controller = RoleController(db)
    return controller.restore_default_permissions(
        role_name=role_name,
        current_user=current_user
    )


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get a single role by ID.

    **Permissions:** Admin only

    Returns the role with all associated permissions.
    """
    controller = RoleController(db)
    return controller.get_role(
        role_id=role_id,
        current_user=current_user
    )


@router.post("/", response_model=RoleResponse, status_code=201)
async def create_role(
    role_data: RoleCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Create a new role.

    **Permissions:** Admin only

    **Required fields:**
    - name (internal name, e.g., 'custom_role')
    - display_name (human-readable name)

    **Optional fields:**
    - description
    - permission_ids (list of permission UUIDs)
    """
    controller = RoleController(db)
    return controller.create_role(
        role_data=role_data,
        current_user=current_user
    )


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    role_data: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Update an existing role.

    **Permissions:** Admin only

    All fields are optional. Permissions can be updated separately
    using the dedicated permission endpoints.
    """
    controller = RoleController(db)
    return controller.update_role(
        role_id=role_id,
        role_data=role_data,
        current_user=current_user
    )


@router.delete("/{role_id}")
async def delete_role(
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Delete a role (soft delete).

    **Permissions:** Admin only

    **Validation:**
    - System roles (admin, sales_manager, sales_rep) cannot be deleted

    Sets is_active = false to preserve referential integrity.
    """
    controller = RoleController(db)
    return controller.delete_role(
        role_id=role_id,
        current_user=current_user
    )


# ==================== PERMISSION ENDPOINTS ====================

@router.get("/permissions/all", response_model=List[PermissionResponse])
async def get_all_permissions(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get all active permissions.

    **Permissions:** Admin only

    Returns all permissions ordered by category and name.
    """
    controller = PermissionController(db)
    return controller.list_permissions(current_user=current_user)


@router.get("/permissions/grouped")
async def get_permissions_grouped_by_category(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get permissions grouped by category.

    **Permissions:** Admin only

    Returns a dictionary of category -> permissions for easier organization.
    Useful for building permission management UIs.
    """
    controller = PermissionController(db)
    return controller.get_permissions_grouped(current_user=current_user)


@router.get("/permissions/stats")
async def get_permission_statistics(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get permission statistics.

    **Permissions:** Admin only

    Returns:
    - Total permissions
    - Active permissions
    - Number of categories
    - Permissions per category
    """
    controller = PermissionController(db)
    return controller.get_permission_statistics(current_user=current_user)
