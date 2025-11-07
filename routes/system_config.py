from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..core.database import get_db
from ..core.auth import get_current_user, require_admin
from ..models.user import UserProfile
from ..models.system_config import SystemConfiguration
from ..schemas.system_config import (
    SystemConfigResponse, SystemConfigBulkUpdate, SystemConfigBulkUpdateRequest,
    SystemConfigBulkUpdateItem, SystemConfigCreate, SystemConfigUpdate,
    SystemConfigCategoryResponse, SystemConfigSchemaResponse, SystemConfigExportResponse,
    SystemConfigValidationResponse, SystemConfigBulkUpdateRequestNew
)
from ..services.system_config_service import SystemConfigManager

router = APIRouter()


@router.get("/", response_model=List[SystemConfigResponse])
async def get_all_configurations(
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_admin())
):
    """Get all system configurations"""
    query = db.query(SystemConfiguration).filter(
        SystemConfiguration.is_active == True)

    if category:
        query = query.filter(SystemConfiguration.category == category)

    configurations = query.order_by(
        SystemConfiguration.category, SystemConfiguration.key).all()
    return configurations


@router.get("/grouped", response_model=Dict[str, Dict[str, Any]])
async def get_configurations_grouped(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_admin())
):
    """Get configurations grouped by category"""
    configurations = db.query(SystemConfiguration).filter(
        SystemConfiguration.is_active == True
    ).all()

    grouped = {}
    for config in configurations:
        if config.category not in grouped:
            grouped[config.category] = {}

        # Convert key from dot notation to nested structure
        key_parts = config.key.split('.')
        if len(key_parts) == 2:
            category, field = key_parts
            grouped[config.category][field] = config.value
        else:
            grouped[config.category][config.key] = config.value

    return grouped


@router.get("/categories", response_model=List[SystemConfigCategoryResponse])
async def get_configurations_by_categories(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_admin())
):
    """Get configurations organized by categories with metadata"""
    configurations = db.query(SystemConfiguration).filter(
        SystemConfiguration.is_active == True
    ).order_by(SystemConfiguration.category, SystemConfiguration.key).all()

    schema = SystemConfigManager.get_configuration_schema()
    categories = {}

    for config in configurations:
        if config.category not in categories:
            category_info = schema["categories"].get(config.category, {})
            categories[config.category] = {
                "category": config.category,
                "label": category_info.get("label", config.category.title()),
                "description": category_info.get("description", ""),
                "icon": category_info.get("icon", "Settings"),
                "configurations": []
            }
        categories[config.category]["configurations"].append(config)

    return list(categories.values())


@router.get("/schema", response_model=SystemConfigSchemaResponse)
async def get_configuration_schema(
    current_user: UserProfile = Depends(require_admin())
):
    """Get the configuration schema for frontend validation"""
    return SystemConfigManager.get_configuration_schema()


@router.post("/", response_model=SystemConfigResponse)
async def create_configuration(
    config_data: SystemConfigCreate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_admin())
):
    """Create a new system configuration"""
    # Check if configuration already exists
    existing = db.query(SystemConfiguration).filter(
        SystemConfiguration.key == config_data.key
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configuration with this key already exists"
        )

    # Validate configuration value
    if not SystemConfigManager.validate_configuration(config_data.key, config_data.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid configuration value"
        )

    config = SystemConfiguration(**config_data.model_dump())
    db.add(config)
    db.commit()
    db.refresh(config)

    return config


@router.get("/debug-test")
async def debug_test_route():
    """Simple test route to verify routing is working"""
    print("DEBUG: Simple test route called")
    return {"message": "Debug test successful", "timestamp": datetime.utcnow()}


@router.put("/bulk-test-no-auth", response_model=Dict[str, Any])
async def test_bulk_update_route_no_auth(
    data: Dict[str, Any]
):
    """Test route without authentication to debug the bulk update issue"""
    print(f"Raw test data received (no auth): {data}")
    return {"success": True, "received": data}


@router.put("/bulk-test", response_model=Dict[str, Any])
async def test_bulk_update_route(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_admin())
):
    """Test route to debug the bulk update issue"""
    print(f"Raw test data received: {data}")
    return {"success": True, "received": data}


@router.put("/bulk-raw", response_model=Dict[str, Any])
async def update_configurations_bulk_raw(
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_admin())
):
    """Update multiple configurations at once - raw JSON approach"""
    try:
        # Get raw JSON from request
        raw_data = await request.json()
        print(f"RAW ROUTE - Received data: {raw_data}")

        configurations = raw_data.get('configurations', [])
        print(f"RAW ROUTE - Configurations count: {len(configurations)}")

        updated_count = 0
        errors = []

        for config_update in configurations:
            config_key = config_update.get('key')
            config_value = config_update.get('value')

            if not config_key:
                errors.append("Missing configuration key")
                continue

            # Validate configuration value
            if not SystemConfigManager.validate_configuration(config_key, config_value):
                errors.append(f"Invalid value for configuration: {config_key}")
                continue

            # Find and update configuration
            config = db.query(SystemConfiguration).filter(
                SystemConfiguration.key == config_key
            ).first()

            if config:
                config.value = config_value
                updated_count += 1
            else:
                errors.append(f"Configuration not found: {config_key}")

        if errors:
            return {
                "success": False,
                "errors": errors,
                "updated_count": updated_count
            }

        db.commit()

        return {
            "success": True,
            "updated_count": updated_count,
            "message": f"Successfully updated {updated_count} configurations"
        }

    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": f"Failed to update configurations: {str(e)}"
        }


@router.put("/bulk-new", response_model=Dict[str, Any])
async def update_configurations_bulk_new(
    update_data: SystemConfigBulkUpdateRequestNew,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_admin())
):
    """Update multiple configurations at once - new version"""
    print(f"NEW ROUTE - Raw request received - Type: {type(update_data)}")
    print(f"NEW ROUTE - Received bulk update request: {update_data}")
    print(
        f"NEW ROUTE - Configurations count: {len(update_data.configurations)}")

    updated_count = 0
    errors = []

    try:
        for config_update in update_data.configurations:
            config_key = config_update.key
            config_value = config_update.value

            if not config_key:
                errors.append("Missing configuration key")
                continue

            # Validate configuration value
            if not SystemConfigManager.validate_configuration(config_key, config_value):
                errors.append(f"Invalid value for configuration: {config_key}")
                continue

            # Find and update configuration
            config = db.query(SystemConfiguration).filter(
                SystemConfiguration.key == config_key
            ).first()

            if config:
                config.value = config_value
                updated_count += 1
            else:
                errors.append(f"Configuration not found: {config_key}")

        if errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Some configurations failed to update", "errors": errors}
            )

        db.commit()

        return {
            "success": True,
            "updated_count": updated_count,
            "message": f"Successfully updated {updated_count} configurations"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configurations: {str(e)}"
        )


@router.put("/bulk", response_model=Dict[str, Any])
async def update_configurations_bulk(
    update_data: SystemConfigBulkUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_admin())
):
    """Update multiple configurations at once"""
    print(f"BULK ROUTE - Raw request received - Type: {type(update_data)}")
    print(f"BULK ROUTE - Received bulk update request: {update_data}")
    print(f"BULK ROUTE - Model dump: {update_data.model_dump()}")
    print(
        f"BULK ROUTE - Configurations count: {len(update_data.configurations)}")

    updated_count = 0
    errors = []

    try:
        for config_update in update_data.configurations:
            config_key = config_update.key
            config_value = config_update.value

            if not config_key:
                errors.append("Missing configuration key")
                continue

            # Validate configuration value
            if not SystemConfigManager.validate_configuration(config_key, config_value):
                errors.append(f"Invalid value for configuration: {config_key}")
                continue

            # Find and update configuration
            config = db.query(SystemConfiguration).filter(
                SystemConfiguration.key == config_key
            ).first()

            if config:
                config.value = config_value
                updated_count += 1
            else:
                errors.append(f"Configuration not found: {config_key}")

        if errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Some configurations failed to update", "errors": errors}
            )

        db.commit()

        return {
            "success": True,
            "updated_count": updated_count,
            "message": f"Successfully updated {updated_count} configurations"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configurations: {str(e)}"
        )


