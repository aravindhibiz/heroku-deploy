from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Callable, Union
from .database import get_db
from .security import verify_token
from ..models.user import UserProfile
from ..models.role import Role, Permission

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = verify_token(credentials.credentials)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user

# Role-based access control functions
def require_role(allowed_roles: List[str]) -> Callable:
    """Decorator factory to require specific roles for endpoint access"""
    def role_checker(current_user: UserProfile = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker

def require_admin():
    """Require admin role"""
    return require_role(['admin'])

def require_manager_or_admin():
    """Require sales_manager or admin role"""
    return require_role(['admin', 'sales_manager'])

def require_sales_user():
    """Require any sales role (sales_rep, sales_manager, admin)"""
    return require_role(['admin', 'sales_manager', 'sales_rep'])

def require_any_authenticated():
    """Require any authenticated user"""
    return require_role(['admin', 'sales_manager', 'sales_rep', 'user'])

# Data ownership validation
def can_access_user_data(current_user: UserProfile, target_user_id: str) -> bool:
    """Check if current user can access another user's data"""
    if current_user.role == 'admin':
        return True
    if current_user.role == 'sales_manager':
        # TODO: Implement team membership check
        return True  # For now, allow managers to access all data
    return str(current_user.id) == target_user_id

def can_modify_user_data(current_user: UserProfile, target_user_id: str) -> bool:
    """Check if current user can modify another user's data"""
    if current_user.role == 'admin':
        return True
    if current_user.role == 'sales_manager':
        # TODO: Implement team membership check
        return True  # For now, allow managers to modify team data
    return str(current_user.id) == target_user_id

def validate_data_access(target_user_id: str):
    """Dependency to validate data access permissions"""
    def access_validator(current_user: UserProfile = Depends(get_current_user)):
        if not can_access_user_data(current_user, target_user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this resource"
            )
        return current_user
    return access_validator


# Dynamic permission-based access control
def get_user_permissions(db: Session, user: UserProfile) -> List[str]:
    """Get all permission names for a user based on their role"""
    role = db.query(Role).filter(
        Role.name == user.role,
        Role.is_active == True
    ).first()

    if not role:
        return []

    return [permission.name for permission in role.permissions if permission.is_active]


def has_permission(db: Session, user: UserProfile, permission_name: str) -> bool:
    """Check if user has a specific permission"""
    user_permissions = get_user_permissions(db, user)
    return permission_name in user_permissions


def has_any_permission(db: Session, user: UserProfile, permission_names: List[str]) -> bool:
    """Check if user has any of the specified permissions"""
    user_permissions = get_user_permissions(db, user)
    return any(perm in user_permissions for perm in permission_names)


def has_all_permissions(db: Session, user: UserProfile, permission_names: List[str]) -> bool:
    """Check if user has all of the specified permissions"""
    user_permissions = get_user_permissions(db, user)
    return all(perm in user_permissions for perm in permission_names)


def require_permission(permission_name: str) -> Callable:
    """Dependency factory to require a specific permission for endpoint access"""
    def permission_checker(
        current_user: UserProfile = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        if not has_permission(db, current_user, permission_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required permission: {permission_name}"
            )
        return current_user
    return permission_checker


def require_any_permission(permission_names: List[str]) -> Callable:
    """Dependency factory to require any one of the specified permissions"""
    def permission_checker(
        current_user: UserProfile = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        if not has_any_permission(db, current_user, permission_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required one of: {', '.join(permission_names)}"
            )
        return current_user
    return permission_checker


def require_all_permissions(permission_names: List[str]) -> Callable:
    """Dependency factory to require all specified permissions"""
    def permission_checker(
        current_user: UserProfile = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        if not has_all_permissions(db, current_user, permission_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required all of: {', '.join(permission_names)}"
            )
        return current_user
    return permission_checker


def check_resource_permission(
    db: Session,
    user: UserProfile,
    view_all_permission: str,
    view_own_permission: str,
    resource_owner_id: str
) -> bool:
    """
    Check if user can access a resource based on view_all or view_own permissions

    Args:
        db: Database session
        user: Current user
        view_all_permission: Permission to view all resources (e.g., 'deals.view_all')
        view_own_permission: Permission to view own resources (e.g., 'deals.view_own')
        resource_owner_id: Owner ID of the resource being accessed

    Returns:
        True if user can access the resource
    """
    # Check if user has view_all permission
    if has_permission(db, user, view_all_permission):
        return True

    # Check if user has view_own permission and owns the resource
    if has_permission(db, user, view_own_permission) and str(user.id) == str(resource_owner_id):
        return True

    return False