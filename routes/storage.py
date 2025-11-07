"""
Storage configuration API routes.
"""

from fastapi import APIRouter, Depends
from core.storage_config import StorageConfig, get_storage_config
from core.auth import get_current_user
from models.user import UserProfile


router = APIRouter()


@router.get("/config", response_model=dict)
async def get_storage_configuration(
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Get current storage configuration.

    Returns storage backend type and basic configuration info
    (sensitive data like keys are not included).
    """
    config = get_storage_config()

    # Return safe configuration info
    return {
        "backend": config.backend.value,
        "max_file_size": config.max_file_size,
        "max_file_size_mb": round(config.max_file_size / (1024 * 1024), 2),
        "allowed_extensions": config.allowed_extensions,
        "azure_configured": bool(
            config.azure.connection_string or
            (config.azure.account_name and config.azure.account_key)
        ),
        "container_name": config.azure.container_name if config.backend.value == "azure_blob" else None
    }


@router.get("/health")
async def check_storage_health(
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Check storage backend health and connectivity.
    """
    from services.file_storage_factory import get_file_storage_service

    try:
        storage_service = get_file_storage_service()
        config = get_storage_config()

        # Basic connectivity test
        if config.backend.value == "azure_blob":
            # For Azure, try to check if we can access the service
            # This is a simple test - you might want to make it more comprehensive
            return {
                "status": "healthy",
                "backend": config.backend.value,
                "message": "Azure Blob Storage service initialized successfully"
            }
        else:
            # For local storage, check if directory exists and is writable
            import os
            base_path = config.local.base_path

            if not os.path.exists(base_path):
                os.makedirs(base_path, exist_ok=True)

            if os.access(base_path, os.W_OK):
                return {
                    "status": "healthy",
                    "backend": config.backend.value,
                    "message": f"Local storage directory '{base_path}' is accessible"
                }
            else:
                return {
                    "status": "error",
                    "backend": config.backend.value,
                    "message": f"Local storage directory '{base_path}' is not writable"
                }

    except Exception as e:
        return {
            "status": "error",
            "backend": config.backend.value if 'config' in locals() else "unknown",
            "message": f"Storage backend error: {str(e)}"
        }
