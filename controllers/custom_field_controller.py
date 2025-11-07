"""
Custom Fields Controller Layer

This module provides HTTP request handling and response formatting for custom
field endpoints. Handles validation, error mapping, and response transformation.

Key Features:
- Request validation and transformation
- Exception mapping to HTTP status codes
- Response formatting with proper schemas
- Business logic delegation to service layer
- Comprehensive error handling
- Support for both field management and value operations

Author: CRM System
Date: 2024
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.custom_field import CustomField, CustomFieldValue, FieldType, EntityType, PlacementType
from services.custom_field_service_new import CustomFieldService
from schemas.custom_field import (
    CustomFieldCreate,
    CustomFieldUpdate,
    CustomFieldResponse,
    CustomFieldValueCreate,
    CustomFieldValueUpdate,
    CustomFieldValueResponse,
    CustomFieldWithValue,
    BulkCustomFieldValuesUpdate,
    FieldTypeEnum,
    EntityTypeEnum
)


class CustomFieldController:
    """
    Controller class for custom field HTTP operations.

    This class handles all HTTP-related logic for custom field endpoints,
    including request validation, response formatting, and error handling.

    Responsibilities:
    - Validate incoming requests
    - Transform requests to service calls
    - Format responses using Pydantic schemas
    - Map exceptions to HTTP status codes
    - Provide OpenAPI documentation
    """

    def __init__(self, db: Session):
        """
        Initialize the CustomFieldController.

        Args:
            db (Session): SQLAlchemy database session
        """
        self.db = db
        self.service = CustomFieldService(db)

    # ==================== Custom Field Management ====================

    def list_custom_fields(
        self,
        entity_type: Optional[EntityTypeEnum] = None,
        is_active: Optional[bool] = True,
        placement: Optional[str] = None
    ) -> List[CustomFieldResponse]:
        """
        List all custom fields with optional filtering.

        Args:
            entity_type (Optional[EntityTypeEnum]): Filter by entity type
            is_active (Optional[bool]): Filter by active status
            placement (Optional[str]): Filter by placement

        Returns:
            List[CustomFieldResponse]: List of custom fields
        """
        try:
            placement_enum = None
            if placement:
                try:
                    placement_enum = PlacementType(placement)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid placement type: {placement}"
                    )

            entity_type_model = EntityType(
                entity_type) if entity_type else None

            fields = self.service.repository.get_all(
                entity_type=entity_type_model,
                is_active=is_active,
                placement=placement_enum
            )

            return [CustomFieldResponse.from_orm(field) for field in fields]

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving custom fields: {str(e)}"
            )

    def get_custom_field(self, field_id: UUID) -> CustomFieldResponse:
        """
        Get a specific custom field by ID.

        Args:
            field_id (UUID): The custom field ID

        Returns:
            CustomFieldResponse: The custom field

        Raises:
            HTTPException: If field not found
        """
        field = self.service.repository.get_by_id(field_id)

        if not field:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Custom field not found: {field_id}"
            )

        return CustomFieldResponse.from_orm(field)

    def create_custom_field(
        self,
        field_data: CustomFieldCreate,
        created_by: Optional[UUID] = None
    ) -> CustomFieldResponse:
        """
        Create a new custom field.

        Args:
            field_data (CustomFieldCreate): Field data
            created_by (Optional[UUID]): User ID who created the field

        Returns:
            CustomFieldResponse: The created custom field

        Raises:
            HTTPException: If validation fails
        """
        try:
            # Validate field configuration
            is_valid, error_msg = self.service.validate_field_config(
                field_data.field_type,
                field_data.field_config
            )

            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid field configuration: {error_msg}"
                )

            # Generate unique field key
            field_key = self.service.generate_unique_field_key(field_data.name)

            # Create the custom field
            new_field = CustomField(
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
                created_by=created_by
            )

            created_field = self.service.repository.create(new_field)
            return CustomFieldResponse.from_orm(created_field)

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating custom field: {str(e)}"
            )

    def update_custom_field(
        self,
        field_id: UUID,
        field_data: CustomFieldUpdate
    ) -> CustomFieldResponse:
        """
        Update an existing custom field.

        Args:
            field_id (UUID): The custom field ID
            field_data (CustomFieldUpdate): Updated field data

        Returns:
            CustomFieldResponse: The updated custom field

        Raises:
            HTTPException: If field not found or validation fails
        """
        field = self.service.repository.get_by_id(field_id)

        if not field:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Custom field not found: {field_id}"
            )

        try:
            # Validate field configuration if provided
            if field_data.field_config is not None:
                is_valid, error_msg = self.service.validate_field_config(
                    field.field_type,
                    field_data.field_config
                )

                if not is_valid:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid field configuration: {error_msg}"
                    )

            # Update only provided fields
            update_data = field_data.model_dump(exclude_unset=True)
            for field_name, value in update_data.items():
                setattr(field, field_name, value)

            updated_field = self.service.repository.update(field)
            return CustomFieldResponse.from_orm(updated_field)

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating custom field: {str(e)}"
            )

    def delete_custom_field(self, field_id: UUID) -> Dict[str, str]:
        """
        Delete a custom field and all its values.

        Args:
            field_id (UUID): The custom field ID

        Returns:
            Dict[str, str]: Success message

        Raises:
            HTTPException: If field not found
        """
        field = self.service.repository.get_by_id(field_id)

        if not field:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Custom field not found: {field_id}"
            )

        try:
            self.service.repository.delete(field)
            return {"message": "Custom field deleted successfully"}

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting custom field: {str(e)}"
            )

    # ==================== Custom Field Value Operations ====================

    def create_or_update_field_value(
        self,
        value_data: CustomFieldValueCreate
    ) -> CustomFieldValueResponse:
        """
        Create or update a custom field value.

        Args:
            value_data (CustomFieldValueCreate): Value data

        Returns:
            CustomFieldValueResponse: The created or updated value

        Raises:
            HTTPException: If field not found or validation fails
        """
        # Get the custom field
        custom_field = self.service.repository.get_by_id(
            UUID(value_data.custom_field_id)
        )

        if not custom_field:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Custom field not found"
            )

        # Validate field value
        is_valid, error_msg = self.service.validate_field_value(
            custom_field.field_type,
            value_data.value,
            custom_field.field_config
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid field value: {error_msg}"
            )

        try:
            # Upsert the value
            field_value = self.service.repository.upsert_value(
                UUID(value_data.custom_field_id),
                UUID(value_data.entity_id),
                value_data.entity_type,
                value_data.value
            )

            return CustomFieldValueResponse.from_orm(field_value)

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error saving field value: {str(e)}"
            )

    def get_entity_custom_fields(
        self,
        entity_type: EntityTypeEnum,
        entity_id: UUID
    ) -> List[CustomFieldWithValue]:
        """
        Get all custom fields for an entity with their current values.

        Args:
            entity_type (EntityTypeEnum): The entity type
            entity_id (UUID): The entity ID

        Returns:
            List[CustomFieldWithValue]: Custom fields with values
        """
        try:
            entity_type_model = EntityType(entity_type)

            # Get all active custom fields for this entity type
            custom_fields = self.service.repository.get_by_entity_type(
                entity_type_model,
                is_active=True
            )

            # Get current values for this entity
            field_values = self.service.repository.get_entity_values(
                entity_id,
                entity_type_model
            )

            # Create a mapping of field_id to value
            value_map = {str(fv.custom_field_id)
                             : fv.value for fv in field_values}

            # Combine fields with their values
            result = []
            for field in custom_fields:
                field_dict = {
                    "id": str(field.id),
                    "name": field.name,
                    "field_key": field.field_key,
                    "description": field.description,
                    "field_type": field.field_type,
                    "entity_type": field.entity_type,
                    "is_required": field.is_required,
                    "is_active": field.is_active,
                    "placement": field.placement,
                    "field_config": field.field_config,
                    "order_index": field.order_index,
                    "help_text": field.help_text,
                    "placeholder": field.placeholder,
                    "created_by": str(field.created_by) if field.created_by else None,
                    "created_at": field.created_at,
                    "updated_at": field.updated_at,
                    "current_value": value_map.get(str(field.id))
                }
                result.append(CustomFieldWithValue(**field_dict))

            return result

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving entity custom fields: {str(e)}"
            )

    def bulk_update_field_values(
        self,
        bulk_data: BulkCustomFieldValuesUpdate
    ) -> Dict[str, Any]:
        """
        Bulk update custom field values for an entity.

        Args:
            bulk_data (BulkCustomFieldValuesUpdate): Bulk update data

        Returns:
            Dict[str, Any]: Update results
        """
        try:
            entity_type_model = EntityType(bulk_data.entity_type)
            entity_id = UUID(bulk_data.entity_id)

            # Convert list of dicts to single dict
            field_values = {}
            for item in bulk_data.field_values:
                if isinstance(item, dict):
                    # Handle dict format
                    for key, value in item.items():
                        field_values[key] = value

            # Save field values with validation
            success, errors = self.service.save_custom_field_values(
                entity_id,
                entity_type_model,
                field_values,
                validate_required=False  # Don't enforce required on bulk update
            )

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"message": "Bulk update failed", "errors": errors}
                )

            return {
                "success": True,
                "message": f"Updated {len(field_values)} field(s) successfully",
                "updated_count": len(field_values)
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error during bulk update: {str(e)}"
            )

    def delete_entity_field_values(
        self,
        entity_type: EntityTypeEnum,
        entity_id: UUID
    ) -> Dict[str, str]:
        """
        Delete all custom field values for an entity.

        Args:
            entity_type (EntityTypeEnum): The entity type
            entity_id (UUID): The entity ID

        Returns:
            Dict[str, str]: Success message with count
        """
        try:
            entity_type_model = EntityType(entity_type)
            deleted_count = self.service.delete_entity_field_values(
                entity_id,
                entity_type_model
            )

            return {"message": f"Deleted {deleted_count} field value(s)"}

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting field values: {str(e)}"
            )

    # ==================== Utility Operations ====================

    def get_field_types(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Get all available field types.

        Returns:
            Dict[str, List[Dict[str, str]]]: Field types with labels
        """
        return {
            "field_types": [
                {"value": ft.value, "label": ft.value.replace(
                    '_', ' ').title()}
                for ft in FieldTypeEnum
            ]
        }

    def get_entity_types(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Get all available entity types.

        Returns:
            Dict[str, List[Dict[str, str]]]: Entity types with labels
        """
        return {
            "entity_types": [
                {"value": et.value, "label": et.value.title()}
                for et in EntityTypeEnum
            ]
        }

    def get_field_statistics(
        self,
        entity_type: Optional[EntityTypeEnum] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about custom fields.

        Args:
            entity_type (Optional[EntityTypeEnum]): Filter by entity type

        Returns:
            Dict[str, Any]: Field statistics
        """
        try:
            if entity_type:
                entity_type_model = EntityType(entity_type)
                count = self.service.repository.count_by_entity_type(
                    entity_type_model)
                return {
                    "entity_type": entity_type,
                    "total_fields": count
                }
            else:
                stats = {}
                for et in EntityTypeEnum:
                    entity_type_model = EntityType(et)
                    count = self.service.repository.count_by_entity_type(
                        entity_type_model)
                    stats[et.value] = count

                return {
                    "by_entity_type": stats,
                    "total_fields": sum(stats.values())
                }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving statistics: {str(e)}"
            )