@router.put("/{config_id}", response_model=SystemConfigResponse)
async def update_configuration(
    config_id: str,
    config_data: SystemConfigUpdate,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_admin())
):
    """Update a system configuration"""
    config = db.query(SystemConfiguration).filter(
        SystemConfiguration.id == config_id).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )

    # Validate configuration value
    if not SystemConfigManager.validate_configuration(config.key, config_data.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid configuration value"
        )

    # Update configuration
    update_data = config_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    db.commit()
    db.refresh(config)

    return config


@router.put("/bulk-test-no-auth", response_model=Dict[str, Any])
async def test_bulk_update_route_no_auth(
    data: Dict[str, Any]
):
    """Test route without authentication to debug the bulk update issue"""
    print(f"Raw test data received (no auth): {data}")
    return {"success": True, "received": data}


@router.put("/bulk-test", response_model=Dict[str, Any])
async def test_bulk_update_route(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_admin())
):
    """Test route to debug the bulk update issue"""
    print(f"Raw test data received: {data}")
    return {"success": True, "received": data}


@router.get("/debug-test")
async def debug_test_route():
    """Simple test route to verify routing is working"""
    print("DEBUG: Simple test route called")
    return {"message": "Debug test successful", "timestamp": datetime.utcnow()}


@router.put("/bulk-raw", response_model=Dict[str, Any])
async def update_configurations_bulk_raw(
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_admin())
):
    """Update multiple configurations at once - raw JSON approach"""
    try:
        # Get raw JSON from request
        raw_data = await request.json()
        print(f"RAW ROUTE - Received data: {raw_data}")

        configurations = raw_data.get('configurations', [])
        print(f"RAW ROUTE - Configurations count: {len(configurations)}")

        updated_count = 0
        errors = []

        for config_update in configurations:
            config_key = config_update.get('key')
            config_value = config_update.get('value')

            if not config_key:
                errors.append("Missing configuration key")
                continue

            # Validate configuration value
            if not SystemConfigManager.validate_configuration(config_key, config_value):
                errors.append(f"Invalid value for configuration: {config_key}")
                continue

            # Find and update configuration
            config = db.query(SystemConfiguration).filter(
                SystemConfiguration.key == config_key
            ).first()

            if config:
                config.value = config_value
                updated_count += 1
            else:
                errors.append(f"Configuration not found: {config_key}")

        if errors:
            return {
                "success": False,
                "errors": errors,
                "updated_count": updated_count
            }

        db.commit()

        return {
            "success": True,
            "updated_count": updated_count,
            "message": f"Successfully updated {updated_count} configurations"
        }

    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": f"Failed to update configurations: {str(e)}"
        }


@router.put("/bulk-new", response_model=Dict[str, Any])
async def update_configurations_bulk_new(
    update_data: SystemConfigBulkUpdateRequestNew,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_admin())
):
    """Update multiple configurations at once - new version"""
    print(f"NEW ROUTE - Raw request received - Type: {type(update_data)}")
    print(f"NEW ROUTE - Received bulk update request: {update_data}")
    print(
        f"NEW ROUTE - Configurations count: {len(update_data.configurations)}")

    updated_count = 0
    errors = []

    try:
        for config_update in update_data.configurations:
            config_key = config_update.key
            config_value = config_update.value

            if not config_key:
                errors.append("Missing configuration key")
                continue

            # Validate configuration value
            if not SystemConfigManager.validate_configuration(config_key, config_value):
                errors.append(f"Invalid value for configuration: {config_key}")
                continue

            # Find and update configuration
            config = db.query(SystemConfiguration).filter(
                SystemConfiguration.key == config_key
            ).first()

            if config:
                config.value = config_value
                updated_count += 1
            else:
                errors.append(f"Configuration not found: {config_key}")

        if errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Some configurations failed to update", "errors": errors}
            )

        db.commit()

        return {
            "success": True,
            "updated_count": updated_count,
            "message": f"Successfully updated {updated_count} configurations"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configurations: {str(e)}"
        )


@router.put("/bulk", response_model=Dict[str, Any])
async def update_configurations_bulk(
    update_data: SystemConfigBulkUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_admin())
):
    """Update multiple configurations at once"""
    print(f"Raw request received - Type: {type(update_data)}")
    print(f"Received bulk update request: {update_data}")
    print(f"Model dump: {update_data.model_dump()}")
    print(f"Configurations count: {len(update_data.configurations)}")

    updated_count = 0
    errors = []

    try:
        for config_update in update_data.configurations:
            config_key = config_update.key
            config_value = config_update.value

            if not config_key:
                errors.append("Missing configuration key")
                continue

            # Validate configuration value
            if not SystemConfigManager.validate_configuration(config_key, config_value):
                errors.append(f"Invalid value for configuration: {config_key}")
                continue

            # Find and update configuration
            config = db.query(SystemConfiguration).filter(
                SystemConfiguration.key == config_key
            ).first()

            if config:
                config.value = config_value
                updated_count += 1
            else:
                errors.append(f"Configuration not found: {config_key}")

        if errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Some configurations failed to update", "errors": errors}
            )

        db.commit()

        return {
            "success": True,
            "updated_count": updated_count,
            "message": f"Successfully updated {updated_count} configurations"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configurations: {str(e)}"
        )


@router.get("/current", response_model=Dict[str, Any])
async def get_current_configuration(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_admin())
):
    """Get current effective configuration values"""
    configurations = db.query(SystemConfiguration).filter(
        SystemConfiguration.is_active == True
    ).all()

    current_config = {}
    for config in configurations:
        # Create nested structure like general.currency -> {general: {currency: "USD"}}
        key_parts = config.key.split('.')
        if len(key_parts) == 2:
            category, field = key_parts
            if category not in current_config:
                current_config[category] = {}
            current_config[category][field] = config.value
        else:
            current_config[config.key] = config.value

    return current_config


@router.get("/export", response_model=SystemConfigExportResponse)
async def export_configuration(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_admin())
):
    """Export all system configurations"""
    configurations = db.query(SystemConfiguration).filter(
        SystemConfiguration.is_active == True
    ).all()

    export_data = {}
    for config in configurations:
        export_data[config.key] = {
            "value": config.value,
            "category": config.category,
            "description": config.description
        }

    return {
        "export_date": datetime.utcnow(),
        "configurations": export_data,
        "metadata": {
            "version": "1.0",
            "total_configurations": len(configurations),
            "exported_by": current_user.email
        }
    }


@router.post("/validate", response_model=SystemConfigValidationResponse)
async def validate_configurations(
    configurations: List[Dict[str, Any]],
    current_user: UserProfile = Depends(require_admin())
):
    """Validate configuration values"""
    errors = []
    warnings = []

    for config in configurations:
        key = config.get("key")
        value = config.get("value")

        if not key:
            errors.append("Configuration key is required")
            continue

        if not SystemConfigManager.validate_configuration(key, value):
            errors.append(f"Invalid value for configuration: {key}")

        # Add specific warnings
        if key.endswith("_timeout_minutes") and isinstance(value, int) and value < 30:
            warnings.append(
                f"Short timeout value for {key} may cause user issues")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


@router.post("/initialize", response_model=Dict[str, Any])
async def initialize_default_configurations(
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_admin())
):
    """Initialize system with default configurations"""
    success = SystemConfigManager.initialize_default_configurations(db)

    if success:
        return {"success": True, "message": "Default configurations initialized successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize default configurations"
        )


@router.delete("/{config_id}")
async def delete_configuration(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(require_admin())
):
    """Delete a system configuration (soft delete)"""
    config = db.query(SystemConfiguration).filter(
        SystemConfiguration.id == config_id).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )

    # Soft delete by setting is_active to False
    config.is_active = False
    db.commit()

    return {"message": "Configuration deleted successfully"}
