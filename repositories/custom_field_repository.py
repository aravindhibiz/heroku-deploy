"""
Custom Fields Repository Layer

This module provides data access operations for CustomField and CustomFieldValue entities.
Implements the Repository pattern for database interactions.

Key Features:
- CRUD operations for custom fields and values
- Entity-type based queries
- Bulk operations for field values
- Efficient querying with relationships
- Value validation and formatting

Author: CRM System
Date: 2024
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import desc, and_, or_
from sqlalchemy.orm import Session, joinedload
from models.custom_field import (
    CustomField,
    CustomFieldValue,
    FieldType,
    EntityType,
    PlacementType
)


class CustomFieldRepository:
    """
    Repository class for CustomField and CustomFieldValue database operations.

    This class encapsulates all database queries and operations for custom fields,
    providing a clean interface for the service layer.

    Responsibilities:
    - Execute database queries for custom fields
    - Handle filtering by entity type and placement
    - Manage custom field values
    - Support bulk operations
    - Provide efficient joins and eager loading
    """

    def __init__(self, db: Session):
        """
        Initialize the CustomFieldRepository.

        Args:
            db (Session): SQLAlchemy database session
        """
        self.db = db

    # ==================== Custom Field Operations ====================

    def get_all(
        self,
        entity_type: Optional[EntityType] = None,
        is_active: Optional[bool] = None,
        placement: Optional[PlacementType] = None
    ) -> List[CustomField]:
        """
        Get all custom fields with optional filtering.

        Args:
            entity_type (Optional[EntityType]): Filter by entity type
            is_active (Optional[bool]): Filter by active status
            placement (Optional[PlacementType]): Filter by placement

        Returns:
            List[CustomField]: List of custom fields
        """
        query = self.db.query(CustomField)

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

        return query.order_by(
            CustomField.order_index,
            CustomField.created_at
        ).all()

    def get_by_id(self, field_id: UUID) -> Optional[CustomField]:
        """
        Get a custom field by its ID.

        Args:
            field_id (UUID): The custom field ID

        Returns:
            Optional[CustomField]: The custom field if found
        """
        return self.db.query(CustomField).filter(
            CustomField.id == field_id
        ).first()

    def get_by_field_key(
        self,
        field_key: str,
        entity_type: Optional[EntityType] = None
    ) -> Optional[CustomField]:
        """
        Get a custom field by its field key.

        Args:
            field_key (str): The field key
            entity_type (Optional[EntityType]): Filter by entity type

        Returns:
            Optional[CustomField]: The custom field if found
        """
        query = self.db.query(CustomField).filter(
            CustomField.field_key == field_key
        )

        if entity_type:
            query = query.filter(CustomField.entity_type == entity_type)

        return query.first()

    def get_by_entity_type(
        self,
        entity_type: EntityType,
        is_active: bool = True
    ) -> List[CustomField]:
        """
        Get all custom fields for a specific entity type.

        Args:
            entity_type (EntityType): The entity type
            is_active (bool): Filter by active status

        Returns:
            List[CustomField]: List of custom fields
        """
        query = self.db.query(CustomField).filter(
            CustomField.entity_type == entity_type
        )

        if is_active is not None:
            query = query.filter(CustomField.is_active == is_active)

        return query.order_by(
            CustomField.order_index,
            CustomField.created_at
        ).all()

    def get_for_placement(
        self,
        entity_type: EntityType,
        placement: PlacementType,
        is_active: bool = True
    ) -> List[CustomField]:
        """
        Get custom fields for a specific placement (form, detail, list).

        Args:
            entity_type (EntityType): The entity type
            placement (PlacementType): The placement type
            is_active (bool): Filter by active status

        Returns:
            List[CustomField]: List of custom fields
        """
        query = self.db.query(CustomField).filter(
            CustomField.entity_type == entity_type,
            or_(
                CustomField.placement == placement,
                CustomField.placement == PlacementType.BOTH
            )
        )

        if is_active is not None:
            query = query.filter(CustomField.is_active == is_active)

        return query.order_by(
            CustomField.order_index,
            CustomField.created_at
        ).all()

    def get_required_fields(
        self,
        entity_type: EntityType,
        is_active: bool = True
    ) -> List[CustomField]:
        """
        Get all required custom fields for an entity type.

        Args:
            entity_type (EntityType): The entity type
            is_active (bool): Filter by active status

        Returns:
            List[CustomField]: List of required custom fields
        """
        query = self.db.query(CustomField).filter(
            CustomField.entity_type == entity_type,
            CustomField.is_required == True
        )

        if is_active is not None:
            query = query.filter(CustomField.is_active == is_active)

        return query.all()

    def create(self, custom_field: CustomField) -> CustomField:
        """
        Create a new custom field.

        Args:
            custom_field (CustomField): The custom field to create

        Returns:
            CustomField: The created custom field
        """
        self.db.add(custom_field)
        self.db.commit()
        self.db.refresh(custom_field)
        return custom_field

    def update(self, custom_field: CustomField) -> CustomField:
        """
        Update an existing custom field.

        Args:
            custom_field (CustomField): The custom field with updated values

        Returns:
            CustomField: The updated custom field
        """
        self.db.commit()
        self.db.refresh(custom_field)
        return custom_field

    def delete(self, custom_field: CustomField) -> None:
        """
        Delete a custom field (cascades to values).

        Args:
            custom_field (CustomField): The custom field to delete
        """
        self.db.delete(custom_field)
        self.db.commit()

    def field_key_exists(self, field_key: str) -> bool:
        """
        Check if a field key already exists.

        Args:
            field_key (str): The field key to check

        Returns:
            bool: True if exists, False otherwise
        """
        return self.db.query(CustomField).filter(
            CustomField.field_key == field_key
        ).first() is not None

    def count_by_entity_type(self, entity_type: EntityType) -> int:
        """
        Count custom fields for an entity type.

        Args:
            entity_type (EntityType): The entity type

        Returns:
            int: Number of custom fields
        """
        return self.db.query(CustomField).filter(
            CustomField.entity_type == entity_type,
            CustomField.is_active == True
        ).count()

    # ==================== Custom Field Value Operations ====================

    def get_value_by_id(self, value_id: UUID) -> Optional[CustomFieldValue]:
        """
        Get a custom field value by its ID.

        Args:
            value_id (UUID): The value ID

        Returns:
            Optional[CustomFieldValue]: The value if found
        """
        return self.db.query(CustomFieldValue).filter(
            CustomFieldValue.id == value_id
        ).first()

    def get_value(
        self,
        field_id: UUID,
        entity_id: UUID
    ) -> Optional[CustomFieldValue]:
        """
        Get a specific custom field value.

        Args:
            field_id (UUID): The custom field ID
            entity_id (UUID): The entity ID

        Returns:
            Optional[CustomFieldValue]: The value if found
        """
        return self.db.query(CustomFieldValue).filter(
            and_(
                CustomFieldValue.custom_field_id == field_id,
                CustomFieldValue.entity_id == entity_id
            )
        ).first()

    def get_entity_values(
        self,
        entity_id: UUID,
        entity_type: EntityType
    ) -> List[CustomFieldValue]:
        """
        Get all custom field values for an entity.

        Args:
            entity_id (UUID): The entity ID
            entity_type (EntityType): The entity type

        Returns:
            List[CustomFieldValue]: List of field values
        """
        return self.db.query(CustomFieldValue).filter(
            and_(
                CustomFieldValue.entity_id == entity_id,
                CustomFieldValue.entity_type == entity_type
            )
        ).all()

    def get_entity_values_with_fields(
        self,
        entity_id: UUID,
        entity_type: EntityType
    ) -> List[CustomFieldValue]:
        """
        Get all custom field values for an entity with field definitions loaded.

        Args:
            entity_id (UUID): The entity ID
            entity_type (EntityType): The entity type

        Returns:
            List[CustomFieldValue]: List of field values with custom_field loaded
        """
        return self.db.query(CustomFieldValue).options(
            joinedload(CustomFieldValue.custom_field)
        ).filter(
            and_(
                CustomFieldValue.entity_id == entity_id,
                CustomFieldValue.entity_type == entity_type
            )
        ).all()

    def create_value(self, field_value: CustomFieldValue) -> CustomFieldValue:
        """
        Create a new custom field value.

        Args:
            field_value (CustomFieldValue): The value to create

        Returns:
            CustomFieldValue: The created value
        """
        self.db.add(field_value)
        self.db.commit()
        self.db.refresh(field_value)
        return field_value

    def update_value(self, field_value: CustomFieldValue) -> CustomFieldValue:
        """
        Update an existing custom field value.

        Args:
            field_value (CustomFieldValue): The value with updated data

        Returns:
            CustomFieldValue: The updated value
        """
        self.db.commit()
        self.db.refresh(field_value)
        return field_value

    def delete_value(self, field_value: CustomFieldValue) -> None:
        """
        Delete a custom field value.

        Args:
            field_value (CustomFieldValue): The value to delete
        """
        self.db.delete(field_value)
        self.db.commit()

    def delete_entity_values(
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
        deleted_count = self.db.query(CustomFieldValue).filter(
            and_(
                CustomFieldValue.entity_id == entity_id,
                CustomFieldValue.entity_type == entity_type
            )
        ).delete()

        self.db.commit()
        return deleted_count

    def upsert_value(
        self,
        field_id: UUID,
        entity_id: UUID,
        entity_type: EntityType,
        value: Optional[str]
    ) -> CustomFieldValue:
        """
        Create or update a custom field value.

        Args:
            field_id (UUID): The custom field ID
            entity_id (UUID): The entity ID
            entity_type (EntityType): The entity type
            value (Optional[str]): The value

        Returns:
            CustomFieldValue: The created or updated value
        """
        existing = self.get_value(field_id, entity_id)

        if existing:
            existing.value = value
            return self.update_value(existing)
        else:
            new_value = CustomFieldValue(
                custom_field_id=field_id,
                entity_id=entity_id,
                entity_type=entity_type,
                value=value
            )
            return self.create_value(new_value)

    def bulk_upsert_values(
        self,
        entity_id: UUID,
        entity_type: EntityType,
        field_values: Dict[str, Any]
    ) -> tuple[int, List[str]]:
        """
        Bulk create or update custom field values.

        Args:
            entity_id (UUID): The entity ID
            entity_type (EntityType): The entity type
            field_values (Dict[str, Any]): Dictionary of field_key -> value

        Returns:
            tuple[int, List[str]]: (updated_count, list of errors)
        """
        updated_count = 0
        errors = []

        for field_key, value in field_values.items():
            try:
                # Get the custom field
                custom_field = self.get_by_field_key(field_key, entity_type)

                if not custom_field:
                    errors.append(f"Field '{field_key}' not found")
                    continue

                # Upsert the value
                self.upsert_value(
                    custom_field.id,
                    entity_id,
                    entity_type,
                    str(value) if value is not None else None
                )
                updated_count += 1

            except Exception as e:
                errors.append(f"Error updating field '{field_key}': {str(e)}")

        return updated_count, errors
