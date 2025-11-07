"""
System Configuration Routes

This module defines API endpoints for system configuration management.
Provides a clean, well-documented REST API for configuration operations.

Endpoints:
- GET /system-config - List all configurations
- GET /system-config/schema - Get configuration schema
- GET /system-config/grouped - Get configurations grouped by category
- GET /system-config/categories - Get configurations by specific categories
- GET /system-config/current - Get current effective configuration
- GET /system-config/export - Export all configurations
- POST /system-config - Create a new configuration
- POST /system-config/validate - Validate configurations without saving
- POST /system-config/initialize - Initialize default configurations
- PUT /system-config/bulk - Bulk update configurations
- PUT /system-config/{config_id} - Update a single configuration
- DELETE /system-config/{config_id} - Deactivate a configuration

Author: CRM System
Date: 2024
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.auth import require_admin
from ..controllers.system_config_controller import SystemConfigController
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

router = APIRouter(prefix="/system-config", tags=["System Configuration"])


@router.get(
    "",
    response_model=List[SystemConfigResponse],
    summary="List all system configurations",
    description="""
    Retrieve all system configurations with optional filtering.
    
    **Parameters:**
    - category: Filter by configuration category (general, sales, notifications, etc.)
    - include_inactive: Include deactivated configurations in results
    
    **Returns:** List of system configurations
    
    **Admin Access Required**
    """,
    status_code=status.HTTP_200_OK
)
async def get_all_configurations(
    category: Optional[str] = Query(None, description="Filter by category"),
    include_inactive: bool = Query(
        False, description="Include inactive configurations"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin())
):
    """List all system configurations with optional filtering."""
    controller = SystemConfigController(db)
    return controller.list_configurations(
        category=category,
        include_inactive=include_inactive
    )


@router.get(
    "/schema",
    response_model=SystemConfigSchemaResponse,
    summary="Get configuration schema",
    description="""
    Retrieve the configuration schema with category definitions and field types.
    
    Provides metadata about all configuration categories including:
    - Category labels and descriptions
    - Category icons and display order
    - Field types and validation rules
    - Available options for select fields
    
    **Returns:** Configuration schema with categories and field types
    
    **Admin Access Required**
    """,
    status_code=status.HTTP_200_OK
)
async def get_configuration_schema(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin())
):
    """Get the configuration schema with categories and field types."""
    controller = SystemConfigController(db)
    return controller.get_schema()


@router.get(
    "/grouped",
    response_model=Dict[str, Dict[str, Any]],
    summary="Get configurations grouped by category",
    description="""
    Retrieve all configurations organized by category in nested format.
    
    **Returns:** Dictionary with category names as keys and key-value configuration dictionaries as values
    
    **Example Response:**
    ```json
    {
        "general": {
            "company_name": "My Company",
            "currency": "USD"
        },
        "sales": {
            "default_pipeline_stage": "new",
            "require_deal_value": true
        }
    }
    ```
    
    **Admin Access Required**
    """,
    status_code=status.HTTP_200_OK
)
async def get_configurations_grouped(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin())
):
    """Get configurations grouped by category in nested format."""
    controller = SystemConfigController(db)
    return controller.get_grouped_configurations()


@router.get(
    "/categories",
    response_model=List[SystemConfigCategoryResponse],
    summary="Get configurations by categories with metadata",
    description="""
    Retrieve configurations for specific categories with full metadata.
    
    **Parameters:**
    - categories: List of category names to retrieve
    
    **Returns:** List of category objects with configurations and metadata
    
    Each category response includes:
    - Category name and label
    - Description and icon
    - List of configurations in that category
    
    **Admin Access Required**
    """,
    status_code=status.HTTP_200_OK
)
async def get_configurations_by_categories(
    categories: List[str] = Query(...,
                                  description="List of categories to retrieve"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin())
):
    """Get configurations for specific categories with metadata."""
    controller = SystemConfigController(db)
    return controller.get_configurations_by_categories(categories)


@router.get(
    "/current",
    response_model=Dict[str, Any],
    summary="Get current effective configuration",
    description="""
    Retrieve the current active configuration as a nested dictionary.
    
    **Returns:** Current configuration values organized by category
    
    **Example Response:**
    ```json
    {
        "general": {
            "company_name": "My Company",
            "currency": "USD"
        },
        "sales": {
            "default_pipeline_stage": "new"
        }
    }
    ```
    
    **Admin Access Required**
    """,
    status_code=status.HTTP_200_OK
)
async def get_current_configuration(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin())
):
    """Get current effective configuration."""
    controller = SystemConfigController(db)
    return controller.get_current_configuration()


@router.get(
    "/export",
    response_model=SystemConfigExportResponse,
    summary="Export all configurations",
    description="""
    Export all active configurations with metadata.
    
    **Returns:** Export data including:
    - Export timestamp
    - All configuration values
    - Export metadata (count, categories, version)
    
    Useful for:
    - Backing up current configuration
    - Transferring settings between environments
    - Configuration documentation
    
    **Admin Access Required**
    """,
    status_code=status.HTTP_200_OK
)
async def export_configurations(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin())
):
    """Export all configurations with metadata."""
    controller = SystemConfigController(db)
    return controller.export_configurations()


@router.post(
    "",
    response_model=SystemConfigResponse,
    summary="Create a new configuration",
    description="""
    Create a new system configuration.
    
    **Request Body:** Configuration data including key, value, category, and description
    
    **Validation:**
    - Key must be unique
    - Value must pass type validation (email, integer, boolean)
    - Category is required
    
    **Returns:** The created configuration
    
    **Admin Access Required**
    """,
    status_code=status.HTTP_201_CREATED
)
async def create_configuration(
    config_data: SystemConfigCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin())
):
    """Create a new system configuration."""
    controller = SystemConfigController(db)
    return controller.create_configuration(config_data)


@router.post(
    "/validate",
    response_model=SystemConfigValidationResponse,
    summary="Validate configurations",
    description="""
    Validate configuration values without saving to database.
    
    **Request Body:** List of configurations to validate
    
    **Validation Checks:**
    - Email format validation
    - Integer range validation
    - Boolean type validation
    - Required field validation
    
    **Returns:** Validation results with errors and warnings
    
    Useful for pre-validating bulk imports or testing configuration changes.
    
    **Admin Access Required**
    """,
    status_code=status.HTTP_200_OK
)
async def validate_configurations(
    bulk_data: SystemConfigBulkUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin())
):
    """Validate configurations without saving."""
    controller = SystemConfigController(db)
    return controller.validate_configurations(bulk_data)


@router.post(
    "/initialize",
    response_model=Dict[str, Any],
    summary="Initialize default configurations",
    description="""
    Initialize all default system configurations.
    
    Creates or updates configurations to match the system defaults across all categories:
    - General Settings (company info, formats)
    - Sales Settings (pipeline, deals)
    - Notification Settings (emails, alerts)
    - Security Settings (passwords, authentication)
    - Backup Settings (automatic backups)
    - Integration Settings (external services)
    - Performance Settings (caching, limits)
    
    **Returns:** Initialization results with counts
    
    Safe to run multiple times - only creates missing configs or updates inactive ones.
    
    **Admin Access Required**
    """,
    status_code=status.HTTP_200_OK
)
async def initialize_default_configurations(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin())
):
    """Initialize all default configurations."""
    controller = SystemConfigController(db)
    return controller.initialize_defaults()


@router.put(
    "/bulk",
    response_model=Dict[str, Any],
    summary="Bulk update configurations",
    description="""
    Update multiple configurations in a single request.
    
    **Request Body:** List of configuration updates (key and value pairs)
    
    **Features:**
    - Validates all configurations before updating
    - Atomic operation (all or nothing)
    - Returns detailed results
    
    **Returns:** Update results with success count and any errors
    
    **Example Request:**
    ```json
    {
        "configurations": [
            {"key": "general.currency", "value": "EUR"},
            {"key": "sales.require_deal_value", "value": true}
        ]
    }
    ```
    
    **Admin Access Required**
    """,
    status_code=status.HTTP_200_OK
)
async def bulk_update_configurations(
    bulk_data: SystemConfigBulkUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin())
):
    """Bulk update multiple configurations."""
    controller = SystemConfigController(db)
    return controller.bulk_update_configurations(bulk_data)


@router.put(
    "/{config_id}",
    response_model=SystemConfigResponse,
    summary="Update a configuration",
    description="""
    Update a single system configuration.
    
    **Parameters:**
    - config_id: UUID of the configuration to update
    
    **Request Body:** Updated configuration data (value and/or description)
    
    **Validation:**
    - Configuration must exist
    - New value must pass type validation
    
    **Returns:** The updated configuration
    
    **Admin Access Required**
    """,
    status_code=status.HTTP_200_OK
)
async def update_configuration(
    config_id: UUID,
    config_data: SystemConfigUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin())
):
    """Update a single configuration."""
    controller = SystemConfigController(db)
    return controller.update_configuration(config_id, config_data)


@router.delete(
    "/{config_id}",
    response_model=Dict[str, str],
    summary="Deactivate a configuration",
    description="""
    Soft delete a configuration by setting is_active to False.
    
    **Parameters:**
    - config_id: UUID of the configuration to deactivate
    
    **Returns:** Success message
    
    Note: This is a soft delete. The configuration remains in the database
    but is marked as inactive and won't be returned in normal queries.
    
    **Admin Access Required**
    """,
    status_code=status.HTTP_200_OK
)
async def delete_configuration(
    config_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin())
):
    """Soft delete a configuration."""
    controller = SystemConfigController(db)
    return controller.delete_configuration(config_id)
