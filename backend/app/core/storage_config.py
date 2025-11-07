"""
Storage configuration management for the CRM application.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class StorageBackend(str, Enum):
    """Available storage backend options."""
    LOCAL = "local"
    AZURE_BLOB = "azure_blob"


class AzureConfig(BaseModel):
    """Azure Blob Storage configuration."""
    account_name: Optional[str] = Field(
        None, description="Azure storage account name")
    account_key: Optional[str] = Field(
        None, description="Azure storage account key")
    connection_string: Optional[str] = Field(
        None, description="Azure storage connection string")
    container_name: str = Field(
        "crm-files", description="Azure blob container name")


class LocalConfig(BaseModel):
    """Local storage configuration."""
    base_path: str = Field(
        "uploads", description="Base directory for local storage")


class StorageConfig(BaseModel):
    """Storage configuration settings."""
    backend: StorageBackend = Field(
        StorageBackend.LOCAL, description="Storage backend to use")
    max_file_size: int = Field(
        10 * 1024 * 1024, description="Maximum file size in bytes (default 10MB)")
    allowed_extensions: list = Field(
        default=[
            ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
            ".jpg", ".jpeg", ".png", ".gif", ".txt", ".zip", ".rar", ".csv"
        ],
        description="Allowed file extensions"
    )
    azure: AzureConfig = Field(default_factory=AzureConfig)
    local: LocalConfig = Field(default_factory=LocalConfig)


# Default storage configuration
DEFAULT_STORAGE_CONFIG = StorageConfig()


def get_storage_config() -> StorageConfig:
    """Get the current storage configuration."""
    import os

    config = StorageConfig()

    # Override with environment variables
    storage_backend = os.getenv("STORAGE_BACKEND", "local")
    if storage_backend == "azure_blob":
        config.backend = StorageBackend.AZURE_BLOB
    else:
        config.backend = StorageBackend.LOCAL

    # Azure configuration
    config.azure.account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
    config.azure.account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
    config.azure.connection_string = os.getenv(
        "AZURE_STORAGE_CONNECTION_STRING")
    config.azure.container_name = os.getenv(
        "AZURE_BLOB_CONTAINER_NAME", "crm-files")

    # Local configuration
    config.local.base_path = os.getenv("LOCAL_STORAGE_PATH", "uploads")

    return config
