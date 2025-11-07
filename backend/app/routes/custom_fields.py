from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any
import re
import uuid
from ..core.database import get_db
from ..core.auth import get_current_user, require_admin, require_manager_or_admin
from ..models.user import UserProfile
from ..models.custom_field import CustomField, CustomFieldValue, FieldType, EntityType, PlacementType
from ..schemas.custom_field import (
    CustomFieldCreate, CustomFieldUpdate, CustomFieldResponse,
    CustomFieldValueCreate, CustomFieldValueUpdate, CustomFieldValueResponse,
    BulkCustomFieldValuesUpdate, CustomFieldWithValue, EntityWithCustomFields,
    FieldTypeEnum, EntityTypeEnum
)

router = APIRouter()


def generate_field_key(name: str) -> str:
    """Generate a unique field key from field name"""
    # Remove special characters and convert to lowercase
    key = re.sub(r'[^a-zA-Z0-9\s]', '', name)
    key = re.sub(r'\s+', '_', key.strip()).lower()
    # Add prefix to avoid conflicts
    return f"custom_{key}"


def validate_field_value(field_type: FieldType, value: str, field_config: Dict[str, Any] = None) -> bool:
    """Validate field value based on field type and configuration"""
    if not value:
        return True  # Empty values are handled by required validation

    # Safely handle None field_config
    if field_config is None:
        field_config = {}

    try:
        if field_type == FieldType.NUMBER:
            num_val = float(value)
            min_val = field_config.get('min_value')
            max_val = field_config.get('max_value')
            if min_val is not None and num_val < min_val:
                return False
            if max_val is not None and num_val > max_val:
                return False

        elif field_type == FieldType.EMAIL:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, value):
                return False

        elif field_type == FieldType.URL:
            import re
            url_pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
            if not re.match(url_pattern, value):
                return False

        elif field_type in [FieldType.SELECT, FieldType.MULTI_SELECT]:
            options_list = field_config.get('options', [])
            if not isinstance(options_list, list):
                return True  # Skip validation if options not properly configured
            options = [opt.get('value') if isinstance(opt, dict) else opt for opt in options_list]
            if field_type == FieldType.MULTI_SELECT:
                values = value.split(',')
                for val in values:
                    if val.strip() not in options:
                        return False
            else:
                if value not in options:
                    return False

        elif field_type == FieldType.BOOLEAN:
            if value.lower() not in ('true', 'false', '1', '0', 'yes', 'no'):
                return False

        return True
    except Exception as e:
        print(f"Validation error: {e}")
        return False

# Custom Field Management Routes


@router.post("/", response_model=CustomFieldResponse)
async def create_custom_field(
    field_data: CustomFieldCreate,
    db: Session = Depends(get_db)
    # current_user: UserProfile = Depends(require_manager_or_admin)  # Temporarily disabled for testing
):
    """Create a new custom field"""

    try:
        # Generate unique field key
        base_key = generate_field_key(field_data.name)
        field_key = base_key
        counter = 1

        while db.query(CustomField).filter(CustomField.field_key == field_key).first():
            field_key = f"{base_key}_{counter}"
            counter += 1

        # Create custom field
        custom_field = CustomField(
            name=field_data.name,
            description=field_data.description,
            field_type=field_data.field_type,
            entity_type=field_data.entity_type,
            is_required=field_data.is_required,
            is_active=field_data.is_active,
            placement=field_data.placement,
            field_config=field_data.field_config,
            order_index=field_data.order_index,
            help_text=field_data.help_text,
            placeholder=field_data.placeholder,
            field_key=field_key,
            created_by=None  # Temporarily disabled for testing
        )

        db.add(custom_field)
        db.commit()
        db.refresh(custom_field)
        return custom_field

    except Exception as e:
        db.rollback()
        import traceback
        error_detail = f"Error creating custom field: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(error_detail)  # This will show in server logs
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[CustomFieldResponse])
async def get_custom_fields(
    entity_type: Optional[EntityTypeEnum] = Query(None),
    is_active: Optional[bool] = Query(True),
    placement: Optional[str] = Query(None),
    db: Session = Depends(get_db)
    # current_user: UserProfile = Depends(get_current_user)  # Temporarily disabled for testing
):
    """Get all custom fields with optional filtering"""

    query = db.query(CustomField)

    if entity_type:
        query = query.filter(CustomField.entity_type == entity_type)

    if is_active is not None:
        query = query.filter(CustomField.is_active == is_active)

    if placement:
        query = query.filter(
            or_(
                CustomField.placement == placement,
                CustomField.placement == PlacementType.BOTH
            )
        )

    # Order by order_index, then by creation date
    query = query.order_by(CustomField.order_index, CustomField.created_at)

    return query.all()


