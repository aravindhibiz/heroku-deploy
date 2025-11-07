"""
Custom Fields Routes

This module defines API endpoints for custom field management.
Provides a clean, well-documented REST API for field and value operations.

Endpoints:
Field Management:
- GET /custom-fields - List all custom fields
- GET /custom-fields/{field_id} - Get a custom field
- POST /custom-fields - Create a custom field
- PUT /custom-fields/{field_id} - Update a custom field
- DELETE /custom-fields/{field_id} - Delete a custom field

Field Value Operations:
- GET /custom-fields/values/{entity_type}/{entity_id} - Get entity field values
- POST /custom-fields/values - Create/update field value
- PUT /custom-fields/values/bulk - Bulk update field values
- DELETE /custom-fields/values/{entity_type}/{entity_id} - Delete entity values

Utility Endpoints:
- GET /custom-fields/types/field-types - Get available field types
- GET /custom-fields/types/entity-types - Get available entity types
- GET /custom-fields/stats - Get field statistics

Author: CRM System
Date: 2024
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.auth import get_current_user, require_manager_or_admin
from ..models.user import UserProfile
from ..controllers.custom_field_controller import CustomFieldController
from ..schemas.custom_field import (
    CustomFieldCreate,
    CustomFieldUpdate,
    CustomFieldResponse,
    CustomFieldValueCreate,
    CustomFieldValueResponse,
    CustomFieldWithValue,
    BulkCustomFieldValuesUpdate,
    FieldTypeEnum,
    EntityTypeEnum
)

router = APIRouter(prefix="/custom-fields", tags=["Custom Fields"])


# ==================== Custom Field Management ====================

@router.get(
    "",
    response_model=List[CustomFieldResponse],
    summary="List all custom fields",
    description="""
    Retrieve all custom fields with optional filtering.
    
    **Parameters:**
    - entity_type: Filter by entity type (contact, company, deal, activity, task)
    - is_active: Filter by active status (default: true)
    - placement: Filter by placement (form, detail_view, list_view, both)
    
    **Returns:** List of custom fields ordered by order_index and creation date
    
    **Authentication Required**
    """,
    status_code=status.HTTP_200_OK
)
async def get_custom_fields(
    entity_type: Optional[EntityTypeEnum] = Query(
        None, description="Filter by entity type"),
    is_active: Optional[bool] = Query(
        True, description="Filter by active status"),
    placement: Optional[str] = Query(None, description="Filter by placement"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """List all custom fields with optional filtering."""
    controller = CustomFieldController(db)
    return controller.list_custom_fields(
        entity_type=entity_type,
        is_active=is_active,
        placement=placement
    )


@router.get(
    "/{field_id}",
    response_model=CustomFieldResponse,
    summary="Get a custom field",
    description="""
    Retrieve a specific custom field by ID.
    
    **Parameters:**
    - field_id: UUID of the custom field
    
    **Returns:** Custom field details
    
    **Authentication Required**
    """,
    status_code=status.HTTP_200_OK
)
async def get_custom_field(
    field_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get a specific custom field."""
    controller = CustomFieldController(db)
    return controller.get_custom_field(field_id)


@router.post(
    "",
    response_model=CustomFieldResponse,
    summary="Create a custom field",
    description="""
    Create a new custom field.
    
    **Request Body:** Custom field data including:
    - name: Field display name (required)
    - field_type: Type of field (text, number, select, etc.)
    - entity_type: Entity this field applies to
    - field_config: Type-specific configuration (e.g., options for select fields)
    
    **Validation:**
    - Field key is auto-generated from name
    - Select fields must have options in field_config
    - Number fields validate min/max values
    
    **Returns:** The created custom field with generated field_key
    
    **Manager/Admin Access Required**
    """,
    status_code=status.HTTP_201_CREATED
)
async def create_custom_field(
    field_data: CustomFieldCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_manager_or_admin())
):
    """Create a new custom field."""
    controller = CustomFieldController(db)
    return controller.create_custom_field(
        field_data=field_data,
        created_by=current_user.id
    )


@router.put(
    "/{field_id}",
    response_model=CustomFieldResponse,
    summary="Update a custom field",
    description="""
    Update an existing custom field.
    
    **Parameters:**
    - field_id: UUID of the custom field to update
    
    **Request Body:** Updated field data (partial updates supported)
    
    **Note:** field_type and entity_type cannot be changed after creation
    
    **Returns:** The updated custom field
    
    **Manager/Admin Access Required**
    """,
    status_code=status.HTTP_200_OK
)
async def update_custom_field(
    field_id: UUID,
    field_data: CustomFieldUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_manager_or_admin())
):
    """Update an existing custom field."""
    controller = CustomFieldController(db)
    return controller.update_custom_field(field_id, field_data)


@router.delete(
    "/{field_id}",
    response_model=Dict[str, str],
    summary="Delete a custom field",
    description="""
    Delete a custom field and all its values.
    
    **Parameters:**
    - field_id: UUID of the custom field to delete
    
    **Warning:** This will delete all custom field values associated with this field
    across all entities. This action cannot be undone.
    
    **Returns:** Success message
    
    **Manager/Admin Access Required**
    """,
    status_code=status.HTTP_200_OK
)
async def delete_custom_field(
    field_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_manager_or_admin())
):
    """Delete a custom field and all its values."""
    controller = CustomFieldController(db)
    return controller.delete_custom_field(field_id)


