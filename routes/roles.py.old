from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel
from ..core.database import get_db
from ..core.auth import get_current_user
from ..models.user import UserProfile
from ..models.role import Role, Permission
from ..schemas.role import (
    RoleResponse, RoleCreate, RoleUpdate,
    PermissionResponse, RolePermissionUpdate
)

router = APIRouter()


@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify routing is working"""
    return {"message": "Roles router is working"}


@router.get("/", response_model=List[RoleResponse])
async def get_all_roles(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    # Only admin users can manage roles
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    roles = db.query(Role).filter(Role.is_active == True).all()
    return roles


@router.get("/permissions", response_model=List[PermissionResponse])
async def get_all_permissions(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    # Only admin users can view permissions
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    permissions = db.query(Permission).filter(
        Permission.is_active == True).all()
    return permissions


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role_by_id(
    role_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    # Only admin users can view roles
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    role = db.query(Role).filter(Role.id == role_id,
                                 Role.is_active == True).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    return role


@router.get("/by-name/{role_name}/permissions")
async def get_role_permissions(
    role_name: str,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get permissions for a specific role by name"""
    # Only admin users can view role permissions
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    # Handle both display names and internal names
    role_name_map = {
        'admin': 'admin',
        'sales_manager': 'sales_manager',
        'sales_rep': 'sales_rep',
        'sales_operations': 'sales_operations',
        'Admin': 'admin',
        'Sales Manager': 'sales_manager',
        'Sales Rep': 'sales_rep',
        'Sales Operations': 'sales_operations'
    }

    internal_name = role_name_map.get(
        role_name, role_name.lower().replace(' ', '_'))

    role = db.query(Role).filter(
        Role.name == internal_name,
        Role.is_active == True
    ).first()

    if not role:
        # Return empty permissions for unknown roles
        return {}

    # Return permissions as a dictionary
    permissions = {}
    for permission in role.permissions:
        permissions[permission.name] = True

    return permissions


class PermissionUpdateRequest(BaseModel):
    role_name: Optional[str] = None
    permissions: Dict[str, bool]


@router.put("/by-name/{role_name}/permissions")
async def update_role_permissions_by_name(
    role_name: str,
    request_data: PermissionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Update permissions for a specific role by name"""
    print(f"Received request for role: {role_name}")
    print(f"Request data: {request_data}")

    # Only admin users can update role permissions
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    # Extract permissions from request data
    permissions = request_data.permissions
    print(f"Extracted permissions: {permissions}")

    # Handle both display names and internal names
    role_name_map = {
        'admin': 'admin',
        'sales_manager': 'sales_manager',
        'sales_rep': 'sales_rep',
        'sales_operations': 'sales_operations',
        'Admin': 'admin',
        'Sales Manager': 'sales_manager',
        'Sales Rep': 'sales_rep',
        'Sales Operations': 'sales_operations'
    }

    internal_name = role_name_map.get(
        role_name, role_name.lower().replace(' ', '_'))
    print(f"Mapped role name '{role_name}' to internal name '{internal_name}'")

    role = db.query(Role).filter(
        Role.name == internal_name,
        Role.is_active == True
    ).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{internal_name}' not found"
        )

    print(f"Found role: {role.name} - {role.display_name}")

    # Clear existing permissions
    role.permissions.clear()

    # Add new permissions based on the update
    for permission_name, enabled in permissions.items():
        if enabled:
            permission = db.query(Permission).filter(
                Permission.name == permission_name,
                Permission.is_active == True
            ).first()
            if permission:
                role.permissions.append(permission)

    db.commit()
    db.refresh(role)

    # Return updated permissions as dictionary
    updated_permissions = {}
    for permission in role.permissions:
        updated_permissions[permission.name] = True

    return {
        "role_name": role.display_name,
        "permissions": updated_permissions,
        "message": f"Updated permissions for {role.display_name}"
    }


@router.post("/by-name/{role_name}/restore-defaults")
async def restore_default_permissions(
    role_name: str,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Restore default permissions for a role"""
    # Only admin users can restore permissions
    if current_user.role != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )

    # Import the default permissions function
    from ..seeds.permissions_seed import get_default_role_permissions

    # Handle role name mapping
    role_name_map = {
        'Admin': 'admin',
        'Sales Manager': 'sales_manager',
        'Sales Rep': 'sales_rep',
        'User': 'user'
    }

    internal_name = role_name_map.get(role_name, role_name.lower().replace(' ', '_'))

    # Find the role
    role = db.query(Role).filter(
        Role.name == internal_name,
        Role.is_active == True
    ).first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{internal_name}' not found"
        )

    # Get default permissions for this role
    default_permissions = get_default_role_permissions()
    permission_names = default_permissions.get(internal_name, [])

    # Clear existing permissions
    role.permissions.clear()

    # Add default permissions
    for permission_name in permission_names:
        permission = db.query(Permission).filter(
            Permission.name == permission_name,
            Permission.is_active == True
        ).first()
        if permission:
            role.permissions.append(permission)

    db.commit()
    db.refresh(role)

    # Return updated permissions as dictionary
    restored_permissions = {}
    for permission in role.permissions:
        restored_permissions[permission.name] = True

    return {
        "role_name": role.display_name,
        "permissions": restored_permissions,
        "message": f"Restored default permissions for {role.display_name}"
    }