@router.get("/{field_id}", response_model=CustomFieldResponse)
async def get_custom_field(
    field_id: str,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get a specific custom field"""

    custom_field = db.query(CustomField).filter(
        CustomField.id == field_id).first()
    if not custom_field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom field not found"
        )

    return custom_field


@router.put("/{field_id}", response_model=CustomFieldResponse)
async def update_custom_field(
    field_id: str,
    field_update: CustomFieldUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_manager_or_admin)
):
    """Update a custom field"""

    custom_field = db.query(CustomField).filter(
        CustomField.id == field_id).first()
    if not custom_field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom field not found"
        )

    # Update only provided fields
    update_data = field_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(custom_field, field, value)

    db.commit()
    db.refresh(custom_field)

    return custom_field


@router.delete("/{field_id}")
async def delete_custom_field(
    field_id: str,
    db: Session = Depends(get_db)
    # current_user: UserProfile = Depends(require_admin)  # Temporarily disabled for testing
):
    """Delete a custom field and all its values"""

    custom_field = db.query(CustomField).filter(
        CustomField.id == field_id).first()
    if not custom_field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom field not found"
        )

    db.delete(custom_field)
    db.commit()

    return {"message": "Custom field deleted successfully"}

# Custom Field Values Routes


@router.post("/values/", response_model=CustomFieldValueResponse)
async def create_field_value(
    value_data: CustomFieldValueCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Create or update a custom field value"""

    # Get the custom field
    custom_field = db.query(CustomField).filter(
        CustomField.id == value_data.custom_field_id).first()
    if not custom_field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom field not found"
        )

    # Validate field value
    if value_data.value and not validate_field_value(
        custom_field.field_type,
        value_data.value,
        custom_field.field_config
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid field value"
        )

    # Check if value already exists
    existing_value = db.query(CustomFieldValue).filter(
        and_(
            CustomFieldValue.custom_field_id == value_data.custom_field_id,
            CustomFieldValue.entity_id == value_data.entity_id
        )
    ).first()

    if existing_value:
        # Update existing value
        existing_value.value = value_data.value
        db.commit()
        db.refresh(existing_value)
        return existing_value
    else:
        # Create new value
        field_value = CustomFieldValue(**value_data.model_dump())
        db.add(field_value)
        db.commit()
        db.refresh(field_value)
        return field_value