# ==================== Custom Field Value Operations ====================

@router.get(
    "/values/{entity_type}/{entity_id}",
    response_model=List[CustomFieldWithValue],
    summary="Get entity custom field values",
    description="""
    Get all custom fields for an entity with their current values.
    
    **Parameters:**
    - entity_type: Type of entity (contact, company, deal, activity, task)
    - entity_id: UUID of the entity
    
    **Returns:** List of custom fields with their current values for the entity
    
    Includes both fields with values and fields without values (current_value will be null).
    Useful for rendering forms and detail views.
    
    **Authentication Required**
    """,
    status_code=status.HTTP_200_OK
)
async def get_entity_custom_fields(
    entity_type: EntityTypeEnum,
    entity_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get all custom fields for an entity with their current values."""
    controller = CustomFieldController(db)
    return controller.get_entity_custom_fields(entity_type, entity_id)


@router.post(
    "/values",
    response_model=CustomFieldValueResponse,
    summary="Create or update field value",
    description="""
    Create or update a custom field value for an entity.
    
    **Request Body:**
    - custom_field_id: UUID of the custom field
    - entity_id: UUID of the entity
    - entity_type: Type of entity
    - value: The field value (as string)
    
    **Validation:**
    - Value is validated based on field type (email, number, select, etc.)
    - Select fields validate against configured options
    - Number fields validate against min/max values
    
    **Returns:** The created or updated field value
    
    **Authentication Required**
    """,
    status_code=status.HTTP_200_OK
)
async def create_or_update_field_value(
    value_data: CustomFieldValueCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Create or update a custom field value."""
    controller = CustomFieldController(db)
    return controller.create_or_update_field_value(value_data)


@router.put(
    "/values/bulk",
    response_model=Dict[str, Any],
    summary="Bulk update field values",
    description="""
    Update multiple custom field values for an entity in a single request.
    
    **Request Body:**
    - entity_id: UUID of the entity
    - entity_type: Type of entity
    - field_values: List of {field_key: value} pairs
    
    **Features:**
    - Validates all field values before updating
    - Creates or updates values as needed
    - Returns detailed results with any errors
    
    **Example Request:**
    ```json
    {
        "entity_id": "123e4567-e89b-12d3-a456-426614174000",
        "entity_type": "contact",
        "field_values": [
            {"custom_industry": "Technology"},
            {"custom_employee_count": "50"},
            {"custom_is_partner": "true"}
        ]
    }
    ```
    
    **Returns:** Success status, updated count, and any errors
    
    **Authentication Required**
    """,
    status_code=status.HTTP_200_OK
)
async def bulk_update_field_values(
    bulk_data: BulkCustomFieldValuesUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Bulk update custom field values for an entity."""
    controller = CustomFieldController(db)
    return controller.bulk_update_field_values(bulk_data)


@router.delete(
    "/values/{entity_type}/{entity_id}",
    response_model=Dict[str, str],
    summary="Delete entity field values",
    description="""
    Delete all custom field values for an entity.
    
    **Parameters:**
    - entity_type: Type of entity
    - entity_id: UUID of the entity
    
    **Warning:** This will delete all custom field values for this entity.
    This action cannot be undone.
    
    **Returns:** Success message with deleted count
    
    **Authentication Required**
    """,
    status_code=status.HTTP_200_OK
)
async def delete_entity_field_values(
    entity_type: EntityTypeEnum,
    entity_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Delete all custom field values for an entity."""
    controller = CustomFieldController(db)
    return controller.delete_entity_field_values(entity_type, entity_id)


# ==================== Utility Endpoints ====================

@router.get(
    "/types/field-types",
    response_model=Dict[str, List[Dict[str, str]]],
    summary="Get available field types",
    description="""
    Get all available custom field types.
    
    **Returns:** List of field types with values and labels
    
    Available types:
    - text, number, select, multi_select
    - date, datetime, boolean
    - email, phone, url
    - textarea, currency, percentage
    
    **Authentication Required**
    """,
    status_code=status.HTTP_200_OK
)
async def get_field_types(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get all available field types."""
    controller = CustomFieldController(db)
    return controller.get_field_types()


@router.get(
    "/types/entity-types",
    response_model=Dict[str, List[Dict[str, str]]],
    summary="Get available entity types",
    description="""
    Get all available entity types that can have custom fields.
    
    **Returns:** List of entity types with values and labels
    
    Available types:
    - contact, company, deal, activity, task
    
    **Authentication Required**
    """,
    status_code=status.HTTP_200_OK
)
async def get_entity_types(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get all available entity types."""
    controller = CustomFieldController(db)
    return controller.get_entity_types()


@router.get(
    "/stats",
    response_model=Dict[str, Any],
    summary="Get field statistics",
    description="""
    Get statistics about custom fields.
    
    **Parameters:**
    - entity_type: Optional filter by entity type
    
    **Returns:** Field counts by entity type
    
    Useful for dashboards and monitoring custom field usage.
    
    **Authentication Required**
    """,
    status_code=status.HTTP_200_OK
)
async def get_field_statistics(
    entity_type: Optional[EntityTypeEnum] = Query(
        None, description="Filter by entity type"),
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get statistics about custom fields."""
    controller = CustomFieldController(db)
    return controller.get_field_statistics(entity_type)
