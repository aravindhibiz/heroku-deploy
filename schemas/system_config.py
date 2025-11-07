from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, List
from datetime import datetime
import uuid


class SystemConfigBase(BaseModel):
    key: str
    value: Any
    category: str
    description: Optional[str] = None


class SystemConfigCreate(SystemConfigBase):
    pass


class SystemConfigUpdate(BaseModel):
    value: Any
    description: Optional[str] = None


class SystemConfigResponse(SystemConfigBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SystemConfigBulkUpdate(BaseModel):
    configurations: Dict[str, Any]


class SystemConfigBulkUpdateItem(BaseModel):
    key: str
    value: Any


class SystemConfigBulkUpdateRequest(BaseModel):
    configurations: List[SystemConfigBulkUpdateItem] = Field(
        ...,
        description="List of configuration updates"
    )


class SystemConfigCategoryResponse(BaseModel):
    category: str
    label: str
    description: str
    icon: str
    configurations: List[SystemConfigResponse]


class SystemConfigSchemaResponse(BaseModel):
    categories: Dict[str, Dict[str, Any]]
    field_types: Dict[str, Any]


class SystemConfigExportResponse(BaseModel):
    export_date: datetime
    configurations: Dict[str, Any]
    metadata: Dict[str, Any]


class SystemConfigValidationResponse(BaseModel):
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []
