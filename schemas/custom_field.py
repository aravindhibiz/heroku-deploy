from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

# Enums for field types


class FieldTypeEnum(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    TEXTAREA = "textarea"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"


class EntityTypeEnum(str, Enum):
    CONTACT = "contact"
    COMPANY = "company"
    DEAL = "deal"
    ACTIVITY = "activity"
    TASK = "task"


class PlacementTypeEnum(str, Enum):
    FORM = "form"
    DETAIL_VIEW = "detail_view"
    LIST_VIEW = "list_view"
    BOTH = "both"

# Base schemas


class CustomFieldBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    field_type: FieldTypeEnum
    entity_type: EntityTypeEnum
    is_required: bool = False
    is_active: bool = True
    placement: PlacementTypeEnum = PlacementTypeEnum.BOTH
    field_config: Optional[Dict[str, Any]] = None
    order_index: str = "0"
    help_text: Optional[str] = None
    placeholder: Optional[str] = None

    @validator('field_config')
    def validate_field_config(cls, v, values):
        """Validate field configuration based on field type"""
        if not v:
            return v

        field_type = values.get('field_type')

        if field_type in [FieldTypeEnum.SELECT, FieldTypeEnum.MULTI_SELECT]:
            if not v.get('options'):
                raise ValueError(
                    'Select fields must have options in field_config')
            if not isinstance(v['options'], list):
                raise ValueError('Options must be a list')

        if field_type == FieldTypeEnum.NUMBER:
            if 'min_value' in v and 'max_value' in v:
                if v['min_value'] >= v['max_value']:
                    raise ValueError('min_value must be less than max_value')

        return v


class CustomFieldCreate(CustomFieldBase):
    pass


class CustomFieldUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_required: Optional[bool] = None
    is_active: Optional[bool] = None
    placement: Optional[PlacementTypeEnum] = None
    field_config: Optional[Dict[str, Any]] = None
    order_index: Optional[str] = None
    help_text: Optional[str] = None
    placeholder: Optional[str] = None


class CustomFieldResponse(CustomFieldBase):
    id: str
    field_key: str
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @validator('id', 'created_by', pre=True)
    def convert_uuid_to_string(cls, v):
        if v is None:
            return None
        return str(v)

# Custom field value schemas


class CustomFieldValueBase(BaseModel):
    custom_field_id: str
    entity_id: str
    entity_type: EntityTypeEnum
    value: Optional[str] = None


class CustomFieldValueCreate(CustomFieldValueBase):
    pass


class CustomFieldValueUpdate(BaseModel):
    value: Optional[str] = None


class CustomFieldValueResponse(CustomFieldValueBase):
    id: str
    created_at: datetime
    updated_at: datetime
    custom_field: Optional[CustomFieldResponse] = None

    class Config:
        from_attributes = True

# Bulk operations


class BulkCustomFieldValuesUpdate(BaseModel):
    entity_id: str
    entity_type: EntityTypeEnum
    field_values: List[Dict[str, Any]]  # {field_key: value}


class CustomFieldWithValue(CustomFieldResponse):
    current_value: Optional[str] = None

# Entity with custom fields


class EntityWithCustomFields(BaseModel):
    entity_id: str
    entity_type: EntityTypeEnum
    custom_fields: List[CustomFieldWithValue]

# Field configuration schemas for different field types


class SelectFieldConfig(BaseModel):
    # [{"value": "option1", "label": "Option 1"}]
    options: List[Dict[str, str]]
    allow_multiple: bool = False


class NumberFieldConfig(BaseModel):
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    decimal_places: Optional[int] = 2
    prefix: Optional[str] = None  # For currency fields
    suffix: Optional[str] = None  # For percentage fields


class TextFieldConfig(BaseModel):
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None  # Regex pattern
    format: Optional[str] = None  # email, phone, url, etc.


class DateFieldConfig(BaseModel):
    min_date: Optional[str] = None
    max_date: Optional[str] = None
    default_to_today: bool = False


# Export all schemas
__all__ = [
    'FieldTypeEnum', 'EntityTypeEnum', 'PlacementTypeEnum',
    'CustomFieldBase', 'CustomFieldCreate', 'CustomFieldUpdate', 'CustomFieldResponse',
    'CustomFieldValueBase', 'CustomFieldValueCreate', 'CustomFieldValueUpdate', 'CustomFieldValueResponse',
    'BulkCustomFieldValuesUpdate', 'CustomFieldWithValue', 'EntityWithCustomFields',
    'SelectFieldConfig', 'NumberFieldConfig', 'TextFieldConfig', 'DateFieldConfig'
]
