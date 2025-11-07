"""
Custom Fields Service Layer

This module provides business logic for custom field management.
Handles validation, field key generation, value formatting, and business rules.

Key Features:
- Field key generation with uniqueness
- Field value validation (type-specific)
- Required field validation
- Value formatting for display
- Bulk operations with validation
- Field configuration validation

Author: CRM System
Date: 2024
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
import re
from sqlalchemy.orm import Session

from ..models.custom_field import CustomField, CustomFieldValue, FieldType, EntityType, PlacementType
from ..repositories.custom_field_repository import CustomFieldRepository


class CustomFieldService:
    """
    Service class for custom field business logic.

    This class handles all custom field management operations, including
    validation, key generation, formatting, and business rules.

    Responsibilities:
    - Generate unique field keys
    - Validate field values based on type
    - Validate required fields
    - Format values for display
    - Handle bulk operations
    - Manage field configurations
    """

    def __init__(self, db: Session):
        """
        Initialize the CustomFieldService.

        Args:
            db (Session): SQLAlchemy database session
        """
        self.db = db
        self.repository = CustomFieldRepository(db)

    def generate_unique_field_key(self, name: str) -> str:
        """
        Generate a unique field key from field name.

        Args:
            name (str): The field name

        Returns:
            str: Unique field key
        """
        # Remove special characters and convert to lowercase
        key = re.sub(r'[^a-zA-Z0-9\s]', '', name)
        key = re.sub(r'\s+', '_', key.strip()).lower()
        base_key = f"custom_{key}"

        # Ensure uniqueness
        field_key = base_key
        counter = 1

        while self.repository.field_key_exists(field_key):
            field_key = f"{base_key}_{counter}"
            counter += 1

        return field_key

    def validate_field_value(
        self,
        field_type: FieldType,
        value: Any,
        field_config: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate a field value based on its type and configuration.

        Args:
            field_type (FieldType): The field type
            value (Any): The value to validate
            field_config (Optional[Dict[str, Any]]): Field configuration

        Returns:
            tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        if value is None or value == '':
            # Empty values are OK (required check is separate)
            return True, None

        value_str = str(value)
        field_config = field_config or {}

        try:
            # Number validation
            if field_type == FieldType.NUMBER:
                try:
                    num_val = float(value_str)
                    min_val = field_config.get('min_value')
                    max_val = field_config.get('max_value')

                    if min_val is not None and num_val < min_val:
                        return False, f"Value must be at least {min_val}"
                    if max_val is not None and num_val > max_val:
                        return False, f"Value must be at most {max_val}"
                except ValueError:
                    return False, "Invalid number format"

            # Email validation
            elif field_type == FieldType.EMAIL:
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, value_str):
                    return False, "Invalid email format"

            # URL validation
            elif field_type == FieldType.URL:
                url_pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
                if not re.match(url_pattern, value_str):
                    return False, "Invalid URL format"

            # Phone validation (basic)
            elif field_type == FieldType.PHONE:
                phone_pattern = r'^[\d\s\-\+\(\)]+$'
                if not re.match(phone_pattern, value_str):
                    return False, "Invalid phone number format"

            # Select validation
            elif field_type in [FieldType.SELECT, FieldType.MULTI_SELECT]:
                options_list = field_config.get('options', [])
                if not isinstance(options_list, list):
                    return True, None  # Skip if options not configured

                # Extract option values
                options = []
                for opt in options_list:
                    if isinstance(opt, dict):
                        options.append(opt.get('value'))
                    else:
                        options.append(str(opt))

                if field_type == FieldType.MULTI_SELECT:
                    values = [v.strip() for v in value_str.split(',')]
                    invalid = [v for v in values if v not in options]
                    if invalid:
                        return False, f"Invalid options: {', '.join(invalid)}"
                else:
                    if value_str not in options:
                        return False, f"Invalid option: {value_str}"

            # Boolean validation
            elif field_type == FieldType.BOOLEAN:
                valid_values = ('true', 'false', '1', '0', 'yes', 'no')
                if value_str.lower() not in valid_values:
                    return False, "Invalid boolean value"

            # Currency/Percentage validation (numeric)
            elif field_type in [FieldType.CURRENCY, FieldType.PERCENTAGE]:
                try:
                    float(value_str)
                except ValueError:
                    return False, f"Invalid {field_type.value} format"

            # Date validation (basic ISO format check)
            elif field_type in [FieldType.DATE, FieldType.DATETIME]:
                # Basic check - could be enhanced with actual datetime parsing
                if not re.match(r'^\d{4}-\d{2}-\d{2}', value_str):
                    return False, f"Invalid {field_type.value} format (expected YYYY-MM-DD)"

            return True, None

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def validate_required_fields(
        self,
        entity_type: EntityType,
        field_values: Dict[str, Any]
    ) -> List[str]:
        """
        Validate that all required custom fields have values.

        Args:
            entity_type (EntityType): The entity type
            field_values (Dict[str, Any]): Dictionary of field_key -> value

        Returns:
            List[str]: List of validation errors
        """
        errors = []

        # Get all required fields for this entity type
        required_fields = self.repository.get_required_fields(entity_type)

        for field in required_fields:
            value = field_values.get(field.field_key)
            if value is None or str(value).strip() == '':
                errors.append(f"Required field '{field.name}' is missing")

        return errors

    def format_value_for_display(
        self,
        field_type: FieldType,
        value: Any,
        field_config: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Format field value for display based on field type.

        Args:
            field_type (FieldType): The field type
            value (Any): The value to format
            field_config (Optional[Dict[str, Any]]): Field configuration

        Returns:
            Any: Formatted value
        """
        if value is None or value == '':
            return None

        value_str = str(value)
        field_config = field_config or {}

        try:
            if field_type == FieldType.NUMBER:
                return float(value_str)

            elif field_type == FieldType.CURRENCY:
                prefix = field_config.get('prefix', '$')
                try:
                    num = float(value_str)
                    return f"{prefix}{num:,.2f}"
                except ValueError:
                    return value_str

            elif field_type == FieldType.PERCENTAGE:
                try:
                    num = float(value_str)
                    return f"{num}%"
                except ValueError:
                    return value_str

            elif field_type == FieldType.BOOLEAN:
                return value_str.lower() in ('true', '1', 'yes')

            elif field_type == FieldType.MULTI_SELECT:
                return [v.strip() for v in value_str.split(',')]

            else:
                return value_str

        except Exception:
            return value_str

    def get_entity_custom_fields_dict(
        self,
        entity_id: UUID,
        entity_type: EntityType
    ) -> Dict[str, Any]:
        """
        Get custom field values as a dictionary for an entity.

        Args:
            entity_id (UUID): The entity ID
            entity_type (EntityType): The entity type

        Returns:
            Dict[str, Any]: Dictionary with field_key as keys
        """
        # Get all active custom fields for this entity type
        custom_fields = self.repository.get_by_entity_type(
            entity_type, is_active=True)

        # Get current values for this entity
        field_values = self.repository.get_entity_values_with_fields(
            entity_id, entity_type)

        # Create a mapping of field_id to value
        value_map = {
            str(fv.custom_field_id): fv.value
            for fv in field_values
            if fv.custom_field
        }

        # Create result dictionary
        result = {}
        for field in custom_fields:
            field_id_str = str(field.id)
            raw_value = value_map.get(field_id_str)

            result[field.field_key] = {
                'value': raw_value,
                'formatted_value': self.format_value_for_display(
                    field.field_type, raw_value, field.field_config
                ),
                'field_name': field.name,
                'field_type': field.field_type.value,
                'is_required': field.is_required,
                'field_config': field.field_config
            }

        return result

    def save_custom_field_values(
        self,
        entity_id: UUID,
        entity_type: EntityType,
        field_values: Dict[str, Any],
        validate_required: bool = True
    ) -> tuple[bool, List[str]]:
        """
        Save custom field values for an entity with validation.

        Args:
            entity_id (UUID): The entity ID
            entity_type (EntityType): The entity type
            field_values (Dict[str, Any]): Dictionary of field_key -> value
            validate_required (bool): Whether to validate required fields

        Returns:
            tuple[bool, List[str]]: (success, list of errors)
        """
        errors = []

        # Validate required fields if requested
        if validate_required:
            required_errors = self.validate_required_fields(
                entity_type, field_values)
            if required_errors:
                return False, required_errors

        # Validate and save each field value
        for field_key, value in field_values.items():
            # Get the custom field
            custom_field = self.repository.get_by_field_key(
                field_key, entity_type)

            if not custom_field:
                errors.append(f"Custom field '{field_key}' not found")
                continue

            # Validate field value
            is_valid, error_msg = self.validate_field_value(
                custom_field.field_type,
                value,
                custom_field.field_config
            )

            if not is_valid:
                errors.append(f"Field '{field_key}': {error_msg}")
                continue

            # Upsert the value
            try:
                self.repository.upsert_value(
                    custom_field.id,
                    entity_id,
                    entity_type,
                    str(value) if value is not None else None
                )
            except Exception as e:
                errors.append(f"Error saving field '{field_key}': {str(e)}")

        if errors:
            return False, errors

        return True, []

    def delete_entity_field_values(
        self,
        entity_id: UUID,
        entity_type: EntityType
    ) -> int:
        """
        Delete all custom field values for an entity.

        Args:
            entity_id (UUID): The entity ID
            entity_type (EntityType): The entity type

        Returns:
            int: Number of values deleted
        """
        return self.repository.delete_entity_values(entity_id, entity_type)

    def validate_field_config(
        self,
        field_type: FieldType,
        field_config: Optional[Dict[str, Any]]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate field configuration based on field type.

        Args:
            field_type (FieldType): The field type
            field_config (Optional[Dict[str, Any]]): Field configuration

        Returns:
            tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        if not field_config:
            return True, None

        try:
            # Select/Multi-select must have options
            if field_type in [FieldType.SELECT, FieldType.MULTI_SELECT]:
                if 'options' not in field_config:
                    return False, "Select fields must have options in field_config"
                if not isinstance(field_config['options'], list):
                    return False, "Options must be a list"
                if len(field_config['options']) == 0:
                    return False, "Options list cannot be empty"

            # Number fields - validate min/max
            if field_type == FieldType.NUMBER:
                min_val = field_config.get('min_value')
                max_val = field_config.get('max_value')
                if min_val is not None and max_val is not None:
                    if min_val >= max_val:
                        return False, "min_value must be less than max_value"

            return True, None

        except Exception as e:
            return False, f"Configuration validation error: {str(e)}"
