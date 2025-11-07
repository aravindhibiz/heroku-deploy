"""
System Configuration Controller Layer

This module provides HTTP request handling and response formatting for system
configuration endpoints. Handles validation, error mapping, and response transformation.

Key Features:
- Request validation and transformation
- Exception mapping to HTTP status codes
- Response formatting with proper schemas
- Business logic delegation to service layer
- Comprehensive error handling

Author: CRM System
Date: 2024
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models.system_config import SystemConfiguration
from ..services.system_config_service_new import SystemConfigService
from ..schemas.system_config import (
    SystemConfigCreate,
    SystemConfigUpdate,
    SystemConfigResponse,
    SystemConfigBulkUpdateRequest,
    SystemConfigCategoryResponse,
    SystemConfigSchemaResponse,
    SystemConfigExportResponse,
    SystemConfigValidationResponse
)


class SystemConfigController:
    """
    Controller class for system configuration HTTP operations.

    This class handles all HTTP-related logic for configuration endpoints,
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
        Initialize the SystemConfigController.

        Args:
            db (Session): SQLAlchemy database session
        """
        self.db = db
        self.service = SystemConfigService(db)

    def list_configurations(
        self,
        category: Optional[str] = None,
        include_inactive: bool = False
    ) -> List[SystemConfigResponse]:
        """
        List all system configurations with optional filtering.

        Args:
            category (Optional[str]): Filter by category
            include_inactive (bool): Include inactive configurations

        Returns:
            List[SystemConfigResponse]: List of configurations
        """
        try:
            configurations = self.service.repository.get_all(
                category=category,
                include_inactive=include_inactive
            )
            return [SystemConfigResponse.from_orm(config) for config in configurations]
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving configurations: {str(e)}"
            )

    def get_configuration(self, config_id: UUID) -> SystemConfigResponse:
        """
        Get a specific configuration by ID.

        Args:
            config_id (UUID): The configuration ID

        Returns:
            SystemConfigResponse: The configuration

        Raises:
            HTTPException: If configuration not found
        """
        configuration = self.service.repository.get_by_id(config_id)

        if not configuration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration not found: {config_id}"
            )

        return SystemConfigResponse.from_orm(configuration)

    def get_configuration_by_key(self, key: str) -> SystemConfigResponse:
        """
        Get a specific configuration by key.

        Args:
            key (str): The configuration key

        Returns:
            SystemConfigResponse: The configuration

        Raises:
            HTTPException: If configuration not found
        """
        configuration = self.service.repository.get_by_key(key)

        if not configuration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration not found: {key}"
            )

        return SystemConfigResponse.from_orm(configuration)

    def create_configuration(
        self,
        config_data: SystemConfigCreate
    ) -> SystemConfigResponse:
        """
        Create a new system configuration.

        Args:
            config_data (SystemConfigCreate): Configuration data

        Returns:
            SystemConfigResponse: The created configuration

        Raises:
            HTTPException: If validation fails or key already exists
        """
        # Check if configuration with this key already exists
        existing = self.service.repository.get_by_key(config_data.key)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Configuration with key '{config_data.key}' already exists"
            )

        # Validate configuration value
        is_valid, errors = self.service.validate_configuration(
            config_data.key,
            config_data.value
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Validation errors: {', '.join(errors)}"
            )

        try:
            new_config = SystemConfiguration(**config_data.dict())
            created_config = self.service.repository.create(new_config)
            return SystemConfigResponse.from_orm(created_config)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating configuration: {str(e)}"
            )

    def update_configuration(
        self,
        config_id: UUID,
        config_data: SystemConfigUpdate
    ) -> SystemConfigResponse:
        """
        Update an existing configuration.

        Args:
            config_id (UUID): The configuration ID
            config_data (SystemConfigUpdate): Updated data

        Returns:
            SystemConfigResponse: The updated configuration

        Raises:
            HTTPException: If configuration not found or validation fails
        """
        configuration = self.service.repository.get_by_id(config_id)

        if not configuration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration not found: {config_id}"
            )

        # Validate new value if provided
        if config_data.value is not None:
            is_valid, errors = self.service.validate_configuration(
                configuration.key,
                config_data.value
            )

            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Validation errors: {', '.join(errors)}"
                )

        try:
            # Update fields
            update_data = config_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(configuration, field, value)

            updated_config = self.service.repository.update(configuration)
            return SystemConfigResponse.from_orm(updated_config)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating configuration: {str(e)}"
            )

    def bulk_update_configurations(
        self,
        bulk_data: SystemConfigBulkUpdateRequest
    ) -> Dict[str, Any]:
        """
        Update multiple configurations at once.

        Args:
            bulk_data (SystemConfigBulkUpdateRequest): Bulk update data

        Returns:
            Dict[str, Any]: Update results

        Raises:
            HTTPException: If validation fails
        """
        try:
            # Convert to list of dicts
            updates = [item.dict() for item in bulk_data.configurations]

            # Use service for validation and update
            result = self.service.bulk_update_configurations(updates)

            if not result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Bulk update failed",
                        "errors": result["errors"]
                    }
                )

            return {
                "success": True,
                "updated": result["updated"],
                "message": f"Successfully updated {result['updated']} configuration(s)"
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error during bulk update: {str(e)}"
            )

    def delete_configuration(self, config_id: UUID) -> Dict[str, str]:
        """
        Soft delete a configuration (set is_active to False).

        Args:
            config_id (UUID): The configuration ID

        Returns:
            Dict[str, str]: Success message

        Raises:
            HTTPException: If configuration not found
        """
        configuration = self.service.repository.get_by_id(config_id)

        if not configuration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration not found: {config_id}"
            )

        try:
            self.service.repository.soft_delete(configuration)
            return {"message": "Configuration deactivated successfully"}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting configuration: {str(e)}"
            )

    def get_schema(self) -> SystemConfigSchemaResponse:
        """
        Get the configuration schema with categories and field types.

        Returns:
            SystemConfigSchemaResponse: Schema definition
        """
        try:
            schema = self.service.get_configuration_schema()
            return SystemConfigSchemaResponse(**schema)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving schema: {str(e)}"
            )

    def get_grouped_configurations(self) -> Dict[str, Dict[str, Any]]:
        """
        Get configurations grouped by category in nested format.

        Returns:
            Dict[str, Dict[str, Any]]: Configurations by category with key-value pairs
            Example: {"general": {"company_name": "My Company", "currency": "USD"}}
        """
        try:
            grouped = self.service.repository.get_grouped_by_category()

            # If no configurations exist, initialize defaults
            if not grouped or len(grouped) == 0:
                print("No configurations found, initializing defaults...")
                self.service.initialize_default_configurations()
                grouped = self.service.repository.get_grouped_by_category()

            # Convert to nested format for frontend
            result = {}
            for category, configs in grouped.items():
                result[category] = {}
                for config in configs:
                    # Extract field name from key (e.g., "general.company_name" -> "company_name")
                    field_name = config.key.split(
                        '.')[-1] if '.' in config.key else config.key
                    result[category][field_name] = config.value

            return result
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving grouped configurations: {str(e)}"
            )

    def get_configurations_by_categories(
        self,
        categories: List[str]
    ) -> List[SystemConfigCategoryResponse]:
        """
        Get configurations for specific categories with metadata.

        Args:
            categories (List[str]): List of category names

        Returns:
            List[SystemConfigCategoryResponse]: Configurations with metadata
        """
        try:
            schema = self.service.get_configuration_schema()
            category_metadata = schema["categories"]

            result = []
            for category in categories:
                configs = self.service.repository.get_by_category(category)

                # Get metadata for this category
                metadata = category_metadata.get(category, {
                    "label": category.title(),
                    "description": f"{category.title()} configuration",
                    "icon": "settings",
                    "order": 99
                })

                result.append(SystemConfigCategoryResponse(
                    category=category,
                    label=metadata.get("label", category.title()),
                    description=metadata.get("description", ""),
                    icon=metadata.get("icon", "settings"),
                    configurations=[
                        SystemConfigResponse.from_orm(config) for config in configs
                    ]
                ))

            return result
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving configurations by categories: {str(e)}"
            )

    def get_current_configuration(self) -> Dict[str, Any]:
        """
        Get current effective configuration (all active configs).

        Returns:
            Dict[str, Any]: Current configuration values
        """
        try:
            return self.service.get_current_configuration()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving current configuration: {str(e)}"
            )

    def export_configurations(self) -> SystemConfigExportResponse:
        """
        Export all configurations with metadata.

        Returns:
            SystemConfigExportResponse: Export data
        """
        try:
            export_data = self.service.export_configurations()
            return SystemConfigExportResponse(**export_data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error exporting configurations: {str(e)}"
            )

    def validate_configurations(
        self,
        bulk_data: SystemConfigBulkUpdateRequest
    ) -> SystemConfigValidationResponse:
        """
        Validate configurations without saving.

        Args:
            bulk_data (SystemConfigBulkUpdateRequest): Configurations to validate

        Returns:
            SystemConfigValidationResponse: Validation results
        """
        try:
            # Convert to list of dicts
            configurations = [item.dict() for item in bulk_data.configurations]

            validation_result = self.service.validate_bulk_configurations(
                configurations)
            return SystemConfigValidationResponse(**validation_result)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error validating configurations: {str(e)}"
            )

    def initialize_defaults(self) -> Dict[str, Any]:
        """
        Initialize all default configurations.

        Returns:
            Dict[str, Any]: Initialization results
        """
        try:
            result = self.service.initialize_default_configurations()
            return {
                "success": True,
                "message": "Default configurations initialized successfully",
                "created": result["created"],
                "updated": result["updated"],
                "total": result["total"]
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error initializing defaults: {str(e)}"
            )
