from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import uuid


class PermissionBase(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    category: str


class PermissionResponse(PermissionBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoleBase(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    permission_ids: List[uuid.UUID] = []


class RoleUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[List[uuid.UUID]] = None


class RoleResponse(RoleBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    permissions: List[PermissionResponse] = []

    model_config = {"from_attributes": True}


class RolePermissionUpdate(BaseModel):
    role_id: Optional[uuid.UUID] = None
    role_name: Optional[str] = None
    permissions: Dict[str, bool]  # permission_name -> enabled/disabled