@router.get("/values/{entity_type}/{entity_id}", response_model=List[CustomFieldWithValue])
async def get_entity_custom_fields(
    entity_type: EntityTypeEnum,
    entity_id: str,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Get all custom fields for an entity with their current values"""

    # Get all active custom fields for this entity type
    custom_fields = db.query(CustomField).filter(
        and_(
            CustomField.entity_type == entity_type,
            CustomField.is_active == True
        )
    ).order_by(CustomField.order_index, CustomField.created_at).all()

    # Get current values for this entity
    field_values = db.query(CustomFieldValue).filter(
        and_(
            CustomFieldValue.entity_id == entity_id,
            CustomFieldValue.entity_type == entity_type
        )
    ).all()

    # Create a mapping of field_id to value
    value_map = {fv.custom_field_id: fv.value for fv in field_values}

    # Combine fields with their values
    result = []
    for field in custom_fields:
        field_with_value = CustomFieldWithValue(
            **field.__dict__,
            current_value=value_map.get(str(field.id))
        )
        result.append(field_with_value)

    return result


@router.put("/values/bulk", response_model=Dict[str, str])
async def bulk_update_field_values(
    bulk_data: BulkCustomFieldValuesUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Bulk update custom field values for an entity"""

    errors = []
    updated_count = 0

    for field_key, value in bulk_data.field_values.items():
        try:
            # Get the custom field by key
            custom_field = db.query(CustomField).filter(
                and_(
                    CustomField.field_key == field_key,
                    CustomField.entity_type == bulk_data.entity_type
                )
            ).first()

            if not custom_field:
                errors.append(f"Field '{field_key}' not found")
                continue

            # Validate required fields
            if custom_field.is_required and not value:
                errors.append(f"Field '{field_key}' is required")
                continue

            # Validate field value
            if value and not validate_field_value(
                custom_field.field_type, str(value), custom_field.field_config
            ):
                errors.append(f"Invalid value for field '{field_key}'")
                continue

            # Create or update field value
            existing_value = db.query(CustomFieldValue).filter(
                and_(
                    CustomFieldValue.custom_field_id == custom_field.id,
                    CustomFieldValue.entity_id == bulk_data.entity_id
                )
            ).first()

            if existing_value:
                existing_value.value = str(
                    value) if value is not None else None
            else:
                field_value = CustomFieldValue(
                    custom_field_id=custom_field.id,
                    entity_id=bulk_data.entity_id,
                    entity_type=bulk_data.entity_type,
                    value=str(value) if value is not None else None
                )
                db.add(field_value)

            updated_count += 1

        except Exception as e:
            errors.append(f"Error updating field '{field_key}': {str(e)}")

    db.commit()

    result = {
        "message": f"Updated {updated_count} fields successfully",
        "updated_count": str(updated_count)
    }

    if errors:
        result["errors"] = errors

    return result


@router.delete("/values/{entity_type}/{entity_id}")
async def delete_entity_field_values(
    entity_type: EntityTypeEnum,
    entity_id: str,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user)
):
    """Delete all custom field values for an entity"""

    deleted_count = db.query(CustomFieldValue).filter(
        and_(
            CustomFieldValue.entity_id == entity_id,
            CustomFieldValue.entity_type == entity_type
        )
    ).delete()

    db.commit()

    return {"message": f"Deleted {deleted_count} field values"}

# Utility routes
# Temporary routes without authentication for testing


@router.post("/test")
async def create_custom_field_test(
    field_data: CustomFieldCreate,
    db: Session = Depends(get_db)
):
    """Create a new custom field (test - no auth)"""

    # Generate unique field key
    base_key = generate_field_key(field_data.name)
    field_key = base_key
    counter = 1

    while db.query(CustomField).filter(CustomField.field_key == field_key).first():
        field_key = f"{base_key}_{counter}"
        counter += 1

    # Create custom field without user requirement
    custom_field = CustomField(
        **field_data.model_dump(),
        field_key=field_key,
        created_by=None  # Temporary - no auth
    )

    db.add(custom_field)
    db.commit()
    db.refresh(custom_field)

    return custom_field


@router.get("/test", response_model=List[CustomFieldResponse])
async def get_custom_fields_test(
    entity_type: Optional[EntityTypeEnum] = Query(None),
    is_active: Optional[bool] = Query(True),
    placement: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all custom fields (test - no auth)"""

    query = db.query(CustomField)

    if entity_type:
        query = query.filter(CustomField.entity_type == entity_type)

    if is_active is not None:
        query = query.filter(CustomField.is_active == is_active)

    if placement:
        query = query.filter(
            or_(
                CustomField.placement == placement,
                CustomField.placement == PlacementType.BOTH
            )
        )

    # Order by order_index, then by creation date
    query = query.order_by(CustomField.order_index, CustomField.created_at)

    return query.all()


@router.get("/types/field-types")
async def get_field_types():
    """Get all available field types"""
    return {
        "field_types": [
            {"value": ft.value, "label": ft.value.replace('_', ' ').title()}
            for ft in FieldTypeEnum
        ]
    }


@router.get("/types/entity-types")
async def get_entity_types():
    """Get all available entity types"""
    return {
        "entity_types": [
            {"value": et.value, "label": et.value.title()}
            for et in EntityTypeEnum
        ]
    }
