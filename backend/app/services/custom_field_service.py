from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Dict, Any, List, Optional
from ..models.custom_field import CustomField, CustomFieldValue, EntityType
from ..schemas.custom_field import CustomFieldWithValue


class CustomFieldService:
    """Service class for handling custom field operations"""

    @staticmethod
    def get_entity_custom_fields_dict(
        db: Session,
        entity_id: str,
        entity_type: EntityType
    ) -> Dict[str, Any]:
        """Get custom field values as a dictionary for an entity"""

        # Get all active custom fields for this entity type
        custom_fields = db.query(CustomField).filter(
            and_(
                CustomField.entity_type == entity_type,
                CustomField.is_active == True
            )
        ).all()

        # Get current values for this entity
        field_values = db.query(CustomFieldValue).filter(
            and_(
                CustomFieldValue.entity_id == entity_id,
                CustomFieldValue.entity_type == entity_type
            )
        ).all()

        # Create a mapping of field_key to value
        value_map = {
            fv.custom_field.field_key: fv.value for fv in field_values if fv.custom_field}

        # Create result dictionary with field_key as keys
        result = {}
        for field in custom_fields:
            result[field.field_key] = {
                'value': value_map.get(field.field_key),
                'field_name': field.name,
                'field_type': field.field_type.value,
                'is_required': field.is_required,
                'field_config': field.field_config
            }

        return result

    @staticmethod
    def format_field_value_for_display(field_type: str, value: str, field_config: Dict = None) -> Any:
        """Format field value for display based on field type"""
        if not value:
            return None

        field_config = field_config or {}

        try:
            if field_type == 'number':
                return float(value)
            elif field_type == 'currency':
                prefix = field_config.get('prefix', '$')
                return f"{prefix}{float(value):,.2f}"
            elif field_type == 'percentage':
                return f"{float(value)}%"
            elif field_type == 'boolean':
                return value.lower() in ('true', '1', 'yes')
            elif field_type in ['select', 'multi_select']:
                if field_type == 'multi_select':
                    return value.split(',')
                return value
            else:
                return value
        except:
            return value

    @staticmethod
    def validate_required_fields(
        db: Session,
        entity_type: EntityType,
        field_values: Dict[str, Any]
    ) -> List[str]:
        """Validate that all required custom fields have values"""

        errors = []

        # Get all required custom fields for this entity type
        required_fields = db.query(CustomField).filter(
            and_(
                CustomField.entity_type == entity_type,
                CustomField.is_required == True,
                CustomField.is_active == True
            )
        ).all()

        for field in required_fields:
            if field.field_key not in field_values or not field_values[field.field_key]:
                errors.append(f"Required field '{field.name}' is missing")

        return errors

    @staticmethod
    def save_custom_field_values(
        db: Session,
        entity_id: str,
        entity_type: EntityType,
        field_values: Dict[str, Any]
    ) -> bool:
        """Save custom field values for an entity"""

        try:
            for field_key, value in field_values.items():
                # Get the custom field
                custom_field = db.query(CustomField).filter(
                    and_(
                        CustomField.field_key == field_key,
                        CustomField.entity_type == entity_type
                    )
                ).first()

                if not custom_field:
                    print(f"WARNING: Custom field '{field_key}' not found, skipping")
                    continue

                # Check if value already exists
                existing_value = db.query(CustomFieldValue).filter(
                    and_(
                        CustomFieldValue.custom_field_id == custom_field.id,
                        CustomFieldValue.entity_id == entity_id
                    )
                ).first()

                if existing_value:
                    # Update existing value
                    existing_value.value = str(
                        value) if value is not None else None
                else:
                    # Create new value
                    field_value = CustomFieldValue(
                        custom_field_id=custom_field.id,
                        entity_id=entity_id,
                        entity_type=entity_type,
                        value=str(value) if value is not None else None
                    )
                    db.add(field_value)

            # Flush to DB (but don't commit - let caller handle commit)
            db.flush()
            return True
        except Exception as e:
            print(f"ERROR saving custom field values: {e}")
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def delete_custom_field_values(
        db: Session,
        entity_id: str,
        entity_type: EntityType
    ) -> int:
        """Delete all custom field values for an entity"""

        deleted_count = db.query(CustomFieldValue).filter(
            and_(
                CustomFieldValue.entity_id == entity_id,
                CustomFieldValue.entity_type == entity_type
            )
        ).delete()

        return deleted_count

    @staticmethod
    def get_custom_fields_for_form(
        db: Session,
        entity_type: EntityType,
        placement: str = "form"
    ) -> List[CustomField]:
        """Get custom fields that should be displayed in forms"""

        return db.query(CustomField).filter(
            and_(
                CustomField.entity_type == entity_type,
                CustomField.is_active == True,
                CustomField.placement.in_([placement, "both"])
            )
        ).order_by(CustomField.order_index, CustomField.created_at).all()
